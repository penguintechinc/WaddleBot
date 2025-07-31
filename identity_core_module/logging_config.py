"""
Comprehensive AAA Logging Configuration for WaddleBot Identity Core Module
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from functools import wraps
import time
import traceback
from .config import Config

# Create log directory if it doesn't exist
os.makedirs(Config.LOG_DIR, exist_ok=True)

def setup_logging():
    """Setup comprehensive logging with console, file, and optional syslog output"""
    
    logger = logging.getLogger(Config.MODULE_NAME)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    logger.handlers = []
    
    # Custom formatter with structured output
    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            # Base format
            timestamp = datetime.utcnow().isoformat()
            level = record.levelname
            module = f"{Config.MODULE_NAME}:{Config.MODULE_VERSION}"
            
            # Extract custom fields
            event_type = getattr(record, 'event_type', 'SYSTEM')
            user_id = getattr(record, 'user_id', '')
            platform = getattr(record, 'platform', '')
            action = getattr(record, 'action', '')
            result = getattr(record, 'result', '')
            execution_time = getattr(record, 'execution_time', '')
            
            # Build structured log
            log_entry = f"[{timestamp}] {level} {module} {event_type}"
            
            if user_id:
                log_entry += f" user={user_id}"
            if platform:
                log_entry += f" platform={platform}"
            if action:
                log_entry += f" action={action}"
            if result:
                log_entry += f" result={result}"
            if execution_time:
                log_entry += f" execution_time={execution_time}ms"
            
            # Add message
            log_entry += f" {record.getMessage()}"
            
            # Add exception info if present
            if record.exc_info:
                log_entry += f"\n{self.formatException(record.exc_info)}"
            
            return log_entry
    
    formatter = StructuredFormatter()
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(Config.LOG_DIR, f'{Config.MODULE_NAME}.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Syslog Handler (optional)
    if Config.ENABLE_SYSLOG:
        try:
            syslog_handler = logging.handlers.SysLogHandler(
                address=(Config.SYSLOG_HOST, Config.SYSLOG_PORT),
                facility=getattr(logging.handlers.SysLogHandler, f'LOG_{Config.SYSLOG_FACILITY}')
            )
            syslog_handler.setFormatter(formatter)
            logger.addHandler(syslog_handler)
        except Exception as e:
            logger.error(f"Failed to setup syslog handler: {e}")
    
    return logger

def log_event(event_type, category, **kwargs):
    """
    Log structured events for AAA compliance
    
    Event Types:
    - AUTH: Authentication events
    - AUTHZ: Authorization events  
    - AUDIT: User actions and changes
    - ERROR: Error conditions
    - SYSTEM: System events
    """
    logger = logging.getLogger(Config.MODULE_NAME)
    
    # Build extra fields
    extra = {
        'event_type': event_type,
        'category': category
    }
    extra.update(kwargs)
    
    # Determine log level
    if event_type == 'ERROR':
        level = logging.ERROR
    elif event_type in ['AUTH', 'AUTHZ', 'AUDIT']:
        level = logging.INFO
    else:
        level = logging.DEBUG
    
    # Log the event
    logger.log(level, f"{category} event", extra=extra)

def audit_action(action_name):
    """Decorator for automatic audit logging of user actions"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            start_time = time.time()
            user_id = None
            platform = None
            result = "success"
            error_msg = None
            
            try:
                # Try to extract user context
                from py4web import request, auth
                if hasattr(auth, 'user_id'):
                    user_id = auth.user_id
                elif hasattr(request, 'waddlebot_user_id'):
                    user_id = request.waddlebot_user_id
                
                # Extract platform if available
                if hasattr(request, 'json') and request.json:
                    platform = request.json.get('platform')
                
                # Execute function
                response = f(*args, **kwargs)
                
                return response
                
            except Exception as e:
                result = "error"
                error_msg = str(e)
                raise
                
            finally:
                # Calculate execution time
                execution_time = int((time.time() - start_time) * 1000)
                
                # Log audit event
                log_event(
                    "AUDIT",
                    action_name,
                    user_id=user_id,
                    platform=platform,
                    action=action_name,
                    result=result,
                    execution_time=execution_time,
                    error=error_msg
                )
        
        return wrapped
    return decorator

def log_authentication(username, success, method="password", details=None):
    """Log authentication attempts"""
    log_event(
        "AUTH",
        "LOGIN",
        user=username,
        action="login_attempt",
        result="success" if success else "failed",
        method=method,
        details=details or {}
    )

def log_authorization(user_id, resource, permission, granted, details=None):
    """Log authorization decisions"""
    log_event(
        "AUTHZ",
        "PERMISSION",
        user_id=user_id,
        resource=resource,
        permission=permission,
        action="permission_check",
        result="granted" if granted else "denied",
        details=details or {}
    )

def log_api_key_usage(api_key_id, user_id, endpoint, success=True):
    """Log API key usage"""
    log_event(
        "AUTH",
        "API_KEY",
        user_id=user_id,
        api_key_id=api_key_id,
        endpoint=endpoint,
        action="api_key_used",
        result="success" if success else "failed"
    )

def log_identity_operation(user_id, operation, platform, success, details=None):
    """Log identity linking operations"""
    log_event(
        "AUDIT",
        "IDENTITY",
        user_id=user_id,
        platform=platform,
        action=operation,
        result="success" if success else "failed",
        details=details or {}
    )

def log_system_event(event, details=None):
    """Log system-level events"""
    log_event(
        "SYSTEM",
        event.upper(),
        action=event,
        details=details or {}
    )

# Create audit logger instance
audit_logger = setup_logging()