"""
Lambda Service - AWS Lambda Invocation

Handles AWS Lambda function invocations with async support
"""

import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from pydal import DAL

from config import Config

logger = logging.getLogger(__name__)


class LambdaService:
    """Service for AWS Lambda operations"""

    def __init__(self, db: DAL):
        """
        Initialize Lambda service

        Args:
            db: PyDAL database instance
        """
        self.db = db
        self._lambda_client = None
        self._setup_tables()
        logger.info("Lambda service initialized")

    def _get_client(self):
        """Get or create Lambda client"""
        if self._lambda_client is None:
            self._lambda_client = boto3.client(
                'lambda',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
        return self._lambda_client

    def _setup_tables(self):
        """Setup database tables for Lambda invocations"""
        self.db.define_table(
            'lambda_invocations',
            self.db.Field('function_name', 'string', required=True),
            self.db.Field('invocation_type', 'string', required=True),
            self.db.Field('payload', 'text'),
            self.db.Field('alias', 'string'),
            self.db.Field('version', 'string'),
            self.db.Field('status_code', 'integer'),
            self.db.Field('response_payload', 'text'),
            self.db.Field('function_error', 'string'),
            self.db.Field('executed_version', 'string'),
            self.db.Field('request_id', 'string'),
            self.db.Field('success', 'boolean'),
            self.db.Field('error_message', 'text'),
            self.db.Field('invoked_at', 'datetime', default=datetime.utcnow),
            self.db.Field('completed_at', 'datetime'),
            migrate=False  # Don't try to migrate - table already exists
        )
        logger.info("Lambda invocations table setup complete")

    async def invoke_function(
        self,
        function_name: str,
        payload: str,
        invocation_type: str = 'RequestResponse',
        alias: Optional[str] = None,
        version: Optional[str] = None
    ) -> tuple[bool, int, str, str, str, str]:
        """
        Invoke Lambda function

        Args:
            function_name: Name of Lambda function
            payload: JSON payload string
            invocation_type: RequestResponse, Event, or DryRun
            alias: Function alias to invoke
            version: Function version to invoke

        Returns:
            Tuple of (success, status_code, response_payload, function_error,
                     log_result, executed_version)
        """
        try:
            logger.info(f"Invoking Lambda function: {function_name}")

            # Build function qualifier
            qualifier = None
            if alias:
                qualifier = alias
            elif version:
                qualifier = version

            # Run boto3 call in executor for async compatibility
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._invoke_lambda,
                function_name,
                payload,
                invocation_type,
                qualifier
            )

            # Extract response data
            status_code = response.get('StatusCode', 0)
            response_payload = response.get('Payload').read().decode('utf-8') if 'Payload' in response else ''
            function_error = response.get('FunctionError', '')
            log_result = response.get('LogResult', '')
            executed_version = response.get('ExecutedVersion', '')

            # Decode log result if present
            if log_result:
                try:
                    log_result = base64.b64decode(log_result).decode('utf-8')
                except Exception as e:
                    logger.warning(f"Failed to decode log result: {e}")

            # Log invocation to database
            self.db.lambda_invocations.insert(
                function_name=function_name,
                invocation_type=invocation_type,
                payload=payload,
                alias=alias,
                version=version,
                status_code=status_code,
                response_payload=response_payload,
                function_error=function_error,
                executed_version=executed_version,
                success=status_code == 200 and not function_error,
                completed_at=datetime.utcnow()
            )
            self.db.commit()

            success = status_code == 200 and not function_error
            logger.info(f"Lambda invocation completed: {function_name}, success={success}")

            return success, status_code, response_payload, function_error, log_result, executed_version

        except ClientError as e:
            error_msg = str(e)
            logger.error(f"AWS Lambda client error: {error_msg}")

            # Log failed invocation
            self.db.lambda_invocations.insert(
                function_name=function_name,
                invocation_type=invocation_type,
                payload=payload,
                alias=alias,
                version=version,
                success=False,
                error_message=error_msg,
                completed_at=datetime.utcnow()
            )
            self.db.commit()

            return False, 0, '', '', '', error_msg

        except Exception as e:
            error_msg = f"Lambda invocation error: {str(e)}"
            logger.error(error_msg)

            # Log failed invocation
            self.db.lambda_invocations.insert(
                function_name=function_name,
                invocation_type=invocation_type,
                payload=payload,
                alias=alias,
                version=version,
                success=False,
                error_message=error_msg,
                completed_at=datetime.utcnow()
            )
            self.db.commit()

            return False, 0, '', '', '', error_msg

    def _invoke_lambda(
        self,
        function_name: str,
        payload: str,
        invocation_type: str,
        qualifier: Optional[str]
    ):
        """
        Synchronous Lambda invocation (runs in executor)

        Args:
            function_name: Lambda function name
            payload: JSON payload
            invocation_type: Invocation type
            qualifier: Version or alias qualifier

        Returns:
            Lambda response
        """
        client = self._get_client()

        invoke_params = {
            'FunctionName': function_name,
            'InvocationType': invocation_type,
            'Payload': payload.encode('utf-8'),
            'LogType': 'Tail'
        }

        if qualifier:
            invoke_params['Qualifier'] = qualifier

        return client.invoke(**invoke_params)

    async def invoke_async(
        self,
        function_name: str,
        payload: str
    ) -> tuple[bool, int, str]:
        """
        Invoke Lambda function asynchronously (Event invocation type)

        Args:
            function_name: Name of Lambda function
            payload: JSON payload string

        Returns:
            Tuple of (success, status_code, request_id)
        """
        try:
            logger.info(f"Invoking Lambda function asynchronously: {function_name}")

            # Use Event invocation type for async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._invoke_lambda,
                function_name,
                payload,
                'Event',
                None
            )

            status_code = response.get('StatusCode', 0)
            request_id = response.get('ResponseMetadata', {}).get('RequestId', '')

            # Log async invocation
            self.db.lambda_invocations.insert(
                function_name=function_name,
                invocation_type='Event',
                payload=payload,
                status_code=status_code,
                request_id=request_id,
                success=status_code == 202,
                completed_at=datetime.utcnow()
            )
            self.db.commit()

            success = status_code == 202
            logger.info(f"Lambda async invocation completed: {function_name}, success={success}")

            return success, status_code, request_id

        except Exception as e:
            error_msg = f"Lambda async invocation error: {str(e)}"
            logger.error(error_msg)
            return False, 0, error_msg

    async def invoke_with_alias(
        self,
        function_name: str,
        alias: str,
        payload: str
    ) -> tuple[bool, int, str, str, str, str]:
        """
        Invoke Lambda function with specific alias

        Args:
            function_name: Name of Lambda function
            alias: Function alias
            payload: JSON payload string

        Returns:
            Same as invoke_function
        """
        return await self.invoke_function(function_name, payload, 'RequestResponse', alias=alias)

    async def invoke_with_version(
        self,
        function_name: str,
        version: str,
        payload: str
    ) -> tuple[bool, int, str, str, str, str]:
        """
        Invoke Lambda function with specific version

        Args:
            function_name: Name of Lambda function
            version: Function version
            payload: JSON payload string

        Returns:
            Same as invoke_function
        """
        return await self.invoke_function(function_name, payload, 'RequestResponse', version=version)

    async def list_functions(
        self,
        max_items: int = 50,
        next_marker: Optional[str] = None
    ) -> tuple[bool, list[dict], str]:
        """
        List Lambda functions

        Args:
            max_items: Maximum number of functions to return
            next_marker: Pagination marker

        Returns:
            Tuple of (success, functions_list, next_marker)
        """
        try:
            logger.info("Listing Lambda functions")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._list_functions,
                max_items,
                next_marker
            )

            functions = []
            for func in response.get('Functions', []):
                functions.append({
                    'function_name': func.get('FunctionName', ''),
                    'function_arn': func.get('FunctionArn', ''),
                    'runtime': func.get('Runtime', ''),
                    'role': func.get('Role', ''),
                    'handler': func.get('Handler', ''),
                    'code_size': func.get('CodeSize', 0),
                    'description': func.get('Description', ''),
                    'timeout': func.get('Timeout', 0),
                    'memory_size': func.get('MemorySize', 0),
                    'last_modified': func.get('LastModified', ''),
                    'version': func.get('Version', ''),
                })

            next_marker = response.get('NextMarker', '')
            logger.info(f"Listed {len(functions)} Lambda functions")

            return True, functions, next_marker

        except Exception as e:
            error_msg = f"Error listing Lambda functions: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg

    def _list_functions(
        self,
        max_items: int,
        next_marker: Optional[str]
    ):
        """
        Synchronous list functions (runs in executor)

        Args:
            max_items: Maximum items to return
            next_marker: Pagination marker

        Returns:
            Lambda response
        """
        client = self._get_client()

        list_params = {
            'MaxItems': max_items
        }

        if next_marker:
            list_params['Marker'] = next_marker

        return client.list_functions(**list_params)

    async def get_function_config(
        self,
        function_name: str
    ) -> tuple[bool, Optional[dict]]:
        """
        Get Lambda function configuration

        Args:
            function_name: Name of Lambda function

        Returns:
            Tuple of (success, function_config)
        """
        try:
            logger.info(f"Getting Lambda function config: {function_name}")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._get_function_config,
                function_name
            )

            config = {
                'function_name': response.get('FunctionName', ''),
                'function_arn': response.get('FunctionArn', ''),
                'runtime': response.get('Runtime', ''),
                'role': response.get('Role', ''),
                'handler': response.get('Handler', ''),
                'code_size': response.get('CodeSize', 0),
                'description': response.get('Description', ''),
                'timeout': response.get('Timeout', 0),
                'memory_size': response.get('MemorySize', 0),
                'last_modified': response.get('LastModified', ''),
                'version': response.get('Version', ''),
            }

            logger.info(f"Retrieved function config: {function_name}")
            return True, config

        except Exception as e:
            error_msg = f"Error getting function config: {str(e)}"
            logger.error(error_msg)
            return False, None

    def _get_function_config(self, function_name: str):
        """
        Synchronous get function config (runs in executor)

        Args:
            function_name: Lambda function name

        Returns:
            Lambda response
        """
        client = self._get_client()
        return client.get_function_configuration(FunctionName=function_name)

    async def close(self):
        """Close Lambda service resources"""
        logger.info("Closing Lambda service")
        if self._lambda_client:
            # boto3 clients don't need explicit closing
            self._lambda_client = None
