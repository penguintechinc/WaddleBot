"""
Workflow API Controller
=======================

REST API for workflow management with:
- CRUD operations (create, read, update, delete, list)
- Publish and validate endpoints
- Authentication and authorization middleware
- Error handling with proper HTTP status codes
- Pagination support
- Comprehensive logging

Endpoints:
- POST   /api/v1/workflows           - Create workflow
- GET    /api/v1/workflows           - List workflows
- GET    /api/v1/workflows/:id       - Get workflow
- PUT    /api/v1/workflows/:id       - Update workflow
- DELETE /api/v1/workflows/:id       - Delete (archive) workflow
- POST   /api/v1/workflows/:id/publish  - Publish workflow
- POST   /api/v1/workflows/:id/validate - Validate workflow
"""

import logging
from quart import Blueprint, request, current_app
from functools import wraps
from typing import Callable

from flask_core import (
    success_response,
    error_response,
    paginate_response,
    async_endpoint,
    auth_required,
)
from services.workflow_service import (
    WorkflowService,
    WorkflowServiceException,
    WorkflowNotFoundException,
    WorkflowPermissionException,
)
from services.license_service import LicenseValidationException


logger = logging.getLogger(__name__)


# Create blueprint
workflow_api = Blueprint('workflow_api', __name__, url_prefix='/api/v1/workflows')


def get_workflow_service() -> WorkflowService:
    """Get workflow service from app context."""
    return current_app.config.get('workflow_service')


def handle_workflow_errors(f: Callable) -> Callable:
    """
    Decorator to handle workflow-specific exceptions.

    Converts workflow exceptions to appropriate HTTP responses.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except LicenseValidationException as e:
            # HTTP 402 Payment Required for license failures
            logger.warning(
                f"License validation failed: {e.message}",
                extra={
                    "event_type": "AUTHZ",
                    "action": f.__name__,
                    "community": str(e.community_id),
                    "result": "PAYMENT_REQUIRED"
                }
            )
            return error_response(
                message=e.message,
                status_code=402,
                error_code="PAYMENT_REQUIRED",
                details={"community_id": e.community_id}
            )
        except WorkflowNotFoundException as e:
            return error_response(
                message=e.message,
                status_code=404,
                error_code="WORKFLOW_NOT_FOUND"
            )
        except WorkflowPermissionException as e:
            return error_response(
                message=e.message,
                status_code=403,
                error_code="PERMISSION_DENIED"
            )
        except WorkflowServiceException as e:
            return error_response(
                message=e.message,
                status_code=e.status_code,
                error_code="WORKFLOW_ERROR"
            )
        except ValueError as e:
            # Client errors (bad input)
            return error_response(
                message=str(e),
                status_code=400,
                error_code="BAD_REQUEST"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error in {f.__name__}: {str(e)}",
                extra={
                    "event_type": "ERROR",
                    "action": f.__name__,
                    "result": "FAILURE"
                },
                exc_info=True
            )
            return error_response(
                message="Internal server error",
                status_code=500,
                error_code="INTERNAL_ERROR"
            )

    return decorated_function


# ============================================================================
# POST /api/v1/workflows - Create workflow
# ============================================================================

@workflow_api.route('', methods=['POST'])
@async_endpoint
@auth_required
@handle_workflow_errors
async def create_workflow():
    """
    Create a new workflow.

    Request Body:
    {
        "name": "Workflow Name",
        "description": "Description",
        "nodes": {},
        "connections": [],
        "trigger_type": "command",
        "trigger_config": {},
        "global_variables": {}
    }

    Returns:
        201: Created workflow
        400: Invalid input
        401: Unauthorized
        402: Payment Required (license validation failed)
        500: Server error
    """
    user_info = request.current_user
    user_id = int(user_info['user_id'])

    data = await request.get_json()

    # Validate required fields
    if not data:
        raise ValueError("Request body is required")

    if 'name' not in data:
        raise ValueError("Field 'name' is required")

    if 'entity_id' not in data:
        raise ValueError("Field 'entity_id' is required")

    if 'community_id' not in data:
        raise ValueError("Field 'community_id' is required")

    entity_id = int(data['entity_id'])
    community_id = int(data['community_id'])

    # Get license key if provided
    license_key = data.get('license_key')

    # Create workflow
    workflow_service = get_workflow_service()
    workflow = await workflow_service.create_workflow(
        workflow_data=data,
        community_id=community_id,
        entity_id=entity_id,
        user_id=user_id,
        license_key=license_key
    )

    return success_response(
        data=workflow,
        status_code=201,
        message="Workflow created successfully"
    )


# ============================================================================
# GET /api/v1/workflows - List workflows
# ============================================================================

@workflow_api.route('', methods=['GET'])
@async_endpoint
@auth_required
@handle_workflow_errors
async def list_workflows():
    """
    List accessible workflows with pagination and filters.

    Query Parameters:
        entity_id (required): Entity ID
        community_id: Community ID
        status: Filter by status (draft, active, archived)
        search: Search in name/description
        page: Page number (default: 1)
        per_page: Items per page (default: 20)

    Returns:
        200: Paginated list of workflows
        400: Invalid parameters
        401: Unauthorized
        500: Server error
    """
    user_info = request.current_user
    user_id = int(user_info['user_id'])

    # Get query parameters
    entity_id = request.args.get('entity_id')
    if not entity_id:
        raise ValueError("Query parameter 'entity_id' is required")

    entity_id = int(entity_id)

    # Optional filters
    community_id = request.args.get('community_id')
    community_id = int(community_id) if community_id else None

    status = request.args.get('status')
    search = request.args.get('search')

    # Pagination
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        raise ValueError("Invalid pagination parameters")

    if page < 1:
        raise ValueError("Page must be >= 1")

    if per_page < 1 or per_page > 100:
        raise ValueError("Per page must be between 1 and 100")

    # Build filters
    filters = {}
    if status:
        filters['status'] = status
    if search:
        filters['search'] = search

    # List workflows
    workflow_service = get_workflow_service()
    result = await workflow_service.list_workflows(
        entity_id=entity_id,
        user_id=user_id,
        filters=filters,
        page=page,
        per_page=per_page,
        community_id=community_id
    )

    # Return with pagination metadata
    return success_response(
        data=result['workflows'],
        meta={
            "pagination": {
                "page": result['page'],
                "per_page": result['per_page'],
                "total": result['total'],
                "total_pages": result['total_pages'],
                "has_next": result['page'] < result['total_pages'],
                "has_prev": result['page'] > 1,
            }
        }
    )


# ============================================================================
# GET /api/v1/workflows/:id - Get workflow
# ============================================================================

@workflow_api.route('/<workflow_id>', methods=['GET'])
@async_endpoint
@auth_required
@handle_workflow_errors
async def get_workflow(workflow_id: str):
    """
    Get workflow by ID.

    Path Parameters:
        workflow_id: Workflow UUID

    Query Parameters:
        community_id: Optional community ID for context

    Returns:
        200: Workflow data
        401: Unauthorized
        403: Permission denied
        404: Workflow not found
        500: Server error
    """
    user_info = request.current_user
    user_id = int(user_info['user_id'])

    community_id = request.args.get('community_id')
    community_id = int(community_id) if community_id else None

    workflow_service = get_workflow_service()
    workflow = await workflow_service.get_workflow(
        workflow_id=workflow_id,
        user_id=user_id,
        community_id=community_id
    )

    return success_response(data=workflow)


# ============================================================================
# PUT /api/v1/workflows/:id - Update workflow
# ============================================================================

@workflow_api.route('/<workflow_id>', methods=['PUT'])
@async_endpoint
@auth_required
@handle_workflow_errors
async def update_workflow(workflow_id: str):
    """
    Update workflow.

    Path Parameters:
        workflow_id: Workflow UUID

    Request Body:
    {
        "name": "Updated Name",
        "description": "Updated Description",
        "nodes": {},
        "connections": [],
        ... other updateable fields
    }

    Returns:
        200: Updated workflow
        400: Invalid input
        401: Unauthorized
        403: Permission denied
        404: Workflow not found
        500: Server error
    """
    user_info = request.current_user
    user_id = int(user_info['user_id'])

    data = await request.get_json()

    if not data:
        raise ValueError("Request body is required")

    community_id = data.get('community_id')
    community_id = int(community_id) if community_id else None

    workflow_service = get_workflow_service()
    workflow = await workflow_service.update_workflow(
        workflow_id=workflow_id,
        updates=data,
        user_id=user_id,
        community_id=community_id
    )

    return success_response(
        data=workflow,
        message="Workflow updated successfully"
    )


# ============================================================================
# DELETE /api/v1/workflows/:id - Delete (archive) workflow
# ============================================================================

@workflow_api.route('/<workflow_id>', methods=['DELETE'])
@async_endpoint
@auth_required
@handle_workflow_errors
async def delete_workflow(workflow_id: str):
    """
    Delete (archive) workflow.

    Path Parameters:
        workflow_id: Workflow UUID

    Query Parameters:
        community_id: Optional community ID for context

    Returns:
        200: Workflow archived
        401: Unauthorized
        403: Permission denied
        404: Workflow not found
        500: Server error
    """
    user_info = request.current_user
    user_id = int(user_info['user_id'])

    community_id = request.args.get('community_id')
    community_id = int(community_id) if community_id else None

    workflow_service = get_workflow_service()
    result = await workflow_service.delete_workflow(
        workflow_id=workflow_id,
        user_id=user_id,
        community_id=community_id
    )

    return success_response(
        data=result,
        message="Workflow archived successfully"
    )


# ============================================================================
# POST /api/v1/workflows/:id/publish - Publish workflow
# ============================================================================

@workflow_api.route('/<workflow_id>/publish', methods=['POST'])
@async_endpoint
@auth_required
@handle_workflow_errors
async def publish_workflow(workflow_id: str):
    """
    Publish and activate workflow after validation.

    Path Parameters:
        workflow_id: Workflow UUID

    Request Body (optional):
    {
        "community_id": 123
    }

    Returns:
        200: Workflow published
        400: Validation failed
        401: Unauthorized
        403: Permission denied
        404: Workflow not found
        500: Server error
    """
    user_info = request.current_user
    user_id = int(user_info['user_id'])

    data = await request.get_json() or {}

    community_id = data.get('community_id')
    community_id = int(community_id) if community_id else None

    workflow_service = get_workflow_service()
    workflow = await workflow_service.publish_workflow(
        workflow_id=workflow_id,
        user_id=user_id,
        community_id=community_id
    )

    return success_response(
        data=workflow,
        message="Workflow published successfully"
    )


# ============================================================================
# POST /api/v1/workflows/:id/validate - Validate workflow
# ============================================================================

@workflow_api.route('/<workflow_id>/validate', methods=['POST'])
@async_endpoint
@auth_required
@handle_workflow_errors
async def validate_workflow(workflow_id: str):
    """
    Validate workflow structure and configuration.

    Path Parameters:
        workflow_id: Workflow UUID

    Returns:
        200: Validation result
        401: Unauthorized
        404: Workflow not found
        500: Server error

    Response:
    {
        "success": true,
        "data": {
            "is_valid": true,
            "errors": [],
            "warnings": [],
            "node_validation_errors": {},
            "error_count": 0,
            "warning_count": 0
        }
    }
    """
    user_info = request.current_user
    user_id = int(user_info['user_id'])

    workflow_service = get_workflow_service()
    validation_result = await workflow_service.validate_workflow(
        workflow_id=workflow_id
    )

    return success_response(
        data=validation_result,
        message="Validation completed"
    )


# ============================================================================
# Error Handlers
# ============================================================================

@workflow_api.errorhandler(400)
async def bad_request(error):
    """Handle 400 Bad Request errors."""
    return error_response(
        message=str(error),
        status_code=400,
        error_code="BAD_REQUEST"
    )


@workflow_api.errorhandler(401)
async def unauthorized(error):
    """Handle 401 Unauthorized errors."""
    return error_response(
        message="Authentication required",
        status_code=401,
        error_code="UNAUTHORIZED"
    )


@workflow_api.errorhandler(403)
async def forbidden(error):
    """Handle 403 Forbidden errors."""
    return error_response(
        message="Permission denied",
        status_code=403,
        error_code="FORBIDDEN"
    )


@workflow_api.errorhandler(404)
async def not_found(error):
    """Handle 404 Not Found errors."""
    return error_response(
        message="Resource not found",
        status_code=404,
        error_code="NOT_FOUND"
    )


@workflow_api.errorhandler(500)
async def internal_error(error):
    """Handle 500 Internal Server Error."""
    logger.error(f"Internal server error: {str(error)}", exc_info=True)
    return error_response(
        message="Internal server error",
        status_code=500,
        error_code="INTERNAL_ERROR"
    )


# ============================================================================
# Blueprint registration helper
# ============================================================================

def register_workflow_api(app, workflow_service: WorkflowService):
    """
    Register workflow API blueprint with app.

    Args:
        app: Quart application instance
        workflow_service: Configured WorkflowService instance
    """
    # Store workflow service in app config
    app.config['workflow_service'] = workflow_service

    # Register blueprint
    app.register_blueprint(workflow_api)

    logger.info(
        "Workflow API registered",
        extra={
            "event_type": "SYSTEM",
            "action": "register_workflow_api",
            "result": "SUCCESS"
        }
    )
