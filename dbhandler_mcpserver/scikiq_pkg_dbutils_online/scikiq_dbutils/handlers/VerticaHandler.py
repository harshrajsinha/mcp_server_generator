# PYTHON PACKAGES
from pandas.io.sql import get_schema
import pandas as pd
import vertica_python
import uuid 
import csv
import json
import time
from io import StringIO
import math as math
import datetime
from collections import OrderedDict
from pypika import Table, Field, JoinType, Tables, VerticaQuery, Order, functions as fn
from sqlalchemy import create_engine, types as sqlalchemyTypes
from urllib.parse import quote
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from collections import defaultdict
import gc


#CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression
from scikiq_dbutils.handlers.DBConnection import (
    clsDBConnection, ViewCreationError, where_recursive_condition, where_condition, 
    where_recursive_condition_col_dict, where_Colcondition, getReqSrcCols, MergeStatement
)
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict

class VerticaInsertException(Exception):
    pass

class clsVerticaDB(clsDBConnection):
    """
        Usage:

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

        self.engine = None

        if("resource_key" in config):
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None

        if "schema" in config and config["schema"] :
            self.schema = config["schema"]
        else :
            self.schema = 'public'

        if "connection_type" in config :
            self.connection_type = config["connection_type"]
        else :
            self.connection_type = None            

        self.version = self.getVersion()

        self.db_type = "VERTICA"            

    def getConnectionType(self):
        if self.connection_type is None :
            return "SR"
        else :
            return self.connection_type            

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        '''
        syntax              : COMMENT ON COLUMN [[database.]schema.]table.column IS {'comment' | NULL}

        [database.]schema	: Database and schema. The default schema is public. If you specify a database, 
                              it must be the current database.

        table.column	    : The name of the table and column with which to associate the comment.
        
        comment	            : Specifies the comment text to add. If a comment already exists for this column, 
                            this comment overwrites the previous comment. Comments can be up to 8192 characters in length. 
                            If a comment exceeds that limitation, Vertica truncates the comment and alerts the user with a message.

        NULL	            : Removes an existing comment.        
        '''

        success = True
        try :
            self.connect()

            if comment :
                qry = """COMMENT ON COLUMN "{schema}"."{table}"."{column}" IS '{comment}'""".format(
                    schema = self.schema,
                    table = tbl_name,
                    column = col_name,
                    comment = comment
                )
            else :
                qry = """COMMENT ON COLUMN "{schema}"."{table}"."{column}" IS NULL""".format(
                    schema = self.schema,
                    table = tbl_name,
                    column = col_name
                )

            self.executeSql(qry)
            self.close()
        except Exception:
            self.close()
            success = False

        return success                   

    def connect(self,errors='ignore'):
        try:
            resp = {}
            resp['resource_call'] = 'connect'

            self.connection = vertica_python.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.dbname,
                connecconnection_timeoutt_timeout=10800 ,
                unicode_error= errors
                # timeout of the data base and 108000 means 3 hours
            )

            self.cursor = self.connection.cursor()
            if self.schema :
                self.cursor.execute("SET SEARCH_PATH TO " + self.schema)
            
            #callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsVerticaDB,self).callConnectionAudit(resp)   

        except Exception as e:
            #callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsVerticaDB,self).callConnectionAudit(resp)

            raise

    def close(self):
        print("closing connection on implicit call...")
        if self.cursor :
            self.cursor.close()

        if self.connection :
            self.connection.close()

    def testConnection(self):
        resp = {}
        try:
            db =vertica_python.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.dbname,
                connecconnection_timeoutt_timeout=10800 ,
                # timeout of the data base and 108000 means 3 hours
            )

            db.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS   
        except vertica_python.errors.Error as exc: 
            error, = exc.args
            resp['error'] = 1
            if '3781' in error:
                resp['msg']= ScikiqMessages.MSG_INCORRECT_DB_CREDENTIALS
            elif '2983' in error:
                resp['msg']= "Please check the name of Database"
            else:
                error_value = error.split(',')
                try:
                    resp['msg'] = "Database Error |"+ error_value[6]+"|"+ error_value[1]
                except Exception as e:
                    resp['msg'] = "Database Error |"+ str(error)

        #callConnectionAudit using for audit the record.
        super(clsVerticaDB,self).callConnectionAudit(resp)

        return resp

    def createView(self, view_name, sql_query):
        '''
           @Description : View is the result set of a stored query on the data.
           param:
           view_name: view name (required)
           sql_query: query for view(required)
        '''
        try :
            crt_stmt = "CREATE OR REPLACE VIEW {} AS {}".format(view_name, sql_query)
            res = self.executeSql(crt_stmt)
            if not res['status']:
                print(res['msg'])
                # Raise an exception with the response message
                raise ViewCreationError(f"Failed to create view '{view_name}': {res['msg']}")
        except Exception:
            raise

        return view_name

    def executeQueryOld(self, query, limit=None, manage_connection=True):
        results = None
        try:
            if manage_connection:
                self.connect()

            if limit is not None:
                if ";" in query:
                    query = query.replace(";", " limit " + str(limit) + ";")
                else:
                    query = query + " limit " + str(limit) + ";"

            results = pd.read_sql(query, self.connection)
            if manage_connection:
                print("closing connection...")
                self.close()
        except Exception as e:
            if manage_connection:
                print("closing connection on exeception...")
                self.close()
            raise

        return results

    def executeSql(self, query, manage_connection=True):
        success = 0
        msg = ScikiqMessages.MSG_SUCCESS
        x = -1

        try:
            if manage_connection:
                self.connect()

            self.cursor.execute(query)
            x = self.cursor.rowcount
            if x == -1 or x == -2:  # Check if rowcount is -1 or -2
                x = 0            
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
        
    def executeInsertUpdate(self, tablename, df, if_exists='append', chunksize=10000, dtype={}):
        list_of_tables = self.get_all_tables(tablename)
        table_found = False

        if len(list_of_tables) > 0:
            # exact match needed !!
            table_found = len([x for x in list_of_tables if x[1] == 'TABLE' and x[0] == tablename]) == 1

        if table_found:
            print("Custom Insert pandas to vertica ")
            pv = Pandas_to_Vertica(df, tablename, chunksize=chunksize, schema=self.schema)
            # self.connect()
            pv.to_sql(ver_connection=self)
            # self.close()
            df = pv.df
            return df

        for col in df.select_dtypes('O'):
            try:
                # Handle UUID value in the df because .str function is not working.
                ## logic not working properly if df[col][0] was null
                idx = df[col].first_valid_index()  # Will return None
                first_valid_value = df[col].loc[idx] if idx is not None else None
                if first_valid_value is not None and isinstance(first_valid_value, uuid.UUID):
                    df[col].apply(str)
                else:
                    df[col] = df[col].str.replace(',', '')
                    df[col] = df[col].str.replace('"', '')
                    df[col] = df[col].str.replace('\\', '')
                    df[col] = df[col].str.replace(':', '')
            except Exception as e:
                print(e)

        if len(dtype) == 0:
            dtypedict = {}
            for src_col_name, src_col_type in zip(df.columns, df.dtypes):
                if "int" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                elif "float" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                elif "bool" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN}) 
                elif "date" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})
                else: ## including object
                    mx_length = self.maxLengthColumn(df[src_col_name])
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR(length=mx_length*4)})
        else:
            dtypedict = dtype

        # self.create_engine()
        with self.get_engine_connection() as connection:
            if self.schema:
                connection.execute("SET SEARCH_PATH TO " + self.schema)        

            if chunksize is None:
                try:
                    df.to_sql(
                        con=connection, 
                        name=tablename, 
                        dtype=dtypedict, 
                        if_exists=if_exists, 
                        chunksize=chunksize,
                        index=False
                    )
                except Exception as e:
                    if 'executemany is implemented for simple INSERT statements only' == str(e):
                        pv = Pandas_to_Vertica(df, tablename, chunksize=chunksize, schema=self.schema)
                        # self.connect()
                        pv.to_sql(ver_connection=self)
                        # self.close()
                        df = pv.df
            else:
                cnt = df.shape[0]
                batch_size = 1000
                if isinstance(chunksize, int):
                    batch_size = chunksize
                
                bt_cnt = int(math.ceil(cnt / batch_size))

                start = 0
                end = 0
                idx = 1
                if cnt > batch_size:
                    for i in range(bt_cnt):
                        if idx == bt_cnt:
                            end = cnt
                        else:
                            end = (idx * batch_size)
                        print('start :' + str(start))
                        print('end :' + str(end))
                        df2 = df.iloc[start:end, :].copy()
                        ## if_exists argument should 'append' once the iteration starts.
                        if_exists='append' if idx > 1 else if_exists
                        ## for debug
                        ##df2.to_csv("Df2_"+str(start)+ "_" + str(end) + ".csv")
                        try:
                            df2.to_sql(con=connection, name=tablename, dtype=dtypedict, if_exists=if_exists,
                                       chunksize=chunksize, index=False)
                        except Exception as e:
                            if 'executemany is implemented for simple INSERT statements only' == str(e):
                                pv = Pandas_to_Vertica(df2, tablename, chunksize=chunksize, schema=self.schema)
                                # self.connect()
                                pv.to_sql(ver_connection=self)
                                # self.close()

                        start = end
                        idx += 1
                else:
                    try:
                        df.to_sql(
                            con=connection, 
                            name=tablename, 
                            dtype=dtypedict, 
                            if_exists=if_exists,
                            chunksize=chunksize, 
                            index=False
                        )
                    except Exception as e:
                        if 'executemany is implemented for simple INSERT statements only' == str(e):
                            pv = Pandas_to_Vertica(df, tablename, chunksize=chunksize, schema=self.schema)
                            # self.connect()
                            pv.to_sql(ver_connection=self)
                            # self.close()
                        else :
                            raise VerticaInsertException(e)



        return df

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()
        query = " SELECT DISTINCT TABLE_NAME, TABLE_TYPE, SCHEMA_NAME AS TABLE_SCHEMA FROM ALL_TABLES "

        if include_view:
            query += " WHERE TABLE_TYPE IN ('TABLE', 'VIEW')"
        else:
            query += " WHERE TABLE_TYPE = 'TABLE'"

        if search :
            query += " AND TABLE_NAME LIKE '%{}%'".format(search)
        if self.schema :
            query += " AND SCHEMA_NAME = '{}'".format(self.schema)
                
        query += " ORDER BY TABLE_NAME ASC;"

        self.cursor.execute(query)

        results = self.cursor.fetchall()
        self.close()

        return results

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)
        data_dict = []
        self.connect()
        for data_table in results:
            dict_dynamic = {}
            data_table = list(data_table)[0]
            dict_dynamic["tablename"] = data_table
            
            self.cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM COLUMNS WHERE TABLE_NAME = '{}' ORDER BY COLUMN_NAME".format(
                data_table
            ))

            dict_dynamic["columnname"] = self.cursor.fetchall()
            # [member[0] for member in self.cursor.description]
            data_dict.append(dict_dynamic)

        self.close()

        return data_dict

    def getTableColumns(self, tablename, type = ''):
        query = "SELECT COLUMN_NAME, DATA_TYPE FROM COLUMNS WHERE TABLE_NAME = '{}'".format(tablename)

        if self.schema:
            query += " AND TABLE_SCHEMA = '{}'".format(self.schema)        

        query += " ORDER BY COLUMN_NAME "            
        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()

        return results


    def getVersion(self):
        try:
            query = "SELECT VERSION()"
            vrn = self.executeQuery(query)

            if "v9" in vrn["VERSION"][0]:
                vrn = "old"
            else:
                vrn = "new"

        except Exception:
            vrn = "new"

        return vrn


    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        test_type= self.getTableDetails(table_name=tbl_name)
        t_type= test_type['TABLE_TYPE'][0]

        self.connect()

        if t_type == "TABLE":
            if self.version == "old":
                query = """
                    select c.TABLE_SCHEMA as "TABLE_SCHEMA",
                    c.TABLE_NAME as "TABLE_NAME",
                    '{}' as "TABLE_TYPE",
                    c.COLUMN_NAME as "COLUMN_NAME",
                    c.DATA_TYPE as "DATA_TYPE",
                    c.ORDINAL_POSITION as "ORDINAL_POSITION",
                    c.NUMERIC_PRECISION as "NUMERIC_PRECISION",
                    c.NUMERIC_SCALE as "NUMERIC_SCALE" ,
                    c.IS_NULLABLE  as "IS_NULLABLE",
                    c.CHARACTER_MAXIMUM_LENGTH as "CHARACTER_MAXIMUM_LENGTH",
                    c.DATA_TYPE_LENGTH as "DATA_TYPE_LENGTH",
                    case when left(c.DATA_TYPE,7) = 'numeric' then concat(concat(c.NUMERIC_PRECISION,','),COALESCE(c.NUMERIC_SCALE,0)) 
                    else cast(COALESCE(c.data_type_length,c.CHARACTER_MAXIMUM_LENGTH,c.DATETIME_PRECISION) as varchar) end as "CHARACTER_MAX_LENGTH", 
                    '' as "COMMENT",
                    case when c.COLUMN_DEFAULT is null then '' else c.COLUMN_DEFAULT end as "COLUMN_DEFAULT",
                    COALESCE ((select 1 from v_catalog.constraint_columns where table_schema = c.table_schema
                    and table_name = c.table_name and column_name = c. column_name and CONSTRAINT_TYPE = 'p'), 0) as "IS_PRIMARYKEY",
                    COALESCE ((select 1 from v_catalog.constraint_columns where table_schema = c.table_schema and table_name = c.table_name
                    and column_name = c. column_name and CONSTRAINT_TYPE = 'u'), 0) as "IS_UNIQUEKEY",
                    '' as "IS_NONUNIQUEKEY",
                    case when c.IS_IDENTITY = 'true' then 1 else 0 end as "AUTO_INCREMENT",
                    c.DATA_TYPE_LENGTH as "COLUMN_LENGTH",
                    case when c.NUMERIC_SCALE  is null then 0 else c.NUMERIC_SCALE  end as "COLUMN_PRECISION",
                    case when c.COLUMN_SET_USING is null then '' else c.COLUMN_SET_USING end as "COLUMN_CHARACTERSET",
                    '' as "REFERENCED_TABLENAME",
                    '' as "REFERENCED_COLUMNNAME"
                from v_catalog.columns c
                WHERE c.TABLE_NAME = '{}'
            """.format(t_type,tbl_name)    
                
            else:
                query = """
                    select c.TABLE_SCHEMA as "TABLE_SCHEMA",
                    c.TABLE_NAME as "TABLE_NAME",
                    '{}' as "TABLE_TYPE",
                    c.COLUMN_NAME as "COLUMN_NAME",
                    c.DATA_TYPE as "DATA_TYPE",
                    c.ORDINAL_POSITION as "ORDINAL_POSITION",
                    c.NUMERIC_PRECISION as "NUMERIC_PRECISION",
                    c.NUMERIC_SCALE as "NUMERIC_SCALE" ,
                    c.IS_NULLABLE  as "IS_NULLABLE",
                    c.CHARACTER_MAXIMUM_LENGTH as "CHARACTER_MAXIMUM_LENGTH",
                    c.DATA_TYPE_LENGTH as "DATA_TYPE_LENGTH",
                    case when left(c.DATA_TYPE,7) = 'numeric' then concat(concat(c.NUMERIC_PRECISION,','),COALESCE(c.NUMERIC_SCALE,0)) 
                    else cast(COALESCE(c.data_type_length,c.CHARACTER_MAXIMUM_LENGTH,c.DATETIME_PRECISION) as varchar) end as "CHARACTER_MAX_LENGTH", 
                    case when c2.COMMENT  is null then '' else c2.COMMENT end as "COMMENT",
                    case when c.COLUMN_DEFAULT is null then '' else c.COLUMN_DEFAULT end as "COLUMN_DEFAULT",
                    COALESCE ((select 1 from v_catalog.constraint_columns where table_schema = c.table_schema
                    and table_name = c.table_name and column_name = c. column_name and CONSTRAINT_TYPE = 'p'), 0) as "IS_PRIMARYKEY",
                    COALESCE ((select 1 from v_catalog.constraint_columns where table_schema = c.table_schema and table_name = c.table_name
                    and column_name = c. column_name and CONSTRAINT_TYPE = 'u'), 0) as "IS_UNIQUEKEY",
                    '' as "IS_NONUNIQUEKEY",
                    case when c.IS_IDENTITY = 'true' then 1 else 0 end as "AUTO_INCREMENT",
                    c.DATA_TYPE_LENGTH as "COLUMN_LENGTH",
                    case when c.NUMERIC_SCALE  is null then 0 else c.NUMERIC_SCALE  end as "COLUMN_PRECISION",
                    case when c.COLUMN_SET_USING is null then '' else c.COLUMN_SET_USING end as "COLUMN_CHARACTERSET",
                    case when fk.REFERENCE_TABLE_NAME is null then '' else fk.REFERENCE_TABLE_NAME end as "REFERENCED_TABLENAME",
                    case when fk.REFERENCE_COLUMN_NAME is null then '' else fk.REFERENCE_COLUMN_NAME end as "REFERENCED_COLUMNNAME"
                from v_catalog.columns c
                left join v_catalog.comments c2 
                    on c.table_schema = c2.object_schema 
                    and c.table_name = c2.object_name 
                    and object_type = 'COLUMN'
                    and c2.child_object = c.COLUMN_NAME
                left join v_catalog.foreign_keys fk
                on c.table_schema = fk.table_schema
                and c.table_name = fk.table_name
                and c.column_name = fk.column_name
                WHERE c.TABLE_NAME = '{}'
            """.format(t_type,tbl_name)
               

        elif t_type == "VIEW":
                 query = """
                    select 
                    TABLE_SCHEMA as "TABLE_SCHEMA",
                    TABLE_NAME as "TABLE_NAME",
                    '{}' as "TABLE_TYPE",
                    COLUMN_NAME as "COLUMN_NAME",
                    DATA_TYPE as "DATA_TYPE", 
                    ORDINAL_POSITION as "ORDINAL_POSITION",
                    NUMERIC_PRECISION as "NUMERIC_PRECISION",
                    NUMERIC_SCALE as "NUMERIC_SCALE" ,
                    ' ' AS IS_NULLABLE,
                    CHARACTER_MAXIMUM_LENGTH as "CHARACTER_MAXIMUM_LENGTH",
                    DATA_TYPE_LENGTH as "DATA_TYPE_LENGTH",
                    case when left(data_type,7) = 'numeric' then concat(concat(NUMERIC_PRECISION,','),COALESCE(NUMERIC_SCALE,0))     
                        else cast(COALESCE(data_type_length,CHARACTER_MAXIMUM_LENGTH,DATETIME_PRECISION) as varchar)
                    end  as CHARACTER_MAX_LENGTH, 
                    '' as "COMMENT",
                    '' as  "COLUMN_DEFAULT",
                     0 as  "IS_PRIMARYKEY",
                     0 as  "IS_UNIQUEKEY",
                    '' as "IS_NONUNIQUEKEY",
                     0 as "AUTO_INCREMENT",
                     0 as "COLUMN_LENGTH",
                     0 as "COLUMN_PRECISION",
                    '' as  "COLUMN_CHARACTERSET",
                    '' as "CONSTRAINT_NAME",
                    '' as "REFERENCED_TABLENAME",        
                    '' as  "REFERENCED_COLUMNNAME",     
                    'no' as  "KEY_COL"    
                    from  v_catalog.view_columns c
                    WHERE TABLE_NAME = '{}'
                    """.format(t_type,tbl_name)
 
        if self.schema:
            query += " AND c.TABLE_SCHEMA = '{}'".format(self.schema)

        if sort_on_position :
            query += " ORDER BY ORDINAL_POSITION "
        else :
            query += " ORDER BY COLUMN_NAME "
       
        self.cursor.execute(query)
        desc_value = [d[0] for d in self.cursor.description]
        desc = [item.upper() for item in desc_value]
        results = [dict(zip(desc, res)) for res in self.cursor.fetchall()]
        self.close()

        return results

    def getRenamesColMetricsDict(self, config_details=OrderedDict()):
        col_dict = OrderedDict()
        col_lst = []
        idx_dict = {}
        if config_details:
            #Get column key and alias name with list of vlaues
            for key, col_details in config_details.items():
                    for lst in col_details:
                        col_dict[key] = lst['alias']
                        col_lst.append(key)
            #Get column occurences of the data.
            for key, _ in col_dict.items():
                indices = [index for index, element in enumerate(col_lst) if element == key]
                idx_dict[key] = indices

        return idx_dict

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
        tbls_name = {}  
        ## table name is a key value pair {"dim_projects" : "dp"} tablename and alias
        if tablename is not None:
            for key in tablename.keys():
                tbl_name = key
                alias =  tablename[tbl_name]
                if not self.schema:
                    tbls[alias] = Table(tbl_name, alias = alias)
                else:
                    tbls[alias] = Table(tbl_name, alias = alias,schema=self.schema)
                tbls_name[alias] = tbl_name
        
        index = 0
        for key in tbls.keys():
            if index == 0:
                _query = VerticaQuery.from_(tbls[key])
            else : 
                if tbls_name[key] in joins:
                    join_type = joins[tbls_name[key]]
                    if join_type == "inner" :
                        how=JoinType.inner
                    elif join_type == "right" :
                        how=JoinType.right
                    elif join_type == "left" :
                        how=JoinType.left
                    elif join_type == "full" :
                        how=JoinType.full
                    _query = _query.join(tbls[key], how).on(
                        eval('tbls[list(joinCondition[index-1]["left"].keys())[0]]'+'.'+list(joinCondition[index-1]["left"].values())[0]+ ' == '+ 'tbls[list(joinCondition[index-1]["right"].keys())[0]]'+ '.' + list(joinCondition[index-1]["right"].values())[0]))
            index = index + 1

        if columnnames is not None:
            agg_func = {
                "SUM":fn.Sum,
                "AVG":fn.Avg,
                "MIN":fn.Min,
                "MAX":fn.Max,
                "COUNT":fn.Count,                
                }

            lst_fields = []
            #Add column names which is derived/custom columns by user
            custom_column_names_dict = {}
            is_cal_field_available = 0

            for key, value in columnnames.items():
                ## Change input pattern now value will be list
                for list_item in value:
                    ## if condition to handle json from build model
                    ## "dim_project0.projectid" : ""  ## alisa.colname : agg fun and
                    ## else condtion to handle json from ETL
                    ## "projectid":"SUM" ## colname:AGG fun

                    ## if . found in column and but doesn't have table json format, raises error on eval
                    ## validation should be at front end level also
                    if "." in key and key.split(".")[0] in tbls:
                        key = key.split(".")
                        col_tbl_name = key[0]
                        col_name = key[1]
                        if value !='' :
                            #lst_fields.append(Field(tbls[col_tbl_name], agg_func[value](col_name)))
                            lst_fields.append( agg_func[value](eval('tbls[col_tbl_name]' + "." + col_name )))
                        else :
                            if " as " in col_name:
                                lst_fields.append(Field(col_name.split(" as ")[0] ,table= tbls[col_tbl_name], alias = col_name.split(" as ")[1]))
                            else:
                                lst_fields.append(Field(col_name,table=tbls[col_tbl_name]))
                    else :
                        if str(list_item['agg']).upper() =='DISTINCT COUNT' :
                            lst_fields.append(fn.Count(Field(key),alias=list_item['alias']).distinct())

                        elif list_item['agg'] == 'total_record_count':
                            lst_fields.append(agg_func["COUNT"]('*', alias=list_item['alias']))
                        elif list_item['agg'] !='' :
                            lst_fields.append(agg_func[str(list_item['agg']).upper()](
                                Field(key)
                                ,alias=list_item['alias'])
                                )
                        else:
                            lst_fields.append(Field(key).as_(list_item['alias']))
                    
                    #Check calcualted field is avaialbe or not.
                    if 'is_calculated' in list_item and list_item['is_calculated']=='1':
                        is_cal_field_available = 1
                    
                    #Add custom column in the list.
                    if 'column_type' in  list_item.keys():
                        if list_item['column_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = list_item['expression']
                    elif 'col_type' in  list_item.keys():
                        if list_item['col_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = list_item['expression']                            

        if distinct:
            _query = _query.select(*lst_fields).distinct()
        else :
            _query = _query.select(*lst_fields)

        if limit  is not None:
            if isinstance(limit,list) and len(limit)==1:
                limit = int(limit[0])
                _query = _query.limit(limit)
            elif isinstance(limit,str):
                limit = int(limit)
                _query = _query.limit(limit)     
            elif isinstance(limit, int):
                _query = _query.limit(limit)

        # add offset
        if offset is not None:
            _query = _query.offset(offset)

        if orderby is not None :
            if isinstance(orderby,dict): ## deprecated in new version 2021/08/31
                try:
                    
                    order_asc = Order.asc if orderby['direction'] == 'ASC' else Order.desc
                    for index , order_by_column_name in enumerate(orderby['columns'],start=0):
                        for column_name , column_config in columnnames.items():
                            if column_name == order_by_column_name:
                                orderby['columns'][index] = column_config[0]['alias'] 
                    _query  = _query.orderby(*orderby['columns'],order=order_asc)
                except:
                    __column_names_list = columnnames.keys()
                    for key, value in orderby.items():                        
                        order_asc = Order.asc if value == 'ASC' else Order.desc
                        col_index_dct = self.getRenamesColMetricsDict(columnnames)
                        if key in __column_names_list:
                            if key in col_index_dct:
                                for _index in col_index_dct[key]:
                                    _query  = _query.orderby(_index+1,order=order_asc)
            elif isinstance(orderby,list):
                for dct in orderby:
                    for col,asc_desc in dct.items():
                        order_asc = Order.asc if asc_desc == 'ASC' else Order.desc
                        _query  = _query.orderby(col,order=order_asc)
        
        whre_cond_col_dict = {}
        if filters and "rules" in filters:
            _query=_query.where(
                where_recursive_condition(
                    filters["condition"],
                    filters["rules"],
                    colDict=columnnames
                )
            )

            col_date_format_dict = {}
            col_date_format_list = []
            
            whre_cond_col_dict, whre_cond_col_lst = where_recursive_condition_col_dict(
                filters["condition"],
                filters["rules"], 
                dbType="VERTICA", 
                col_date_format_dict=col_date_format_dict,
                col_date_format_list = col_date_format_list,
                colDict=columnnames
            )

        if groupby is not None:
            for key ,value in groupby.items():
                _query = _query.groupby(key)

        if(is_cal_field_available):
            query =_query.get_sql(quote_char=None)
        else:
            query =_query.get_sql()

        #replacing string from last occurance.
        for col in whre_cond_col_dict:
            if col:
                col_count = whre_cond_col_lst.count(col)
                split_lst = query.rsplit(col, col_count)
                if len(split_lst)>0:
                    
                    if len(split_lst) ==2:
                        split_lst[0] = split_lst[0][:-2]+' '
                        split_lst[1] = ' '+split_lst[1][1:]
                        query = col.join(split_lst)
                    
                    elif len(split_lst) ==3:
                        split_lst[0] = split_lst[0][:-2]+' '
                        split_lst[1] = ' '+split_lst[1][1:len(split_lst[1])-1]+' '
                        split_lst[2] = ' '+split_lst[2][1:]
                        query = col.join(split_lst)

        query = self.formatQuery(tablename,groupby, query, filters,columnnames,schema=self.schema)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)

        return query

    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                format_string = GetDBDateFormat.get_dbdate_format(db_type="VERTICA",format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, format_string, _dict,db_type="VERTICA")
                if(not column_expression):
                    column_expression =  _dict['expression_value']
                query = query.replace(_key, column_expression, 1)
                expression_column_names_lst.append(column_expression)

        return (query, expression_column_names_lst)


    def formatQuery(self, tablename, groupby=None, query=None, filters=None, columnnames=None, schema=None):
        ## if no filters or group by then no need to format query
        # if filters is None and groupby is None:
        if not(filters or groupby) or (len(filters) == 0 and len(groupby.keys()) == 0):
            return query

        for key in tablename.keys():
            table = key                
            alias =  tablename[key]

        select_clause = query.split(' FROM ')[0]

        if filters is not None or groupby is not None:
            if  len(filters) !=0:
                where_clause = query.split('WHERE')[1]
            if groupby:
                if len(groupby) > 0  and  len(filters) > 0 :
                    where_clause = where_clause.split('GROUP BY')[0]
                    group_clause = query.split('GROUP BY')[1]
                elif  len(groupby) > 0 :
                    group_clause = query.split('GROUP BY')[1]
       
        for key, value in columnnames.items():
            for item in value :
                if "type" in item :
                    if item['type']=='date' and item['format']!='':                 
                        format_string=GetDBDateFormat.get_dbdate_format(db_type="VERTICA",format_string=item['format'])
                        temp_qry = format_string
                        temp_qry = temp_qry.replace('columnName','"'+alias+'"'+'.'+'"'+key+'"')
                        temp_qry = temp_qry.replace('alias','"'+item['alias']+'"')
                        temp_qry = temp_qry.replace('colFormat',format_string)
                        select_clause=select_clause.replace('"'+key+'"',temp_qry,1)                

        if filters is not None and "rules" in filters:
            where_clause = self.formatFilter(alias,filters["condition"],filters["rules"], where_clause)        

        if groupby and len(groupby)!=0:                
            for key,value in groupby.items():
                if "type" in value :
                    if(value['type'].upper()=='DATE' and  value['format']!=''):
                        format_string = GetDBDateFormat.get_dbdate_format(db_type="VERTICA",format_string=value['format'])
                        temp_qry = format_string
                        temp_qry = temp_qry.replace('columnName','"'+alias+'"'+'.'+'"'+key+'"')
                        temp_qry = temp_qry.replace('alias','"'+key+'"')
                        temp_qry = temp_qry.replace('colFormat',format_string)
                        group_clause = group_clause.replace('"'+alias+'"'+'.'+'"'+key+'"',temp_qry,1)

        ## schema not used in this function as schema already added while creating connection
        if len(filters) > 0:
            select_clause += ' FROM "{table_name}" "{alias}" WHERE {where_clause}'.format(
                table_name = table, 
                alias = alias, 
                where_clause = where_clause
            )  
        else :
            select_clause += ' FROM "{table_name}" "{alias}" '.format(table_name = table, alias = alias)              
        
        if groupby and len(groupby)> 0:
            select_clause += ' GROUP BY {}'.format(group_clause)

        return select_clause

    def create_engine(self):
        # it requires pip install sqlalchemy-vertica
        self.engine_statement = create_engine(
            f'vertica+vertica_python://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}',
            poolclass=QueuePool,
            pool_size=5,  # Adjust this based on your needs and system capabilities
            max_overflow=10,
            pool_timeout=30            
        )

    @contextmanager
    def get_engine_connection(self):
        self.create_engine()
        conn = self.engine_statement.connect()
        try:
            with conn.begin():
                yield conn
        except Exception as e:
            raise e
        finally:
            conn.close()   
    
    def close_engine(self):
        if self.engine:
            self.engine.close()

    def readTable(self, tbl_name, limit, **others):
        random_sample = others.get("random_sample", False)   
        manage_connection = others.get("manage_connection", True)   

        ## vertica was throwing error when table name
        ## starts with digit like public.29thNovYellowDemo
        if self.schema :
            tbl_name = '{}."{}"'.format(self.schema, tbl_name) 

        query = "SELECT * FROM "+ tbl_name
        
        if random_sample:
            query += " ORDER BY RANDOM() "

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection = manage_connection)
        res["df_text"] = None 

        return res               
     
    def getUpdateQuery(
            self,
            targetTableName,
            columnnames = {},
            filters = [],
            joins = {},
            input_tbl_replica = 'temp_table',
            sqlQuery = None
        ):
        
        filters =  None if filters == [{"from":"","column": "","operator": "","value": ""}] or filters == [] else filters
       
        test, final = Tables(input_tbl_replica, targetTableName)
        
        _query = VerticaQuery.update(final) 
        _query=_query.from_(test)
        if joins: 
            for k,v in joins.items():
                    where = f'{input_tbl_replica}"."{k}'
                    where_val= f'{targetTableName}"."{v}' 
                    where_op = 'equal'
                    _query = where_Colcondition(where=where, query=_query, where_val=where_val, where_op=where_op)   
       
        if columnnames:
            if joins:
                for k,v in columnnames.items():
                    _query = _query.set(Field(v,table = final), Field(k,table = test))
            else:
                for k,v in columnnames.items():
                    _query = _query.set(Field(v,table = final),k)

        if filters is not None:
            
            for index, filt in enumerate(filters):
                ##TODO
                node_from = filt['from']
                wherew = filt['column']
                if node_from =="source": ## test side 
                    where = f'{input_tbl_replica}"."{wherew}' 
                else:
                    ## final side
                    where = f'{targetTableName}"."{wherew}' 
                try:
                    where_val = eval(filt['value'])
                except Exception:
                    where_val = filters[index]['value']
                    
                where_op = filt['operator']
                _query = where_condition(where=where, query=_query, where_val=where_val, where_op=where_op)

        if sqlQuery is None:
            return _query.get_sql()
        else:
            return self.updateQueryUsingSubQuery(_query.get_sql(),input_tbl_replica,sqlQuery)

    def updateQueryUsingSubQuery(self, updateQuery, input_tbl_replica, subQuery):
        #split query by where clause.
        split_qury = updateQuery.split('WHERE')

        if len(split_qury) > 1:
            where_clause = split_qury[1]
        else:
            where_clause = ' 1=1 ' 

        new_upd_qry = split_qury[0] +' FROM ('+subQuery+') as '+input_tbl_replica+ ' WHERE '+ where_clause
        
        return new_upd_qry

    def updateType(self,df, tableDetails, mappedColumn):
        
        dtypedict = {}  # create and empty dictionary        

        for src_col_name ,src_col_type in zip(df.columns,df.dtypes):
            if src_col_name in  mappedColumn:
                trgt_mapped_col=mappedColumn[src_col_name]
                # getting target column name mapped with source

                if trgt_mapped_col !='' or trgt_mapped_col is not None:
                    trgt_col_detail = next(filter(lambda x: (x[0]==trgt_mapped_col),tableDetails['columnName']))
                    if trgt_col_detail :
                        # split column datatype value in case of varchar to remove detail part of length
                        trgt_col_dtype=trgt_col_detail[1].split('(')[0]
                        if len(trgt_col_detail) > 2 :
                            trgt_col_dtype_len = trgt_col_detail[3]                    
                        else :
                            trgt_col_dtype_len = 8000

                        trgt_col_dtype = trgt_col_dtype.upper()
                        if trgt_col_dtype in ('TEXT','STR','VARCHAR', 'LONG VARCHAR','NVARCHAR','CHAR')  :
                            dtypedict.update({src_col_name:sqlalchemyTypes.VARCHAR(length=int(trgt_col_dtype_len))})
                        elif trgt_col_dtype =='INT'  :
                            dtypedict.update({src_col_name:sqlalchemyTypes.BIGINT}) 
                        elif  trgt_col_dtype in ('FLOAT', 'DEC') :
                            dtypedict.update({src_col_name:sqlalchemyTypes.FLOAT}) 
                        elif trgt_col_dtype in ('BOOLEAN','BOL') :
                            dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN}) 
                        elif trgt_col_dtype in ('TIMESTAMP','DATE', 'DAT', 'TMS') :
                            dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME}) 
            else:
                if "object" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                elif "int64" in str(src_col_type) :
                    dtypedict.update({src_col_name:sqlalchemyTypes.BIGINT}) 
                elif "float64" in str(src_col_type) :
                    dtypedict.update({src_col_name:sqlalchemyTypes.FLOAT}) 
                elif "bool" in str(src_col_type) :
                    dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN}) 
                elif "datetime64[ns]" in str(src_col_type) :
                    dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})   

        return dtypedict

    # added tableDetails parameter to pass table columns data type
    def updateTable(
            self,
            df,
            targetTableName,
            columnnames={},
            filters=[],
            joins={},
            fromTable= None,
            sameSchema = False,
            tableDetails={},
            sqlQuery=None
        ):

        '''
            https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1        
        '''

        src_used_cols  = getReqSrcCols(columnnames, filters, joins)

        ## selected only those columns where are either in join or columns
        df = df[src_used_cols]

        input_tbl_replica = f'temp_tablestr{(uuid.uuid1())}' if fromTable is None else fromTable
        input_tbl_replica = input_tbl_replica.replace('-','_')
        
        print('Temp table used for update',input_tbl_replica)

        sql= self.getUpdateQuery(targetTableName,columnnames,filters,joins,input_tbl_replica,sqlQuery=sqlQuery)
        self.create_engine()


        if sameSchema or input_tbl_replica not in sql:
            with self.engine_statement.begin() as conn:     # TRANSACTION
                t = conn.execute(sql)
                print("matched rows = {}".format(t.rowcount))
                return df,sql
        # elif input_tbl_replica not in sql:
        #     with self.engine_statement.begin() as conn:     # TRANSACTION
        #         t = conn.execute(sql)
        #         print("matched rows = {}".format(t.rowcount))
        #         return df,sql
        else:
            try:
                for col in df.select_dtypes('O'):
                    try:
                        #Handle UUID value in the df because .str function is not working.
                        ## logic not working properly if df[col][0] was null
                        idx = df[col].first_valid_index()  # Will return None
                        first_valid_value = df[col].loc[idx] if idx is not None else None
                        if first_valid_value is not None and isinstance(first_valid_value, uuid.UUID):
                            df[col].apply(str)
                        else:
                            df[col] = df[col].str.replace(',','')
                            df[col] = df[col].str.replace('"','')
                            df[col] = df[col].str.replace('\\','')
                            df[col] = df[col].str.replace(':','')
                    except Exception as e:
                        print(e)

                with self.engine_statement.connect() as connection:
                    if self.schema :
                        connection.execute("SET SEARCH_PATH TO " + self.schema)        

                    data_types = self.updateType(df,tableDetails,columnnames)

                    df.to_sql(input_tbl_replica, connection, if_exists = 'replace', dtype = data_types, index=False)

                # this code will change the sql to support vertica update for two table
                sql_buffer = sql.split('WHERE')                
                where_clause = ' WHERE '+sql_buffer[1]
                from_clause = ' FROM '+input_tbl_replica
                set_clause = sql_buffer[0].split('SET')
                update_clause = set_clause[0]
                set_clause = set_clause[1]               
                column_map = ' SET '
               
                for column in set_clause.split(','):
                    set_clause=column.split('=')
                    if column_map==' SET ':
                        # when set close varibale have where clouse then appending taht where clouse also                                             
                            column_map=column_map+set_clause[0]+'='+input_tbl_replica+'.'+set_clause[1]                                         
                    else:                                             
                            column_map=column_map+','+set_clause[0]+'='+input_tbl_replica+'.'+set_clause[1]                     
                sql=update_clause+column_map+ from_clause+where_clause 
                # end here the vertica update section
                with self.engine_statement.begin() as conn:     # TRANSACTION
                    if self.schema :
                        conn.execute("SET SEARCH_PATH TO " + self.schema)    

                    t = conn.execute(sql)
                    print("matched rows = {}".format(t.rowcount))
                    conn.execute("DROP TABLE IF EXISTS "+ input_tbl_replica)

                return df, sql
            except Exception as e:                    
                    with self.engine_statement.begin() as conn:   # TRANSACTION   
                        if self.schema :
                            conn.execute("SET SEARCH_PATH TO " + self.schema)   

                        sql = f'DROP TABLE IF EXISTS "'+ input_tbl_replica+'"'                
                        s = conn.execute(sql) 
                    raise Exception(e)  

    def truncateTable(self,table_name):
        if not self.schema:
            query = f'TRUNCATE TABLE {table_name}'
        else:
            query = "TRUNCATE TABLE "+self.schema+"."+ table_name

        self.executeSql(query)

    #TODO: generateCreateTableScript function need to be tested for Vertica
    def generateCreateTableScript(self, tableDetails):
        query = "CREATE TABLE " + tableDetails["tableName"] + "("

        len_col = len(tableDetails["colDetails"])
        index = 0
        for x in tableDetails["colDetails"] :
            index += 1
            query = query + " `" + x['columnName'] + '`' 
            if(int(x['length']) > 0 and x['dbType'] in ("char", "varchar") ) :
                query += " " + x['dbType'] + "(" + str(x['length']) + ")"
            elif x['dbType'] == "int" :
                query += " " + x['dbType'] 
                if x['isPrimaryKey'] == 1 :
                    query += " PRIMARY KEY"
                if x['isAutoIncrement'] == 1 :
                    query += " AUTO_INCREMENT"
            elif x['dbType'] == "decimal" :
                query += " " + x['dbType'] + "(" + str(x['precision']) + ")"
                
            if x['nullable'] == "true" :
                query += " NULL"
            else :
                query += " NOT NULL"      
                
            if 'default' in x :
                if len(x["default"]) > 0 :
                    query += " DEFAULT " + x["default"]
                
            if(index < len_col) :
                query += ","     
            else :
                ## Add FK contraints
                if 'fk' in tableDetails :
                    len_fk = len(tableDetails["fk"])
                    fk_index = 0
                    fk_query = ","
                    
                    for y in tableDetails["fk"] :
                        fk_index += 1
                        #CONSTRAINT `daas_assets_created_by_4ce65b17_fk_daas_user_id` FOREIGN KEY (`created_by`) REFERENCES `daas_user` (`id`),
                        fk_query += " CONSTRAINT " + y['keyName'] + " FOREIGN KEY (`" + y['columnFK'] + "`) REFERENCES `" + y['table'] + "` (`" + y['column'] + '`)'
                        if(fk_index < len_fk) :
                            fk_query += ","
                            
                    query += fk_query                                            
                query += ")"     

        return query

    def generateCreateTableScriptETL(self, tableDetails):
               
        tableName = tableDetails["tableName"]
        createColumnData = tableDetails['createColumnData']
        #createColumnData =[{'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'} ..]

        sep = '"'
        createQuery = f'CREATE TABLE   {tableName}  '

        lst_cols = []
        if len(createColumnData)>0:
            for inpDict in createColumnData:
                col = inpDict['target_column']
                datatype = inpDict['datatype']
                col_query = f' {sep}{col}{sep} {datatype}'
                lst_cols.append(col_query)

        cols_query = ",".join(lst_cols)
        query = f'''{createQuery} ( {cols_query} ) '''

        return query

    def createTable(self, tableDetails, etl=False):
        if etl ==True:
            query = self.generateCreateTableScriptETL(tableDetails)
            result = self.executeSql(query)
            return result
        else:
            query = self.generateCreateTableScript(tableDetails)
            result = self.executeSql(query)

            return True          

    def getColumnLOV(self, table_name, col_name, order='ASC'):
        self.connect()
        full_table_name = table_name

        if isinstance(full_table_name,dict):
            for t_name, alias_name in full_table_name.items():
                full_table_name = t_name

        if self.schema is not None :
            full_table_name = '"' + self.schema + '".' + full_table_name        

        query = f'SELECT DISTINCT "{col_name}" as values FROM {full_table_name} WHERE 1 = 1 ORDER BY "{col_name}" {order}'      
        results = pd.read_sql(query, self.connection) 
        self.close()
        
        return results['values'].tolist()        

    def getColumnsProfile(self, table_name, with_min_max = False, filter = None):        
        df_col_dtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = table_name
        if self.schema is not None :
            full_table_name = self.schema + "." + '"' + full_table_name + '"'

        index = 0
        for row in df_col_dtls :
            ## splitted DB Type as db type contains precison & length also ex varchar(255), numeric(17,3)
            x = row["DATA_TYPE"]
            x = x.split("(")[0] 
            if x.upper() in ['VARCHAR', 'TIMESTAMP' ,'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'DOUBLE PRECISION', 'SMALLINT', 'INTEGER', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL', 'INT' ] :
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE  , """
                if with_min_max :
                    sub_query += """  
                                    TO_CHAR(max("{col_name}")) AS MAX_VAL, 
                                    TO_CHAR(min("{col_name}")) AS MIN_VAL, """
                sub_query += """ 
                                    COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """
            else :
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE , """
                if with_min_max :
                    sub_query += """  
                                    TO_CHAR(max(0)) AS MAX_VAL, 
                                    TO_CHAR(min(0)) AS MIN_VAL, """
                sub_query += """ 
                                    COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """

            sub_query += """ FROM {table_name}  """

            if filter :
                sub_query += " WHERE " + filter

            sub_query += " GROUP BY 1 " 

            sub_query = sub_query.format(col_name = row["COLUMN_NAME"], data_type = row["DATA_TYPE"], table_name = full_table_name)       
            df_sub = self.executeQuery(sub_query)

            if index == 0 :
                df = df_sub.copy()
            else :
                df = pd.concat([df, df_sub])

            index += 1             

        return df     

    def getTableDetails(self, table_name = None, type = {}):
        schema = "public"

        if self.schema is not None :
            schema = self.schema

        sep = "','"

        if table_name:
            if isinstance(table_name, list) :
                table_name = "'{}'" .format(sep.join(table_name))
            else :
                table_name = "'{}'".format(table_name)

        query = """
            SELECT 
            t.TABLE_SCHEMA,
            t.table_name AS TABLE_NAME,
            col.columns as NO_OF_COLS,
            case when (SUM(cs.used_bytes) / 1024/1024 ) is null then 0 else (SUM(cs.used_bytes) / 1024/1024 ) end as SIZE_IN_MB,
            case when cs.row_count is null then 0 else cs.row_count end AS NO_OF_ROWS, 
            la.last_access as LAST_UPDATED ,
            case when t.is_temp_table = true then 'TEMP TABLE' 
                when t.is_system_table = true then 'SYS TABLE' 
                when t.is_flextable = true then 'FLEX TABLE'
                else 'TABLE' 
            end as TABLE_TYPE,
            '' as COMMENT
        FROM tables t
        left join (
            select anchor_table_schema, anchor_table_name, sum(row_count) row_count, sum(used_bytes) used_bytes
            from 
            (
                select node_name, anchor_table_schema, anchor_table_name, sum(row_count)/count(1) as  row_count,
                sum(used_bytes)/count(1) as used_bytes
                from v_monitor.column_storage 
                group by node_name, anchor_table_schema, anchor_table_name
            ) a
            GROUP  by anchor_table_schema, anchor_table_name
        ) cs        
            on cs.anchor_table_schema = t.table_schema
            and cs.anchor_table_name = t.table_name
        join (
        	select distinct table_id as tables,count(*) as columns
        	from v_catalog.columns GROUP by table_id
        ) col 
        	on col.tables = t.table_id
        inner join (
        	select t.table_schema,t.table_name,ta.last_access 
        	from v_catalog.tables t
        	left join (
        		select table_oid,max(time) as last_access 
        		from v_internal.dc_projections_used 
        		group by table_oid
        	) ta
        		on t.table_id = ta.table_oid
        ) la 
        	on la.table_schema = t.table_schema 
        	and la.table_name = t.table_name
        where t.table_schema = '{schema}' 
        """

        if table_name:
            query += "  and t.table_name in ({table_name}) "

        query += """
            GROUP BY 
                t.table_name,
                t.table_schema,
                la.last_access,cs.row_count,
                col.columns,
                case 
                    when t.is_temp_table = true then 'TEMP TABLE' 
                    when t.is_system_table = true then 'SYS TABLE' 
                    when t.is_flextable = true then 'FLEX TABLE'
                    else 'TABLE' 
                end  

            UNION

            SELECT  
                v.TABLE_SCHEMA,
                v.table_name AS TABLE_NAME,
                vcols.columns as NO_OF_COLS,
                0 as SIZE_IN_MB,
                0 AS NO_OF_ROWS,
                v.create_time as LAST_UPDATED,
                'VIEW' as TABLE_TYPE,
                cm.comment as COMMENT
            FROM v_catalog.views v
            INNER JOIN (
                SELECT vc.table_id, COUNT(1) as columns FROM v_catalog.VIEW_COLUMNS AS vc GROUP BY 1
            ) vcols
                ON v.table_id = vcols.table_id
            LEFT OUTER JOIN  comments 	cm
                ON cm.object_schema = v.TABLE_SCHEMA
                AND cm.object_name = v.table_name 
            WHERE v.TABLE_SCHEMA = '{schema}'
        """
        
        if table_name:
            query += "  and v.table_name in ({table_name}) "

        query = query.format(schema=schema, table_name=table_name)
        
        df = self.executeQuery(query, limit = None)

        return  df

    def getTableRelationships(self, table_name, bi_directional = False):

        if bi_directional :
            query = """
                SELECT
                    table_name AS table_name,
                    column_name AS col_name,
                    reference_table_name AS ref_table_name,
                    reference_column_name AS ref_col_name
                FROM v_catalog.foreign_keys
                WHERE table_name =  '{table_name}'
                UNION ALL
                SELECT
                    table_name AS table_name,
                    column_name AS col_name,
                    reference_table_name AS ref_table_name,
                    reference_column_name AS ref_col_name
                FROM v_catalog.foreign_keys
                WHERE reference_table_name = '{table_name}'
            """         
        else :
            query = """
                SELECT
                    table_name AS table_name,
                    column_name AS col_name,
                    reference_table_name AS ref_table_name,
                    reference_column_name AS ref_col_name
                FROM v_catalog.foreign_keys
                WHERE table_name =  '{table_name}'
            """                     

        if self.schema :
            sub_qry = " and table_schema = '{schema}' and reference_table_schema = '{schema}'".format(schema = self.schema)
            query = query.format(table_name = table_name, schema = sub_qry)
        else :
            query = query.format(table_name = table_name, schema = "")

        df = self.executeQuery(query, limit = None)

        return  df

   
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

        mrgstmt = MergeStatement(
            source_table = src_table_name,
            target_table = tgt_table_name,
            on_condition=on_condition,
            matched_mapping = matched_mapping,
            non_matched_mapping = non_matched_mapping,
            on_match =on_match,
            on_not_match= on_not_match,
            filter_condition=filter_condition,
            encloser = '"',
            target_encloser=target_encloser
        )
        
        merge_query =mrgstmt.get_query()

        return merge_query
    
    def getDropTableQuery(self,table_name):
        return  f"DROP TABLE IF EXISTS {table_name}"

    def dropTable(self, table_name):
        query = self.getDropTableQuery(table_name)
        self.executeSql(query)

    def dq_dashboard_data_freshness_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select DATE(%(col_name)s) date_col,count (1) row_added from %(table_name)s
            where DATE(%(col_name)s) between '%(from_date)s' and  '%(to_date)s'
            group by DATE(%(col_name)s) order by 1 asc
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})

        return query

    def dq_dashboard_data_modify_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select 
                DATE(%(col_name)s) date_col,
                count (1) row_added 
            from %(table_name)s 
            where DATE(%(col_name)s) between '%(from_date)s' and '%(to_date)s'
            group by %(col_name)s order by 1 asc
        ''' % ({
            "col_name": columnname, 
            "table_name": tablename, 
            "from_date": fromdate, 
            "to_date": todate
        })

        return query

    def dq_dashboard_data_delete_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select 
                DATE(%(col_name)s) date_col,
                count (1) row_added 
            from %(table_name)s
            where %(col_name)s is not null and  DATE(%(col_name)s) between '%(from_date)s' and '%(to_date)s'
            group by DATE(%(col_name)s) order by 1 asc
        ''' % ({
            "col_name": columnname, 
            "table_name": tablename, 
            "from_date": fromdate, 
            "to_date": todate
        })

        return query

    def dq_dashboard_stk_query(self, tablename, columnname, fromdate, todate, datasources_col_name):
        query = '''
            select 
                DATE(%(col_name)s) date_col,
                COALESCE(CAST(%(datasources_col_name)s AS VARCHAR), 'Other') src, 
                count(1) row_added 
            from %(table_name)s
            where DATE(%(col_name)s) between '%(from_date)s' and '%(to_date)s'
            group by DATE(%(col_name)s), 2 order by 1 asc
        ''' % ({
            "col_name": columnname, 
            "table_name": tablename, 
            "from_date": fromdate, 
            "to_date": todate,
            "datasources_col_name": datasources_col_name
        })

        return query

    def get_connection_statement(self):
        statement = f"vertica+vertica_python://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"
        return statement

    def get_incremental_columns(self, table_name):
        try:
            # added distinct for unique data
            # removed join with comment table as it is duplicating col names in BSEG table
            query = """Select DISTINCT c.column_name as COLUMN_NAME, c.data_type as DATA_TYPE
            from v_catalog.columns c
            left join v_catalog.constraint_columns cc 
            	on c.table_schema = cc.table_schema 
            	and c.table_name = cc.table_name 
            	and c.column_name = cc. column_name 
            left join v_catalog.foreign_keys fk 
            	on c.table_schema = fk.table_schema 
            	and c.table_name = fk.table_name 
            	and c.column_name = fk.column_name
            WHERE 
             (
                (c.data_type like ('timestamp%') 
                or c.data_type = 'date')
                or 
                (	(upper(cc.CONSTRAINT_TYPE) = 'P'
                        or upper(cc.CONSTRAINT_TYPE) = 'C') 
                    AND c.data_type = 'int'
                )
             )
             AND c.TABLE_NAME = '{table_name}'""".format(table_name=table_name)
            if self.schema:
                query += " AND c.TABLE_SCHEMA= '" + self.schema + "'"

            self.connect()
            df = self.executeQuery(query, limit=None)
            df = df[['COLUMN_NAME','DATA_TYPE']]
        except Exception as e:
            self.close()
            print(e)
            raise
        return df

    def fetch_delta_columns(self, table_name, **others):
        try:
            df=None
            inc_columns = self.get_incremental_columns(table_name)
            full_table_name = '"' + table_name + '"'
            if self.schema is not None:
                full_table_name = '"' + self.schema + '"' + "." + full_table_name

            queries = []
            index = 0
            for index, row in inc_columns.iterrows():
                sub_query = """ 
                    SELECT 
                        '{col_name}' AS COLUMN_NAME,
                        '{DATA_TYPE}' as DATA_TYPE,
                        COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                        COUNT(1) AS TOTAL_COUNT, 
                        NVL(SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END),0) AS NULL_CNT 
                    FROM {table_name} 
                """

                sub_query = sub_query.format(
                    col_name=row["COLUMN_NAME"],
                    table_name=full_table_name,
                    DATA_TYPE=row['DATA_TYPE']
                )
                queries.append(sub_query)

            # changed logic to a single query
            if queries:
                final_query = " UNION ALL ".join(queries)
                df = self.executeQuery(final_query)

            if df is not None:
                df_date = df.loc[(df['DATA_TYPE'].str.upper().str.contains('TIME*|DATE*'))]
                if not df_date.empty:
                    df_date = df_date[df_date['UNQ_VAL'] == df_date['UNQ_VAL'].max()]
                df_integer = df.loc[(df['DATA_TYPE'].str.upper().str.contains('INT*'))]
                if not df_integer.empty:
                    df_integer = df_integer.loc[
                        df_integer['UNQ_VAL'] == df_integer['TOTAL_COUNT']]
                df = pd.concat([df_integer, df_date], axis=0)
                df = df[['COLUMN_NAME', 'DATA_TYPE']]
            else:
                df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])

        except Exception as e:
            self.close()
            print(e)
            raise
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
            val = row[con["source_col"]].replace("'", "''") if isinstance(row[con["source_col"]], str) else row[con["source_col"]]
            where_clause += condition.format(col_name = '"' + con["target_col"] + '"', value = val)

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
            val = row[con["source_col"]].replace("'", "''") if isinstance(row[con["source_col"]], str) else row[con["source_col"]]
            where_clause += condition.format(col_name = '"' + con["target_col"] + '"'  , value = val)

        for key in matched_mapping.keys():
            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += merge_stmt_dict["VERTICA"]["set"]["NULL"].format(col_name = '"' + key + '"', value = 'null')                            
            else :
                val = row[matched_mapping[key]].replace("'", "''") if isinstance(row[matched_mapping[key]], str) else row[matched_mapping[key]]
                set_clause += merge_stmt_dict["VERTICA"]["set"][col_type].format(col_name = '"' + key + '"', value = val)                         

        set_clause = set_clause.rstrip(",")
        qry = upd_clause + set_clause + where_clause

        print("upd_stmt :", qry)
        return self.executeSql(qry, manage_connection=manage_connection)

    def db_column_type(self,columns,column_types):
        """
        Vertica-specific type conversion mapping.

        Vertica type OIDs:
        5: BOOLEAN
        6: INTEGER
        7: FLOAT/REAL
        8: NUMERIC/DECIMAL/MONEY
        9: DOUBLE PRECISION
        10: CHAR/VARCHAR/TEXT
        11: DATE
        12: TIME
        13: TIMESTAMP
        14: TIMESTAMPTZ
        15: INTERVAL
        16: BINARY/VARBINARY
        """
        type_converters = {}

        for col, vtype in zip(columns, column_types):
            #this function write inside DBConnection

            # Map Vertica type codes to conversion types
            if vtype in (6, 7, 16):  # Numeric types
                type_converters[col] = ('numeric', False)
            elif vtype ==10:  # DATE
                type_converters[col] = ('date', False)
            elif vtype in (11,12, 13,15):  # TIMESTAMP types
                type_converters[col] = ('timestamp', False)
            elif vtype == 5:  # BOOLEAN
                type_converters[col] = ('boolean', False)
            else:  # Default to string for all other types
                type_converters[col] = ('string', False)

        return type_converters

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
                val = row[non_matched_mapping[key]].replace("'", "''") if isinstance(row[non_matched_mapping[key]], str) else row[non_matched_mapping[key]]
                values += merge_stmt_dict["VERTICA"]["insert"][col_type].format(value = val) + ","
            else :
                values += merge_stmt_dict["VERTICA"]["insert"]["NULL"].format(value = 'null') + ","

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection=manage_connection)


class Pandas_to_Vertica:
    '''
    1 Append Only # No Truncate
    2 Expects Schema and Table
    3 Handles Basic Exceptions
    # TODO not handling errors
    '''
    
    def __init__(self,df,table_name,schema='public',chunksize=0):
        
        self.df = df
        self.table_name = table_name
        self.schema = schema
        self.truncate =False ## TODO

        self.get_chunk_size(chunksize)
        self.preprocess()

        self.get_columns_str()
        
    def get_chunk_size(self,chunk):
        if chunk == 0 or chunk is None:
            if self.df.size < 500_000:
                self.chunksize = len(self.df)
            else:
                self.chunksize = 5000                  
        else:
            self.chunksize = chunk

    def get_columns_str(self):
        self.columns_str = ",".join([f'"{x}"' for x  in self.df.columns.tolist()])
        
    def get_right_delimiter(self,df):
        #chr(28) file separator
        #chr(29) group
        #chr(30) record
        #chr(31) unit

        delimiter_list = [chr(30),'|','~',';',',',':',"!","@","#","$","%","&","-","_","`","<",">",chr(31)]
        for delimiter in delimiter_list:
            for col in df.select_dtypes('O'):
                try:
                    if df[col].str.contains(delimiter,regex=False).any():
                        break
                except Exception as e:
                    print(f'On {col} error {str(e)}')
            else:
                break
        return delimiter
    
    def get_copy_str(self):
        self.copy_str = f"""
            COPY "{self.schema}"."{self.table_name}"({self.columns_str})FROM STDIN DELIMITER  '{self.delimiter}' 
            ABORT ON ERROR ENFORCELENGTH	
        """
        

    def preprocess(self):
        for col in self.df.select_dtypes('O'):
            try:
                #Handle UUID value in the df because .str function is not working.
                ## logic not working properly if df[col][0] was null
                idx = self.df[col].first_valid_index()  # Will return None
                first_valid_value = self.df[col].loc[idx] if idx is not None else None
                if first_valid_value is not None and isinstance(first_valid_value, uuid.UUID):
                    self.df[col] = self.df[col].apply(str)
                elif first_valid_value is not None and isinstance(first_valid_value,(datetime.date,datetime.datetime)):
                    self.df[col] = pd.to_datetime(self.df[col])
                elif first_valid_value is not None and isinstance(first_valid_value,(bool)):
                    self.df[col] = self.df[col].astype(bool)
            except Exception as e:
                print(e)

    def to_str_io(self,df):
        
        self.delimiter = self.get_right_delimiter(df)
        print("delimiter:",self.delimiter)
        # turn the df into a csv-like object
        self.stream = StringIO()
        
        df.copy().to_csv(
            self.stream, 
            sep=self.delimiter,
            index=False, 
            header=False,
            quoting=csv.QUOTE_NONE, 
            quotechar='', 
            escapechar='\\'
        )
        

                
    def to_db(self,ver_connection):
        
        # reset the position of the stream variable
        self.stream.seek(0)
        self.get_copy_str()

        # load to data
        ver_connection.connect(errors='raise')
        cursor =ver_connection.connection.cursor()
        cursor.copy(self.copy_str,self.stream.getvalue(),buffer_size=65536)
        cursor.execute('COMMIT;')

        self.stream.flush()
        self.stream.close()
    
    def chunker(self,seq, size):
        for pos in range(0, len(seq), size):
            print(f'Processing Rows: [{pos} .. {pos+size}]/[{len(seq)}]')
            yield (seq.iloc[pos:pos + size]).copy()    

    def to_sql(self,ver_connection):
        if not self.df.empty: 
            for chunked_df in self.chunker(self.df,self.chunksize):
                self.to_str_io(chunked_df)
                self.to_db(ver_connection)


    def is_table_exists(self):
        pass

    def getTableIndexDetails(self, tablename):
        pass



