import abc
import json
from collections import defaultdict
import gc
import time
import pandas as pd

from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.handlers.__init__ import AUDIT_LOGS
from pypika import Field
from pypika import Criterion
from pypika.functions import Upper, Lower
from sqlalchemy import types as sqlalchemyTypes


class ExecuteQueryException(Exception):
    pass


pattern = "/,"


def getReqSrcCols(columns, filters, joins):
    '''
    columns : dict
    filters : list
    joins : dict
    '''
    src_used_cols = []
    ## columns which are used in update
    src_used_cols.append(list(columns.keys()))

    ## columns which are used in join condition
    src_used_cols.append(list(joins.keys()))

    ## src_used_cols is now list of list, so it need to be flatten
    src_used_cols = [item for sublist in src_used_cols for item in sublist]

    ## columns which are in filter condition
    for x in filters:
        if x["from"] == "source":
            if x["column"] not in src_used_cols:
                src_used_cols.append(x["column"])

    return src_used_cols


## Sample JSON for Create Table
tableDetails = {
    "tableName": "test1",
    "colDetails": [
        {
            "columnName": "id",
            "dbType": "int",
            "length": 0,
            "precision": "",
            "isAutoIncrement": 1,
            "isPrimaryKey": 1,
            "nullable": "false"
        },
        {
            "columnName": "name",
            "dbType": "varchar",
            "length": 100,
            "precision": "",
            "isAutoIncrement": 0,
            "isPrimaryKey": 0,
            "nullable": "false"
        },
        {
            "columnName": "amount",
            "dbType": "decimal",
            "length": 0,
            "precision": "18,3",
            "isAutoIncrement": 0,
            "isPrimaryKey": 0,
            "nullable": "true",
            "default": "0.0"
        }
    ],
    "fk": [
        {
            "columnFK": "id",
            "keyName": "fk_daas_test1_userid",
            "table": "daas_user",
            "column": "id"
        }
    ]
}


def where_condition(
        where=None,
        where_op=None,
        where_val=None,
        query=None
):
    operators_map = {
        "equal": Field(where).eq(where_val),
        "greaterthan": Field(where).gt(where_val),
        "lessthan": Field(where).lt(where_val),
        "greaterthaneq": Field(where).gte(where_val),
        "lessthaneq": Field(where).lte(where_val),
        "notequal": Field(where).ne(where_val),
        "like": Field(where).like(where_val),
        "in": Field(where).isin(where_val),  ## args
        #         "between":Field(where).between(where_val[0],where_val[1])
    }
    ## for more mapping --> help(Field("A")) and check available functions
    return query.where(operators_map[where_op])


# this method used to parse query buider json for filter and generate chained
# filter for pypikka and return sql query for the input filter
def where_recursive_condition_col_dict(
        condition="AND",
        rules=None,
        dbType=None,
        col_date_format_dict=None,
        col_date_format_list=None,
        colDict=None
):

    criterianList = []
    for rule in rules:
        if "rules" in rule:
            criterianList.append(
                where_recursive_condition_col_dict(
                    rule["condition"], rule["rules"],
                    dbType=dbType,
                    col_date_format_dict=col_date_format_dict,
                    col_date_format_list=col_date_format_list
                )
            )
        else:
            if "type" in rule and rule["type"] == 'calendar':
                to_char_dateformat = GetDBDateFormat.get_dbdate_format(db_type=dbType, format_string=rule['format'])
                to_char_dateformat = to_char_dateformat.replace('columnName', rule["field"])
                col_date_format_dict[to_char_dateformat] = to_char_dateformat
                col_date_format_list.append(to_char_dateformat)

    return col_date_format_dict, col_date_format_list


# this method used to parse query buider json for filter and generate chained
# filter for pypikka and return sql query for the input filter

def where_recursive_condition(condition="AND", rules=None, colDict=None):
    criterianList = []
    for rule in rules:
        rule_operator = rule.get("operator")

        if "rules" in rule:
            criterianList.append(
                where_recursive_condition(
                    rule["condition"], rule["rules"],
                    colDict=colDict
                )
            )
        else:
            rule_value = rule.get("value")
            rule_field = rule["field"]
            field = Field(rule_field)

            if "type" in rule and rule["type"] == 'calendar':
                dtFormat = GetDBDateFormat()
                to_char_dateformat = dtFormat.verticaFormatDict[rule['format']]
                comp = None

                if colDict and rule_field in colDict:
                    colDetails = colDict[rule_field][0]
                    if 'comp' in colDetails and colDetails['type'] == 'date' and colDetails['comp']:
                        comp = colDetails['comp']
                        rule_operator = 'in'

                        if comp == 'prev-month':
                            _format = rule["format"].split('-')
                            for i, cal_format in enumerate(_format):
                                if 'm' in cal_format or 'M' in cal_format:
                                    _rule_val_lst = rule_value.split('-')
                                    if _rule_val_lst[i].isnumeric():
                                        _rule_val_lst[i] = int(_rule_val_lst[i])

                                        if _rule_val_lst[i] == 1:
                                            _rule_val_lst[i] = '12'
                                        else:
                                            _rule_val_lst[i] = str(_rule_val_lst[i] - 1).zfill(2)

                                    _rule_val_lst = '-'.join(map(str, _rule_val_lst))
                                    rule_value = rule_value + ',' + _rule_val_lst
                                    break

                        elif comp == 'prev-year' or comp == 'prev-quarter':
                            _format = rule["format"].split('-')
                            for i, cal_format in enumerate(_format):
                                if 'y' in cal_format or 'Y' in cal_format:
                                    _rule_val_lst = rule_value.split('-')
                                    new_val = ''
                                    if _rule_val_lst[i].isnumeric():
                                        _rule_val_lst[i] = str(int(_rule_val_lst[i]) - 1)
                                        new_val = str(int(_rule_val_lst[i]) + 1)
                                    rule_value = new_val + ',' + _rule_val_lst[i]
                                    break

                operators_map = {
                    "equal": Field(to_char_dateformat.replace('columnName', rule_field)).eq(rule_value),
                    "equals": Field(to_char_dateformat.replace('columnName', rule_field)).eq(rule_value),
                    "greaterthan": Field(to_char_dateformat.replace('columnName', rule_field)).gt(rule_value),
                    "lessthan": Field(to_char_dateformat.replace('columnName', rule_field)).lt(rule_value),
                    "greaterthanequal": Field(to_char_dateformat.replace('columnName', rule_field)).gte(rule_value),
                    "greater_or_equal": Field(to_char_dateformat.replace('columnName', rule_field)).gte(rule_value),
                    "lessthanequal": Field(to_char_dateformat.replace('columnName', rule_field)).lte(rule_value),
                    "less_or_equal": Field(to_char_dateformat.replace('columnName', rule_field)).lte(rule_value),
                    "not_equal": Field(to_char_dateformat.replace('columnName', rule_field)).ne(rule_value),
                    "like": Field(to_char_dateformat.replace('columnName', rule_field)).like(rule_value),
                    "isnull": Field(to_char_dateformat.replace('columnName', rule_field)).isnull(),
                    "notnull": Field(to_char_dateformat.replace('columnName', rule_field)).notnull(),
                    "contains": Field(to_char_dateformat.replace('columnName', rule_field)).like(
                        "%" + str(rule_value) + "%"),
                    "startswith": Field(to_char_dateformat.replace('columnName', rule_field)).like(
                        str(rule_value) + "%"),
                    "endswith": Field(to_char_dateformat.replace('columnName', rule_field)).like("%" + str(rule_value)),
                    "in": Field(to_char_dateformat.replace('columnName', rule_field)).isin(rule_value.split(',')),
                }
            else:
                operators_map = {
                    "equal": field.eq(rule_value),
                    "equals": field.eq(rule_value),
                    "greaterthan": field.gt(rule_value),
                    "lessthan": field.lt(rule_value),
                    "greater_or_equal": field.gte(rule_value),
                    "greaterthanequal": field.gte(rule_value),
                    "less_or_equal": field.lte(rule_value),
                    "lessthanequal": field.lte(rule_value),
                    "not_equal": field.ne(rule_value),
                    "like": field.like(rule_value),
                    "isnull": field.isnull(),
                    "notnull": field.notnull(),
                    "contains": field.like("%" + str(rule_value) + "%"),
                    "startswith": field.like(str(rule_value) + "%"),
                    "endswith": field.like("%" + str(rule_value)),
                    "isupper": Upper(field).eq(field),
                    "islower": Lower(field).eq(field),
                }

            if rule_operator == 'in' or rule_operator == 'notin':
                if isinstance(rule_value, str):
                    operators_map["in"] = field.isin(rule_value.split(','))
                    operators_map["notin"] = field.notin(rule_value.split(','))
                else:
                    operators_map["in"] = field.isin([rule_value])
                    operators_map["notin"] = field.notin([rule_value])
            elif rule_operator == 'between':
                if isinstance(rule_value, str):
                    operators_map["between"] = field.between(rule_value.split(",")[0], rule_value.split(",")[1])
                else:
                    operators_map["between"] = field.between(rule_value[0], rule_value[1])
            elif rule_operator == 'dates_between':
                operators_map["dates_between"] = field.between(rule_value[0], rule_value[1])

            criterianList.append(operators_map[rule_operator])

    if condition == "AND":
        return Criterion.all(criterianList)
    else:
        return Criterion.any(criterianList)


def where_Colcondition(
        where=None,
        where_op=None,
        where_val=None,
        query=None
):
    ## for more mapping --> help(Field("A")) and check available functions
    return query.where(Field(where) == Field(where_val))


class ViewCreationError(Exception):
    """Exception raised when a view creation operation fails."""
    pass


class clsDBConnection(metaclass=abc.ABCMeta):
    db_type = ""

    def __init__(self, db_type):
        self.db_type = db_type

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass

    def check_polars_availability(self, use_polars):
        """
        Check if Polars is available for use as a DataFrame library.

        Args:
            use_polars (bool): The current setting for using Polars

        Returns:
            tuple: (use_polars, polars_available) - updated flags based on availability
        """
        polars_available = False

        if use_polars:
            try:
                import polars as pl
                polars_available = True
            except ImportError:
                use_polars = False

        return use_polars, polars_available

    def _apply_query_limit(self, query, limit):
        """
        Apply row limit to query based on database type.

        Args:
            query (str): Original SQL query
            limit (int): Number of rows to limit to

        Returns:
            str: Modified query with limit applied
        """
        if limit is None:
            return query

        if self.db_type == "SQLSERVER":
            # SQL Server uses TOP clause
            if "select" in query.lower():
                query = query.lower().replace("select", f"select top {limit}", 1)
            else:
                query = query.lower().replace("select", f"SELECT TOP {limit}", 1)

        elif self.db_type == "ORACLE":
            if hasattr(self, 'version') and self.version == "old":
                # Oracle older versions use ROWNUM
                if "where" in query.lower():
                    query = query.lower().replace("where", f"where rownum <= {limit} AND", 1)
                else:
                    query += f" where rownum <= {limit}"
            else:
                # Oracle modern versions use FETCH FIRST n ROWS ONLY syntax
                if ";" in query:
                    query = query.replace(";", f" FETCH FIRST {limit} ROWS ONLY;")
                else:
                    query += f" FETCH FIRST {limit} ROWS ONLY"

        else:
            # Most databases use LIMIT clause
            if ";" in query:
                query = query.replace(";", f" limit {limit};")
            else:
                query += f" limit {limit}"

        return query

    def _is_monetary_column(self, column_name):
        """
        Detect if a column likely contains monetary values based on its name.

        Args:
            column_name (str): Name of the column

        Returns:
            bool: True if the column likely contains monetary values
        """
        monetary_terms = ['amount', 'price', 'value', 'cost', 'revenue', 'qty', 'quantity']
        return any(term in column_name.lower() for term in monetary_terms)

    def db_column_type(self, columns, column_types):
        # only implemented in vertica db
        type_converters = {}

        for col, vtype in zip(columns, column_types):
            # this function write inside DBConnection

            # Map Vertica type codes to conversion types
            if vtype in (6, 7, 16):  # Numeric types
                type_converters[col] = ('numeric', False)
        return type_converters


    def _process_with_pandas(self, columns, type_converters, batch_size):
        """
        Process query results using Pandas.

        Args:
            columns (list): Column names
            type_converters (dict): Column type conversion mapping
            batch_size (int): Number of rows to fetch in each batch

        Returns:
            pandas.DataFrame: Result data
        """
        data_chunks = []
        rows_processed = 0

        if self.db_type == "ORACLE":
            import cx_Oracle

        # Process data in chunks to control memory usage
        while True:
            try:
                chunk = self.cursor.fetchmany(batch_size)
            except (AttributeError, TypeError):
                # Fallback for databases that don't support fetchmany with size
                chunk = self.cursor.fetchmany()

            if not chunk:
                break

            rows_processed += len(chunk)

            if self.db_type == "ORACLE":
                # Process each row and handle LOBs
                processed_chunk = []
                for row in chunk:
                    processed_row = []
                    for value in row:
                        if isinstance(value, cx_Oracle.LOB):
                            if value.type == cx_Oracle.CLOB:
                                processed_row.append(value.read())  # Read CLOB data
                            elif value.type == cx_Oracle.BLOB:
                                try:
                                    processed_row.append(value.read().decode('utf-8'))  # Try decoding as text
                                except UnicodeDecodeError:
                                    processed_row.append(value.read())  # Fallback: keep as raw bytes
                        else:
                            processed_row.append(value)
                    processed_chunk.append(processed_row)

                # Create DataFrame from the processed chunk
                chunk_df = pd.DataFrame(processed_chunk, columns=columns)
            else:
                # Create DataFrame from the chunk
                chunk_df = pd.DataFrame(chunk, columns=columns)

            # Apply type conversions efficiently
            for col, (type_name, is_amount) in type_converters.items():
                try:
                    if type_name == 'numeric':
                        if is_amount:
                            # Clean monetary values then convert
                            chunk_df[col] = pd.to_numeric(
                                chunk_df[col].astype(str).str.replace(r'[,$]', '', regex=True),
                                errors='coerce'
                            )
                        else:
                            chunk_df[col] = pd.to_numeric(chunk_df[col], errors='coerce')
                    elif type_name == 'date':
                        chunk_df[col] = pd.to_datetime(chunk_df[col], errors='coerce').dt.date
                    elif type_name == 'timestamp':
                        chunk_df[col] = pd.to_datetime(chunk_df[col], errors='ignore')
                    elif type_name == 'boolean':
                        chunk_df[col] = chunk_df[col].astype('boolean')
                except Exception as e:
                    # Fall back to string type on conversion error
                    chunk_df[col] = chunk_df[col].astype(str)

            data_chunks.append(chunk_df)

            # Clean up to reduce memory pressure
            del chunk
            if self.db_type == "ORACLE":
                del processed_chunk   
            gc.collect()

        # Combine all chunks
        if data_chunks:
            results = pd.concat(data_chunks, ignore_index=True)
            del data_chunks
            gc.collect()
        else:
            # Return empty DataFrame with correct columns
            results = pd.DataFrame(columns=columns)

        return results


    def _process_with_polars(self, columns, type_converters, batch_size):
        """
        Process query results using Polars for better performance.

        Args:
            columns (list): Column names
            type_converters (dict): Column type conversion mapping
            batch_size (int): Number of rows to fetch in each batch

        Returns:
            polars.DataFrame: Result data
        """
        import polars as pl

        if self.db_type == "ORACLE":
            import cx_Oracle

        # Initialize variables
        rows_processed = 0
        data_chunks = []

        # Create polars schema based on column types
        pl_schema = {}
        for col, (type_name, _) in type_converters.items():
            if type_name == 'numeric':
                pl_schema[col] = pl.Float64
            elif type_name in ('date', 'timestamp'):
                pl_schema[col] = pl.Utf8  # Will convert to proper types later
            elif type_name == 'boolean':
                pl_schema[col] = pl.Boolean
            else:
                pl_schema[col] = pl.Utf8

        # Process data in chunks to control memory usage
        while True:
            try:
                chunk = self.cursor.fetchmany(batch_size)
            except (AttributeError, TypeError):
                # Fallback for databases that don't support fetchmany with size
                chunk = self.cursor.fetchmany()

            if not chunk:
                break

            rows_processed += len(chunk)

            try:
                # Pre-allocate column dictionaries for performance
                col_dict = {col: [] for col in columns}

                # Process each row and handle CLOB/BLOB data
                for row in chunk:
                    for i, (col, val) in enumerate(zip(columns, row)):
                        conv_type, is_amount = type_converters[col]

                        if val is None:
                            col_dict[col].append(None)
                            continue

                        if self.db_type == "ORACLE" and isinstance(val, cx_Oracle.LOB):
                            if val.type == cx_Oracle.CLOB:
                                col_dict[col].append(val.read())  # Read CLOB data
                            elif val.type == cx_Oracle.BLOB:
                                col_dict[col].append(val.read().decode('utf-8'))  # Decode BLOB data
                        else:
                            # Apply appropriate type conversion
                            try:
                                if conv_type == 'numeric':
                                    if is_amount and isinstance(val, str):
                                        # Clean monetary values
                                        val = val.replace('$', '').replace(',', '')
                                    col_dict[col].append(float(val) if val is not None else None)
                                elif conv_type == 'date':
                                    col_dict[col].append(val.isoformat() if val is not None else None)
                                elif conv_type == 'timestamp':
                                    col_dict[col].append(val.isoformat() if val is not None else None)
                                elif conv_type == 'boolean':
                                    col_dict[col].append(bool(val) if val is not None else None)
                                else:
                                    col_dict[col].append(str(val) if val is not None else None)
                            except Exception as e:
                                # Log conversion errors but continue processing
                                col_dict[col].append(str(val) if val is not None else None)

                # Create Polars DataFrame for this chunk
                chunk_df = pl.DataFrame(col_dict)

                # Convert date/timestamp strings to proper types and manage null column type
                for col, (type_name, _) in type_converters.items():
                    # Only process date and timestamp columns
                    if type_name not in ('date', 'timestamp') or col not in chunk_df.columns:
                        # manage null type
                        chunk_df = self._manage_null_chunks(chunk_df, col, pl_schema.get(col))
                        continue

                    try:
                        # Choose the appropriate Polars type based on type_name
                        pl_type = pl.Date if type_name == 'date' else pl.Datetime
                        pl_schema[col] = pl_type # update proper schema for date like column
                        # Check if column has any non-null values
                        non_null_count = chunk_df.select(pl.col(col).is_not_null().sum()).item()

                        if non_null_count == 0:
                            # If column has only null values, create a properly typed null column
                            chunk_df = chunk_df.with_columns([
                                pl.lit(None).cast(pl_type).alias(col)
                            ])
                        else:
                            # For mixed columns with some non-null values
                            if type_name == 'date':
                                # Use strptime for date columns with format
                                chunk_df = chunk_df.with_columns([
                                    pl.col(col).str.strptime(pl_type, format="%Y-%m-%d", strict=False).alias(col)
                                ])
                            else:
                                # For timestamp columns, use strptime without format for auto-detection
                                chunk_df = chunk_df.with_columns([
                                    pl.col(col).str.strptime(pl_type, strict=False).alias(col)
                                ])
                    except Exception as e:
                        # If conversion fails, keep the column as string
                        pass

                data_chunks.append(chunk_df)

                # Clean up to reduce memory pressure
                del chunk
                del col_dict
                gc.collect()

            except Exception as e:
                gc.collect()
                raise e

        # Combine all chunks
        if data_chunks:
            # data_chunks = self._cast_conflicting_columns_to_string(data_chunks)
            results = pl.concat(data_chunks)
            del data_chunks
            gc.collect()
            # Optimize memory usage
            results = results.shrink_to_fit()
        else:
            # Return empty DataFrame with correct schema
            results = pl.DataFrame(schema=pl_schema)

        return results

    def _manage_null_chunks(self, df, col, dtype):
        import polars as pl
        # Check if column has any non-null values
        non_null_count = df.select(pl.col(col).is_not_null().sum()).item()

        if non_null_count == 0 and dtype:
            # If column has only null values, create a properly typed null column
            df = df.with_columns([
                pl.lit(None).cast(dtype).alias(col)
            ])
        return df

    def _cast_conflicting_columns_to_string(self, dfs):
        """Automatically detect and cast conflicting columns to string"""
        import polars as pl
        
        # Find columns with different types across DataFrames
        column_types = {}
        for df in dfs:
            for col, dtype in df.schema.items():
                if col not in column_types:
                    column_types[col] = set()
                column_types[col].add(dtype)
        
        # Identify columns with conflicts - ignore Null types
        conflicting_columns = []
        for col, types in column_types.items():
            non_null_types = {t for t in types if t != pl.Null}
            if len(non_null_types) > 1:  # Only conflicts between non-null types
                conflicting_columns.append(col)
        
        print(f"Conflicting columns type in chunks: {conflicting_columns}")
        
        # Cast conflicting columns to string
        fixed_dfs = []
        for df in dfs:
            cast_expressions = []
            for col in df.columns:
                if col in conflicting_columns:
                    cast_expressions.append(pl.col(col).cast(pl.Utf8))
                else:
                    cast_expressions.append(pl.col(col))
            
            df_fixed = df.with_columns(cast_expressions)
            fixed_dfs.append(df_fixed)
        
        return fixed_dfs

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=100000,
                     profile=False):
        """
        Optimized query execution with Polars support focusing on both speed and memory efficiency.
        Compatible with multiple database backends including pymssql.
        """
        timings = defaultdict(float) if profile else None
        results = None

        try:
            use_polars, polars_available = self.check_polars_availability(use_polars)
            # Time connection
            start_time = time.time()
            if manage_connection:
                self.connect()
            if profile:
                timings['connection'] = time.time() - start_time

            # apply limit
            query = self._apply_query_limit(query, limit)

            # Time query execution
            start_time = time.time()
            self.cursor.execute(query)
            if profile:
                timings['query_execution'] = time.time() - start_time

            # Get column information once
            columns = [desc[0] for desc in self.cursor.description]
            column_types = [desc[1] for desc in self.cursor.description]
            type_converters = self.db_column_type(columns, column_types)
            # Time data fetching and processing
            start_time = time.time()

            if use_polars and polars_available:
                results = self._process_with_polars(columns, type_converters, batch_size)
            else:  # Pandas fallback
                results = self._process_with_pandas(columns, type_converters, batch_size)

            if profile:
                timings['data_fetching'] = time.time() - start_time
                timings['rows_processed'] = len(results) if results is not None else 0
                timings['total_time'] = sum(v for k, v in timings.items() if isinstance(v, float))
                timings['rows_per_second'] = (timings['rows_processed'] / timings['total_time']
                                              if timings['total_time'] > 0 else 0)

            if manage_connection:
                close_start = time.time()
                print("closing connection...")
                self.close()
                if profile:
                    timings['connection_close'] = time.time() - close_start

        except Exception as e:
            if manage_connection:
                print("closing connection on exception...")
                self.close()
            raise e

        if profile:
            return results, timings
        return results
    

    @abc.abstractmethod
    def executeInsertUpdate(self, query, df):
        pass

    @abc.abstractmethod
    def testConnection(self):
        pass

    @abc.abstractmethod
    def get_all_tables(self, search=None, type=None, limit=None):
        pass

    @abc.abstractmethod
    def getAllTablesWithColumns(self, search):
        pass

    @abc.abstractmethod
    def getTableColumns(self, tablename, type=''):
        pass

    @abc.abstractmethod
    def getTableColumnsDetails(self, tbl_name, **others):
        pass

    def generate_dataset2(self, cursor, batch_size):
        for row in cursor.fetchmany(batch_size):
            yield row

    @abc.abstractmethod
    def generateQuery(
            self,
            tablename=None,
            columnnames=None,
            limit=None,
            orderby=None,
            filters=None,
            groupby=None,
            distinct=0):
        pass

    @abc.abstractmethod
    def create_engine(self):
        pass

    @abc.abstractmethod
    def executeSql(self, query, manage_connection=True):
        pass

    @abc.abstractmethod
    def readTable(self, tbl_name, limit, **others):
        pass

    @abc.abstractmethod
    def createTable(self, tableName, etl=False):
        pass

    @abc.abstractmethod
    def truncateTable(self, table_name):
        pass

    @abc.abstractmethod
    def getColumnLOV(self, table_name, col_name):
        pass

    @abc.abstractmethod
    def getColumnsProfile(self, table_name, with_min_max, filter):
        pass

    @abc.abstractmethod
    def getTableDetails(self, table_name, type={}):
        pass

    @abc.abstractmethod
    def getTableRelationships(self, table_name):
        pass

    @abc.abstractmethod
    def createView(self, view_name, sql_query):
        pass

    @abc.abstractmethod
    def get_incremental_columns(self, table_name, **others):
        pass

    @abc.abstractmethod
    def fetch_delta_columns(self, table_name, **others):
        pass

    @abc.abstractmethod
    def update_column_comment(self, tbl_name, col_name, comment, **others):
        pass

    @abc.abstractmethod
    def find_row(tbl_name, row, on_condition, manage_connection):
        pass

    @abc.abstractmethod
    def update_row(target_table, row, on_condition, matched_mapping, col_details, manage_connection):
        pass

    @abc.abstractmethod
    def insert_row(target_table, row, non_matched_mapping, col_details, manage_connection):
        pass

    def handle_special_char(self, col):
        return col

    def maxLengthColumn(self, df_column):
        try:
            mx_length = df_column.str.len().max()
            if mx_length < 80:
                mx_length = 80
            return mx_length
        except Exception:
            return 80

    def callConnectionAudit(self, test_conn_response):
        if AUDIT_LOGS in (1, True, "1"):
            try:
                ## moved import inside function as ADAL install will be required if imported on top
                from scikiq_utils.datasource.http.httpHandler import HttpApiHandler
                if test_conn_response:
                    if self.resource_key:
                        conn_config = {}
                        conn_config['resource_key'] = self.resource_key
                        conn_config['resource_type'] = 'connection'
                        conn_config['resource_call'] = None
                        conn_config['connection_response'] = json.dumps(test_conn_response)
                        HttpApiHandler.resource_audit_api_call(conn_config)
                    else:
                        print("Alert: Getting empty resource key so not able to create audit log history.")
                else:
                    raise ValueError("Test connection response is not valid.")
            except Exception as e:
                print(e)

    def formatFilter(self, alias, condition="AND", rules=None, query=None):
        date_time_lis = ["DATETIME", "TMS"]
        replace_col = []
        i = 1
        for rule in rules:
            if "rules" in rule:
                query = self.formatFilter(alias, rule["condition"], rule["rules"], query)
            else:
                if rule["type"].upper() in date_time_lis:
                    if "format" in rule:
                        format_string = rule['format']
                    # elif rule["type"].upper() == "DATE":
                    #     format_string = "yyyy-mm-dd"
                    else:
                        format_string = "yy-mm-dd hh:mm:ss"

                    format_string = GetDBDateFormat.get_dbdate_format(db_type=self.db_type, format_string=format_string)
                    temp_qry = format_string.replace('columnName', f'"{alias}"."{rule["field"]}_$${str(i)}"')
                    replace_col.append({"column_name": rule["field"] + "_$$" + str(i), "o_field": rule["field"]})
                    query = query.replace(f'"{rule["field"]}"', temp_qry, 1)
                    i += 1
        for data in replace_col:
            query = query.replace(f'"{data["column_name"]}"', data["o_field"])

        return query

    def getMergeQuery(
            self,
            src_table_name,
            tgt_table_name,
            on_condition,
            matched_mapping,
            non_matched_mapping,
            on_match="UPDATE",
            on_not_match="INSERT",
            filter_condition=[],
            target_encloser=''
    ):
        raise NotImplementedError("Merge Statement Not supported for the selected database!!")

    def getDropTableQuery(self, table_name):
        # return  f"DROP TABLE IF EXISTS {table_name}"
        raise NotImplementedError("Not Implemented Error !!")

    def getTableColumnDtypes(self, table_name):
        list_of_dict = self.getTableColumnsDetails(table_name)
        col_dtype = {x['COLUMN_NAME']: (x['DATA_TYPE']).upper() for x in list_of_dict}
        col_dtype_len = {x['COLUMN_NAME']: x['CHARACTER_MAXIMUM_LENGTH'] for x in list_of_dict}
        col_dtype = {k: v.split("(")[0] for k, v in col_dtype.items()}

        return col_dtype, col_dtype_len

    def getSqlAlchemyDtype(self, src_df, target_tbl_name, src_target_mapping):
        dtypedict = {}
        target_col_dtype, col_dtype_len = self.getTableColumnDtypes(target_tbl_name)

        for src_col_name, src_col_type in zip(src_df.columns, src_df.dtypes):

            if src_col_name in src_target_mapping:
                trgt_mapped_col = src_target_mapping[src_col_name]
                # getting target column name mapped with source

                if trgt_mapped_col != '' or trgt_mapped_col is not None:
                    trgt_col_dtype = target_col_dtype[trgt_mapped_col]
                    trgt_col_dtype_len = col_dtype_len[trgt_mapped_col]

                    if trgt_col_dtype in ('TEXT', 'STR', 'VARCHAR', 'VARCHAR2', 'LONG VARCHAR', 'NVARCHAR', 'CHAR'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR(length=int(trgt_col_dtype_len))})
                    elif trgt_col_dtype == 'INT':
                        dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                    elif trgt_col_dtype in ('FLOAT', 'DEC', 'NUMERIC', 'NUMBER'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                    elif trgt_col_dtype in ('BOOLEAN', 'BOL'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                    elif trgt_col_dtype in ('TIMESTAMP', 'DATE', 'DAT', 'TMS'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})
            else:
                dtype_str = str(src_col_type)
                if "category" in dtype_str:
                    dtype_str = str(src_col_type.categories.dtype)

                if "object" in dtype_str:
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                elif "int" in dtype_str:
                    dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                elif "float" in dtype_str:
                    dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                elif "bool" in dtype_str:
                    dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                elif "date" in dtype_str:
                    dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})

        return dtypedict

    def generateCreateTableScriptETL(self, tableDetails):
        table_name = tableDetails["tableName"]
        create_column_data = tableDetails['createColumnData']

        sep = '"'
        createQuery = f'CREATE TABLE   {table_name}  '

        lst_cols = []
        if len(create_column_data) > 0:
            for inpDict in create_column_data:
                col = inpDict['target_column']
                datatype = inpDict['datatype']
                col_query = f' {sep}{col}{sep} {datatype}'
                lst_cols.append(col_query)

        cols_query = ",".join(lst_cols)
        query = f'''{createQuery} ( {cols_query} ) '''

        return query

    def target_col_listforinsert(self, unmatched_mapping, encloser='"'):
        insert_query = ""
        if len(unmatched_mapping) > 0:
            insrt_list = []
            for target_column, _ in unmatched_mapping.items():
                target_column = self.handle_special_char(target_column)
                insrt_list.append(f'{encloser}{target_column}{encloser}')

            insert_query = ",".join(insrt_list)

        return insert_query

    def src_col_listforinsert(self, unmatched_mapping, encloser='"'):
        insert_query = ""
        if len(unmatched_mapping) > 0:
            insrt_list = []
            for _, src_column in unmatched_mapping.items():
                src_column = self.handle_special_char(src_column)
                insrt_list.append(f'ot.{encloser}{src_column}{encloser}')

            insert_query = ",".join(insrt_list)

        return insert_query

    def set_stmt_forupdate(self, set_stmt_tmpl, matched_mapping):
        insert_query = ""
        if len(matched_mapping) > 0:
            insrt_list = []
            for target_column, src_column in matched_mapping.items():
                src_column = self.handle_special_char(src_column)
                insrt_list.append(set_stmt_tmpl.format(
                    src_col=src_column,
                    tgt_col=target_column
                ))

            insert_query = ",".join(insrt_list)

        return insert_query

    def join_insert_query(
            self,
            src_table_name,
            tgt_table_name,
            on_condition,
            non_matched_mapping,
            filter_condition,
            encloser
    ):

        '''
            -- template insert
            INSERT INTO {encloser}{target_tbl}{encloser} ({target_cols})
            SELECT {src_cols} FROM {encloser}{src_tbl}{encloser} ot
            LEFT OUTER JOIN {encloser}{target_tbl}{encloser} ot2
                ON ot.{encloser}{src_col}{encloser} = ot2.{encloser}{tgt_col}{encloser}
            WHERE ot2.{encloser}{tgt_col}{encloser} IS NULL

            -- on condition template
            ot.{encloser}{src_col}{encloser} = ot2.{encloser}{tgt_col}{encloser}

            -- where condition template
            ot2.{encloser}{tgt_col}{encloser} IS NULL
        '''

        main_tmpl = '''
            INSERT INTO {encloser}{target_tbl}{encloser} ({target_cols})
            SELECT {src_cols} FROM {encloser}{src_tbl}{encloser} ot
            LEFT OUTER JOIN {encloser}{target_tbl}{encloser} ot2
                ON {on_condition}
            WHERE 1=1 {where_condition}
        '''

        on_condition_tmpl = '''ot.{encloser}{src_col}{encloser} = ot2.{encloser}{tgt_col}{encloser}'''
        on_clause = self.get_on_condition(on_condition_tmpl, on_condition, tgt_table_name, encloser=encloser)

        ##TODO: null condtion and where condition will make full where clause
        null_condition_tmpl = ''' AND ot2.{encloser}{tgt_col}{encloser} IS NULL'''
        where_clause = self.get_null_condition(null_condition_tmpl, on_condition, encloser)
        ##TODO: where condition template is pending
        fltr_condition_tmpl = ''' AND {src_tgt_alias}.{encloser}{col}{encloser} {opr} {val}'''
        where_clause += self.get_filter_condition(
            filter_condition_tmpl=fltr_condition_tmpl,
            filter_condition=filter_condition,
            src_alias="ot",
            tgt_alias="ot2",
            encloser=encloser
        )

        print("on_clause: " + on_clause)
        print("where_clause: " + where_clause)

        ## get source col list
        src_cols = self.src_col_listforinsert(non_matched_mapping, encloser)
        ## get target col list
        target_cols = self.target_col_listforinsert(non_matched_mapping, encloser)

        qry = main_tmpl.format(
            target_tbl=tgt_table_name,
            target_cols=target_cols,
            src_cols=src_cols,
            src_tbl=src_table_name,
            on_condition=on_clause,
            where_condition=where_clause,
            encloser=encloser
        )

        print("Query: " + qry)

        return qry

    def join_upd_query(
            self,
            src_table_name,
            tgt_table_name,
            on_condition,
            matched_mapping,
            filter_condition
    ):

        '''
            -- template update
            UPDATE "{target_tbl}" i
            SET "{tgt_col}" = i2."{src_col}"
            FROM "{src_tbl}" i2
            WHERE i."{src_col}" = i2."{tgt_col}"

            -- where condition template
            AND i."{src_col}" = i2."{tgt_col}"
        '''

        main_tmpl = '''
            UPDATE "{target_tbl}" i
            SET {set_stmt}
            FROM "{src_tbl}" i2
            WHERE 1=1 {where_condition}
        '''

        where_condition_tmpl = '''AND i."{tgt_col}" = i2."{src_col}"'''
        where_clause = self.get_on_condition(
            where_condition_tmpl,
            on_condition=on_condition,
            target_tbl=tgt_table_name,
            sep=" "
        )

        fltr_condition_tmpl = ''' AND {src_tgt_alias}."{col}" {opr} {val}'''
        where_clause += self.get_filter_condition(
            filter_condition_tmpl=fltr_condition_tmpl,
            filter_condition=filter_condition,
            src_alias="i2",
            tgt_alias="i"
        )

        ## get source col list
        set_stmt_template = '''"{tgt_col}" = i2."{src_col}"'''
        set_stmt = self.set_stmt_forupdate(set_stmt_template, matched_mapping)

        qry = main_tmpl.format(
            target_tbl=tgt_table_name,
            set_stmt=set_stmt,
            src_tbl=src_table_name,
            where_condition=where_clause
        )

        print("Query: " + qry)

        return qry

    def join_del_query(
            self,
            src_table_name,
            tgt_table_name,
            on_condition,
            filter_condition,
            encloser
    ):

        '''
            -- template delete
            DELETE FROM {encloser}{target_tbl}{encloser}
            WHERE EXISTS (
                SELECT NULL FROM {encloser}{src_tbl}{encloser} i WHERE 1=1
                -- loop for on clause and where clause
                AND i.{encloser}{src_col}{encloser} = {encloser}{target_tbl}{encloser}.{encloser}{tgt_col}{encloser}
                AND i.{encloser}{src_col}{encloser} {operator} {value}
            )

            -- where_condtion_tmpl
            AND i.{encloser}{src_col}{encloser}{operator} {value}
        '''

        main_tmpl = '''
            DELETE FROM {encloser}{target_tbl}{encloser} 
            WHERE EXISTS (
                SELECT NULL FROM {encloser}{src_tbl}{encloser} i WHERE 1=1 {others}
            )
        '''

        on_condition_tmpl = ' AND i.{encloser}{src_col}{encloser} {opr} {encloser}{target_tbl}{encloser}.{encloser}{tgt_col}{encloser}'

        where_clause = self.get_on_condition(on_condition_tmpl, on_condition, tgt_table_name, sep="", encloser=encloser)

        fltr_condition_tmpl = ''' AND {src_tgt_alias} {encloser}{col}{encloser} {opr} {val}'''
        where_clause += self.get_filter_condition(
            filter_condition_tmpl=fltr_condition_tmpl,
            filter_condition=filter_condition,
            src_alias="i.",
            tgt_alias="",
            encloser=encloser
        )

        print("where_condtion: " + where_clause)

        qry = main_tmpl.format(
            target_tbl=tgt_table_name,
            src_tbl=src_table_name,
            others=where_clause,
            encloser=encloser
        )

        print("Query: " + qry)

        return qry

    def get_null_condition(self, where_condition_tmpl, where_clause, encloser='"'):

        '''ot2."{tgt_col}" IS NULL'''

        if len(where_clause) == 0:
            raise ValueError("ON condition can not be empty")

        on_list = []

        for condition in where_clause:
            target_column = self.handle_special_char(condition.get("target_col"))

            on_list.append(where_condition_tmpl.format(
                tgt_col=target_column,
                encloser=encloser
            ))

        ## multiple condition sud be join using "and"
        on_query = " ".join(on_list)

        return on_query

    def get_on_condition(self, on_condition_tmpl, on_condition, target_tbl, sep=" AND ", encloser='"'):

        if len(on_condition) == 0:
            raise ValueError("ON condition can not be empty")

        on_list = []

        for condition in on_condition:
            operator = condition.get("condition")
            source_column = self.handle_special_char(condition.get("source_col"))
            target_column = self.handle_special_char(condition.get("target_col"))

            on_list.append(on_condition_tmpl.format(
                src_col=source_column,
                opr=operator,
                tgt_col=target_column,
                target_tbl=target_tbl,
                encloser=encloser
            ))

        ## multiple condition sud be join using "and"
        on_query = sep.join(on_list)

        return on_query

    def get_filter_condition(self, filter_condition_tmpl, filter_condition, src_alias, tgt_alias, sep=" AND ",
                             encloser='"'):

        """
        Insert Query filter template

        fltr_condition_tmpl = ''' AND {src_tgt_alias}."{col}" {opr} {val}'''
        """

        fltr_list = []
        fltr_query = ""

        for condition in filter_condition:
            operator = condition.get("condition")
            col = self.handle_special_char(condition.get("col"))
            val = condition.get("value", "")
            col_type = condition.get("col_type", "src")

            src_tgt_alias = tgt_alias
            if col_type == "src":
                src_tgt_alias = src_alias

            if operator == "isnull":
                operator = "is null"
                val = ""
            elif operator == "notnull":
                operator = "is not null"
                val = ""

            fltr_list.append(filter_condition_tmpl.format(
                col=col,
                opr=operator,
                val=val,
                src_tgt_alias=src_tgt_alias,
                encloser=encloser
            ))

        ## multiple condition sud be join using "and"
        fltr_query = sep.join(fltr_list)

        return fltr_query
    

    def get_filtered_row_count(self, table_name, filter="1=1"):
        if not filter or filter.strip() == "1=1":
            return None
        try:
            # Determine table reference based on DB type
            if self.db_type == "MYSQL":
                # MySQL: no schema, use backticks
                table_ref = f"`{table_name}`"
            elif self.db_type == "BIGQUERY":
                # BigQuery format is `dataset_id.table_name`
                if self.dataset_id:
                    table_ref = f"`{self.dataset_id}`.`{table_name}`"
                else:
                    table_ref = f"`{table_name}`"
            else:
                #Other DBs: use schema if available, and double quotes
                if self.schema:
                    table_ref = f'"{self.schema}"."{table_name}"'
                else:
                    table_ref = f'"{table_name}"'

            query = f"SELECT COUNT(*) AS ROW_COUNT FROM {table_ref} WHERE {filter}"
            df = self.executeQuery(query)

            df.columns = df.columns.str.upper()

            if not df.empty:
                return int(df["ROW_COUNT"][0])
        except Exception:
            return 0

        return 0


class MergeStatement:
    def __init__(self,
                 source_table,
                 target_table,
                 on_condition,
                 matched_mapping,
                 non_matched_mapping,
                 on_match="UPDATE",
                 on_not_match="INSERT",
                 filter_condition=[],
                 use_alias=True,
                 encloser='',
                 target_encloser=''
                 ):

        self.source_table = source_table
        self.target_table = target_table
        self.matched_mapping = matched_mapping
        self.non_matched_mapping = non_matched_mapping
        self.on_condtion_mapping = on_condition

        self.on_match = on_match
        self.on_not_match = on_not_match
        self.filter_condition = filter_condition
        self.use_alias = use_alias
        self.encloser = encloser
        self.target_encloser = target_encloser

    def merge_init(self):
        if self.use_alias:
            if self.target_encloser:
                query = f'''MERGE INTO {self.target_encloser}{self.target_table}{self.target_encloser} AS tgt USING {self.source_table} AS src '''
            else:
                query = f'''MERGE INTO {self.encloser}{self.target_table}{self.encloser} AS tgt USING {self.encloser}{self.source_table}{self.encloser} AS src '''
        else:
            query = f'''MERGE INTO {self.encloser}{self.target_table}{self.encloser} tgt USING {self.source_table} src '''

        return query

    def handle_special_char(self, col):
        # if " " in col or "/" in col :
        #     col = f'"{col}"'
        if len(self.encloser) > 0:
            col = f'{self.encloser}{col}{self.encloser}'

        return col

    def write_on_condition(self):
        if len(self.on_condtion_mapping) == 0:
            raise ValueError("ON condition can not be empty")

        on_list = []

        for condition in self.on_condtion_mapping:
            operator = condition.get("condition")
            source_column = self.handle_special_char(condition.get("source_col"))
            target_column = self.handle_special_char(condition.get("target_col"))
            on_list.append(f'tgt.{target_column} {operator} src.{source_column}')

        ## multiple condition sud be join using "and"
        on_query = " and ".join(on_list)

        fltr_list = []
        fltr_query = ""

        ## code changes to handle filter condition
        fltr_condition_tmpl = ''' AND {src_tgt_alias}.{col} {opr} {val}'''
        for condition in self.filter_condition:
            operator = condition.get("condition")
            col = self.handle_special_char(condition.get("col"))
            val = condition.get("value", "")
            col_type = condition.get("col_type", "src")

            src_tgt_alias = 'tgt'
            if col_type == "src":
                src_tgt_alias = 'src'

            if operator == "isnull":
                operator = "is null"
                val = ""
            elif operator == "notnull":
                operator = "is not null"
                val = ""

            fltr_list.append(fltr_condition_tmpl.format(
                col=col,
                opr=operator,
                val=val,
                src_tgt_alias=src_tgt_alias
            ))

        ## multiple condition sud be join using "and"
        fltr_query = ' '.join(fltr_list)

        query = f'ON  ({on_query + fltr_query})'

        return query

    def write_when_matched(self):
        update_or_others = self.write_query(self.on_match, self.matched_mapping)
        query = " "
        # if no query generated
        if len(update_or_others) > 0:
            query = f'WHEN MATCHED THEN  {update_or_others}'
        return query

    def write_when_not_matched(self):
        update_or_others = self.write_query(self.on_not_match, self.non_matched_mapping)
        query = " "
        # if no query generated
        if len(update_or_others) > 0:
            query = f'WHEN NOT MATCHED THEN {update_or_others}'
        return query

    def write_update_query(self, dict_mapping):
        query = ''
        if len(dict_mapping) > 0:
            update_statement = 'UPDATE SET'
            update_list = []
            for target_column, source_column in dict_mapping.items():
                # Don't put tgt here-- vertica raises error
                target_column = self.handle_special_char(target_column)
                source_column = self.handle_special_char(source_column)
                update_list.append(f'{target_column}=src.{source_column}')
            update_query = ",".join(update_list)
            query = f'{update_statement} {update_query}'
        return query

    def write_insert_query(self, dict_mapping):
        insert_query = ''
        if len(dict_mapping) > 0:
            insert_stmt = "INSERT "
            columns_stmt = ",".join(
                [self.handle_special_char(col) for col in list(dict_mapping)])  ## keys must target_column
            values_stmt = ",".join(
                [f'src.{self.handle_special_char(src_col)}' for src_col in dict_mapping.values()])  # values src column
            insert_query = f'{insert_stmt} ({columns_stmt}) VALUES ({values_stmt})'
        return insert_query

    def write_query(self, condition, dict_mapping):
        if condition.upper() == "UPDATE":
            query = self.write_update_query(dict_mapping)
        elif condition.upper() == "INSERT":
            query = self.write_insert_query(dict_mapping)
        else:
            query = ""
        return query

    def get_query(self):
        merge_stmt = self.merge_init()
        on_query = self.write_on_condition()
        when_matched_query = self.write_when_matched()
        when_not_matched_query = self.write_when_not_matched()
        final_query = f'{merge_stmt} \n {on_query}\n{when_matched_query} \n{when_not_matched_query}'

        return final_query
    

