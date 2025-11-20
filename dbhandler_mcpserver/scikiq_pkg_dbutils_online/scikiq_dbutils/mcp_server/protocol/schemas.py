"""
MCP Tool Schema Definitions

Defines schemas for MCP tools and their parameters according to JSON Schema specification.
"""

from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass, field
from enum import Enum


class ParameterType(Enum):
    """Supported parameter types for MCP tools"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


@dataclass
class ParameterSchema:
    """Schema for a single parameter"""
    type: Union[ParameterType, str]
    description: Optional[str] = None
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    format: Optional[str] = None
    items: Optional['ParameterSchema'] = None
    properties: Optional[Dict[str, 'ParameterSchema']] = None
    required: Optional[List[str]] = None
    additional_properties: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON Schema format"""
        result = {}
        
        if isinstance(self.type, ParameterType):
            result["type"] = self.type.value
        else:
            result["type"] = self.type
            
        if self.description:
            result["description"] = self.description
        if self.enum:
            result["enum"] = self.enum
        if self.default is not None:
            result["default"] = self.default
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.min_length is not None:
            result["minLength"] = self.min_length
        if self.max_length is not None:
            result["maxLength"] = self.max_length
        if self.pattern:
            result["pattern"] = self.pattern
        if self.format:
            result["format"] = self.format
        if self.items:
            result["items"] = self.items.to_dict()
        if self.properties:
            result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        if self.required:
            result["required"] = self.required
        if self.additional_properties is not None:
            result["additionalProperties"] = self.additional_properties
            
        return result


@dataclass
class ToolSchema:
    """Schema definition for an MCP tool"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if "type" not in self.input_schema:
            self.input_schema["type"] = "object"
        if "properties" not in self.input_schema:
            self.input_schema["properties"] = {}
    
    def add_parameter(self, name: str, schema: ParameterSchema, required: bool = False):
        """Add a parameter to the tool schema"""
        self.input_schema["properties"][name] = schema.to_dict()
        
        if required:
            if "required" not in self.input_schema:
                self.input_schema["required"] = []
            if name not in self.input_schema["required"]:
                self.input_schema["required"].append(name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool definition format"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


# Common parameter schemas for database operations
DB_CONNECTION_PARAMS = {
    "connection_id": ParameterSchema(
        type=ParameterType.STRING,
        description="Database connection identifier"
    ),
    "config": ParameterSchema(
        type=ParameterType.OBJECT,
        description="Database configuration object",
        properties={
            "dbType": ParameterSchema(
                type=ParameterType.STRING,
                description="Database type (MYSQL, POSTGRES, ORACLE, etc.)",
                enum=["MYSQL", "POSTGRES", "ORACLE", "SQLSERVER", "MONGODB", 
                      "SNOWFLAKE", "BIGQUERY", "REDSHIFT", "ATHENA", "SAPHANA",
                      "VERTICA", "DB2", "TERADATA", "CHROMADB", "SAGEMAKER"]
            ),
            "hostname": ParameterSchema(
                type=ParameterType.STRING,
                description="Database hostname or IP address"
            ),
            "port": ParameterSchema(
                type=ParameterType.INTEGER,
                description="Database port number"
            ),
            "dbname": ParameterSchema(
                type=ParameterType.STRING,
                description="Database name"
            ),
            "dbuser": ParameterSchema(
                type=ParameterType.STRING,
                description="Database username"
            ),
            "dbpassword": ParameterSchema(
                type=ParameterType.STRING,
                description="Database password (will be encoded)"
            ),
            "schema": ParameterSchema(
                type=ParameterType.STRING,
                description="Database schema name (optional)"
            )
        },
        required=["dbType", "hostname", "dbname", "dbuser", "dbpassword"]
    )
}

QUERY_PARAMS = {
    "query": ParameterSchema(
        type=ParameterType.STRING,
        description="SQL query to execute"
    ),
    "limit": ParameterSchema(
        type=ParameterType.INTEGER,
        description="Maximum number of rows to return (optional)",
        minimum=1
    ),
    "use_polars": ParameterSchema(
        type=ParameterType.BOOLEAN,
        description="Use Polars for faster data processing (optional)",
        default=False
    ),
    "batch_size": ParameterSchema(
        type=ParameterType.INTEGER,
        description="Batch size for data processing (optional)",
        default=100000,
        minimum=1000
    )
}

TABLE_PARAMS = {
    "table_name": ParameterSchema(
        type=ParameterType.STRING,
        description="Name of the database table"
    ),
    "search": ParameterSchema(
        type=ParameterType.STRING,
        description="Search pattern for filtering tables (optional)"
    ),
    "table_type": ParameterSchema(
        type=ParameterType.STRING,
        description="Type of table objects to return (optional)",
        enum=["TABLE", "VIEW", "SYSTEM_TABLE"]
    )
}

COLUMN_PARAMS = {
    "column_name": ParameterSchema(
        type=ParameterType.STRING,
        description="Name of the database column"
    ),
    "column_names": ParameterSchema(
        type=ParameterType.ARRAY,
        description="List of column names",
        items=ParameterSchema(type=ParameterType.STRING)
    )
}

FILTER_PARAMS = {
    "filters": ParameterSchema(
        type=ParameterType.ARRAY,
        description="Filter conditions for query",
        items=ParameterSchema(
            type=ParameterType.OBJECT,
            properties={
                "field": ParameterSchema(
                    type=ParameterType.STRING,
                    description="Field name to filter on"
                ),
                "operator": ParameterSchema(
                    type=ParameterType.STRING,
                    description="Filter operator",
                    enum=["equal", "not_equal", "greater_than", "less_than", 
                           "greater_equal", "less_equal", "like", "in", "between"]
                ),
                "value": ParameterSchema(
                    type="string|number|array",
                    description="Filter value"
                )
            },
            required=["field", "operator", "value"]
        )
    ),
    "order_by": ParameterSchema(
        type=ParameterType.ARRAY,
        description="Columns to order results by (optional)",
        items=ParameterSchema(
            type=ParameterType.OBJECT,
            properties={
                "column": ParameterSchema(
                    type=ParameterType.STRING,
                    description="Column name"
                ),
                "direction": ParameterSchema(
                    type=ParameterType.STRING,
                    description="Sort direction",
                    enum=["ASC", "DESC"],
                    default="ASC"
                )
            },
            required=["column"]
        )
    ),
    "group_by": ParameterSchema(
        type=ParameterType.ARRAY,
        description="Columns to group results by (optional)",
        items=ParameterSchema(type=ParameterType.STRING)
    )
}