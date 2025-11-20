"""
Utility Module Initialization

This module provides utility functions and classes for the MCP server.
"""

from .error_handler import (
    ErrorType, MCPError, ConnectionError, SQLError, ValidationError, 
    SecurityError, RateLimitError, handle_error, handle_success,
    validate_required_params, validate_connection_id, safe_int_conversion,
    truncate_large_data, ErrorContext
)

from .monitoring import (
    ToolMetrics, PerformanceMonitor, performance_monitor, log_tool_execution,
    StructuredLogger, setup_comprehensive_logging, SecurityAuditLogger, security_logger
)

__all__ = [
    # Error handling
    'ErrorType', 'MCPError', 'ConnectionError', 'SQLError', 'ValidationError',
    'SecurityError', 'RateLimitError', 'handle_error', 'handle_success',
    'validate_required_params', 'validate_connection_id', 'safe_int_conversion',
    'truncate_large_data', 'ErrorContext',
    
    # Monitoring
    'ToolMetrics', 'PerformanceMonitor', 'performance_monitor', 'log_tool_execution',
    'StructuredLogger', 'setup_comprehensive_logging', 'SecurityAuditLogger', 'security_logger'
]