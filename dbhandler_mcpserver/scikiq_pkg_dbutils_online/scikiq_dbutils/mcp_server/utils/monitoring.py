"""
Monitoring and Logging Utilities

Provides comprehensive logging, performance monitoring, and tool execution tracking.
"""

import time
import logging
import functools
import asyncio
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json


@dataclass
class ToolMetrics:
    """Metrics for individual tool execution"""
    
    tool_name: str
    total_calls: int = 0
    total_duration_ms: float = 0.0
    successful_calls: int = 0
    failed_calls: int = 0
    average_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    last_called: Optional[datetime] = None
    error_count_by_type: Dict[str, int] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Monitors tool execution performance and provides metrics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics: Dict[str, ToolMetrics] = {}
        self.global_start_time = time.time()
        
    def record_tool_execution(self, 
                            tool_name: str, 
                            duration_ms: float, 
                            success: bool,
                            error_type: Optional[str] = None):
        """
        Record metrics for a tool execution
        
        Args:
            tool_name: Name of the executed tool
            duration_ms: Execution duration in milliseconds
            success: Whether execution was successful
            error_type: Type of error if execution failed
        """
        if tool_name not in self.metrics:
            self.metrics[tool_name] = ToolMetrics(tool_name=tool_name)
        
        metrics = self.metrics[tool_name]
        
        # Update basic counters
        metrics.total_calls += 1
        metrics.total_duration_ms += duration_ms
        metrics.last_called = datetime.now()
        
        # Update min/max duration
        metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)
        metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)
        
        # Update success/failure counts
        if success:
            metrics.successful_calls += 1
        else:
            metrics.failed_calls += 1
            if error_type:
                metrics.error_count_by_type[error_type] = metrics.error_count_by_type.get(error_type, 0) + 1
        
        # Calculate average duration
        metrics.average_duration_ms = metrics.total_duration_ms / metrics.total_calls
        
        # Log performance warnings
        if duration_ms > 5000:  # 5 seconds
            self.logger.warning(f"Slow tool execution: {tool_name} took {duration_ms:.2f}ms")
    
    def get_tool_metrics(self, tool_name: str) -> Optional[ToolMetrics]:
        """Get metrics for a specific tool"""
        return self.metrics.get(tool_name)
    
    def get_all_metrics(self) -> Dict[str, ToolMetrics]:
        """Get all tool metrics"""
        return self.metrics.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        total_calls = sum(m.total_calls for m in self.metrics.values())
        total_failures = sum(m.failed_calls for m in self.metrics.values())
        total_duration = sum(m.total_duration_ms for m in self.metrics.values())
        
        uptime_seconds = time.time() - self.global_start_time
        
        return {
            "uptime_seconds": uptime_seconds,
            "total_tool_calls": total_calls,
            "total_failures": total_failures,
            "success_rate": (total_calls - total_failures) / total_calls if total_calls > 0 else 0,
            "average_request_duration_ms": total_duration / total_calls if total_calls > 0 else 0,
            "tools_count": len(self.metrics),
            "calls_per_second": total_calls / uptime_seconds if uptime_seconds > 0 else 0
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def log_tool_execution(func: Callable) -> Callable:
    """
    Decorator to log tool execution with performance monitoring
    
    Args:
        func: Function to decorate (async or sync)
        
    Returns:
        Decorated function with logging and monitoring
    """
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        tool_name = func.__name__
        connection_id = kwargs.get('connection_id') or (args[0] if args else None)
        
        logger = logging.getLogger(f"tools.{tool_name}")
        start_time = time.time()
        
        # Log start
        logger.info(f"Executing {tool_name}", extra={
            "connection_id": connection_id,
            "tool_name": tool_name,
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys())
        })
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log success
            logger.info(f"Tool {tool_name} completed successfully in {duration_ms:.2f}ms", extra={
                "connection_id": connection_id,
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "success": True
            })
            
            # Record metrics
            performance_monitor.record_tool_execution(tool_name, duration_ms, True)
            
            return result
            
        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            
            # Log error
            logger.error(f"Tool {tool_name} failed after {duration_ms:.2f}ms: {str(e)}", extra={
                "connection_id": connection_id,
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "success": False,
                "error_type": error_type
            })
            
            # Record metrics
            performance_monitor.record_tool_execution(tool_name, duration_ms, False, error_type)
            
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        # For synchronous functions, convert to async wrapper
        return asyncio.create_task(async_wrapper(*args, **kwargs))
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class StructuredLogger:
    """
    Structured logger for consistent log formatting
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_structured_logging()
    
    def _setup_structured_logging(self):
        """Setup structured logging format"""
        
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add extra fields
                if hasattr(record, 'connection_id'):
                    log_data["connection_id"] = record.connection_id
                
                if hasattr(record, 'tool_name'):
                    log_data["tool_name"] = record.tool_name
                
                if hasattr(record, 'duration_ms'):
                    log_data["duration_ms"] = record.duration_ms
                
                if hasattr(record, 'success'):
                    log_data["success"] = record.success
                
                if hasattr(record, 'error_type'):
                    log_data["error_type"] = record.error_type
                
                return json.dumps(log_data)
        
        # Only add handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self.logger.debug(message, extra=kwargs)


def setup_comprehensive_logging(log_level: str = "INFO", 
                               log_file: Optional[str] = None,
                               structured: bool = True):
    """
    Setup comprehensive logging for the MCP server
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        structured: Whether to use structured JSON logging
    """
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if not structured else None,
        handlers=[]
    )
    
    logger = logging.getLogger()
    
    # Console handler
    console_handler = logging.StreamHandler()
    
    if structured:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        
        if structured:
            file_formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
            )
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Configure specific loggers
    loggers_config = {
        "scikiq_dbutils.mcp_server": log_level,
        "scikiq_dbutils.handlers": "WARNING",  # Less verbose for database handlers
        "urllib3.connectionpool": "WARNING",   # Suppress HTTP pool logs
        "requests.packages.urllib3": "WARNING"
    }
    
    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(getattr(logging, level.upper()))


class SecurityAuditLogger:
    """
    Specialized logger for security events
    """
    
    def __init__(self):
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)
        
        # Create security-specific handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            'SECURITY - %(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def log_connection_attempt(self, connection_id: str, hostname: str, username: str, success: bool):
        """Log database connection attempt"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"Connection attempt {status}: {connection_id} to {hostname} as {username}")
    
    def log_sql_injection_attempt(self, connection_id: str, query: str, reason: str):
        """Log potential SQL injection attempt"""
        self.logger.warning(f"SQL injection attempt blocked: {connection_id} - {reason} - Query: {query[:100]}...")
    
    def log_rate_limit_exceeded(self, connection_id: str, limit: int, window: str):
        """Log rate limit exceeded"""
        self.logger.warning(f"Rate limit exceeded: {connection_id} - {limit} requests per {window}")
    
    def log_security_violation(self, event_type: str, details: Dict[str, Any]):
        """Log general security violation"""
        self.logger.error(f"Security violation - {event_type}: {json.dumps(details)}")


# Global security audit logger
security_logger = SecurityAuditLogger()