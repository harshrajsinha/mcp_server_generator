"""
JSON-RPC 2.0 Message Classes for Model Context Protocol

Implements the JSON-RPC 2.0 specification for MCP communication.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum


class JsonRpcErrorCode(Enum):
    """Standard JSON-RPC 2.0 error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP specific error codes
    TOOL_NOT_FOUND = -32000
    TOOL_EXECUTION_ERROR = -32001
    DATABASE_CONNECTION_ERROR = -32002
    INVALID_DATABASE_CONFIG = -32003


@dataclass
class JsonRpcError:
    """JSON-RPC 2.0 Error object"""
    code: int
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JsonRpcError':
        return cls(
            code=data["code"],
            message=data["message"],
            data=data.get("data")
        )


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 Request object"""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    jsonrpc: str = "2.0"
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "id": self.id
        }
        if self.params is not None:
            result["params"] = self.params
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JsonRpcRequest':
        return cls(
            method=data["method"],
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'JsonRpcRequest':
        return cls.from_dict(json.loads(json_str))


class JsonRpcResponse:
    """JSON-RPC 2.0 Response object"""
    
    def __init__(self, id: Union[str, int, None], jsonrpc: str = "2.0", 
                 result: Optional[Any] = None, error: Optional[JsonRpcError] = None):
        self.id = id
        self.jsonrpc = jsonrpc
        self.result = result
        self.error = error
        
        if self.result is not None and self.error is not None:
            raise ValueError("Response cannot have both result and error")
        if self.result is None and self.error is None:
            raise ValueError("Response must have either result or error")
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error.to_dict()
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JsonRpcResponse':
        error = None
        if "error" in data:
            error = JsonRpcError.from_dict(data["error"])
        
        return cls(
            id=data["id"],
            result=data.get("result"),
            error=error,
            jsonrpc=data.get("jsonrpc", "2.0")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'JsonRpcResponse':
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def success(cls, id: Union[str, int, None], result: Any) -> 'JsonRpcResponse':
        response = cls.__new__(cls)
        response.id = id
        response.jsonrpc = "2.0"
        response.result = result
        response.error = None
        return response
    
    @classmethod
    def error(cls, id: Union[str, int, None], error: JsonRpcError) -> 'JsonRpcResponse':
        response = cls.__new__(cls)
        response.id = id
        response.jsonrpc = "2.0"
        response.result = None
        response.error = error
        return response


@dataclass
class MCPToolCall:
    """MCP Tool Call representation"""
    name: str
    arguments: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPToolCall':
        return cls(
            name=data["name"],
            arguments=data["arguments"]
        )


@dataclass
class MCPToolResult:
    """MCP Tool Result representation"""
    content: Any
    is_error: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "isError": self.is_error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPToolResult':
        return cls(
            content=data["content"],
            is_error=data.get("isError", False)
        )
    
    @classmethod
    def success(cls, content: Any) -> 'MCPToolResult':
        return cls(content=content, is_error=False)
    
    @classmethod
    def error(cls, content: Any) -> 'MCPToolResult':
        return cls(content=content, is_error=True)


# Helper functions for creating standard errors
def create_parse_error(data: Any = None) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.PARSE_ERROR.value,
        message="Parse error",
        data=data
    )


def create_invalid_request_error(data: Any = None) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.INVALID_REQUEST.value,
        message="Invalid Request",
        data=data
    )


def create_method_not_found_error(method: str = None) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.METHOD_NOT_FOUND.value,
        message="Method not found",
        data={"method": method} if method else None
    )


def create_invalid_params_error(data: Any = None) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.INVALID_PARAMS.value,
        message="Invalid params",
        data=data
    )


def create_internal_error(data: Any = None) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.INTERNAL_ERROR.value,
        message="Internal error",
        data=data
    )


def create_tool_not_found_error(tool_name: str) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.TOOL_NOT_FOUND.value,
        message=f"Tool '{tool_name}' not found",
        data={"tool_name": tool_name}
    )


def create_tool_execution_error(tool_name: str, error_message: str) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.TOOL_EXECUTION_ERROR.value,
        message=f"Tool execution error in '{tool_name}': {error_message}",
        data={"tool_name": tool_name, "error": error_message}
    )


def create_database_connection_error(db_type: str, error_message: str) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.DATABASE_CONNECTION_ERROR.value,
        message=f"Database connection error ({db_type}): {error_message}",
        data={"db_type": db_type, "error": error_message}
    )


def create_invalid_database_config_error(config_errors: List[str]) -> JsonRpcError:
    return JsonRpcError(
        code=JsonRpcErrorCode.INVALID_DATABASE_CONFIG.value,
        message="Invalid database configuration",
        data={"errors": config_errors}
    )