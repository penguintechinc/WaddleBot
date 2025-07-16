"""
Comprehensive logging configuration for WaddleBot Inventory Module
Handles Authentication, Authorization, and Auditing logs
"""

import os
import sys
import logging
import logging.handlers
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# Configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.environ.get("LOG_DIR", "/var/log/waddlebotlog")
ENABLE_SYSLOG = os.environ.get("ENABLE_SYSLOG", "false").lower() == "true"
SYSLOG_HOST = os.environ.get("SYSLOG_HOST", "localhost")
SYSLOG_PORT = int(os.environ.get("SYSLOG_PORT", "514"))
SYSLOG_FACILITY = getattr(logging.handlers.SysLogHandler, 
                         f"LOG_{os.environ.get('SYSLOG_FACILITY', 'LOCAL0')}")

# Module information
MODULE_NAME = "inventory_interaction_module"
MODULE_VERSION = "1.0.0"

@dataclass
class LogEvent:
    """Structured log event for WaddleBot"""
    timestamp: str
    level: str
    module: str
    version: str
    event_type: str  # AUTH, AUTHZ, AUDIT, SYSTEM, ERROR
    community_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    result: Optional[str] = None  # SUCCESS, FAILURE, DENIED
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_log_string(self) -> str:
        """Convert to structured log string"""
        base = (f"[{self.timestamp}] {self.level} {self.module}:{self.version} "
               f"{self.event_type}")
        
        if self.community_id:
            base += f" community={self.community_id}"
        if self.user_id:
            base += f" user={self.user_id}"
        if self.session_id:
            base += f" session={self.session_id}"
        if self.action:
            base += f" action={self.action}"
        if self.resource:
            base += f" resource={self.resource}"
        if self.result:
            base += f" result={self.result}"
        if self.duration_ms:
            base += f" duration={self.duration_ms}ms"
        if self.ip_address:
            base += f" ip={self.ip_address}"
        if self.error_message:
            base += f" error='{self.error_message}'"
        
        if self.details:
            details_str = " ".join([f"{k}={v}" for k, v in self.details.items()])
            base += f" {details_str}"
        
        return base

class WaddleBotLogger:
    """Comprehensive logging system for WaddleBot modules"""
    
    def __init__(self, module_name: str = MODULE_NAME, module_version: str = MODULE_VERSION):
        self.module_name = module_name
        self.module_version = module_version
        self.logger = logging.getLogger(f"waddlebot.{module_name}")
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        self.logger.setLevel(getattr(logging, LOG_LEVEL))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        json_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, LOG_LEVEL))
        console_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        self.setup_file_logging()
        
        # Syslog handler (if enabled)
        if ENABLE_SYSLOG:
            self.setup_syslog_logging()
    
    def setup_file_logging(self):
        """Setup file logging to /var/log/waddlebotlog"""
        try:
            # Create log directory if it doesn't exist
            log_dir = Path(LOG_DIR)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Main application log
            app_log_file = log_dir / f"{self.module_name}.log"
            app_handler = logging.handlers.RotatingFileHandler(
                app_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            app_handler.setLevel(getattr(logging, LOG_LEVEL))
            app_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(app_handler)
            
            # Authentication log
            auth_log_file = log_dir / f"{self.module_name}_auth.log"
            self.auth_handler = logging.handlers.RotatingFileHandler(
                auth_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            self.auth_handler.setLevel(logging.INFO)
            self.auth_handler.setFormatter(logging.Formatter(
                '%(asctime)s - AUTH - %(message)s'
            ))
            
            # Authorization log
            authz_log_file = log_dir / f"{self.module_name}_authz.log"
            self.authz_handler = logging.handlers.RotatingFileHandler(
                authz_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            self.authz_handler.setLevel(logging.INFO)
            self.authz_handler.setFormatter(logging.Formatter(
                '%(asctime)s - AUTHZ - %(message)s'
            ))
            
            # Audit log
            audit_log_file = log_dir / f"{self.module_name}_audit.log"
            self.audit_handler = logging.handlers.RotatingFileHandler(
                audit_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            self.audit_handler.setLevel(logging.INFO)
            self.audit_handler.setFormatter(logging.Formatter(
                '%(asctime)s - AUDIT - %(message)s'
            ))
            
            # Error log
            error_log_file = log_dir / f"{self.module_name}_error.log"
            self.error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            self.error_handler.setLevel(logging.ERROR)
            self.error_handler.setFormatter(logging.Formatter(
                '%(asctime)s - ERROR - %(message)s'
            ))
            
            # Add error handler to main logger
            self.logger.addHandler(self.error_handler)
            
        except Exception as e:
            # Fallback to console only if file logging fails
            self.logger.error(f"Failed to setup file logging: {e}")
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.ERROR)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(console_handler)
    
    def setup_syslog_logging(self):
        """Setup syslog logging"""
        try:
            syslog_handler = logging.handlers.SysLogHandler(
                address=(SYSLOG_HOST, SYSLOG_PORT),
                facility=SYSLOG_FACILITY
            )
            syslog_handler.setLevel(logging.INFO)
            syslog_handler.setFormatter(logging.Formatter(
                f'waddlebot[{self.module_name}]: %(message)s'
            ))
            self.logger.addHandler(syslog_handler)
        except Exception as e:
            self.logger.error(f"Failed to setup syslog logging: {e}")
    
    def log_event(self, event: LogEvent):
        """Log a structured event"""
        log_message = event.to_log_string()
        
        # Log to appropriate handler
        if event.event_type == "AUTH":
            if hasattr(self, 'auth_handler'):
                auth_logger = logging.getLogger(f"waddlebot.{self.module_name}.auth")
                auth_logger.addHandler(self.auth_handler)
                auth_logger.info(log_message)
        elif event.event_type == "AUTHZ":
            if hasattr(self, 'authz_handler'):
                authz_logger = logging.getLogger(f"waddlebot.{self.module_name}.authz")
                authz_logger.addHandler(self.authz_handler)
                authz_logger.info(log_message)
        elif event.event_type == "AUDIT":
            if hasattr(self, 'audit_handler'):
                audit_logger = logging.getLogger(f"waddlebot.{self.module_name}.audit")
                audit_logger.addHandler(self.audit_handler)
                audit_logger.info(log_message)
        elif event.event_type == "ERROR":
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)
    
    def log_authentication(self, user_id: str, action: str, result: str, 
                          details: Optional[Dict[str, Any]] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          session_id: Optional[str] = None):
        """Log authentication events"""
        event = LogEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="INFO",
            module=self.module_name,
            version=self.module_version,
            event_type="AUTH",
            user_id=user_id,
            action=action,
            result=result,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        self.log_event(event)
    
    def log_authorization(self, community_id: str, user_id: str, action: str, 
                         resource: str, result: str,
                         details: Optional[Dict[str, Any]] = None,
                         session_id: Optional[str] = None):
        """Log authorization events"""
        event = LogEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="INFO",
            module=self.module_name,
            version=self.module_version,
            event_type="AUTHZ",
            community_id=community_id,
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            details=details,
            session_id=session_id
        )
        self.log_event(event)
    
    def log_audit(self, community_id: str, user_id: str, action: str, 
                  resource: str, result: str,
                  details: Optional[Dict[str, Any]] = None,
                  duration_ms: Optional[int] = None,
                  session_id: Optional[str] = None):
        """Log audit events"""
        event = LogEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="INFO",
            module=self.module_name,
            version=self.module_version,
            event_type="AUDIT",
            community_id=community_id,
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            details=details,
            duration_ms=duration_ms,
            session_id=session_id
        )
        self.log_event(event)
    
    def log_error(self, error_message: str, community_id: Optional[str] = None,
                  user_id: Optional[str] = None, action: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None):
        """Log error events"""
        event = LogEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="ERROR",
            module=self.module_name,
            version=self.module_version,
            event_type="ERROR",
            community_id=community_id,
            user_id=user_id,
            action=action,
            error_message=error_message,
            details=details
        )
        self.log_event(event)
    
    def log_system(self, message: str, level: str = "INFO",
                   details: Optional[Dict[str, Any]] = None):
        """Log system events"""
        event = LogEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            module=self.module_name,
            version=self.module_version,
            event_type="SYSTEM",
            details=details
        )
        
        # Create custom message
        log_message = f"[{event.timestamp}] {level} {self.module_name}:{self.module_version} SYSTEM {message}"
        if details:
            details_str = " ".join([f"{k}={v}" for k, v in details.items()])
            log_message += f" {details_str}"
        
        if level == "ERROR":
            self.logger.error(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        elif level == "DEBUG":
            self.logger.debug(log_message)
        else:
            self.logger.info(log_message)

# Global logger instance
waddlebot_logger = WaddleBotLogger()

# Convenience functions
def log_auth(user_id: str, action: str, result: str, **kwargs):
    """Convenience function for authentication logging"""
    waddlebot_logger.log_authentication(user_id, action, result, **kwargs)

def log_authz(community_id: str, user_id: str, action: str, resource: str, result: str, **kwargs):
    """Convenience function for authorization logging"""
    waddlebot_logger.log_authorization(community_id, user_id, action, resource, result, **kwargs)

def log_audit(community_id: str, user_id: str, action: str, resource: str, result: str, **kwargs):
    """Convenience function for audit logging"""
    waddlebot_logger.log_audit(community_id, user_id, action, resource, result, **kwargs)

def log_error(error_message: str, **kwargs):
    """Convenience function for error logging"""
    waddlebot_logger.log_error(error_message, **kwargs)

def log_system(message: str, level: str = "INFO", **kwargs):
    """Convenience function for system logging"""
    waddlebot_logger.log_system(message, level, **kwargs)

# Decorator for automatic audit logging
def audit_log(action: str, resource_type: str = "inventory"):
    """Decorator for automatic audit logging"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            # Extract context from function arguments
            community_id = kwargs.get('community_id') or (args[1] if len(args) > 1 else None)
            user_id = kwargs.get('performed_by') or kwargs.get('user_id') or (args[-1] if args else None)
            
            try:
                result = func(*args, **kwargs)
                
                # Determine success/failure
                if isinstance(result, tuple) and len(result) >= 2:
                    success = result[0]
                    audit_result = "SUCCESS" if success else "FAILURE"
                    details = {"message": result[1]} if len(result) > 1 else None
                else:
                    audit_result = "SUCCESS"
                    details = None
                
                # Calculate duration
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Log audit event
                log_audit(
                    community_id=community_id or "unknown",
                    user_id=user_id or "system",
                    action=action,
                    resource=resource_type,
                    result=audit_result,
                    duration_ms=int(duration),
                    details=details
                )
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                # Log error
                log_audit(
                    community_id=community_id or "unknown",
                    user_id=user_id or "system",
                    action=action,
                    resource=resource_type,
                    result="ERROR",
                    duration_ms=int(duration),
                    details={"error": str(e)}
                )
                
                raise
        
        return wrapper
    return decorator

# Authorization decorator
def require_permission(required_permission: str):
    """Decorator for authorization checking"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract context
            community_id = kwargs.get('community_id') or (args[1] if len(args) > 1 else None)
            user_id = kwargs.get('performed_by') or kwargs.get('user_id') or (args[-1] if args else None)
            
            # For demo purposes, we'll assume permission is granted
            # In real implementation, this would check user permissions
            has_permission = True  # This should be replaced with actual permission check
            
            if has_permission:
                log_authz(
                    community_id=community_id or "unknown",
                    user_id=user_id or "system",
                    action=func.__name__,
                    resource="inventory",
                    result="GRANTED",
                    details={"permission": required_permission}
                )
                return func(*args, **kwargs)
            else:
                log_authz(
                    community_id=community_id or "unknown",
                    user_id=user_id or "system",
                    action=func.__name__,
                    resource="inventory",
                    result="DENIED",
                    details={"permission": required_permission}
                )
                raise PermissionError(f"Permission denied: {required_permission}")
        
        return wrapper
    return decorator

# Initialize logging system
log_system("Logging system initialized", details={
    "log_level": LOG_LEVEL,
    "log_dir": LOG_DIR,
    "syslog_enabled": ENABLE_SYSLOG,
    "module": MODULE_NAME,
    "version": MODULE_VERSION
})