"""
DuckDB Handler with AWS S3 Storage Support

This handler implements the clsDBConnection interface for DuckDB with special
support for AWS S3 storage operations where folders in S3 buckets are treated
as tables.

Features:
- Native DuckDB SQL operations
- AWS S3 integration via DuckDB's httpfs extension
- Folder-as-table abstraction for S3 storage
- Support for Parquet, CSV, JSON files in S3
- Efficient columnar data processing
- In-memory and persistent database modes
"""

import os
import json
import logging
import pandas as pd
import duckdb
import boto3
from urllib.parse import urlparse
from collections import OrderedDict
from sqlalchemy import create_engine
from sqlalchemy import types as sqlalchemyTypes
from pypika import Tables, Table, Field, JoinType, Order, functions as fn
from pypika.queries import Schema

# Custom imports
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.handlers.DBConnection import (
    clsDBConnection, 
    ViewCreationError, 
    where_recursive_condition, 
    where_condition,
    where_Colcondition,
    MergeStatement,
    ExecuteQueryException
)
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression


class DuckDBConnectException(Exception):
    """Exception raised when DuckDB connection fails."""
    pass


class DuckDBTableNotFoundException(Exception):
    """Exception raised when a table (S3 folder) is not found."""
    pass


class DuckDBS3Exception(Exception):
    """Exception raised for S3-specific operations."""
    pass


class clsDuckDB(clsDBConnection):
    """
    DuckDB Handler with AWS S3 storage support.
    
    Configuration:
    {
        "database_path": ":memory:" or "/path/to/database.duckdb",
        "s3_access_key_id": "AWS_ACCESS_KEY",
        "s3_secret_access_key": "AWS_SECRET_KEY", 
        "s3_region": "ap-south-1",
        "s3_bucket": "my-data-bucket",
        "s3_prefix": "data/tables/",  # Optional prefix for table folders
        "default_file_format": "parquet",  # parquet, csv, json
        "enable_s3": true,
        "resource_key": "optional_resource_identifier"
    }
    """
    
    def __init__(self, config):
        """Initialize DuckDB connection with S3 configuration."""
        super().__init__("DUCKDB")
        
        # Database configuration
        self.database_path = config.get("database_path", ":memory:")
        self.connection = None
        self.cursor = None
        self.engine_statement = None
        
        # S3 configuration
        self.enable_s3 = config.get("enable_s3", True)
        self.s3_bucket = config.get("s3_bucket")
        self.s3_prefix = config.get("s3_prefix", "")
        self.s3_region = config.get("s3_region", "ap-south-1")
        self.default_file_format = config.get("default_file_format", "parquet")
        
        # AWS credentials
        self.s3_access_key_id = config.get("s3_access_key_id")
        self.s3_secret_access_key = config.get("s3_secret_access_key")
        
        # Resource tracking
        self.resource_key = config.get("resource_key")
        
        # S3 client for metadata operations
        self._s3_client = None
        
        # Schema information cache
        self._table_cache = {}
        
        # Validate configuration
        if self.enable_s3:
            if not self.s3_bucket:
                raise DuckDBConnectException("S3 bucket is required when S3 is enabled")
            if not self.s3_access_key_id or not self.s3_secret_access_key:
                raise DuckDBConnectException("AWS credentials are required for S3 access")

    def _get_s3_client(self):
        """Get or create S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=self.s3_access_key_id,
                aws_secret_access_key=self.s3_secret_access_key,
                region_name=self.s3_region
            )
        return self._s3_client

    def _configure_s3_settings(self):
        """Configure DuckDB S3 settings."""
        if not self.enable_s3:
            return
            
        try:
            # Install and load httpfs extension for S3 support
            self.cursor.execute("INSTALL httpfs;")
            self.cursor.execute("LOAD httpfs;")
            
            # Set S3 credentials
            self.cursor.execute(f"SET s3_region='{self.s3_region}';")
            self.cursor.execute(f"SET s3_access_key_id='{self.s3_access_key_id}';")
            self.cursor.execute(f"SET s3_secret_access_key='{self.s3_secret_access_key}';")
            
            # Configure S3 settings for better performance
            self.cursor.execute("SET s3_use_ssl=true;")
            self.cursor.execute("SET s3_url_style='path';")
            
        except Exception as e:
            raise DuckDBS3Exception(f"Failed to configure S3 settings: {str(e)}")

    def connect(self):
        """Establish connection to DuckDB and configure S3."""
        try:
            resp = {'resource_call': 'connect'}
            
            # Connect to DuckDB
            self.connection = duckdb.connect(self.database_path)
            self.cursor = self.connection.cursor()
            
            # Configure S3 if enabled
            if self.enable_s3:
                self._configure_s3_settings()
            
            resp['msg'] = 'Successfully connected to DuckDB'
            resp['error'] = 0
            self.callConnectionAudit(resp)
            
        except Exception as e:
            resp = {'resource_call': 'connect', 'msg': str(e), 'error': 1}
            self.callConnectionAudit(resp)
            raise DuckDBConnectException(f"Failed to connect to DuckDB: {str(e)}")

    def close(self):
        """Close DuckDB connection."""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.connection:
                self.connection.close()
                self.connection = None
        except Exception as e:
            logging.warning(f"Error closing DuckDB connection: {str(e)}")

    def testConnection(self):
        """Test DuckDB connection and S3 access if enabled."""
        result = {}
        try:
            self.connect()
            
            # Test basic DuckDB functionality
            self.cursor.execute("SELECT 1 as test")
            test_result = self.cursor.fetchone()
            
            if test_result[0] != 1:
                raise Exception("Basic DuckDB query failed")
            
            # Test S3 access if enabled
            if self.enable_s3:
                s3_client = self._get_s3_client()
                # Test bucket access
                s3_client.head_bucket(Bucket=self.s3_bucket)
            
            result = {
                'msg': 'DuckDB connection successful',
                'status': 200,
                'error': 0,
                'data': {
                    'database_path': self.database_path,
                    's3_enabled': self.enable_s3,
                    's3_bucket': self.s3_bucket if self.enable_s3 else None
                }
            }
            
            self.close()
            
        except Exception as e:
            result = {
                'msg': f'DuckDB connection failed: {str(e)}',
                'status': 500,
                'error': 1
            }
            self.close()
        
        self.callConnectionAudit(result)
        return result

    def _get_s3_table_path(self, table_name):
        """Get S3 path for a table (folder)."""
        prefix = self.s3_prefix.rstrip('/') + '/' if self.s3_prefix else ''
        return f"s3://{self.s3_bucket}/{prefix}{table_name}/"

    def _list_s3_files_in_folder(self, table_name):
        """List files in an S3 folder (table)."""
        s3_client = self._get_s3_client()
        prefix = self.s3_prefix.rstrip('/') + '/' if self.s3_prefix else ''
        folder_prefix = f"{prefix}{table_name}/"
        
        try:
            response = s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=folder_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip folder itself
                    if obj['Key'] != folder_prefix:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'file_format': self._detect_file_format(obj['Key'])
                        })
            
            return files
            
        except Exception as e:
            raise DuckDBS3Exception(f"Failed to list files in S3 folder {table_name}: {str(e)}")

    def _detect_file_format(self, file_path):
        """Detect file format from file extension."""
        extension = file_path.lower().split('.')[-1]
        format_map = {
            'parquet': 'parquet',
            'pq': 'parquet', 
            'csv': 'csv',
            'json': 'json',
            'jsonl': 'json',
            'ndjson': 'json',
            'orc': 'orc'  # Added support for ORC files
        }
        return format_map.get(extension, 'unknown')

    def _get_s3_table_schema(self, table_name):
        """Get schema information for an S3 table by sampling files."""
        # Ensure we have a connection
        connection_managed = False
        if self.cursor is None:
            self.connect()
            connection_managed = True
        
        try:
            files = self._list_s3_files_in_folder(table_name)
            
            if not files:
                raise DuckDBTableNotFoundException(f"No files found in S3 folder: {table_name}")
            
            # Find the first file of a supported format (exclude ORC files)
            sample_file = None
            file_format = None
            for file_info in files:
                if file_info['file_format'] in ['parquet', 'csv', 'json']:
                    sample_file = f"s3://{self.s3_bucket}/{file_info['key']}"
                    file_format = file_info['file_format']
                    break
            
            if not sample_file:
                # Check if all files are ORC (unsupported)
                orc_files = [f for f in files if f['file_format'] == 'orc']
                if len(orc_files) == len(files):
                    raise DuckDBS3Exception(f"Table '{table_name}' contains only ORC files, which are not supported by DuckDB")
                else:
                    raise DuckDBS3Exception(f"No supported file formats found in table: {table_name}")
            
            try:
                # Query to describe the file structure
                if file_format == 'parquet':
                    describe_query = f"DESCRIBE SELECT * FROM read_parquet('{sample_file}') LIMIT 0"
                elif file_format == 'csv':
                    describe_query = f"DESCRIBE SELECT * FROM read_csv_auto('{sample_file}') LIMIT 0"
                elif file_format == 'json':
                    describe_query = f"DESCRIBE SELECT * FROM read_json_auto('{sample_file}') LIMIT 0"
                
                self.cursor.execute(describe_query)
                schema_info = self.cursor.fetchall()
                
                columns = []
                for row in schema_info:
                    columns.append({
                        'COLUMN_NAME': row[0],
                        'DATA_TYPE': row[1],
                        'IS_NULLABLE': True,  # Default assumption
                        'COLUMN_DEFAULT': None
                    })
                
                return columns
                
            except Exception as e:
                raise DuckDBS3Exception(f"Failed to get schema for table {table_name}: {str(e)}")
                
        finally:
            # Close connection if we opened it
            if connection_managed:
                self.close()

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=100000, profile=False):
        """Execute SQL query with S3 table resolution."""
        try:
            if manage_connection:
                self.connect()
            
            # Apply limit if specified
            query = self._apply_query_limit(query, limit)
            
            # Replace table names with S3 paths in query if needed
            resolved_query = self._resolve_s3_tables_in_query(query)
            
            # Execute the query using parent class method
            result = super().executeQuery(
                resolved_query, 
                limit=None,  # Already applied
                manage_connection=False,  # We manage it here
                use_polars=use_polars,
                batch_size=batch_size,
                profile=profile
            )
            
            if manage_connection:
                self.close()
                
            return result
            
        except Exception as e:
            if manage_connection:
                self.close()
            raise ExecuteQueryException(f"Query execution failed: {str(e)}")

    def _resolve_s3_tables_in_query(self, query):
        """Replace table references with S3 paths in SQL query."""
        if not self.enable_s3:
            return query
        
        # This is a simplified approach - in a production system,
        # you'd want a proper SQL parser
        resolved_query = query
        
        # Get list of available tables (S3 folders) - this already excludes ORC-only folders
        tables = self.get_all_tables()
        
        for table_info in tables:
            table_name = table_info['table_name']
            s3_path = self._get_s3_table_path(table_name)
            
            # Get supported files only (excluding ORC)
            files = self._list_s3_files_in_folder(table_name)
            supported_files = [f for f in files if f['file_format'] in ['parquet', 'csv', 'json']]
            
            if not supported_files:
                # This shouldn't happen since get_all_tables() filters out ORC-only folders
                logging.warning(f"No supported files found in table '{table_name}' - skipping")
                continue
                
            # Use the most common supported format
            file_formats = [f['file_format'] for f in supported_files]
            primary_format = max(set(file_formats), key=file_formats.count)
            
            # Create appropriate read function based on primary supported format
            if primary_format == 'parquet':
                s3_expression = f"read_parquet('{s3_path}*.parquet')"
            elif primary_format == 'csv':
                s3_expression = f"read_csv_auto('{s3_path}*.csv')"
            elif primary_format == 'json':
                s3_expression = f"read_json_auto('{s3_path}*.json')"
            else:
                # This shouldn't happen, but fallback to auto-detection
                s3_expression = f"'{s3_path}*'"
                
            # Replace table references (simple pattern matching)
            # This handles: FROM table_name, JOIN table_name, etc.
            import re
            pattern = r'\b' + re.escape(table_name) + r'\b'
            resolved_query = re.sub(pattern, f"({s3_expression})", resolved_query)
        
        return resolved_query

    def executeSql(self, query, manage_connection=True):
        """Execute SQL statement (DDL/DML operations)."""
        result = {}
        try:
            if manage_connection:
                self.connect()
            
            # Resolve S3 tables in query
            resolved_query = self._resolve_s3_tables_in_query(query)
            
            self.cursor.execute(resolved_query)
            
            result = {
                'status': True,
                'msg': 'SQL executed successfully',
                'affected_rows': self.cursor.rowcount if hasattr(self.cursor, 'rowcount') else 0
            }
            
            if manage_connection:
                self.close()
                
        except Exception as e:
            if manage_connection:
                self.close()
            result = {
                'status': False,
                'msg': f'SQL execution failed: {str(e)}',
                'error': str(e)
            }
        
        return result

    def get_all_tables(self, search=None, type=None, limit=None):
        """Get all tables (S3 folders) available."""
        tables = []
        
        try:
            if self.enable_s3:
                # List S3 folders as tables
                s3_client = self._get_s3_client()
                prefix = self.s3_prefix.rstrip('/') + '/' if self.s3_prefix else ''
                
                # Use paginator for large buckets
                paginator = s3_client.get_paginator('list_objects_v2')
                page_iterator = paginator.paginate(
                    Bucket=self.s3_bucket,
                    Prefix=prefix,
                    Delimiter='/'
                )
                
                for page in page_iterator:
                    # Get folder names (CommonPrefixes are folders)
                    if 'CommonPrefixes' in page:
                        for folder in page['CommonPrefixes']:
                            folder_name = folder['Prefix'][len(prefix):].rstrip('/')
                            if folder_name:  # Skip empty names
                                # Apply search filter if provided
                                if search and search.lower() not in folder_name.lower():
                                    continue
                                
                                # Check file format compatibility
                                try:
                                    files = self._list_s3_files_in_folder(folder_name)
                                    if not files:
                                        # Empty folder - skip it
                                        continue
                                        
                                    # Check if all files are ORC (unsupported)
                                    file_formats = {f['file_format'] for f in files}
                                    
                                    # If folder contains ONLY ORC files, exclude it completely
                                    if file_formats == {'orc'}:
                                        logging.info(f"Excluding folder '{folder_name}' - contains only ORC files (unsupported)")
                                        continue
                                    
                                    # If folder contains mixed formats, warn about ORC files but include the folder
                                    if 'orc' in file_formats:
                                        supported_formats = file_formats - {'orc', 'unknown'}
                                        if supported_formats:
                                            logging.warning(f"Folder '{folder_name}' contains ORC files which will be ignored. "
                                                          f"Supported formats found: {supported_formats}")
                                    
                                    # Determine primary supported format (ignoring ORC)
                                    supported_formats = file_formats - {'orc', 'unknown'}
                                    if not supported_formats:
                                        # Only unsupported formats - skip this folder
                                        continue
                                        
                                    primary_format = next(iter(supported_formats))
                                    file_count = len([f for f in files if f['file_format'] in supported_formats])
                                    
                                    # Determine compatibility status
                                    if primary_format in ['parquet', 'csv', 'json']:
                                        table_type = f'S3_FOLDER ({primary_format.upper()})'
                                        status = 'COMPATIBLE'
                                    else:
                                        table_type = f'S3_FOLDER ({primary_format.upper()} - UNKNOWN)'
                                        status = 'UNKNOWN'
                                        
                                except Exception as e:
                                    logging.error(f"Error checking folder '{folder_name}': {str(e)}")
                                    # Skip folders that we can't analyze
                                    continue
                                
                                tables.append({
                                    'table_name': folder_name,
                                    'table_type': table_type,
                                    'table_schema': 'S3',
                                    'table_catalog': self.s3_bucket,
                                    'file_count': file_count,
                                    'compatibility_status': status
                                })

            else:
                # For local DuckDB, get actual tables
                if self.connection:
                    self.cursor.execute("SHOW TABLES")
                    results = self.cursor.fetchall()
                    
                    for row in results:
                        table_name = row[0]
                        if search and search.lower() not in table_name.lower():
                            continue
                            
                        tables.append({
                            'table_name': table_name,
                            'table_type': 'TABLE',
                            'table_schema': 'main',
                            'table_catalog': 'duckdb'
                        })
            
            # Apply limit if specified
            if limit and isinstance(limit, int):
                tables = tables[:limit]
                
        except Exception as e:
            logging.error(f"Failed to list tables: {str(e)}")
            
        return tables

    def getAllTablesWithColumns(self, search):
        """Get all tables with their column information."""
        tables_with_columns = []
        
        try:
            tables = self.get_all_tables(search=search)
            
            for table_info in tables:
                table_name = table_info['table_name']
                try:
                    columns = self.getTableColumns(table_name)
                    tables_with_columns.append({
                        'table_name': table_name,
                        'table_type': table_info['table_type'],
                        'columns': columns
                    })
                except Exception as e:
                    logging.warning(f"Failed to get columns for table {table_name}: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Failed to get tables with columns: {str(e)}")
            
        return tables_with_columns

    def getTableColumns(self, tablename, type=''):
        """Get column names for a table."""
        try:
            if self.enable_s3:
                schema_info = self._get_s3_table_schema(tablename)
                return [col['COLUMN_NAME'] for col in schema_info]
            else:
                # For local DuckDB tables - ensure connection
                connection_managed = False
                if self.cursor is None:
                    self.connect()
                    connection_managed = True
                
                try:
                    self.cursor.execute(f"DESCRIBE {tablename}")
                    results = self.cursor.fetchall()
                    return [row[0] for row in results]
                finally:
                    if connection_managed:
                        self.close()
                
        except Exception as e:
            logging.error(f"Failed to get columns for table {tablename}: {str(e)}")
            return []

    def getTableColumnsDetails(self, tbl_name, **others):
        """Get detailed column information for a table."""
        try:
            if self.enable_s3:
                return self._get_s3_table_schema(tbl_name)
            else:
                # For local DuckDB tables - ensure connection
                connection_managed = False
                if self.cursor is None:
                    self.connect()
                    connection_managed = True
                
                try:
                    self.cursor.execute(f"DESCRIBE {tbl_name}")
                    results = self.cursor.fetchall()
                    
                    columns = []
                    for row in results:
                        columns.append({
                            'COLUMN_NAME': row[0],
                            'DATA_TYPE': row[1],
                            'IS_NULLABLE': row[2] == 'YES',
                            'COLUMN_DEFAULT': row[4] if len(row) > 4 else None,
                            'CHARACTER_MAXIMUM_LENGTH': None
                        })
                    
                    return columns
                    
                finally:
                    if connection_managed:
                        self.close()
                
        except Exception as e:
            logging.error(f"Failed to get column details for table {tbl_name}: {str(e)}")
            return []

    def readTable(self, tbl_name, limit, **others):
        """Read data from a table."""
        try:
            query = f"SELECT * FROM {tbl_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            return self.executeQuery(query)
            
        except Exception as e:
            raise ExecuteQueryException(f"Failed to read table {tbl_name}: {str(e)}")

    def createTable(self, tableName, etl=False):
        """Create a table - for S3 mode, this creates a folder structure."""
        if self.enable_s3:
            # Create folder structure in S3
            s3_client = self._get_s3_client()
            prefix = self.s3_prefix.rstrip('/') + '/' if self.s3_prefix else ''
            folder_key = f"{prefix}{tableName}/"
            
            try:
                # Create an empty object to represent the folder
                s3_client.put_object(Bucket=self.s3_bucket, Key=folder_key, Body='')
                return {
                    'status': True,
                    'msg': f'S3 folder created: {folder_key}',
                    's3_path': self._get_s3_table_path(tableName)
                }
            except Exception as e:
                return {
                    'status': False,
                    'msg': f'Failed to create S3 folder: {str(e)}'
                }
        else:
            # For local DuckDB, would need table definition
            return {
                'status': False,
                'msg': 'Table creation requires table definition for local DuckDB'
            }

    def truncateTable(self, table_name):
        """Truncate a table - for S3 mode, this removes all files from folder."""
        if self.enable_s3:
            try:
                # Delete all files in the S3 folder
                s3_client = self._get_s3_client()
                prefix = self.s3_prefix.rstrip('/') + '/' if self.s3_prefix else ''
                folder_prefix = f"{prefix}{table_name}/"
                
                # List all objects in the folder
                response = s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=folder_prefix
                )
                
                if 'Contents' in response:
                    # Delete all objects
                    objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                    s3_client.delete_objects(
                        Bucket=self.s3_bucket,
                        Delete={'Objects': objects_to_delete}
                    )
                
                return {
                    'status': True,
                    'msg': f'Truncated S3 table: {table_name}'
                }
                
            except Exception as e:
                return {
                    'status': False,
                    'msg': f'Failed to truncate S3 table: {str(e)}'
                }
        else:
            # For local DuckDB
            try:
                self.cursor.execute(f"DELETE FROM {table_name}")
                return {
                    'status': True,
                    'msg': f'Truncated table: {table_name}'
                }
            except Exception as e:
                return {
                    'status': False,
                    'msg': f'Failed to truncate table: {str(e)}'
                }

    def executeInsertUpdate(self, query, df):
        """Execute insert/update operations with DataFrame."""
        # This is a simplified implementation
        # In production, you'd want to handle batch inserts more efficiently
        try:
            self.connect()
            
            # For DuckDB, we can create a temporary table from pandas DataFrame
            # and then use it in queries
            temp_table_name = f"temp_df_{id(df)}"
            
            # Register DataFrame as a temporary table in DuckDB
            self.connection.register(temp_table_name, df)
            
            # Replace DataFrame references in query with temp table name
            resolved_query = query.replace('df', temp_table_name)
            
            self.cursor.execute(resolved_query)
            
            # Unregister temporary table
            self.connection.unregister(temp_table_name)
            
            self.close()
            
            return {
                'status': True,
                'msg': 'Insert/Update executed successfully'
            }
            
        except Exception as e:
            self.close()
            return {
                'status': False,
                'msg': f'Insert/Update failed: {str(e)}'
            }

    # Implement other abstract methods with basic functionality
    def getColumnLOV(self, table_name, col_name):
        """Get list of values for a column."""
        try:
            query = f"SELECT DISTINCT {col_name} FROM {table_name} ORDER BY {col_name} LIMIT 100"
            result = self.executeQuery(query)
            return result[col_name].tolist() if not result.empty else []
        except Exception:
            return []

    def getColumnsProfile(self, table_name, with_min_max, filter):
        """Get column profiling information."""
        # Basic implementation - can be enhanced
        try:
            columns = self.getTableColumns(table_name)
            profiles = []
            
            for col in columns:
                profile = {
                    'column_name': col,
                    'data_type': 'unknown',
                    'null_count': 0,
                    'distinct_count': 0
                }
                
                try:
                    # Get basic stats
                    stats_query = f"""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT({col}) as non_null_count,
                        COUNT(DISTINCT {col}) as distinct_count
                    FROM {table_name}
                    """
                    stats_result = self.executeQuery(stats_query)
                    if not stats_result.empty:
                        row = stats_result.iloc[0]
                        profile['total_count'] = row['total_count']
                        profile['null_count'] = row['total_count'] - row['non_null_count']
                        profile['distinct_count'] = row['distinct_count']
                        
                except Exception:
                    pass
                    
                profiles.append(profile)
                
            return profiles
            
        except Exception as e:
            logging.error(f"Failed to get column profiles: {str(e)}")
            return []

    def getTableDetails(self, table_name, type={}):
        """Get detailed table information."""
        try:
            details = {
                'table_name': table_name,
                'table_type': 'S3_FOLDER' if self.enable_s3 else 'TABLE',
                'columns': self.getTableColumnsDetails(table_name)
            }
            
            if self.enable_s3:
                files = self._list_s3_files_in_folder(table_name)
                details['file_count'] = len(files)
                details['total_size'] = sum(f['size'] for f in files)
                details['file_formats'] = list(set(f['file_format'] for f in files))
                details['s3_path'] = self._get_s3_table_path(table_name)
            
            return details
            
        except Exception as e:
            logging.error(f"Failed to get table details for {table_name}: {str(e)}")
            return {}

    def getTableRelationships(self, table_name):
        """Get table relationships - not applicable for S3 folders."""
        return []

    def createView(self, view_name, sql_query):
        """Create a view."""
        try:
            create_view_query = f"CREATE VIEW {view_name} AS {sql_query}"
            result = self.executeSql(create_view_query)
            
            if result['status']:
                return {'status': True, 'msg': f'View {view_name} created successfully'}
            else:
                raise ViewCreationError(result['msg'])
                
        except Exception as e:
            raise ViewCreationError(f"Failed to create view {view_name}: {str(e)}")

    def get_incremental_columns(self, table_name, **others):
        """Get columns suitable for incremental processing."""
        try:
            columns = self.getTableColumnsDetails(table_name)
            incremental_columns = []
            
            for col in columns:
                col_name = col['COLUMN_NAME'].lower()
                col_type = col['DATA_TYPE'].lower()
                
                # Look for date/timestamp columns or ID columns
                if ('date' in col_type or 'timestamp' in col_type or 
                    'time' in col_name or 'date' in col_name or
                    'id' in col_name or 'modified' in col_name or 'updated' in col_name):
                    incremental_columns.append(col)
                    
            return incremental_columns
            
        except Exception:
            return []

    def fetch_delta_columns(self, table_name, **others):
        """Fetch delta columns for change tracking."""
        # Basic implementation - can be enhanced based on requirements
        return self.get_incremental_columns(table_name, **others)

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        """Update column comment - not supported for S3 tables."""
        return False

    def find_row(self, tbl_name, row, on_condition, manage_connection):
        """Find a specific row in the table."""
        # Basic implementation
        try:
            conditions = []
            for condition in on_condition:
                col = condition['target_col']
                val = row.get(col, '')
                conditions.append(f"{col} = '{val}'")
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT * FROM {tbl_name} WHERE {where_clause}"
            
            result = self.executeQuery(query, manage_connection=manage_connection)
            return not result.empty
            
        except Exception:
            return False

    def update_row(self, target_table, row, on_condition, matched_mapping, col_details, manage_connection):
        """Update a row in the target table."""
        # Implementation would depend on specific requirements
        # For S3 tables, this would typically involve rewriting files
        return False

    def insert_row(self, target_table, row, non_matched_mapping, col_details, manage_connection):
        """Insert a row into the target table."""
        # Implementation would depend on specific requirements
        # For S3 tables, this would typically involve appending to files
        return False

    def create_engine(self):
        """Create SQLAlchemy engine - DuckDB has experimental SQLAlchemy support."""
        try:
            # DuckDB SQLAlchemy support (experimental)
            engine_url = f"duckdb:///{self.database_path}"
            self.engine_statement = create_engine(engine_url)
            return self.engine_statement
        except Exception as e:
            logging.warning(f"Failed to create SQLAlchemy engine: {str(e)}")
            return None

    def generateQuery(self, tablename=None, columnnames=None, limit=None, 
                     orderby=None, filters=None, groupby=None, distinct=0):
        """Generate SQL query based on parameters."""
        
        # Start with SELECT
        if columnnames and len(columnnames) > 0:
            if distinct:
                select_clause = f"SELECT DISTINCT {', '.join(columnnames)}"
            else:
                select_clause = f"SELECT {', '.join(columnnames)}"
        else:
            select_clause = "SELECT DISTINCT *" if distinct else "SELECT *"
        
        # FROM clause
        from_clause = f"FROM {tablename}" if tablename else ""
        
        # WHERE clause
        where_clause = ""
        if filters:
            # This would need proper filter parsing - simplified version
            where_clause = "WHERE " + " AND ".join(filters)
        
        # GROUP BY clause  
        group_by_clause = ""
        if groupby:
            group_by_clause = f"GROUP BY {', '.join(groupby)}"
        
        # ORDER BY clause
        order_by_clause = ""
        if orderby:
            order_by_clause = f"ORDER BY {', '.join(orderby)}"
        
        # LIMIT clause
        limit_clause = ""
        if limit:
            limit_clause = f"LIMIT {limit}"
        
        # Combine all clauses
        query_parts = [select_clause, from_clause, where_clause, 
                      group_by_clause, order_by_clause, limit_clause]
        query = " ".join([part for part in query_parts if part])
        
        return query

    def db_column_type(self, columns, column_types):
        """Map DuckDB column types to conversion types."""
        type_converters = {}
        
        for col, dtype in zip(columns, column_types):
            # DuckDB type mapping
            dtype_str = str(dtype).upper()
            
            if 'INT' in dtype_str or 'BIGINT' in dtype_str:
                type_converters[col] = ('numeric', self._is_monetary_column(col))
            elif 'FLOAT' in dtype_str or 'DOUBLE' in dtype_str or 'DECIMAL' in dtype_str:
                type_converters[col] = ('numeric', self._is_monetary_column(col))
            elif 'DATE' in dtype_str:
                type_converters[col] = ('date', False)
            elif 'TIMESTAMP' in dtype_str:
                type_converters[col] = ('timestamp', False)
            elif 'BOOL' in dtype_str:
                type_converters[col] = ('boolean', False)
            else:
                type_converters[col] = ('string', False)
                
        return type_converters

    def handle_special_char(self, col):
        """Handle special characters in column names."""
        if ' ' in col or '-' in col or any(c in col for c in ['/', '(', ')', '[', ']']):
            return f'"{col}"'
        return col