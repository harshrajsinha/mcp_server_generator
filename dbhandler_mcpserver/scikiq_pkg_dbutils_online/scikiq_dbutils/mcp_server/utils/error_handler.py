"""
Error Handling Utilities

Provides consistent error formatting and handling throughout the MCP server.
"""

import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union
from enum import Enum


class ErrorType(Enum):
    """Standard error types for the MCP server"""
    
    CONNECTION_ERROR = "connection_error"
    SQL_ERROR = "sql_error" 
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SECURITY_ERROR = "security_error"
    CONFIG_ERROR = "config_error"
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND_ERROR = "not_found_error"
    TIMEOUT_ERROR = "timeout_error"


class MCPError(Exception):
    """Base exception class for MCP server errors"""
    
    def __init__(self, 
                 message: str, 
                 error_type: ErrorType = ErrorType.INTERNAL_ERROR,
                 details: Optional[Dict[str, Any]] = None,
                 cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now().isoformat()


class ConnectionError(MCPError):
    """Database connection related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorType.CONNECTION_ERROR, details, cause)


class SQLError(MCPError):
    """SQL execution related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorType.SQL_ERROR, details, cause)


class ValidationError(MCPError):
    """Input validation errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorType.VALIDATION_ERROR, details, cause)


class SecurityError(MCPError):
    """Security related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorType.SECURITY_ERROR, details, cause)


class RateLimitError(MCPError):
    """Rate limiting errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, ErrorType.RATE_LIMIT_ERROR, details, cause)


def handle_error(error: Exception, 
                connection_id: Optional[str] = None,
                tool_name: Optional[str] = None,
                include_traceback: bool = False) -> Dict[str, Any]:
    """
    Convert an exception to a standardized error response
    
    Args:
        error: Exception that occurred
        connection_id: Optional connection identifier
        tool_name: Optional tool name where error occurred
        include_traceback: Whether to include full traceback
        
    Returns:
        Standardized error response dictionary
    """
    logger = logging.getLogger(__name__)
    
    # Determine error type and extract details
    if isinstance(error, MCPError):
        error_type = error.error_type.value
        message = error.message
        details = error.details.copy()
        
        if error.cause:
            details["cause"] = str(error.cause)
    else:
        # Map common exception types to our error types
        error_type_mapping = {
            ValueError: ErrorType.VALIDATION_ERROR,
            TypeError: ErrorType.VALIDATION_ERROR,
            ConnectionError: ErrorType.CONNECTION_ERROR,
            TimeoutError: ErrorType.TIMEOUT_ERROR,
            PermissionError: ErrorType.AUTHENTICATION_ERROR,
            FileNotFoundError: ErrorType.NOT_FOUND_ERROR,
        }
        
        error_type = error_type_mapping.get(type(error), ErrorType.INTERNAL_ERROR).value
        message = str(error)
        details = {}
    
    # Add contextual information
    if connection_id:
        details["connection_id"] = connection_id
    
    if tool_name:
        details["tool_name"] = tool_name
    
    # Add traceback if requested
    if include_traceback:
        details["traceback"] = traceback.format_exc()
    
    # Log the error
    log_level = logging.ERROR
    if error_type in [ErrorType.VALIDATION_ERROR.value, ErrorType.RATE_LIMIT_ERROR.value]:
        log_level = logging.WARNING
    
    logger.log(log_level, f"Error in {tool_name or 'unknown'}: {message}", 
               extra={"connection_id": connection_id, "error_type": error_type})
    
    return {
        "content": message,
        "isError": True,
        "error_type": error_type,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }


def handle_success(data: Any, 
                  connection_id: Optional[str] = None,
                  tool_name: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a standardized success response
    
    Args:
        data: Success data to return
        connection_id: Optional connection identifier
        tool_name: Optional tool name
        metadata: Optional metadata to include
        
    Returns:
        Standardized success response dictionary
    """
    response = {
        "content": data,
        "isError": False,
        "timestamp": datetime.now().isoformat()
    }
    
    if metadata:
        response.update(metadata)
    
    # Log successful operation
    if tool_name:
        logger = logging.getLogger(__name__)
        logger.debug(f"Success in {tool_name}", 
                    extra={"connection_id": connection_id, "tool_name": tool_name})
    
    return response


def validate_required_params(params: Dict[str, Any], required_fields: list) -> None:
    """
    Validate that required parameters are present
    
    Args:
        params: Parameter dictionary to validate
        required_fields: List of required field names
        
    Raises:
        ValidationError: If any required field is missing
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in params:
            missing_fields.append(field)
        elif params[field] is None:
            missing_fields.append(field)
        elif isinstance(params[field], str) and not params[field].strip():
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            f"Missing required parameters: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields, "provided_fields": list(params.keys())}
        )


def validate_connection_id(connection_id: str) -> str:
    """
    Validate and sanitize connection ID
    
    Args:
        connection_id: Connection ID to validate
        
    Returns:
        Validated connection ID
        
    Raises:
        ValidationError: If connection ID is invalid
    """
    if not connection_id:
        raise ValidationError("Connection ID is required")
    
    if not isinstance(connection_id, str):
        raise ValidationError("Connection ID must be a string")
    
    connection_id = connection_id.strip()
    
    if len(connection_id) > 100:
        raise ValidationError("Connection ID too long (maximum 100 characters)")
    
    # Allow alphanumeric, underscore, hyphen, and dot
    import re
    if not re.match(r'^[a-zA-Z0-9_.-]+$', connection_id):
        raise ValidationError("Connection ID contains invalid characters (use only letters, numbers, _, -, .)")
    
    return connection_id


def safe_int_conversion(value: Any, field_name: str, min_value: Optional[int] = None, 
                       max_value: Optional[int] = None) -> int:
    """
    Safely convert value to integer with validation
    
    Args:
        value: Value to convert
        field_name: Field name for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Validated integer value
        
    Raises:
        ValidationError: If conversion fails or value is out of range
    """
    if value is None:
        raise ValidationError(f"{field_name} is required")
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid integer, got: {type(value).__name__}")
    
    if min_value is not None and int_value < min_value:
        raise ValidationError(f"{field_name} must be at least {min_value}, got: {int_value}")
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"{field_name} must be at most {max_value}, got: {int_value}")
    
    return int_value


def truncate_large_data(data: Any, max_size: int = 10000, truncation_message: str = None) -> Any:
    """
    Truncate large data to prevent response size issues
    
    Args:
        data: Data to potentially truncate
        max_size: Maximum size threshold
        truncation_message: Custom truncation message
        
    Returns:
        Original data or truncated version with warning
    """
    if isinstance(data, (list, tuple)):
        if len(data) > max_size:
            truncated_data = list(data)[:max_size]
            warning_msg = truncation_message or f"Results truncated to {max_size} items (originally {len(data)} items)"
            
            return {
                "data": truncated_data,
                "truncated": True,
                "original_count": len(data),
                "returned_count": len(truncated_data),
                "warning": warning_msg
            }
    
    elif isinstance(data, dict):
        if len(str(data)) > max_size * 10:  # Rough string size check
            # Try to truncate individual lists within the dict
            truncated_dict = {}
            for key, value in data.items():
                truncated_dict[key] = truncate_large_data(value, max_size // 10)
            
            return truncated_dict
    
    elif isinstance(data, str):
        if len(data) > max_size:
            truncated_text = data[:max_size] + "... (truncated)"
            return {
                "text": truncated_text,
                "truncated": True,
                "original_length": len(data),
                "warning": f"Text truncated to {max_size} characters"
            }
    
    return data


class ErrorContext:
    """Context manager for consistent error handling"""
    
    def __init__(self, 
                 tool_name: str,
                 connection_id: Optional[str] = None,
                 include_traceback: bool = False):
        self.tool_name = tool_name
        self.connection_id = connection_id
        self.include_traceback = include_traceback
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.logger.debug(f"Starting {self.tool_name}", 
                         extra={"connection_id": self.connection_id, "tool_name": self.tool_name})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred
            error_response = handle_error(
                exc_val, 
                self.connection_id, 
                self.tool_name, 
                self.include_traceback
            )
            # Store error response for retrieval
            self.error_response = error_response
            return True  # Suppress the exception
        else:
            self.logger.debug(f"Completed {self.tool_name} successfully",
                            extra={"connection_id": self.connection_id, "tool_name": self.tool_name})
        return False
    
    def get_error_response(self) -> Optional[Dict[str, Any]]:
        """Get error response if an error occurred"""
        return getattr(self, 'error_response', None)