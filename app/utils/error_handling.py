"""
Enhanced Error Handling Framework.

This module provides comprehensive error handling capabilities including
structured logging, automatic recovery, transaction management, and monitoring.
"""

import logging
import traceback
import functools
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Callable
from flask import request, current_app, jsonify
from sqlalchemy.exc import IntegrityError, OperationalError, StatementError
from db import db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    USER_INPUT = "user_input"


class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass


class ValidationError(Exception):
    """Exception for validation errors."""
    pass


class BusinessLogicError(Exception):
    """Exception for business logic violations."""
    pass


class AuthenticationError(Exception):
    """Exception for authentication failures."""
    pass


class AuthorizationError(Exception):
    """Exception for authorization failures."""
    pass


class ErrorContext:
    """Context information for error handling."""
    
    def __init__(self, 
                 operation: str,
                 user_id: Optional[int] = None,
                 request_id: Optional[str] = None,
                 additional_data: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.user_id = user_id
        self.request_id = request_id
        self.additional_data = additional_data or {}
        self.timestamp = datetime.utcnow()


class ErrorHandler:
    """
    Comprehensive error handler with logging, recovery, and monitoring.
    """
    
    def __init__(self):
        """Initialize error handler."""
        self.error_counts = {}
        self.recovery_strategies = self._define_recovery_strategies()
        
    def _define_recovery_strategies(self):
        """Define automatic recovery strategies for different error types."""
        return {
            IntegrityError: self._handle_integrity_error,
            OperationalError: self._handle_operational_error,
            ValidationError: self._handle_validation_error,
            BusinessLogicError: self._handle_business_logic_error,
            AuthenticationError: self._handle_authentication_error,
            AuthorizationError: self._handle_authorization_error,
        }
    
    def handle_error(self, 
                    error: Exception,
                    context: ErrorContext,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    category: ErrorCategory = ErrorCategory.SYSTEM,
                    auto_recover: bool = True) -> Dict[str, Any]:
        """
        Handle an error with comprehensive logging and recovery.
        
        Args:
            error: The exception that occurred
            context: Error context information
            severity: Error severity level
            category: Error category
            auto_recover: Whether to attempt automatic recovery
            
        Returns:
            Dict containing error handling result
        """
        error_id = self._generate_error_id()
        error_type = type(error).__name__
        
        # Log the error with full context
        self._log_error(error, context, severity, category, error_id)
        
        # Track error frequency
        self._track_error_frequency(error_type, context.operation)
        
        # Attempt recovery if enabled
        recovery_result = None
        if auto_recover:
            recovery_result = self._attempt_recovery(error, context)
        
        # Rollback database transaction if needed
        if category == ErrorCategory.DATABASE:
            self._safe_rollback()
        
        # Prepare error response
        error_response = {
            'error_id': error_id,
            'error_type': error_type,
            'severity': severity.value,
            'category': category.value,
            'operation': context.operation,
            'timestamp': context.timestamp.isoformat(),
            'recovered': recovery_result is not None and recovery_result.get('success', False),
            'user_message': self._get_user_friendly_message(error, severity),
            'technical_details': str(error) if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
        
        # Alert if critical error
        if severity == ErrorSeverity.CRITICAL:
            self._send_critical_alert(error_response, context)
        
        return error_response
    
    def _log_error(self, 
                  error: Exception,
                  context: ErrorContext,
                  severity: ErrorSeverity,
                  category: ErrorCategory,
                  error_id: str):
        """Log error with structured information."""
        log_data = {
            'error_id': error_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity.value,
            'category': category.value,
            'operation': context.operation,
            'user_id': context.user_id,
            'request_id': context.request_id,
            'timestamp': context.timestamp.isoformat(),
            'traceback': traceback.format_exc(),
            'additional_data': context.additional_data
        }
        
        # Add request context if available
        if request:
            log_data.update({
                'request_method': request.method,
                'request_url': request.url,
                'request_ip': request.environ.get('REMOTE_ADDR'),
                'user_agent': request.environ.get('HTTP_USER_AGENT')
            })
        
        # Log at appropriate level
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error in {context.operation}", extra=log_data)
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error in {context.operation}", extra=log_data)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error in {context.operation}", extra=log_data)
        else:
            logger.info(f"Low severity error in {context.operation}", extra=log_data)
    
    def _attempt_recovery(self, error: Exception, context: ErrorContext) -> Optional[Dict[str, Any]]:
        """Attempt automatic error recovery."""
        error_type = type(error)
        
        if error_type in self.recovery_strategies:
            try:
                recovery_func = self.recovery_strategies[error_type]
                return recovery_func(error, context)
            except Exception as recovery_error:
                logger.error(f"Recovery failed for {error_type.__name__}: {str(recovery_error)}")
                return None
        
        return None
    
    def _handle_integrity_error(self, error: IntegrityError, context: ErrorContext) -> Dict[str, Any]:
        """Handle database integrity errors."""
        self._safe_rollback()
        
        # Check if it's a foreign key constraint violation
        error_msg = str(error.orig) if hasattr(error, 'orig') else str(error)
        
        if 'foreign key constraint' in error_msg.lower():
            return {
                'success': False,
                'strategy': 'foreign_key_violation',
                'message': 'Referenced record does not exist or cannot be deleted due to dependencies',
                'action': 'validate_references'
            }
        elif 'unique constraint' in error_msg.lower():
            return {
                'success': False,
                'strategy': 'unique_violation',
                'message': 'Duplicate value violates uniqueness constraint',
                'action': 'check_duplicates'
            }
        
        return {
            'success': False,
            'strategy': 'general_integrity',
            'message': 'Database integrity constraint violated',
            'action': 'validate_data'
        }
    
    def _handle_operational_error(self, error: OperationalError, context: ErrorContext) -> Dict[str, Any]:
        """Handle database operational errors."""
        self._safe_rollback()
        
        error_msg = str(error.orig) if hasattr(error, 'orig') else str(error)
        
        if 'database is locked' in error_msg.lower():
            return {
                'success': False,
                'strategy': 'database_locked',
                'message': 'Database is temporarily locked, retry operation',
                'action': 'retry_with_backoff'
            }
        elif 'connection' in error_msg.lower():
            return {
                'success': False,
                'strategy': 'connection_error',
                'message': 'Database connection issue',
                'action': 'reconnect_database'
            }
        
        return {
            'success': False,
            'strategy': 'operational_error',
            'message': 'Database operational error occurred',
            'action': 'check_database_status'
        }
    
    def _handle_validation_error(self, error: ValidationError, context: ErrorContext) -> Dict[str, Any]:
        """Handle validation errors."""
        return {
            'success': False,
            'strategy': 'validation_error',
            'message': str(error),
            'action': 'fix_input_data'
        }
    
    def _handle_business_logic_error(self, error: BusinessLogicError, context: ErrorContext) -> Dict[str, Any]:
        """Handle business logic errors."""
        return {
            'success': False,
            'strategy': 'business_logic_error',
            'message': str(error),
            'action': 'review_business_rules'
        }
    
    def _handle_authentication_error(self, error: AuthenticationError, context: ErrorContext) -> Dict[str, Any]:
        """Handle authentication errors."""
        return {
            'success': False,
            'strategy': 'authentication_error',
            'message': 'Authentication failed',
            'action': 'redirect_to_login'
        }
    
    def _handle_authorization_error(self, error: AuthorizationError, context: ErrorContext) -> Dict[str, Any]:
        """Handle authorization errors."""
        return {
            'success': False,
            'strategy': 'authorization_error',
            'message': 'Access denied',
            'action': 'check_permissions'
        }
    
    def _safe_rollback(self):
        """Safely rollback database transaction."""
        try:
            if db.session.is_active:
                db.session.rollback()
                logger.info("Database transaction rolled back successfully")
        except Exception as rollback_error:
            logger.error(f"Failed to rollback transaction: {str(rollback_error)}")
    
    def _track_error_frequency(self, error_type: str, operation: str):
        """Track error frequency for monitoring."""
        key = f"{error_type}:{operation}"
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Alert if error frequency is high
        if self.error_counts[key] > 10:  # Configurable threshold
            logger.warning(f"High error frequency detected: {key} occurred {self.error_counts[key]} times")
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_user_friendly_message(self, error: Exception, severity: ErrorSeverity) -> str:
        """Get user-friendly error message."""
        error_type = type(error).__name__
        
        user_messages = {
            'IntegrityError': 'The operation could not be completed due to data constraints.',
            'ValidationError': 'Please check your input and try again.',
            'BusinessLogicError': 'This operation is not allowed under current conditions.',
            'AuthenticationError': 'Please log in to continue.',
            'AuthorizationError': 'You do not have permission to perform this action.',
            'OperationalError': 'A temporary system error occurred. Please try again.',
        }
        
        if severity == ErrorSeverity.CRITICAL:
            return 'A critical system error occurred. Please contact support.'
        
        return user_messages.get(error_type, 'An unexpected error occurred. Please try again.')
    
    def _send_critical_alert(self, error_response: Dict[str, Any], context: ErrorContext):
        """Send alert for critical errors."""
        # In production, this would send alerts via email, Slack, etc.
        logger.critical(f"CRITICAL ALERT: {error_response['error_type']} in {context.operation}")


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(operation: str,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 category: ErrorCategory = ErrorCategory.SYSTEM,
                 auto_recover: bool = True):
    """
    Decorator for comprehensive error handling.
    
    Args:
        operation: Name of the operation being performed
        severity: Default error severity
        category: Error category
        auto_recover: Whether to attempt automatic recovery
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(
                operation=operation,
                user_id=getattr(request, 'user_id', None) if request else None,
                request_id=getattr(request, 'id', None) if request else None
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    severity=severity,
                    category=category,
                    auto_recover=auto_recover
                )
                
                # Re-raise with additional context for API endpoints
                if hasattr(e, 'response'):
                    e.response = error_result
                
                raise e
        
        return wrapper
    return decorator


def safe_database_operation(operation: str):
    """
    Decorator for safe database operations with automatic transaction management.
    
    Args:
        operation: Name of the database operation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(operation=operation)
            
            try:
                # Begin transaction if not already in one
                if not db.session.is_active:
                    db.session.begin()
                
                result = func(*args, **kwargs)
                
                # Commit if successful
                db.session.commit()
                return result
                
            except Exception as e:
                # Handle error with automatic rollback
                error_result = error_handler.handle_error(
                    error=e,
                    context=context,
                    category=ErrorCategory.DATABASE,
                    auto_recover=True
                )
                
                # Re-raise with context
                raise DatabaseError(f"Database operation failed: {str(e)}") from e
        
        return wrapper
    return decorator


def validate_input(validation_func: Callable):
    """
    Decorator for input validation with proper error handling.
    
    Args:
        validation_func: Function to validate input
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Validate input
                validation_result = validation_func(*args, **kwargs)
                if not validation_result.get('valid', True):
                    raise ValidationError(validation_result.get('message', 'Validation failed'))
                
                return func(*args, **kwargs)
                
            except ValidationError:
                raise
            except Exception as e:
                context = ErrorContext(operation=f"validate_{func.__name__}")
                error_handler.handle_error(
                    error=e,
                    context=context,
                    category=ErrorCategory.VALIDATION
                )
                raise ValidationError(f"Input validation failed: {str(e)}") from e
        
        return wrapper
    return decorator


def get_error_statistics() -> Dict[str, Any]:
    """Get error statistics for monitoring."""
    return {
        'error_counts': error_handler.error_counts,
        'total_errors': sum(error_handler.error_counts.values()),
        'timestamp': datetime.utcnow().isoformat()
    } 