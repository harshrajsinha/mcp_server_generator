# PYTHON PACKAGES
import cx_Oracle  ## Oracle
import pandas as pd
import uuid
import operator
import json
from collections import OrderedDict
from pypika.queries import QueryBuilder, QueryException
from pypika.utils import builder
from pypika.enums import Dialects
from pypika import Order
from pypika import Query, Table, Field,JoinType
from pypika import Tables
from pypika import OracleQuery
from pypika import functions as fn
from sqlalchemy import text, create_engine, types as sqlalchemyTypes
from urllib.parse import quote
from sqlalchemy.sql import quoted_name


# CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.handlers.DBConnection import clsDBConnection, ViewCreationError, where_recursive_condition, where_condition,MergeStatement
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression

'''
For running code on local machine 
cx_Oracle.init_oracle_client(lib_dir="C:\\OracleInstaClient\\instantclient_21_9")
'''

pattern = "/,"

class OracleQueryBuilder(QueryBuilder):
    def __init__(self):
        super(OracleQueryBuilder, self).__init__(dialect=Dialects.ORACLE)
        self._top = None

    @builder
    def limit(self, value):

        try:
            self._limit = int(value)
        except ValueError:
            raise QueryException("Limit value must be an integer")

    def get_sql(self, *args, **kwargs):
        return super(OracleQueryBuilder, self).get_sql(
            *args, groupby_alias=False, **kwargs
        )

    def _limit_sql(self):
        if self._limit:
            return " FETCH NEXT {} ROWS ONLY".format(str(self._limit))
        else:
            return ""

    def _select_sql(self, **kwargs):
        return "SELECT {distinct}{select} ".format(
            distinct="DISTINCT " if self._distinct else "",
            select=",".join(
                term.get_sql(with_alias=True, subquery=True, **kwargs)
                for term in self._selects
            ),
        )


class OracleQuery(Query):
    """
    Defines a query class for use with Oracle Database.
    """

    @classmethod
    def _builder(cls):
        return OracleQueryBuilder()


class clsOracleDB(clsDBConnection):
    """
        Usage:
            db = OracleDB("user", "pass", "yourserver.com", 1523, "YOUR_SID")
            db.connect()
            db.cursor.execute("SELECT yourcolumn FROM yourtable")
            result1 = [x[0] for x in db.cursor]
            db.close()
            db.connect()
            db.cursor.execute("SELECT yourothercolumn FROM yourothertable")
            result2 = [x[0] for x in db.cursor]
            db.close()
            # do stuff with result1 and result2 ...
    """

    def __init__(self, config):

        self.host = config["hostname"]
        self.port = config["port"]
        self.dbname = config["dbname"]
        self.user = config["dbuser"]
        self.password = config["pwd"]

        self.engine_statement = None
        self.connection = None
        self.cursor = None

        self.resource_key = config.get("resource_key")

        self.schema = config.get("schema")

        self.service_or_sid = config.get("service_or_sid", "SID")

        if self.service_or_sid == "SERVICE_NAME":
            self.tns = cx_Oracle.makedsn(self.host, str(self.port), service_name=self.dbname)
        else:
            self.tns = cx_Oracle.makedsn(self.host, str(self.port), self.dbname)

        self.connection_type = config.get("connection_type")

        self.version = self.getVersion()

        self.db_type = "ORACLE"

    def getConnectionType(self):
        if self.connection_type is None:
            return "SR"
        else:
            return self.connection_type
        
    def update_column_comment(self, tbl_name, col_name, comment, **others):
        success = True
        try :
            self.connect()
            if comment :
                qry = """COMMENT ON COLUMN "{schema}"."{table_name}"."{column_name}" IS '{comment}';""".format(
                    schema=self.schema,
                    comment=comment,
                    table_name=tbl_name,
                    column_name=col_name
                )            
            else :
               qry = """COMMENT ON COLUMN "{schema}"."{table_name}"."{column_name}" IS '';""".format(
                    schema=self.schema,
                    table_name=tbl_name,
                    column_name=col_name
                )         
            self.executeSql(qry)
        except Exception as e :
            self.close()
            print(e)
            success = False
        return success        

    def getVersion(self):
        vrn = "new"
        try:
            qry = "SELECT BANNER FROM v$version WHERE banner LIKE 'Oracle%'"
            vrn = self.executeQuery(qry)
            if "11g" in vrn["BANNER"][0] or "12c" in vrn["BANNER"][0]:
                vrn = "old"
            else:
                vrn = "new"
        except Exception:
            vrn = "new"

        return vrn

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'

            # cx_Oracle.connect("user/pw@dsn", encoding = "UTF-8", nencoding = "UTF-8")

            self.connection = cx_Oracle.connect(self.user, self.password, self.tns, encoding="UTF-8", nencoding="UTF-8")

            if self.schema:
                if self.schema.isupper():
                    self.connection.current_schema = self.schema
                else:
                    self.connection.current_schema = f'"{self.schema}"'

            self.cursor = self.connection.cursor()

            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsOracleDB, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsOracleDB, self).callConnectionAudit(resp)
            raise

    def close(self):
        if self.cursor:
            self.cursor.close()

        if self.connection:
            self.connection.close()

    def testConnection(self):
        resp = {}
        try:
            cx_Oracle.connect(self.user, self.password, self.tns)
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS
        except cx_Oracle.DatabaseError as exc:
            error, = exc.args
            resp['error'] = 1
            if error.code == 1017:
                resp['msg'] = ScikiqMessages.MSG_INCORRECT_DB_CREDENTIALS
            else:
                resp['msg'] = "Database Error | Error Code :" + str(error.code) + "| Error Message :" + error.message
        except Exception as e:
            resp['error'] = 1
            resp['msg'] = str(e)

        # callConnectionAudit using for audit the record.
        super(clsOracleDB, self).callConnectionAudit(resp)

        return resp

    def createView(self, view_name, sql_query):
        '''
           @Description : View is the result set of a stored query on the data.
           param:
           view_name: view name (required)
           sql_query: query for view(required)
        '''
        try:
            crt_stmt = "CREATE OR REPLACE VIEW {} AS {}".format(view_name, sql_query)
            res = self.executeSql(crt_stmt)
            if not res['status']:
                print(res['msg'])
                # Raise an exception with the response message
                raise ViewCreationError(f"Failed to create view '{view_name}': {res['msg']}")
        except Exception as e:
            print(e)
            raise
        return view_name

    def generate_dataset2(self, cursor, batch_size):
        for row in cursor.fetchmany(batch_size):
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
            yield processed_row
            
    
    def executeQueryOld(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=10000, profile=False):
        if manage_connection:
            self.connect()
        try:
            if limit is not None:
                if self.version == "old":
                    if "where" in query:
                        query = query.replace("where", "where rownum <={} AND ".format(str(limit)))
                    elif "WHERE" in query:
                        query = query.replace("WHERE", "WHERE rownum <={} AND ".format(str(limit)))
                    else:
                        query += " where rownum <={} ".format(limit)
                else:
                    if ";" in query:
                        query = query.replace(";", " FETCH NEXT " + str(limit) + " ROWS ONLY")
                    else:
                        query = query + " FETCH NEXT " + str(limit) + " ROWS ONLY"

            # Execute the query
            self.cursor.execute(query)

            # Fetch results and handle CLOB/BLOB data
            columns = [col[0] for col in self.cursor.description]
            data = []
            for row in self.cursor:
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
                data.append(processed_row)

            # Convert to DataFrame
            results = pd.DataFrame(data, columns=columns)

            if manage_connection:
                self.close()

            return results

        except Exception as e:
            if manage_connection:
                self.close()
            print(e)
            raise

    def getSqlAlchemyDtype(self,src_df,target_tbl_name,src_target_mapping):
        dtypedict = {}
        target_col_dtype,col_dtype_len = self.getTableColumnDtypes(target_tbl_name)
        
        for src_col_name ,src_col_type in zip(src_df.columns,src_df.dtypes):
        
            if src_col_name in  src_target_mapping:
                trgt_mapped_col = src_target_mapping[src_col_name]
                # getting target column name mapped with source

                if trgt_mapped_col !='' or trgt_mapped_col is not None:
                    trgt_col_dtype = target_col_dtype[trgt_mapped_col]
                    trgt_col_dtype_len = col_dtype_len[trgt_mapped_col]

                    if trgt_col_dtype in ('TEXT','STR','VARCHAR', 'VARCHAR2', 'LONG VARCHAR','NVARCHAR','CHAR')  :
                        dtypedict.update({src_col_name:sqlalchemyTypes.NVARCHAR(length=int(trgt_col_dtype_len))})
                    elif trgt_col_dtype =='INT'  :
                        dtypedict.update({src_col_name:sqlalchemyTypes.INT}) 
                    elif  trgt_col_dtype in ('FLOAT', 'DEC','NUMERIC','NUMBER') :
                        dtypedict.update({src_col_name:sqlalchemyTypes.FLOAT}) 
                    elif trgt_col_dtype in ('BOOLEAN','BOL') :
                        dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                    elif trgt_col_dtype in ('TIMESTAMP','DATE', 'DAT', 'TMS', 'DATETIME') :
                        dtypedict.update({src_col_name: sqlalchemyTypes.TIMESTAMP})
            else:
                dtype_str = str(src_col_type)
                if "category" in  dtype_str:
                    dtype_str = str(src_col_type.categories.dtype)

                if "object" in dtype_str  :
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                elif "int" in dtype_str :
                    dtypedict.update({src_col_name:sqlalchemyTypes.INT}) 
                elif "float" in dtype_str :
                    dtypedict.update({src_col_name:sqlalchemyTypes.FLOAT}) 
                elif "bool" in dtype_str  :
                    dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                elif "date" in dtype_str :
                    dtypedict.update({src_col_name: sqlalchemyTypes.TIMESTAMP})

        return dtypedict


    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=1000, dtype={}):
        self.create_engine()
        
        # Retrieve column details from the database
        col_details = self.getTableColumns(tablename)
        col_type_mapping = {col[0].upper(): col[1].upper() for col in col_details}  # Map column names to their data types
        
        # Initialize dtype dictionary using col_details
        dtypedict = {}
        for col_name, db_col_type in col_type_mapping.items():
            if db_col_type == "CLOB":
                dtypedict[col_name] = sqlalchemyTypes.CLOB
                if col_name in df.columns:
                    df[col_name] = df[col_name].apply(lambda x: x if isinstance(x, str) else str(x))  # Ensure strings for CLOB
            elif db_col_type == "BLOB":
                dtypedict[col_name] = sqlalchemyTypes.BLOB  # BLOB maps to BLOB
                if col_name in df.columns:
                    df[col_name] = df[col_name].apply(lambda x: x.encode('utf-8') if isinstance(x, str) else x)  # Encode strings for BLOB
            elif db_col_type in ["VARCHAR2", "CHAR", "NVARCHAR2"]:
                dtypedict[col_name] = sqlalchemyTypes.VARCHAR(length=4000)  # Set max length
            elif db_col_type in ["NUMBER", "FLOAT"]:
                dtypedict[col_name] = sqlalchemyTypes.FLOAT
            elif db_col_type == "DATE":
                dtypedict[col_name] = sqlalchemyTypes.DATE
            elif db_col_type in ("TIMESTAMP", "TIMESTAMP(6)", "TIMESTAMP(3)"):
                dtypedict[col_name] = sqlalchemyTypes.TIMESTAMP
            elif db_col_type == "RAW":
                dtypedict[col_name] = sqlalchemyTypes.VARBINARY  # RAW maps to VARBINARY
            else:
                dtypedict[col_name] = sqlalchemyTypes.VARCHAR(length=4000)
        
        # Quote schema if provided
        quoted_schema = quoted_name(self.schema, quote=True) if self.schema else None

        # Ensure quoted table name
        quoted_tbl_name = quoted_name(tablename, quote=True)

        # Quote all column names to preserve case-sensitivity
        df.columns = [quoted_name(col, quote=True) for col in df.columns]

        with self.engine_statement.connect() as connection:
            # Insert data into the database
            try:
                df.to_sql(
                    con=connection,
                    name=quoted_tbl_name,
                    dtype=dtypedict,
                    if_exists=if_exists,
                    index=False,
                    schema=quoted_schema,
                    chunksize=chunksize
                )
            except cx_Oracle.DatabaseError as e:
                print(f"Database error occurred: {e}")
                raise

        return df



    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()

        query = "SELECT OBJECT_NAME AS TABLE_NAME,OBJECT_TYPE as TABLE_TYPE, OWNER AS TABLE_SCHEMA FROM ALL_OBJECTS "

        if include_view == True:
            query += " WHERE OBJECT_TYPE in ('TABLE','VIEW')"
        else:
            query += " WHERE OBJECT_TYPE = 'TABLE'"

        ## search.upper() when drop table flag is checked on etl create table 
        ## and this function is called then tables are not found as the case in upper
        if (search):
            query += " AND OBJECT_NAME LIKE '%{}%'".format(search.upper())

        if self.schema:
            query += "  AND OWNER = '{}'".format(self.schema)

        query += ' ORDER BY TABLE_NAME ASC'

        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()

        return results

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)

        self.connect()

        tables = []
        for tbl in results:

            cols = {}
            tbl = list(tbl)[0]
            cols["tablename"] = tbl

            sub_query = """
                SELECT 
                    COL.COLUMN_NAME AS COLUMN_NAME, 
                    COL.DATA_TYPE AS DATA_TYPE 
                FROM SYS.ALL_TAB_COLUMNS COL 
                INNER JOIN SYS.ALL_TABLES T 
                    ON COL.OWNER = T.OWNER 
                AND COL.TABLE_NAME = T.TABLE_NAME 
                WHERE 1 = 1  
                AND COL.TABLE_NAME = '{}'
            """.format(tbl)

            if self.schema:
                sub_query += " AND COL.OWNER = '{}'".format(self.schema)

            sub_query += ' ORDER BY COL.COLUMN_NAME '

            self.cursor.execute(sub_query)
            cols["columnname"] = self.cursor.fetchall()
            tables.append(cols)

        self.close()
        return tables

    def getTableColumns(self, tablename, type=''):
        query = """ 
            SELECT 
                COL.COLUMN_NAME AS COLUMN_NAME, 
                COL.DATA_TYPE AS DATA_TYPE 
            FROM SYS.ALL_TAB_COLUMNS COL 
            INNER JOIN SYS.ALL_TABLES T 
                ON COL.OWNER = T.OWNER 
            AND COL.TABLE_NAME = T.TABLE_NAME 
            WHERE COL.TABLE_NAME ='{}'
        """.format(tablename)

        if self.schema:
            query += " AND COL.OWNER = '{}'".format(self.schema)

        query += " ORDER BY COLUMN_NAME "

        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()

        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        test_type= self.getTableDetails(table_name=tbl_name)
        t_type = test_type['TABLE_TYPE'][0]

        self.connect() 

        query = """
            SELECT col.OWNER AS "TABLE_SCHEMA", 
                col.TABLE_NAME AS "TABLE_NAME", 
                '{}' as "TABLE_TYPE",
                col.COLUMN_NAME AS "COLUMN_NAME",
                col.DATA_TYPE AS "DATA_TYPE",
                col.DATA_LENGTH AS DATA_TYPE_LENGTH,
                col.COLUMN_ID AS "ORDINAL_POSITION",
                col.DATA_PRECISION AS "NUMERIC_PRECISION",
                col.DATA_SCALE AS "NUMERIC_SCALE",
                CASE WHEN upper(col.NULLABLE) = 'Y' THEN 1 ELSE 0 END AS "IS_NULLABLE",
                col.CHAR_LENGTH AS "CHARACTER_MAXIMUM_LENGTH",
                CASE WHEN col.DATA_PRECISION IS NOT NULL THEN concat(concat(col.DATA_PRECISION,','),col.DATA_SCALE) 
                WHEN col.DATA_PRECISION  IS NULL AND col.DATA_SCALE IS NOT NULL THEN CAST(col.DATA_SCALE  AS varchar(10)) 
                ELSE CAST(col.data_length  AS varchar(10)) end AS "CHARACTER_MAX_LENGTH",
                CASE WHEN cmnts.COMMENTS IS NULL THEN ''  ELSE cmnts.COMMENTS END AS "COMMENT",
                col.DATA_DEFAULT AS "COLUMN_DEFAULT",
                CASE WHEN upper(AC.CONSTRAINT_TYPE) = 'P' THEN 1 ELSE 0 END AS "IS_PRIMARYKEY",
                CASE WHEN upper(AC.CONSTRAINT_TYPE) = 'U' THEN 1 ELSE 0 END AS "IS_UNIQUEKEY",
                '' AS "IS_NONUNIQUEKEY",
                CASE WHEN d.REFERENCED_NAME IS NOT NULL THEN 1 ELSE 0 END AS "AUTO_INCREMENT",
                col.DATA_LENGTH AS "COLUMN_LENGTH",
                CASE WHEN col.DATA_PRECISION > 0 THEN col.DATA_PRECISION ELSE 0 END AS  "COLUMN_PRECISION",
                CASE WHEN col.CHARACTER_SET_NAME IS NULL THEN '' ELSE col.CHARACTER_SET_NAME END AS "COLUMN_CHARACTERSET",
                CASE WHEN acc.CONSTRAINT_NAME IS NULL THEN '' ELSE acc.CONSTRAINT_NAME END AS "CONSTRAINT_NAME",
                CASE WHEN (ac.CONSTRAINT_TYPE) = 'R' THEN ac.TABLE_NAME ELSE '' END AS "REFERENCED_TABLENAME",
                CASE WHEN (ac.CONSTRAINT_TYPE) = 'R' THEN acc.COLUMN_NAME ELSE '' END AS "REFERENCED_COLUMNNAME",
                CASE WHEN acc.CONSTRAINT_NAME IS NOT NULL THEN 'yes' ELSE 'no' END AS "KEY_COL" 
            FROM all_tab_columns col
            LEFT JOIN ALL_COL_COMMENTS cmnts 
                ON col.OWNER = cmnts.OWNER 
                AND col.TABLE_NAME = cmnts.TABLE_NAME 
                AND col.COLUMN_NAME = cmnts.COLUMN_NAME 
            LEFT JOIN ALL_CONS_COLUMNS acc 
                ON col.TABLE_NAME = acc.TABLE_NAME 
                AND col.OWNER = acc.OWNER 
                AND acc.COLUMN_NAME = col.COLUMN_NAME 
                AND acc.POSITION = 1 
            LEFT JOIN ALL_CONSTRAINTS ac 
                ON acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME 
                AND col.OWNER = ac.OWNER 
                AND ac.TABLE_NAME = col.TABLE_NAME 
            LEFT JOIN user_trigger_cols t 
                ON col.TABLE_NAME = t.TABLE_NAME 
                AND col.COLUMN_NAME = t.COLUMN_NAME 
                AND t.TABLE_OWNER = col.OWNER 
            LEFT JOIN user_dependencies d 
                ON d.referenced_type = 'SEQUENCE' 
                AND d.type = 'TRIGGER' 
                AND t.TRIGGER_NAME = d.NAME  
            WHERE upper(col.TABLE_NAME) ='{}'
        """.format(t_type,tbl_name.upper())

        if self.schema:
            query += " AND col.OWNER = '{}'".format(self.schema)

        if sort_on_position:
            query += " ORDER BY col.COLUMN_ID"
        else:
            query += " ORDER BY col.COLUMN_NAME"
        self.cursor.execute(query)
        desc_value = [d[0] for d in self.cursor.description]
        desc = [item.upper() for item in desc_value]
        results = [dict(zip(desc, res)) for res in self.cursor.fetchall()]
        self.close()

        return results

    def getRenamesColMetricsDict(self, config_details=OrderedDict()):
        col_dict = OrderedDict()
        col_lst = []
        
        col_idx_dict = {}
        if config_details:
            # Get column key and alias name with list of vlaues
            for key, col_details in config_details.items():
                for lst in col_details:
                    col_dict[key] = lst['alias']
                    col_lst.append(key)
            # Get column occurences of the data.
            for key, _ in col_dict.items():
                indices = [index for index, element in enumerate(col_lst) if element == key]
                col_idx_dict[key] = indices

        return col_idx_dict

    def generateQuery(
            self, 
            tablename=None, 
            columnnames=None, 
            limit=None,
            orderby=None, 
            filters=None, 
            groupby=None, 
            joins=None,
            joinCondition=None, 
            distinct=0,
            offset=None
        ):

        if tablename is None:
            raise ValueError("Table Name Required")

        tbls = {}
        tbl_names = {}
        ## table name is a key value pair {"dim_projects" : "dp"} tablename and alias
        if tablename is not None:
            for key in tablename.keys():
                tblName = key
                alias = tablename[tblName]

                if not self.schema:
                    tbls[alias] = Table(tblName, alias=alias)
                else:
                    tbls[alias] = Table(tblName, alias=alias, schema=self.schema)

                tbl_names[alias] = tblName

        index = 0
        for key in tbls.keys():
            if index == 0:
                _query = OracleQuery.from_(tbls[key])
            else:
                if tbl_names[key] in joins:
                    join_type = joins[tbl_names[key]]
                    if join_type == "inner":
                        how = join_type.inner
                    elif join_type == "right":
                        how = join_type.right
                    elif join_type == "left":
                        how = join_type.left
                    elif join_type == "full":
                        how = join_type.full

                    _query = _query.join(tbls[key], how).on(
                        eval('tbls[list(joinCondition[index-1]["left"].keys())[0]]' + '.' +
                             list(joinCondition[index - 1]["left"].values())[
                                 0] + ' == ' + 'tbls[list(joinCondition[index-1]["right"].keys())[0]]' + '.' +
                             list(joinCondition[index - 1]["right"].values())[0])
                    )

            index = index + 1

        if columnnames is not None:
            agg_func = {
                "SUM": fn.Sum,
                "AVG": fn.Avg,
                "MIN": fn.Min,
                "MAX": fn.Max,
                "COUNT": fn.Count,
            }

            field_lst = []

            # Add column names which is derived/custom columns by user
            custom_column_names_dict = {}

            for key, value in columnnames.items():
                ## Change input pattern now value will be list
                for lst_item in value:
                    ## if condition to handle json from build model
                    ## "dim_project0.projectid" : ""  ## alisa.colname : agg fun and
                    ## else condtion to handle json from ETL
                    ## "projectid":"SUM" ## colname:AGG fun

                    ## if . found in column and but doesn't have table json format, raises error on eval
                    ## validation should be at front end level also
                    if "." in key and key.split(".")[0] in tbls:
                        key = key.split(".")
                        coltblName = key[0]
                        colName = key[1]
                        if value != '':
                            # field_lst.append(Field(tbls[coltblName], agg_func[value](colName)))
                            field_lst.append(agg_func[value](eval('tbls[coltblName]' + "." + colName)))
                        else:
                            if " as " in colName:
                                field_lst.append(Field(colName.split(" as ")[0], table=tbls[coltblName],
                                                       alias=colName.split(" as ")[1]))
                            else:
                                field_lst.append(Field(colName, table=tbls[coltblName]))
                    else:
                        if str(lst_item['agg']).upper() == 'DISTINCT COUNT':
                            field_lst.append(fn.Count(Field(key), alias=lst_item['alias']).distinct())
                        elif lst_item['agg'] == 'total_record_count' :
                            field_lst.append(agg_func["COUNT"]('*',alias=lst_item['alias']))
                        elif lst_item['agg'] != '':
                            field_lst.append(
                                agg_func[str(lst_item['agg']).upper()](Field(key), alias=lst_item['alias']))
                        else:
                            field_lst.append(Field(key).as_(lst_item['alias']))

                    # Add custom column in the list.
                    if 'column_type' in lst_item.keys():
                        if lst_item['column_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = lst_item['expression']
                    elif 'col_type' in lst_item.keys():
                        if lst_item['col_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = lst_item['expression']

        if distinct:
            _query = _query.select(*field_lst).distinct()
        else:
            _query = _query.select(*field_lst)

        set_old_limit = False
        if limit is not None:
            if isinstance(limit, list) and len(limit) == 1:
                limit = int(limit[0])
            elif isinstance(limit, str):
                limit = int(limit)

            if isinstance(limit, int):
                if self.version == "old":
                    set_old_limit = True
                else:
                    _query = _query.limit(limit)

        #add offset
        if offset  is not None:
            _query = _query.offset(offset)

        if filters is not None and "rules" in filters:
            _query = _query.where(where_recursive_condition(filters["condition"], filters["rules"]))                    

        ## Oracle 11g/12c format is different from current Oracle version
        if set_old_limit and limit is not None:
            _query = _query.where(operator.le(Field('rownum'), int(limit)))            

        if orderby is not None:
            if isinstance(orderby, dict):  ## deprecated in new version 2021/08/31

                try:
                    order_asc = Order.asc if orderby['direction'] == 'ASC' else Order.desc
                    _query = _query.orderby(*orderby['columns'], order=order_asc)
                except Exception as e :
                    print(e)
                    __column_names_list = columnnames.keys()

                    for key, value in orderby.items():
                        order_asc = Order.asc if value == 'ASC' else Order.desc
                        col_idx_dict = self.getRenamesColMetricsDict(columnnames)
                        if key in __column_names_list:
                            if key in col_idx_dict:
                                for _index in col_idx_dict[key]:
                                    _query = _query.orderby(_index + 1, order=order_asc)

            elif isinstance(orderby, list):
                for dct in orderby:
                    for col, asc_desc in dct.items():
                        order_asc = Order.asc if asc_desc == 'ASC' else Order.desc
                        _query = _query.orderby(col, order=order_asc)

        if groupby is not None:
            for key, value in groupby.items():
                _query = _query.groupby(key)                

        query = _query.get_sql()

        ## fix due to issue in Orcle 11g when limit is used with group by or order by 
        query = query.replace('"rownum"', 'rownum')

        query = self.formatQuery(tablename, query, groupby, filters, columnnames, self.schema)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)

        return query



    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                formatString = GetDBDateFormat.get_dbdate_format(db_type="ORACLE", format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, formatString, _dict,db_type="ORACLE")
                if (not column_expression):
                    column_expression = _dict['expression_value']
                query = query.replace(_key, column_expression, 1)
                expression_column_names_lst.append(column_expression)
        return (query, expression_column_names_lst)

    def formatQuery(self, tablename, query, groupby=None, filters=None, columnnames=None, schema=None):
        ## if no filters or group by then no need to format query
        if not (filters or groupby):
            return query

        elif len(filters) == 0 and len(groupby.keys()) == 0:
            return query

        for key in tablename.keys():
            table = key
            alias = tablename[key]

        selectClause = query.split(' FROM ')[0]

        ## changes done because there is no filter but limit is used for supporting Oracle 11g
        if filters is not None or groupby is not None or 'WHERE' in query:
            if len(filters) != 0 or 'WHERE' in query:
                whereClause = query.split('WHERE')[1]
            if groupby:
                if len(groupby) > 0 and (len(filters) > 0 or 'WHERE' in query):
                    whereClause = whereClause.split('GROUP BY')[0]
                    groupClause = query.split('GROUP BY')[1]
                elif len(groupby) > 0:
                    groupClause = query.split('GROUP BY')[1]

        for key, value in columnnames.items():
            for item in value:
                if "type" in item:
                    if item['type'] == 'date' and item['format'] != '':
                        formatString = GetDBDateFormat.get_dbdate_format(db_type="ORACLE", format_string=item['format'])
                        tempQuery = formatString
                        tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        tempQuery = tempQuery.replace('alias', '"' + item['alias'] + '"')
                        tempQuery = tempQuery.replace('colFormat', formatString)
                        selectClause = selectClause.replace('"' + key + '"', tempQuery, 1)

        if filters is not None and "rules" in filters:
            whereClause = self.formatFilter(alias, filters["condition"], filters["rules"], whereClause)

        if groupby is not None and len(groupby) != 0:
            for key, value in groupby.items():
                if "type" in value:
                    if (value['type'].upper() == 'DATE' and value['format'] != ''):
                        formatString = GetDBDateFormat.get_dbdate_format(db_type="ORACLE", format_string=value['format'])
                        tempQuery = formatString
                        tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        tempQuery = tempQuery.replace('alias', '"' + key + '"')
                        tempQuery = tempQuery.replace('colFormat', formatString)
                        groupClause = groupClause.replace('"' + alias + '"' + '.' + '"' + key + '"', tempQuery, 1)

        ## schema not used in this function as schema already added while creating connection
        if len(filters) > 0 or 'WHERE' in query:
            selectClause += ' FROM "{table_name}" "{alias}" WHERE {where_clause}'.format(
                table_name = table, 
                alias=alias,
                where_clause=whereClause
            )
        else:
            selectClause += ' FROM "{table_name}" "{alias}" '.format(table_name=table, alias=alias)

        if groupby and len(groupby) > 0:
                selectClause += ' GROUP BY {}'.format(groupClause)

        return selectClause

    def create_engine(self):
        if self.service_or_sid == "SERVICE_NAME":
            self.engine_statement = create_engine(
                    f'oracle+cx_oracle://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/?service_name={self.dbname}'
            )
        else:
            self.engine_statement = create_engine(f'oracle+cx_oracle://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}')


    def get_connection_statement(self):
        statement = f"oracle+cx_oracle://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}"
        return statement
    
    def executeSql(self, query, manage_connection=True):
        success = 0
        msg = ScikiqMessages.MSG_SUCCESS
        x = -1
        try:
            if manage_connection:
                self.connect()
            self.cursor.execute(query)
            x = self.cursor.rowcount
            self.connection.commit()
            if manage_connection:
                self.close()
            success = 1
        except Exception as e:
            if manage_connection:
                self.close()
            msg = str(e)
            success = 0

        res = {}
        res["status"] = success
        res["result"] = x
        res["msg"] = msg

        return res

    def getUpdateQuery(
            self, 
            targetTableName, 
            columnnames={}, 
            filters=[], 
            joins={}, 
            inputTableReplica='temp_table',
            sqlQuery=None
        ):
        filters = None if filters == [
            {"from": "", "column": "", "operator": "", "value": ""}] or filters == [] else filters
        
        test, final = Tables(inputTableReplica, targetTableName)
        
        _query = OracleQuery.update(final)

        if joins:
            _query = _query.join(test, JoinType.inner)
            joinslist = []
            for k, v in joins.items():
                joinslist.append(Field(v, table=final) == Field(k, table=test))
            strss = ''
            strs = 'joinslist'
            for i in range(len(joinslist)):
                s = "[" + str(i) + "]"
                word = strs + s
                if i + 1 != len(joinslist):
                    word += " & "
                strss += word
            _query = _query.on(eval(strss))
        
        if columnnames:
            if joins:
                for k, v in columnnames.items():
                    _query = _query.set(Field(v, table=final), Field(k, table=test))
            else:
                for k, v in columnnames.items():
                    _query = _query.set(Field(v, table=final), k)
        
        if filters:
            
            for filt in filters:
                node_from = filt['from']
                wherew = filt['column']
                if node_from == "source":  ## test side
                    where = f'{inputTableReplica}"."{wherew}'
                else:
                    ## final side
                    where = f'{targetTableName}"."{wherew}'
                try:
                    where_val = eval(filt['value'])
                except Exception:
                    where_val = filters[where]['filterValue']
                where_op = filt['operator']

                _query = where_condition(where=where, query=_query, where_val=where_val, where_op=where_op)

        return _query.get_sql()

    # added tableDetails parameter to pass table columns data type
    def updateTable(
            self, 
            df, 
            targetTableName, 
            columnnames={}, 
            filters=[], 
            joins={}, 
            fromTable = None, 
            sameSchema = False,
            tableDetails = {}, 
            sqlQuery = None
        ):
        ##found_rows=False https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1        
        input_tbl_replica = f'temp_table' + str(uuid.uuid1()) if fromTable is None else fromTable
        input_tbl_replica = input_tbl_replica.replace('-', '_')
        print('Temp table used for update', input_tbl_replica)
        sql = self.getUpdateQuery(targetTableName, columnnames, filters, joins, input_tbl_replica)
        self.create_engine()
        if input_tbl_replica not in sql:
            with self.engine_statement.begin() as conn:  # TRANSACTION
                conn.execute(sql)
        else:
            try:
                df.to_sql(input_tbl_replica, self.engine_statement, if_exists='replace')
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    t = conn.execute(sql)
                    print("matched rows = {}".format(t.rowcount))
                    s = conn.execute("DROP TABLE IF EXISTS " + input_tbl_replica)
            except Exception as e:
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    sql = f'DROP TABLE IF EXISTS "' + input_tbl_replica + '"'
                    s = conn.execute(sql)
                raise Exception(e)
        return df, sql


    def readTable(self, tbl_name, limit, **others):
        manage_connection = others.get("manage_connection", True)
        # TODO:For use of random_sample keyword see readTable function of vertica.
        if not self.schema:
            query = f'SELECT * FROM "{tbl_name}"'
        else:
            query = f'SELECT * FROM "{self.schema}"."{tbl_name}"'

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection = manage_connection)
        res["df_text"] = None

        return res


    def truncateTable(self, table_name):
        query = f'TRUNCATE TABLE "{table_name}"'
        self.executeSql(query)

    # TODO: generateCreateTableScript function need to be tested for Oracle
    def generateCreateTableScript(self, tableDetails):
        query = f'CREATE TABLE {tableDetails["tableName"]} ('

        lenCol = len(tableDetails["colDetails"])
        index = 0
        for x in tableDetails["colDetails"]:
            index += 1
            query = query + ' "' + x['columnName'] + '"'
            if (int(x['length']) > 0 and x['dbType'] in ("char", "varchar")):
                query += " " + x['dbType'] + "(" + str(x['length']) + ")"
            elif x['dbType'] == "int":
                query += " " + x['dbType']
                if x['isPrimaryKey'] == 1:
                    query += " PRIMARY KEY"
                if x['isAutoIncrement'] == 1:
                    query += " AUTO_INCREMENT"
            elif x['dbType'] == "decimal":
                query += " " + x['dbType'] + "(" + str(x['precision']) + ")"

            if x['nullable'] == "true":
                query += " NULL"
            else:
                query += " NOT NULL"

            if 'default' in x and len(x["default"]) > 0:
                    query += " DEFAULT " + x["default"]

            if (index < lenCol):
                query += ","
            else:
                ## Add FK contraints
                if 'fk' in tableDetails:
                    lenFK = len(tableDetails["fk"])
                    fkIndex = 0
                    fkQuery = ","
                    for y in tableDetails["fk"]:
                        fkIndex += 1
                        # CONSTRAINT "daas_assets_created_by_4ce65b17_fk_daas_user_id" FOREIGN KEY ("created_by") REFERENCES "daas_user" ("id"),
                        fkQuery += " CONSTRAINT " + y['keyName'] + " FOREIGN KEY (`" + y[
                            'columnFK'] + "`) REFERENCES `" + y['table'] + "` (`" + y['column'] + '`)'
                        if (fkIndex < lenFK):
                            fkQuery += ","

                    query += fkQuery
                query += ")"

        return query

    def generateCreateTableScriptETL(self, tableDetails):

        tbl_name = tableDetails["tableName"]
        col_data = tableDetails['createColumnData']
        # col_data =[{'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'} ..]
        
        sep = '"'
        sep_e = '"'
        ## pandas to_sql not able to write in table with table name in lowercase
        ddl_qry = f'CREATE TABLE {sep}{tbl_name}{sep_e}'

        lst_cols = []

        if len(col_data) > 0:
            for col_dtls in col_data:
                ## pandas to_sql not able to write in table with column name in lowercase
                col = col_dtls['target_column']
                datatype = col_dtls['datatype']
                
                datatype =  "TIMESTAMP" if datatype == "DATETIME" else datatype
                col_query = f' {sep}{col}{sep_e} {datatype}'
                lst_cols.append(col_query)

        cols_query = ",".join(lst_cols)
        query = f'''{ddl_qry} ( {cols_query} ) '''

        return query

    def createTable(self, tableDetails, etl=False):
        if etl == True:
            query = self.generateCreateTableScriptETL(tableDetails)
            return self.executeSql(query)
        else:
            query = self.generateCreateTableScript(tableDetails)

        self.executeSql(query)

        return True

    def getColumnLOV(self, table_name, col_name, order='ASC'):
        self.connect()
        full_table_name = table_name

        if self.schema is not None:
            full_table_name = '"' + self.schema + '".' + full_table_name

        query = 'SELECT DISTINCT "{col_name}" as "values" FROM {tbl_name} WHERE 1 = 1 ORDER BY "{col_name}" {order}'.format(
            col_name=col_name,
            tbl_name=full_table_name,
            order=order
        )

        results = pd.read_sql(query, self.connection)

        self.close()

        return results['values'].tolist()

    def getColumnsProfile(self, table_name, with_min_max=False, filter=None):
        dfColDtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = table_name
        if not self.schema:
            full_table_name = f'"{self.schema}"."{full_table_name}"'

        index = 0

        for row in dfColDtls:
            if row["DATA_TYPE"] in ['TIMESTAMP', 'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'DOUBLE PRECISION',
                                    'SMALLINT', 'INTEGER', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL']:
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE  , """
                if with_min_max:
                    sub_query += """  
                                    TO_CHAR(max("{col_name}")) AS MAX_VAL, 
                                    TO_CHAR(min("{col_name}")) AS MIN_VAL, """
                sub_query += """
                                    COUNT(distinct "{col_name}") AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """
            elif row["DATA_TYPE"] in ['CLOB', 'BLOB' ]:
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE  , """
                if with_min_max:
                    sub_query += """  
                                    'NA' AS MAX_VAL, 
                                    'NA' AS MIN_VAL, """
                sub_query += """
                                    COUNT(1) AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """                
            else:
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE , """
                if with_min_max:
                    sub_query += """  
                                    TO_CHAR(max(0)) AS MAX_VAL, 
                                    TO_CHAR(min(0)) AS MIN_VAL, """
                sub_query += """
                                    COUNT(distinct "{col_name}") AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """

            sub_query += """ FROM "{table_name}"  """

            if filter:
                sub_query += " WHERE " + filter

            sub_query += " GROUP BY 1 "

            sub_query = sub_query.format(col_name=row["COLUMN_NAME"], data_type=row["DATA_TYPE"],
                                         table_name=full_table_name)

            df_sub = self.executeQuery(sub_query)

            if index == 0:
                df = df_sub.copy()
            else:
                df = pd.concat([df, df_sub])

            index += 1

        return df
    
    
    def UpdateAllTableStatistics(self):
        """Update statistics for all tables in the schema at once using Oracle's efficient method."""
        self.connect()
        
        if not self.schema:
            raise ValueError("Schema must be specified to update statistics")
        
        query = f"""
        BEGIN
            DBMS_STATS.GATHER_SCHEMA_STATS(
                ownname => '"{self.schema}"',
                estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE  
            );  
        END;
        """

        try:
            self.cursor.execute(query)
            self.connection.commit()
        except Exception:
            pass
        finally:
            self.close()


    def getTableDetails(self, table_name = None, type={}):
        sep = "','"

        # Update statistics if requested - do this BEFORE any other queries
        # we want to update the row_count

        if self.schema:
            self.UpdateAllTableStatistics()
        
        if table_name:
            if isinstance(table_name, list):
                table_name = "'{}'".format(sep.join(table_name))
            else:
                table_name = "'{}'".format(table_name)
        
        query = """
                select 	a.owner as TABLE_SCHEMA,
                        a.table_name as TABLE_NAME,
                        c.num_column as NO_OF_COLS,
                        NVL(s.size_in_mb, 0) as SIZE_IN_MB,
                        o.OBJECT_TYPE as TABLE_TYPE,
                        '' as TABLE_COMMENT,
                        NVL(a.num_rows, 0) AS NO_OF_ROWS,
                        a.last_analyzed AS LAST_UPDATED
                FROM all_tables a  
                INNER JOIN ALL_OBJECTS o
                    ON a.OWNER = o.OWNER 
                    AND a.table_name = o.OBJECT_NAME                  
                left JOIN (
                    SELECT
                        owner, 
                        table_name,
                        count(column_name) AS num_column
                    FROM ALL_TAB_COLUMNS GROUP BY owner,table_name
                ) c 
                    on c.table_name = a.table_name AND c.owner = a.owner
                LEFT JOIN (
                    select 
                    segment_name,
                    sum(bytes)/1024/1024 AS size_in_mb 
                    from USER_SEGMENTS
                    GROUP BY  segment_name
                ) s 
                    ON s.segment_name = a.table_name 
                    
                WHERE 1=1                    
            """

        if table_name:
            query += """ AND upper(a.table_name) in ({table_name})""".format(table_name=table_name.upper())  ##upper() because oracle supports only table in uppercase
        
        if self.schema:
            query += " AND a.owner = '" + self.schema + "'"


        query += """

             union
            select 	a.owner as TABLE_SCHEMA,
                    a.view_name as TABLE_NAME,
                    c.num_column as NO_OF_COLS,
                    0 as SIZE_IN_MB,
                    o.OBJECT_TYPE as TABLE_TYPE,
                    '' as TABLE_COMMENT,
                    0 AS NO_OF_ROWS,
                    o.LAST_DDL_TIME AS LAST_UPDATED
            FROM all_views a 
            INNER JOIN ALL_OBJECTS o
                ON a.OWNER = o.OWNER 
                AND a.VIEW_NAME = o.OBJECT_NAME 
            left JOIN (
                SELECT 
                    owner,
                    table_name,
                    count(column_name) AS num_column
                FROM ALL_TAB_COLUMNS GROUP BY owner,table_name
            ) c 
                on c.table_name = a.view_name AND c.owner = a.owner

            WHERE 1=1 
        """
        if table_name:
            query += """ and upper(a.view_name) in ({table_name})""".format(table_name=table_name.upper())
        
        if self.schema:
            query += " AND a.owner = '" + self.schema + "'"        

        df = self.executeQuery(query, limit=None)
        
        return df

    def getTableRelationships(self, table_name, bi_directional=False):

        query = f"""
            WITH fk_constraints AS (
            SELECT
                c1.TABLE_NAME AS table_name,
                c2.COLUMN_NAME AS col_name,
                c1.r_constraint_name AS ref_constraint_name
            FROM
            all_constraints c1
            LEFT JOIN
                all_cons_columns c2 ON c1.CONSTRAINT_NAME = c2.CONSTRAINT_NAME
            WHERE
                c1.constraint_type = 'R'
                AND c1.r_constraint_name IN (
                SELECT constraint_name
                FROM all_constraints
                WHERE constraint_type IN ('P', 'U')
                AND table_name = UPPER('{table_name}')
                ^1
            )
            ),
            pk_constraints AS (
            SELECT
                c1.CONSTRAINT_NAME AS ref_constraint_name,
                c1.TABLE_NAME AS ref_table_name,
                c2.COLUMN_NAME AS ref_col_name
            FROM
            all_constraints c1
            LEFT JOIN
                all_cons_columns c2 ON c1.CONSTRAINT_NAME = c2.CONSTRAINT_NAME
            WHERE
                c1.constraint_type IN ('P', 'U')
                AND c1.table_name = UPPER('{table_name}')
                ^1
            )
            SELECT
            fk.table_name as "table_name",
            fk.col_name as "col_name",
            pk.ref_table_name as "ref_table_name",
            pk.ref_col_name as "ref_col_name"
            FROM
            fk_constraints fk
            LEFT JOIN
            pk_constraints pk ON fk.ref_constraint_name = pk.ref_constraint_name
        """

        if self.schema:
            query = query.replace("^1", " AND c1.OWNER = '{schema}' ".format(schema=self.schema))
        else:
            query = query.replace("^1", '')

        query = query.format(table_name=table_name.upper(),schema=self.schema)
        
        df = self.executeQuery(query, limit=None)

        return df
    
    def getMergeQuery(self,
                      
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

        mrgstmt = MergeStatement(
            source_table = src_table_name,
            target_table = tgt_table_name,
            on_condition=on_condition,
            matched_mapping = matched_mapping,
            non_matched_mapping = non_matched_mapping,
            on_match =on_match,
            on_not_match= on_not_match,
            filter_condition=filter_condition,
            use_alias=False,
            encloser = '"' ,
            target_encloser = target_encloser 
        )

        merge_query = mrgstmt.get_query()
    
        return merge_query    

    def getDropTableQuery(self, table_name):
        return f"DROP TABLE {table_name}"

    def dropTable(self, table_name):
        query = self.getDropTableQuery(table_name)
        self.executeSql(query)    

    def getTableIndexDetails(self, tablename):
        query = """
            SELECT aic.TABLE_OWNER AS "TABLE_SCHEMA", 
            aic.TABLE_NAME AS "TABLE_NAME", 
            aic.COLUMN_NAME AS "COLUMN_NAME",
            aic.INDEX_NAME AS "INDEX_NAME",
            di.INDEX_TYPE AS "INDEX_TYPE",
            aic.COLUMN_POSITION AS "SEQUENCE"         
            FROM  all_ind_columns aic 
            LEFT JOIN dba_indexes di ON aic.INDEX_NAME = di.INDEX_NAME AND aic.TABLE_NAME = di.TABLE_NAME AND aic.TABLE_OWNER = di.TABLE_OWNER
        WHERE aic.TABLE_NAME='{}'""".format(tablename)

        if self.schema:
            query += "  AND aic.OWNER = '{}'".format(self.schema)

        df = self.executeQuery(query, limit=None)

        return df

    def dq_dashboard_data_freshness_query(self, tablename, columnname, fromdate, todate):
        query = '''
            SELECT TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') as date_col,
            count(1) AS row_added
            FROM "%(table_name)s"
            WHERE TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') BETWEEN TO_DATE('%(from_date)s','yyyy-mm-dd') and TO_DATE('%(to_date)s','yyyy-mm-dd')
            GROUP BY TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd')
            ORDER BY 1
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})

        return query

    def dq_dashboard_data_modify_query(self, tablename, columnname, fromdate, todate):
        query = '''
            SELECT TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') as date_col,
            count(1) AS row_added
            FROM "%(table_name)s"
            WHERE TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') BETWEEN TO_DATE('%(from_date)s','yyyy-mm-dd') and TO_DATE('%(to_date)s','yyyy-mm-dd')
            GROUP BY TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd')
            ORDER BY 1
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})

        return query

    def dq_dashboard_data_delete_query(self, tablename, columnname, fromdate, todate):
        query = '''
            SELECT TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') as date_col,
            count(1) AS row_added
            FROM "%(table_name)s"
            WHERE TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') IS NOT NULL AND 
            TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') BETWEEN TO_DATE('%(from_date)s','yyyy-mm-dd') and TO_DATE('%(to_date)s','yyyy-mm-dd')
            GROUP BY TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd')
            ORDER BY 1 
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})

        return query

    def dq_dashboard_stk_query(self, tablename, columnname, fromdate, todate, datasources_col_name):
        query = '''
            SELECT TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') as date_col,
            NVL(TO_CHAR("%(datasources_col_name)s"),'Other') src, 
            count(1) AS row_added
            FROM "%(table_name)s"
            WHERE TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd') BETWEEN TO_DATE('%(from_date)s','yyyy-mm-dd') and TO_DATE('%(to_date)s','yyyy-mm-dd')
            GROUP BY TO_DATE(to_char("%(col_name)s",'yyyy-mm-dd'),'yyyy-mm-dd'), NVL(TO_CHAR("%(datasources_col_name)s"),'Other')
            ORDER BY 1
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate,
                "datasources_col_name": datasources_col_name})

        return query

    def get_incremental_columns(self, table_name, **others):
        try:
            # added distinct for unique data
            query = """SELECT DISTINCT col.COLUMN_NAME,
                        col.DATA_TYPE
                        FROM all_tab_columns col
                        LEFT JOIN ALL_CONS_COLUMNS acc 
                            ON col.TABLE_NAME = acc.TABLE_NAME 
                            AND col.OWNER = acc.OWNER 
                            AND acc.COLUMN_NAME = col.COLUMN_NAME 
                        LEFT JOIN ALL_CONSTRAINTS ac 
                            ON acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME 
                            AND col.OWNER = ac.OWNER 
                            AND ac.TABLE_NAME = col.TABLE_NAME 
                        LEFT JOIN user_trigger_cols t 
                            ON col.TABLE_NAME = t.TABLE_NAME 
                            AND col.COLUMN_NAME = t.COLUMN_NAME 
                            AND t.TABLE_OWNER = col.OWNER 
                        LEFT JOIN user_dependencies d 
                            ON d.referenced_type = 'SEQUENCE' 
                            AND d.type = 'TRIGGER' 
                            AND t.TRIGGER_NAME = d.NAME  
                        WHERE (col.NULLABLE='N' OR col.NUM_NULLS=0)  
                            AND ((  col.DATA_TYPE IN ('INT', 'NUMBER')
                                    AND (upper(AC.CONSTRAINT_TYPE) IN ('P', 'U')
                                    AND (col.NUM_DISTINCT = col.SAMPLE_SIZE))
                                    OR d.REFERENCED_NAME IS NOT NULL
                                ) 
                            OR ((data_type in ('DATE') 
                                    or col.data_type like 'TIMESTAMP%' 
                                    or col.data_type like 'INTERVAL%')
                                    AND col.NUM_DISTINCT = (SELECT max(atc.NUM_DISTINCT) 
                                                                FROM ALL_TAB_COLUMNS atc
                                                                WHERE atc.TABLE_NAME='{table_name}' 
                                                                AND col.owner = atc.OWNER
                                                                AND (data_type in ('DATE') 
                                                                    or atc.data_type like 'TIMESTAMP%' 
                                                                    or atc.data_type like 'INTERVAL%'))))
                            AND col.table_name = '{table_name}' """.format(table_name=table_name)
            if self.schema:
                query += " AND col.owner = '" + self.schema + "'"

            self.connect()
            df = self.executeQuery(query, limit=None)
        except Exception as e:
            self.close()
            print(e)
            raise
        return df

    def fetch_delta_columns(self, table_name, **others):
        df = self.get_incremental_columns(table_name)
        if df.empty:
            df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])
        return df

    def find_row(self, tbl_name, row, on_condition, manage_connection):
        found = False

        '''
            condition: [{
                target_col: "ORG_KEY",
                condition: "=",
                source_col: "ORG_KEY"
            }]
        '''

        if isinstance(on_condition, str):
            try:
                on_condition = json.loads(on_condition)
            except Exception:
                pass

        condition = " AND {col_name} = '{value}'"
        where_clause = " where 1=1 "

        if not self.schema:
            select_clause = 'select count(1) as CNT from "{}" '.format(tbl_name)
        else:
            select_clause = 'select count(1) as CNT from "{}"."{}" '.format(self.schema, tbl_name)        

        for con in on_condition:
            where_clause += condition.format(col_name = '"' + con["target_col"] + '"', value = row[con["source_col"]])

        qry = select_clause + where_clause

        print("find stmt :", qry)    
        df = self.executeQuery(qry, manage_connection=manage_connection)
        if df["CNT"][0] > 0:
            found = True

        return found    

    def update_row(self, tbl_name, row, on_condition, matched_mapping, col_details, manage_connection):
        if isinstance(on_condition, str):
            try:
                on_condition = json.loads(on_condition)
            except Exception:
                pass

        condition = " and {col_name} = '{value}'"

        where_clause = " where 1=1 "
        set_clause = " set "

        if not self.schema:
            upd_clause = 'update "{}" '.format(tbl_name)
        else:
            upd_clause = 'update "{}"."{}" '.format(self.schema, tbl_name)        

        for con in on_condition:
            where_clause += condition.format(col_name = '"' + con["target_col"] + '"', value = row[con["source_col"]])

        for key in matched_mapping.keys():
            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += merge_stmt_dict["ORACLE"]["set"]["NULL"].format(col_name = '"' + key + '"', value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += merge_stmt_dict["ORACLE"]["set"][col_type].format(col_name = '"' + key + '"', value = row[matched_mapping[key]].replace("'", "''"))                            
                else :
                    set_clause += merge_stmt_dict["ORACLE"]["set"][col_type].format(col_name = '"' + key + '"', value = row[matched_mapping[key]])

        set_clause = set_clause.rstrip(",")
        qry = upd_clause + set_clause + where_clause

        return self.executeSql(qry, manage_connection=manage_connection)

    def insert_row(self, tbl_name, row, non_matched_mapping, col_details, manage_connection):

        '''
            INSERT INTO SCIKIQ_DEV.ORDERS
            (ID, CUSTOMER_ID, PRODUCT_ID, QUANTITY, PRICE, TOTAL_AMOUNT, STORE_ID, CREATED_DATE, CREATED_BY)
            VALUES(0, 0, 0, 0, 0, 0, 0, '', '');        
        '''

        if not self.schema:
            inst_clause = f'INSERT INTO "{tbl_name}"'
        else:
            inst_clause = f'INSERT INTO "{self.schema}"."{tbl_name}"'

        inst_clause += " ({cols}) VALUES ({values})"

        cols = ""
        values = ""
        for key in non_matched_mapping.keys():
            cols += f'"{key}",'

            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if not pd.isnull(row[non_matched_mapping[key]]):
                if isinstance(row[non_matched_mapping[key]], str):
                    values += merge_stmt_dict["ORACLE"]["insert"][col_type].format(value = row[non_matched_mapping[key]].replace("'", "''")) + ","
                else:
                    values += merge_stmt_dict["ORACLE"]["insert"][col_type].format(value = row[non_matched_mapping[key]]) + ","
            else :
                values += merge_stmt_dict["ORACLE"]["insert"]["NULL"].format(value = 'null') + ","

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection=manage_connection)

    def join_upd_query(
            self,
            src_table_name,
            tgt_table_name,
            on_condition,
            matched_mapping,
            filter_condition
        ):

        '''
            example :
            UPDATE (
                SELECT 
                    i."ORACUSTOMERNAME" ORACUSTOMERNAME_OLD, i2."ORACUSTOMERNAME" ORACUSTOMERNAME_NEW,
                    i."ORALASTUPDATED" ORALASTUPDATED_OLD, i2."ORALASTUPDATED" ORALASTUPDATED_NEW,
                    i."ORALOADDATE" ORALOADDATE_OLD, i2."ORALOADDATE" ORALOADDATE_NEW
                FROM "CARDCUSTOMER" i
                INNER JOIN CARDCUSTOMER_TEST i2
                    ON i."ORACUSTOMERID" = i2."ORACUSTOMERID"
                WHERE 1 = 1
            ) t
            SET 
                ORACUSTOMERNAME_OLD = ORACUSTOMERNAME_NEW,
                ORALASTUPDATED_OLD = ORALASTUPDATED_NEW,
                ORALOADDATE_OLD = ORALOADDATE_NEW   	

            template: 
            UPDATE (
                SELECT 
                    i.{tgt_col} {tgt_col}_OLD, i2.{src_col} {src_col}_NEW 
                FROM {target_tbl} i
                INNER JOIN {src_tbl} i2
                    ON i.{tgt_col} = i2.{src_col}
                WHERE 1 = 1
                AND {src_tgt_alias}."{col}" {opr} {val}
            ) t
            SET 
                {tgt_col}_OLD = {src_col}_NEW                            

            select template : i.{tgt_col} {tgt_col}_OLD, i2.{src_col} {src_col}_NEW 
            set template    : {tgt_col}_OLD = {src_col}_NEW
            on template     : i.{tgt_col} = i2.{src_col}
            where template  : AND {src_tgt_alias}."{col}" {opr} {val}
        '''

        main_tmpl = '''
            UPDATE (
                SELECT 
                    {select_cols}
                FROM "{target_tbl}" i
                INNER JOIN "{src_tbl}" i2
                    ON {on_clause}
                WHERE 1 = 1 {where_clause}
            ) t
            SET {set_clause}
        '''

        on_condition_tmpl = ''' i."{tgt_col}" = i2."{src_col}"'''
        on_clause = self.get_on_condition(
            on_condition_tmpl, 
            on_condition=on_condition, 
            target_tbl=tgt_table_name,
        )

        fltr_condition_tmpl = ''' AND {src_tgt_alias}."{col}" {opr} {val}'''      
        where_clause = self.get_filter_condition(
            filter_condition_tmpl=fltr_condition_tmpl,
            filter_condition=filter_condition,
            src_alias="i2",
            tgt_alias="i"
        )

        ## get source col list
        set_stmt_template = '''"{tgt_col}_OLD" = "{src_col}_NEW"'''
        set_stmt = self.set_stmt_forupdate(set_stmt_template, matched_mapping)

        select_stmt_tmpl = 'i."{tgt_col}" "{tgt_col}_OLD", i2."{src_col}" "{src_col}_NEW" '
        select_cols = self.select_stmt_forupdate(select_stmt_tmpl, matched_mapping)

        qry = main_tmpl.format(
            target_tbl = tgt_table_name,
            set_clause = set_stmt,
            src_tbl = src_table_name,
            where_clause = where_clause,
            on_clause = on_clause,
            select_cols = select_cols
        )

        return qry  
    
    def select_stmt_forupdate(self, select_stmt_tmpl, matched_mapping):
        '''
        i.{tgt_col} {tgt_col}_OLD, i2.{src_col} {src_col}_NEW 
        '''

        insert_query = ""
        if len(matched_mapping) >0:
            insrt_list= []
            for target_column, src_column in matched_mapping.items():
                src_column = self.handle_special_char(src_column)
                insrt_list.append(select_stmt_tmpl.format(
                    src_col = src_column,
                    tgt_col = target_column
                ))

            insert_query = ",".join(insrt_list)

        return insert_query       