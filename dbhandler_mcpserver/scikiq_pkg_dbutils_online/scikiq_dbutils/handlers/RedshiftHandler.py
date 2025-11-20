# PYTHON PACKAGES
import pandas as pd
import uuid
import json
import psycopg2
from psycopg2 import errorcodes
from collections import OrderedDict
from sqlalchemy import create_engine
from sqlalchemy import types as sqlalchemyTypes
from pypika import Tables
from pypika import Table, Field, JoinType, Order
from pypika.dialects import VerticaQuery
from pypika import functions as fn
from pypika import PostgreSQLQuery
import dask.dataframe as dd
from urllib.parse import quote

# CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.handlers.DBConnection import (
    clsDBConnection, ViewCreationError, where_recursive_condition, where_condition, 
    where_Colcondition,MergeStatement
)
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression


class PostgresDDLException(Exception):
    pass


class PostgresDMLException(Exception):
    pass


class clsRedshiftDB(clsDBConnection):
    """
        Usage:

    """

    # def __init__(self, user, password, host, port, dbname,schema=None):
    def __init__(self, config):
        self.host = config["hostname"]
        self.port = config["port"]
        self.dbname = config["dbname"]
        self.user = config["dbuser"]
        self.password = config["pwd"]
        
        self.engine_statement = None
        self.connection = None
        self.cursor = None

        self.resource_key = None
        if ("resource_key" in config):
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None
            
        self.schema = 'public'
        if "schema" in config and config["schema"]:
            self.schema = config["schema"]
        else :
            self.schema = 'public'

        self.connection_type = None            
        if "connection_type" in config:
            self.connection_type = config["connection_type"]
        else :
            self.connection_type = None            

        self.db_type="REDSHIFT"            

    def getConnectionType(self):
        if self.connection_type is None:
            return "SR"
        else:
            return self.connection_type            

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        success = True
        try:
            self.connect()

            if comment:
                qry = """COMMENT ON COLUMN
                    "{schema}"."{table_name}"."{column_name}" IS '{comment}';""".format(
                    comment=comment,
                    schema=self.schema,
                    table_name=tbl_name,
                    column_name=col_name,
                )     
            else:
                qry = """COMMENT ON COLUMN
                    "{schema}"."{table_name}"."{column_name}" IS '';""".format(
                    schema=self.schema,
                    table_name=tbl_name,
                    column_name=col_name,
                )    
                
            self.executeSql(qry)
            self.close()
        except Exception as e:
            self.close()
            print(e)
            success = False

        return success             

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'
            
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password= self.password,
                database=self.dbname,
                options=f"-c search_path={self.schema}"
            )
            
            self.cursor = self.connection.cursor()
            if self.schema :
                self.cursor.execute("SET SEARCH_PATH TO " + self.schema)
                
            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsRedshiftDB, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsRedshiftDB, self).callConnectionAudit(resp)
            raise   


    def close(self):
        if self.cursor:
            self.cursor.close()

        if self.connection:
            self.connection.close()

    def testConnection(self):
        resp = {}
        try:
            db = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password= self.password,
                database=self.dbname
                # timeout of the data base and 108000 means 3 hours
            )

            db.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS   
        except psycopg2.OperationalError as e:
            if e.pgcode == psycopg2.errorcodes.INVALID_PASSWORD:
                resp['msg'] = ScikiqMessages.MSG_INCORRECT_DB_CREDENTIALS
            else:
                resp['msg'] = str(e.pgcode) + ": " + str(e)

            resp['error'] = 1                
        except Exception as e:
            resp['msg'] = str(e)
            resp['error'] = 1                

            # callConnectionAudit using for audit the record.
        super(clsRedshiftDB, self).callConnectionAudit(resp)

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
            self.close()
            raise PostgresDDLException(e)
        
        return view_name

    def getDataTypeSample(self, query, batch_size=10000):
        from scikiq_dbutils.handlers.optimize_dataframe import df_reduce_size
        self.connect()
        
        if not ("limit" in query or "LIMIT" in query):
            query = query + " limit " + str(batch_size) + ";"
        
        df = pd.read_sql(query, self.connection)
        df = df_reduce_size(df)
        dtype_mapping = df.dtypes.to_dict()
        self.close()

        return dtype_mapping, df
    
    def generate_dataset(self, query, limit):
        
        if limit:
            self.cursor.execute(f"{query} LIMIT {limit}")                
        else :
            self.cursor.execute(query)        

        # idx = 0
        for row in self.cursor.fetchall():
            # some tramsformation
            # idx += 1
            # print(idx)
            yield row 

    def generate_dataset2(self, cursor, batch_size):
        # idx = 0
        for row in cursor.fetchmany(batch_size):
            # some tramsformation
            # idx += 1
            # print(idx)
            yield row             

    # 2.1. CREATE DF USING GENERATORS
    def executeQueryGen(self,query, limit=500000, manage_connection=True):
        print('Creating pandas DF using generator...')

        try :
            if manage_connection:
                self.connect()

            results = pd.DataFrame(data = self.generate_dataset(query, limit))
            results = dd.from_pandas(results, npartitions=6)

            print('DF successfully created!\n')
        except Exception as e:
            raise PostgresDMLException(e)
        finally:
            if manage_connection:
                self.close()        

        return results     

    ##/* last try
    ##*/    
    def executeQueryLast(self, query, limit=None, manage_connection=True, batch_size = 50000):
        try:
            if limit and int(limit) < batch_size:
                batch_size = int(limit)

            dask_partitions = []
            # offset = 0

            if manage_connection:
                self.connect()

            if limit:
                self.cursor.execute(f"{query} LIMIT {limit}")                
            else :
                self.cursor.execute(query)
            
            col_names = [d[0] for d in self.cursor.description]
            while True:
                chunk = pd.DataFrame(data = self.generate_dataset2(self.cursor, batch_size), columns = col_names)
                if chunk.empty:
                    break            

                dask_chunk = dd.from_pandas(chunk, npartitions=6)  # Convert Pandas DataFrame to Dask DataFrame

                dask_partitions.append(dask_chunk)

                # offset += batch_size  # Increment offset

            # Concatenate all Dask partitions
            if dask_partitions:
                dask_df_result = dd.concat(dask_partitions, interleave_partitions=False, axis=0)
                results = dask_df_result.compute()  # Convert Dask DataFrame to Pandas DataFrame
                results = results.reset_index()
                results = results.drop("index", axis=1)
            else:
                results = pd.DataFrame()  # Return an empty Pandas DataFrame
        except Exception as e:
            raise PostgresDMLException(e)
        finally:
            if manage_connection:
                self.close()
                
        return results    

    def executeQueryOld(self, query, limit=50000, manage_connection=True):
        try:
            batch_size = 50000
            dtype, results_sample = self.getDataTypeSample(query)
            # if 'LIMIT' in query or 'limit' in query:
            #     return results_sample
            # Initialize variables for offset and limit
            offset = 0
            # Create an empty list to store Dask DataFrame partitions
            dask_partitions = []
 
            if len(results_sample) < limit:
                if manage_connection:
                    self.connect()
               
                while True:
                    # Modify the query with offset and limit
 
                    # query_with_limit = f"{query} ORDER BY mbt_id LIMIT {batch_size} OFFSET {offset}"
                    query_with_limit = f"{query} LIMIT {batch_size} OFFSET {offset}"
                    # Execute the query in parallel using Pandas
                    chunk = pd.read_sql_query(query_with_limit, self.connection, dtype=dtype)
 
                    if chunk.empty:
                        # No more data to fetch, break the loop
                        break
 
                    dask_chunk = dd.from_pandas(chunk, npartitions=6)  # Convert Pandas DataFrame to Dask DataFrame
                    dask_partitions.append(dask_chunk)
 
                    offset += batch_size  # Increment offset
                    if offset >= limit:
                        break
 
                # Concatenate all Dask partitions
                if dask_partitions:
                    dask_df_result = dd.concat(dask_partitions, interleave_partitions=True)
                    results = dask_df_result.compute()  # Convert Dask DataFrame to Pandas DataFrame
                else:
                    results = pd.DataFrame()  # Return an empty Pandas DataFrame
            else:
                # If the results size is less than 5000, use results_sample directly (assuming it's a Pandas DataFrame)
                results = results_sample
        except Exception as e:
            raise PostgresDMLException(e)        
        
        finally:
            if manage_connection:
                self.close()
               
        return results        

    def executeSql(self, query, manage_connection=True):
        b_success = 0
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

            b_success = 1
        except Exception as e:
            if manage_connection:
                self.close()
            msg = str(e)
            b_success = 0
            x = -1

        res = {}
        res["status"] = b_success
        res["result"] = x
        res["msg"] = msg

        return res
    
    def executeInsertUpdate(self, tablename, df, if_exists='append', chunksize=50000,dtype={}):
        # self.create_engine()
        # for col in df.select_dtypes('O'):
        #     try:
        #         df[col] = df[col].str.replace('@#$%^', '')  # Replace with your desired delimiter
        #         df[col] = df[col].str.replace('"', '')
        #         df[col] = df[col].str.replace('\\', '')
        #     except Exception as e:
        #         print(e)
        # dtypedict = {}

        # if len(dtype) == 0:
        #     for src_col_name, src_col_type in zip(df.columns, df.dtypes):
        #         if "object" in str(src_col_type):
        #             dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
        #         elif "int64" in str(src_col_type):
        #             dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
        #         elif "float64" in str(src_col_type):
        #             dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
        #         elif "bool" in str(src_col_type):
        #             dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN}) 
        #         elif "datetime64[ns]" in str(src_col_type):
        #             dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})  
        # else:
        #     dtypedict = dtype                      

        # # Begin a transaction
        # try:
        #     self.connect()
        #     # Split the DataFrame into batches
        #     for i in range(0, len(df), chunksize):
        #         batch = df[i:i + chunksize]
        
        #         # Create a file-like object from the batch
        #         from io import StringIO
        #         output = StringIO()
        #         batch.to_csv(output, sep=',', header=True, index=False)
        #         output.seek(0)
        
        #         # Open a cursor
        #         cursor = self.connection.cursor()

        #         # Define the COPY command
        #         # copy_sql = f"COPY {tablename} FROM stdin WITH CSV HEADER DELIMITER as ','"
        #         copy_sql = f"COPY {tablename} FROM STDIN WITH CSV HEADER DELIMITER ','"


        #         # Execute the COPY command with the data from the file-like object
        #         cursor.copy_expert(sql=copy_sql, file=output)

        #         # Commit the changes for this batch
        #         self.connection.commit()

        #         # Close the cursor
        #         cursor.close()
        #         print("running for batch ",i)

        # except Exception as e:
        #     # Rollback the transaction on error
        #     raise e
        # finally:
        #     self.close()
            
        # print("completed for batch ")

        # return df

        self.create_engine()

        for col in df.select_dtypes('O'):
            try:
                df[col] = df[col].str.replace(',', '')
                df[col] = df[col].str.replace('"', '')
                df[col] = df[col].str.replace('\\', '')
            except Exception as e:
                print(e)
        dtypedict = {}

        if len(dtype) == 0:
            for src_col_name, src_col_type in zip(df.columns, df.dtypes):
                if "object" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                elif "int64" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                elif "float64" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                elif "bool" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                elif "datetime64[ns]" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})
        else:
            dtypedict = dtype

        df.to_sql(con=self.engine_statement,dtype=dtypedict,name=tablename, if_exists=if_exists, index=False,chunksize = chunksize,method='multi')
        return df

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()
        query = "SELECT TABLE_NAME,TABLE_TYPE, TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_CATALOG = '{}'".format(
            self.dbname)

        if include_view == True:
            query += " AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')"
        else:
            query += " AND TABLE_TYPE = 'BASE TABLE'"

        if search:
            query += " AND TABLE_NAME LIKE '%{}%'".format(search)

        if self.schema:
            query += " AND TABLE_SCHEMA='{}'".format(self.schema) 
            
        query += " ORDER BY TABLE_NAME"

        self.cursor.execute(query)                
        results = self.cursor.fetchall()
        self.close()

        return results

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)

        # self.cursor.close()
        data_dict = []
        query = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_CATALOG= '{}'".format(
            self.dbname)
        if self.schema:
            query += " AND TABLE_SCHEMA ='{}'".format(self.schema)

        query += " ORDER BY COLUMN_NAME"        
        self.connect()
        for tbls in results:
            col_dtls = {}
            tbls = list(tbls)[0]
            col_dtls["tablename"] = tbls
            query = query.format(tbls)                
            col_dtls["columnname"] = pd.read_sql(query, con=self.connection).values.tolist()
            data_dict.append(col_dtls)

        self.close()
        return data_dict

    def getTableColumns(self, tablename):
        query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_CATALOG = '{}' AND TABLE_NAME = '{}'".format(
            self.dbname, tablename)
        if not self.schema:        
            query += " AND TABLE_SCHEMA = '{}'".format(self.schema)

        query += " ORDER BY COLUMN_NAME"

        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()

        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        test_type= self.getTableDetails(table_name=tbl_name)
        t_type=test_type['TABLE_TYPE'][0]

        query='''   
            SELECT
                cols.TABLE_SCHEMA AS "TABLE_SCHEMA",
                cols.TABLE_NAME as "TABLE_NAME",    
                '{}' as "TABLE_TYPE",       
                cols.COLUMN_NAME as "COLUMN_NAME",  
                cols.DATA_TYPE as "DATA_TYPE",      
                cols.ORDINAL_POSITION as "ORDINAL_POSITION",
                cols.NUMERIC_PRECISION as "NUMERIC_PRECISION",
                cols.NUMERIC_SCALE as "NUMERIC_SCALE",
                cols.IS_NULLABLE as "IS_NULLABLE",
                cols.CHARACTER_MAXIMUM_LENGTH as "CHARACTER_MAXIMUM_LENGTH",
                '' AS DATA_TYPE_LENGTH,
                ''  AS "LENGTH",
                COALESCE(cast(COALESCE(cols.CHARACTER_MAXIMUM_LENGTH,cols.DATETIME_PRECISION) as int),
                (cols.NUMERIC_PRECISION + COALESCE(cols.NUMERIC_SCALE,0))) as "CHARACTER_MAX_LENGTH",
                case when cols.COLUMN_DEFAULT is null then '' else cols.COLUMN_DEFAULT end as "COLUMN_DEFAULT",
                '' as "COMMENT",
                case when upper(tc.CONSTRAINT_TYPE) = 'PRIMARY KEY' then 1 else 0 end as "IS_PRIMARYKEY",
                case when upper(tc.CONSTRAINT_TYPE) = 'UNIQUE' then 1 else 0 end as "IS_UNIQUEKEY",
                '' as "IS_NONUNIQUEKEY",
                '' as "COLUMN_PRECISION",
                case when cols.CHARACTER_SET_NAME is null then '' else cols.CHARACTER_SET_NAME end as "COLUMN_CHARACTERSET",
                case when links.CONSTRAINT_NAME  is null then '' else links.CONSTRAINT_NAME  end as "CONSTRAINT_NAME",
                case when links.CONSTRAINT_NAME is not null then 'yes' else 'no' end as "KEY_COL",
                case when links.TABLE_CATALOG  is null then '' else links.TABLE_CATALOG end as "REFERENCED_TABLENAME",
                case when links.COLUMN_NAME  is null then '' else links.COLUMN_NAME end as "REFERENCED_COLUMNNAME"
            FROM
                INFORMATION_SCHEMA.COLUMNS as cols
            LEFT JOIN  INFORMATION_SCHEMA.KEY_COLUMN_USAGE as links 
                ON cols.TABLE_NAME = links.TABLE_NAME
                AND cols.COLUMN_NAME = links.COLUMN_NAME
                AND cols.TABLE_SCHEMA = links.TABLE_SCHEMA
            LEFT JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
                ON tc.TABLE_SCHEMA = cols.TABLE_SCHEMA
                AND tc.TABLE_NAME = cols.TABLE_NAME
                AND links.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            WHERE cols.TABLE_CATALOG = '{}' AND lower(cols.TABLE_NAME) = '{}'
        '''.format(t_type,
                   self.dbname,
                   tbl_name.lower()) 

        if self.schema:
            query += " AND lower(cols.TABLE_SCHEMA) = '{}'".format(self.schema.lower())

        if sort_on_position :
            query +=  " ORDER BY ORDINAL_POSITION "
        else :
            query += " ORDER BY COLUMN_NAME "  
 
        self.connect()
        self.cursor.execute(query)
        desc = [d[0] for d in self.cursor.description]
        # results = [dict(zip(desc, res)) for res in self.cursor.fetchall()]
        results = [dict((k.upper(), v) for k, v in zip(desc, res)) for res in self.cursor.fetchall()]
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
        tbls = {}     
        ## table name is a key value pair {"dim_projects" : "dp"} tablename and alias
        if tablename is not None:
            for key in tablename.keys():
                tbl_name = key
                alias = tablename[tbl_name]
                if not self.schema:
                    tbls[alias] = Table(tbl_name, alias=alias)
                else:
                    tbls[alias] = Table(tbl_name, alias=alias, schema=self.schema)
                tbls[alias] = tbl_name
        
        index = 0
        for key in tbls.keys():
            if index == 0:
                _query = VerticaQuery.from_(tbls[key])
            else:
                if tbls[key] in joins:
                    join_type = joins[tbls[key]]
                    if join_type == "inner":
                        how = JoinType.inner
                    elif join_type == "right":
                        how = JoinType.right
                    elif join_type == "left":
                        how = JoinType.left
                    elif join_type == "full":
                        how = JoinType.full

                    _query = _query.join(tbls[key], how).on(
                        eval('tbls[list(joinCondition[index-1]["left"].keys())[0]]' + '.' +
                             list(joinCondition[index - 1]["left"].values())[
                                 0] + ' == ' + 'tbls[list(joinCondition[index-1]["right"].keys())[0]]' + '.' +
                             list(joinCondition[index - 1]["right"].values())[0]))
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
                        col_tbl_name = key[0]
                        col_name = key[1]
                        if value != '':
                            # field_lst.append(Field(tbls[col_tbl_name], agg_func[value](col_name)))
                            field_lst.append(agg_func[value](eval('tbls[col_tbl_name]' + "." + col_name)))
                        else:
                            if " as " in col_name:
                                field_lst.append(Field(col_name.split(" as ")[0], table=tbls[col_tbl_name],
                                                       alias=col_name.split(" as ")[1]))
                            else:
                                field_lst.append(Field(col_name, table=tbls[col_tbl_name]))
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
        
        if limit is not None:
            if isinstance(limit, list) and len(limit) == 1:
                limit = int(limit[0])
                _query = _query.limit(limit)
            elif isinstance(limit, str):
                limit = int(limit)
                _query = _query.limit(limit)     
            else:
                _query = _query.limit(limit)
        #add offset
        if offset  is not None:
            _query = _query.offset(offset)
        if orderby is not None:
            if isinstance(orderby, dict):  ## deprecated in new version 2021/08/31

                try:
                    order_asc = Order.asc if orderby['direction'] == 'ASC' else Order.desc 
                    _query = _query.orderby(*orderby['columns'], order=order_asc)
                except:
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

        if filters is not None and "rules" in filters:
            _query = _query.where(where_recursive_condition(filters["condition"], filters["rules"]))

        if groupby is not None:
            for key, value in groupby.items():
                _query = _query.groupby(key)
            # _query = _query.groupby(*groupby)

        query = _query.get_sql()
        query = self.formatQuery(tablename, groupby, _query.get_sql(), filters, columnnames, schema=self.schema)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)

        return query


    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                format_string = GetDBDateFormat.get_dbdate_format(db_type="REDSHIFT", format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, format_string, _dict,db_type="REDSHIFT")
                if (not column_expression):
                    column_expression = _dict['expression_value']
                query = query.replace(_key, column_expression, 1)
                expression_column_names_lst.append(column_expression)
        return (query, expression_column_names_lst)



    def formatQuery(self, tablename, groupby=None, query=None, filters=None, columnnames=None, schema=None):
        if not (filters or groupby):
            return query

        for key in tablename.keys():
            table = key                
            alias = tablename[key]

        limit = ""
        if "LIMIT" in query:
            limit = query.split('LIMIT')[1]                

        if "ORDER BY" in query:
            order_by_clause = query.split('ORDER BY')[1]
            order_by_clause = order_by_clause.replace('"' + alias + '".', "")
            query = query.split('ORDER BY')[0] + " ORDER BY " + order_by_clause

        select_clause = query.split(' FROM ')[0]
        if filters is not None or groupby is not None:
            if len(filters) != 0:
                where_clause = query.split('WHERE')[1]
            if groupby:
                if len(groupby) != 0 and len(filters) != 0:
                    where_clause = where_clause.split('GROUP BY')[0]
                    groupClause = query.split('GROUP BY')[1]
                elif len(groupby) != 0:
                    groupClause = query.split('GROUP BY')[1]
        
        stringFormatUpper = "UPPER(columnName) as alias"
        stringFormatLower = "LOWER(columnName) as alias"
        stringFormatInItCap = "INITCAP(columnName) as alias"

        for key, value in columnnames.items():
            for item in value:
                tmp_qry = ""
                if "type" in item:
                    if item['type'].upper() == 'DATE' and item['format'] != '':
                        format_string = GetDBDateFormat.get_dbdate_format(db_type="REDSHIFT", format_string=item['format'])
                        tmp_qry = format_string
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "UPPER":
                        tmp_qry = stringFormatUpper
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "LOWER":
                        tmp_qry = stringFormatLower
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "INITCAP":
                        tmp_qry = stringFormatInItCap
                    
                    if len(tmp_qry):
                        aliasName = '"{}"."{}"'.format(alias, key)
                        tmp_qry = tmp_qry.replace('columnName', aliasName)
                        select_clause = select_clause.replace('"' + key + '"', tmp_qry, 1)        

        if filters is not None:
            if "rules" in filters:
                where_clause = self.formatFilter(alias, filters["condition"], filters["rules"], where_clause)

        if groupby is not None:
            if len(groupby) != 0:
                for key, value in groupby.items():
                    if "type" in value:
                        if (value['type'].upper() == 'DATE' and value['format'] != ''):
                            format_string = GetDBDateFormat.get_dbdate_format(db_type="REDSHIFT", format_string=value['format'])
                            tmp_qry = format_string
                            tmp_qry = tmp_qry.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                            groupClause = groupClause.replace('"' + alias + '"' + '.' + '"' + key + '"', tmp_qry, 1)

        ## schema not used in this function as schema already added while creating connection
        if len(filters) > 0:
            select_clause += ' FROM "{table_name}" "{alias}" WHERE {where_clause}'.format(
                table_name=table, 
                alias=alias,
                where_clause=where_clause
            )
        else:
            select_clause += ' FROM "{table_name}" "{alias}" '.format(table_name=table, alias=alias)
        
        if groupby and len(groupby) > 0:
            select_clause += ' GROUP BY {}'.format(groupClause)

        if len(limit) > 0 and "LIMIT" not in select_clause:
            select_clause += " LIMIT " + limit            

        return select_clause                   

    def create_engine(self):
        # it requires pip install psycopg2
        self.engine_statement = create_engine(
            f'postgresql+psycopg2://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}',
            connect_args={'options': '-c search_path="{}"'.format(self.schema)})

    def get_connection_statement(self):
        statement = f"postgresql+psycopg2://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}"
        return statement

    def readTable(self, tbl_name, limit, **others):
        random_sample = others.get("random_sample", False)
           
        manage_connection = others.get("manage_connection", True)
        if not self.schema:
            query = 'SELECT * FROM "' + tbl_name + '"'
        else:
            query = 'SELECT * FROM ' + self.schema + '."' + tbl_name + '"'
        
        # if random_sample:
        #     query += " ORDER BY RANDOM() "
        
        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection=manage_connection)
        res["df_text"] = None 

        return res   
     
    def getUpdateQuery(self, targetTableName, columnnames={}, filters=[], joins={}, inputTableReplica='temp_table',
                       sqlQuery=None):
        filters = None if filters == [
            {"from": "", "column": "", "operator": "", "value": ""}] or filters == [] else filters
       
        test, final = Tables(inputTableReplica, targetTableName)
        
        _query = PostgreSQLQuery.update(final) 
        _query = _query.from_(test)
        if joins: 
            for k, v in joins.items():
                where = f'{inputTableReplica}"."{k}'
                where_val = f'{targetTableName}"."{v}'
                where_op = 'equal'
                _query = where_Colcondition(where=where, query=_query, where_val=where_val, where_op=where_op)

        if columnnames:
            if joins:
                for k, v in columnnames.items():
                    _query = _query.set(Field(v, table=final), Field(k, table=test))
            else:
                for k, v in columnnames.items():
                    _query = _query.set(Field(v, table=final),k)

        if filters is not None:
            
            for filt in filters:
                ##TODO
                node_from = filt['from']
                wherew = filt['column']
                if node_from == "source":  ## test side
                    where = f'{inputTableReplica}"."{wherew}' 
                else:
                    ## final side
                    where = f'{targetTableName}"."{wherew}' 
                try:
                    where_val = eval(filt['value'])
                except:
                    where_val = filters[where]['filterValue']
                where_op = filt['operator']
                _query = where_condition(where=where, query=_query, where_val=where_val, where_op=where_op)
        if sqlQuery is None:
            return _query.get_sql()
        else:
            return self.updateQueryUsingSubQuery(_query.get_sql(), inputTableReplica, sqlQuery)

    def updateQueryUsingSubQuery(self, updateQuery, inputTableReplica, subQuery):
        
        getJoinPart = updateQuery.split('WHERE')[1]
        newUpdateQuery = updateQuery.split('WHERE')[
                             0] + ' FROM (' + subQuery + ') as ' + inputTableReplica + ' WHERE ' + getJoinPart
        return newUpdateQuery

    def updateType(self, df, tableDetails, mappedColumn):
        dtypedict = {}  # create and empty dictionary        
        for src_col_name, src_col_type in zip(df.columns, df.dtypes):
            if src_col_name in mappedColumn:
                targetMappedColumn = mappedColumn[src_col_name]
                # getting target column name mapped with source
                if targetMappedColumn != '' or targetMappedColumn is not None:
                    targetColumnDetail = next(
                        filter(lambda x: (x[0] == targetMappedColumn), tableDetails['columnName']))
                    # split column datatype value in case of varchar to remove detail part of length
                    targetColumnDataType = targetColumnDetail[1].split('(')[0]
                    if targetColumnDataType == 'varchar' or targetColumnDataType == 'long varchar':
                        dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                    elif targetColumnDataType == 'int':
                        dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                    elif targetColumnDataType == 'float':
                        dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                    elif targetColumnDataType == 'boolean':
                        dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN}) 
                    elif targetColumnDataType == 'timestamp' or targetColumnDataType == 'date':
                        dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME}) 
            else:
                if "object" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                elif "int64" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                elif "float64" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                elif "bool" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN}) 
                elif "datetime64[ns]" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})                        
        return dtypedict

    def updateTable(self, df, targetTableName, columnnames={}, filters=[], joins={}, fromTable=None, sameSchema=False,
                    tableDetails={}, sqlQuery=None):
        ##found_rows=False https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1        

        in_tbl_replica = f'temp_table {str(uuid.uuid1())}' if fromTable is None else fromTable
        in_tbl_replica = in_tbl_replica.replace('-', '_')
        
        sql = self.getUpdateQuery(targetTableName, columnnames, filters, joins, in_tbl_replica, sqlQuery=sqlQuery)
        self.create_engine()

        if sameSchema or in_tbl_replica not in sql:
            with self.engine_statement.begin() as conn:  # TRANSACTION
                t = conn.execute(sql)

                return df, sql
        else:
            try:
                for col in df.select_dtypes('O'):
                    try:
                        df[col] = df[col].str.replace(',', '')
                        df[col] = df[col].str.replace('"', '')
                        df[col] = df[col].str.replace('\\', '')
                    except Exception as e:
                        print(e)

                df.to_sql(in_tbl_replica, self.engine_statement, if_exists='replace',
                          dtype=self.updateType(df, tableDetails, columnnames), index=False)
                # this code will change the sql to support vertica update for two table
                sql_buffer = sql.split('WHERE')                
                where_clause = ' WHERE ' + sql_buffer[1]
                from_clause = ' FROM ' + in_tbl_replica
                set_clause = sql_buffer[0].split('SET')
                upd_clause = set_clause[0]
                set_clause = set_clause[1]               
                column_map = ' SET '
               
                for column in set_clause.split(','):
                    set_clause = column.split('=')
                    if column_map == ' SET ':
                        # when set close varibale have where clouse then appending taht where clouse also                                             
                        column_map = column_map + set_clause[0] + '=' + in_tbl_replica + '.' + set_clause[1]
                    else:                                             
                        column_map = column_map + ',' + set_clause[0] + '=' + in_tbl_replica + '.' + set_clause[1]
                
                sql = upd_clause + column_map + from_clause + where_clause
                # end here the vertica update section
                
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    t = conn.execute(sql)
                    s = conn.execute("DROP TABLE IF EXISTS " + in_tbl_replica)
                return df, sql
            
            except Exception as e:                    
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    sql = f'DROP TABLE IF EXISTS "{in_tbl_replica}"'                
                    s = conn.execute(sql) 

                raise PostgresDMLException(e)  

    def truncateTable(self, table_name):
        if not self.schema:
            query = f'TRUNCATE TABLE {table_name}'
        else:
            query = "TRUNCATE TABLE " + self.schema + "." + table_name
        self.executeSql(query)

    def generateCreateTableScript(self, tableDetails):
        query = "CREATE TABLE " + '"' + tableDetails["tableName"] + '"' + "("

        len_col = len(tableDetails["colDetails"])
        index = 0

        for x in tableDetails["colDetails"]:
            index += 1
            query = query + '"' + x['columnName'] + '"'
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
                
            # if x['nullable'] == "true":
            #     query += " NULL"
            # else:
            #     query += " NOT NULL"      
                
            if 'default' in x and len(x["default"]) > 0:
                query += " DEFAULT " + x["default"]
                
            if (index < len_col):
                query += ","     
            else:
                ## Add FK contraints
                if 'fk' in tableDetails:
                    len_fk = len(tableDetails["fk"])
                    fk_index = 0
                    fk_query = ","
                    for y in tableDetails["fk"]:
                        fk_index += 1
                        # CONSTRAINT `daas_assets_created_by_4ce65b17_fk_daas_user_id` FOREIGN KEY (`created_by`) REFERENCES `daas_user` (`id`),
                        fk_query += " CONSTRAINT " + y['keyName'] + " FOREIGN KEY (`" + y[
                            'columnFK'] + "`) REFERENCES `" + y['table'] + "` (`" + y['column'] + '`)'
                        if (fk_index < len_fk):
                            fk_query += ","
                            
                    query += fk_query                                            
                query += ")"     

        return query

    def generateCreateTableScriptETL(self, table_dtls):
        tbl_name = table_dtls["tableName"]
        col_data = table_dtls['createColumnData']

        sep = '"'
        sql_stmt = f'CREATE TABLE  "{self.schema}"."{tbl_name}"'

        lst_cols = []
        if len(col_data) > 0:
            for col_dtls in col_data:
                col = col_dtls['target_column']
                datatype = col_dtls['datatype']
                col_query = f' {sep}{col}{sep} {datatype}'
                lst_cols.append(col_query)

        cols_query = ",".join(lst_cols)
        query = f'''{sql_stmt} ( {cols_query} ) '''

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

        query = 'SELECT DISTINCT "{col_name}" as values FROM "{tbl_name}" WHERE 1 = 1 ORDER BY "{col_name}" {order};'.format(
            col_name=col_name,
            tbl_name=table_name,
            order=order
        )  

        results = pd.read_sql(query, self.connection) 
        self.close()
        
        return results['values'].tolist()          

    def getColumnsProfile(self, table_name, with_min_max=False, filter=None):
        df_col_dtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = '"' + table_name + '"'

        if self.schema is not None:
            full_table_name = '"' +self.schema + '"' + "." + full_table_name

        index = 0
        for row in df_col_dtls:
            if row["data_type"].upper() in ['TIMESTAMP', 'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'DOUBLE PRECISION',
                                    'SMALLINT', 'INTEGER', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL', ]:
                sub_query = """ 
                    SELECT '{col_name}' AS COLUMN_NAME, 
                    '{data_type}' AS DATA_TYPE, 
                """
                if with_min_max:
                    sub_query += """  
                        MAX({col_name}) AS MAX_VAL, 
                        MIN({col_name}) AS MIN_VAL,  
                    """
                sub_query += """
                    COUNT(DISTINCT {col_name}) AS UNQ_VAL, 
                    COUNT(1) AS TOTAL_COUNT, 
                    SUM(CASE WHEN({col_name} IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT 
                """
            else:
                sub_query = """ 
                    SELECT '{col_name}' AS COLUMN_NAME, 
                    '{data_type}' AS DATA_TYPE , 
                """
                if with_min_max:
                    sub_query += """  
                        MAX(0) AS MAX_VAL, 
                        MIN(0) AS MIN_VAL,  
                    """
                sub_query += """
                    COUNT(DISTINCT {col_name}) AS UNQ_VAL, 
                    COUNT(1) AS TOTAL_COUNT, 
                    SUM(CASE WHEN({col_name} IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT 
                """

            sub_query += """ FROM {table_name}  """

            if filter:
                sub_query += " WHERE " + filter


            sub_query = sub_query.format(
                col_name=row["column_name"].lower(), 
                data_type=row["data_type"].lower(),
                table_name=full_table_name
            )
            
            df_sub = self.executeQuery(sub_query)

            if index == 0:
                df = df_sub.copy()
            else:
                df = pd.concat([df, df_sub])
                
            index += 1             

        return df    

   
    def getTableRows(self, table_name=None):

        query=""" 
              SELECT 
              "table" as TABLE_NAME,
              "tbl_rows" as NO_OF_ROWS,
              "size" as SIZE_IN_MB
              from svv_table_info 
              where 1=1
              """
        
        if table_name:
            query += ''' and "table" IN {} '''.format(table_name)

        if self.schema is not None:
            query += """ and "schema" = '{}'""".format(self.schema)
        
        df = self.executeQuery(query, limit=None)
        
        df.columns = [x.upper() for x in df.columns] 

        return df


    def getTableDetails(self, table_name=None, type={}):
        
        sep = "','"
        if table_name:
            if isinstance(table_name, list):
                table_name = "('{}')".format("', '".join(table_name))
            else:
                table_name = "('{}')".format(table_name)
        
        df_row = self.getTableRows(table_name=table_name)

        query = """
            SELECT 
            t.table_schema as TABLE_SCHEMA,
            t.table_name as TABLE_NAME, 
            col.n_col as NO_OF_COLS,                              
            t.table_type as TABLE_TYPE,
            '' as TABLE_COMMENT,     
            null as LAST_UPDATED
            FROM information_schema.tables t   
                left join (
                            select 
                            table_schema,
                            table_name , 
                            count(1) as n_col 
                            from information_schema.columns  cc
                            group by 1,2
                          ) col 
                on col.table_schema = t.table_schema 
                and col.table_name = t.table_name
            where 1=1
            """

        if table_name:
            query += """ and t.table_name IN {table_name}""".format(table_name=table_name)

        if self.schema is not None:
            query += " and t.table_schema = '{}'".format(self.schema)


        df_temp = self.executeQuery(query, limit=None)
        df_temp.columns = [x.upper() for x in df_temp.columns] 


        df = pd.merge(df_temp, df_row, on=['TABLE_NAME'], how='inner')
        df.columns = [x.upper() for x in df.columns]
    
        return df

    def getTableRelationships(self, table_name, bi_directional=False):
        query = """
            SELECT 
                fk_tco.table_name AS table_name,
                c.column_name AS col_name,
                pk_tco.table_name AS ref_table_name,
                pk_c.column_name AS ref_col_name
            FROM information_schema.table_constraints fk_tco
            JOIN information_schema.referential_constraints rco
                ON fk_tco.constraint_name = rco.constraint_name
                AND fk_tco.table_catalog = rco.constraint_catalog
                AND fk_tco.table_schema = rco.constraint_schema
            JOIN information_schema.table_constraints pk_tco
                ON rco.unique_constraint_name = pk_tco.constraint_name
                AND rco.unique_constraint_catalog = pk_tco.table_catalog
                AND rco.unique_constraint_schema = pk_tco.table_schema
            JOIN information_schema.key_column_usage c
                ON c.constraint_name = fk_tco.constraint_name
                AND c.table_catalog = fk_tco.table_catalog
                AND c.table_schema = fk_tco.table_schema
                AND c.table_name = fk_tco.table_name
            JOIN information_schema.key_column_usage pk_c
                ON pk_c.constraint_name = pk_tco.constraint_name
            WHERE pk_tco.table_name = '{table_name}' 
            OR fk_tco.table_name = '{table_name}'
        """         

        query = query.format(table_name=table_name)

        if self.schema:
            sub_qry = " and pk_tco.table_schema = '{schema}' ".format(schema=self.schema)
            query += sub_qry
        
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
            encloser='"',
            target_encloser = target_encloser
        )
        merge_query =mrgstmt.get_query()
        
        return merge_query
    
    def getDropTableQuery(self, table_name):
        return f"DROP TABLE IF EXISTS {table_name}"

    def dropTable(self, table_name):
        query = self.getDropTableQuery(table_name)
        self.executeSql(query) 
       
    def getTableIndexDetails(self, tablename):
        query = """
                SELECT 
                i.schemaname AS "TABLE_SCHEMA",
                c.relname AS "TABLE_NAME", 
                d.attname AS "COLUMN_NAME",
                a.relname AS "INDEX_NAME",
                CASE 
                    WHEN UPPER(i.indexdef) LIKE '%USING BTREE%' THEN 'B-TREE'     
                    WHEN UPPER(i.indexdef) LIKE '%USING HASH%' THEN 'HASH'      
                    WHEN UPPER(i.indexdef) LIKE '%USING GIST%' THEN 'GiST'      
                    WHEN UPPER(i.indexdef) LIKE '%USING SP-GIST%' THEN 'SP-GiST'
                    WHEN UPPER(i.indexdef) LIKE '%USING GIN%' THEN 'GIN'
                    WHEN UPPER(i.indexdef) LIKE '%USING BRIN%' THEN 'BRIN'
                    ELSE '' 
                    END AS "INDEX_TYPE",
                    '' as "SEQUENCE"
                FROM 
                pg_class a
                INNER JOIN 
                    pg_index b ON a.oid = b.indexrelid
                INNER JOIN 
                    pg_class c ON b.indrelid = c.oid
                INNER JOIN 
                    pg_attribute d ON c.oid = d.attrelid
                INNER JOIN 
                    pg_indexes i ON c.relname = i.tablename AND i.indexdef LIKE '%' || d.attname || '%' AND c.relname = i.tablename              
                INNER JOIN 
                    information_schema.tables t ON c.relname = t.table_name
                WHERE 
                t.TABLE_CATALOG='{}'
                AND t.TABLE_NAME = '{}'
                """.format(self.dbname, tablename)

        if self.schema:
            query += " AND t.TABLE_SCHEMA ='{}'".format(self.schema)
        
        df = self.executeQuery(query, limit=None)

        return df

    def dq_dashboard_data_freshness_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') as date_col,
            count(1) row_added
            from %(table_name)s 
            where TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD')
            between TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            group by 1 order by 1
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})
        
        return query

    def dq_dashboard_data_modify_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') as date_col,
            count(1) row_added
            from %(table_name)s 
            where TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD')
            between TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            group by 1 order by 1
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})
        
        return query

    def dq_dashboard_data_delete_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') as date_col,
            count(1) row_added
            from %(table_name)s 
            where %(col_name)s is not null and 
            TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            group by 1 order by 1
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})
        
        return query

    def dq_dashboard_stk_query(self, tablename, columnname, fromdate, todate, datasources_col_name):
        query = '''
            select TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') as date_col,
            NULLIF(%(datasources_col_name)s,'Other') src,
            count(1) row_added
            from %(table_name)s  
            where TO_DATE(TO_CHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') between TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            group by 1,2 order by 1
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate,
                "datasources_col_name": datasources_col_name})
        
        return query

    def get_incremental_columns(self, table_name):
        try:
            # added distinct for unique data
            query = """ 
                select DISTINCT
                    c.column_name as "COLUMN_NAME", 
                    c.data_type as "DATA_TYPE"
                FROM information_schema.tables t   
                left join information_schema.columns c 
                    on  c.table_schema = t.table_schema 
                    and c.table_name = t.table_name   
                left join information_schema.constraint_column_usage as ccu 
                    on ccu.table_schema = t.table_schema 
                    and ccu.table_name = t.table_name and ccu.column_name = c.column_name 
                left join information_schema.table_constraints tco 
                    on tco.table_schema = t.table_schema 
                    and tco.constraint_name = ccu.constraint_name 
                    and tco.table_name = t.table_name 
                left join information_schema.key_column_usage kcu
                    on tco.constraint_schema = kcu.constraint_schema
                    and tco.constraint_name = kcu.constraint_name
                WHERE                     
                    (c.is_nullable = 'NO' or (c.is_nullable = 'YES' and c.column_default is not null))
                    and
                    (
                    	(c.data_type like ('timestamp%') 
                    	or c.data_type = 'date')
                    	or 
                    	(	(upper(tco.constraint_type) = 'PRIMARY KEY' 
                    			or upper(tco.constraint_type) = 'UNIQUE')
                    		and data_type = 'integer'
                    	)
                    )
                    AND  t.TABLE_CATALOG='{dbname}' 
                    AND t.TABLE_NAME = '{table_name}'  
                    AND t.TABLE_SCHEMA ='{tab_schema}' """.format(tab_schema=self.schema, dbname=self.dbname,
                                                                  table_name=table_name)
           
            self.connect()
            df = self.executeQuery(query, limit=None)

        except Exception as e:
            self.close()
            raise PostgresDMLException(e)

        return df

    def fetch_delta_columns(self, table_name, **others):
        try:
            df = None
            inc_cols = self.get_incremental_columns(table_name)

            full_table_name = '"' + table_name + '"'
            if self.schema is not None:
                full_table_name = '"' + self.schema + '"' + "." + full_table_name

            index = 0
            for index, row in inc_cols.iterrows():
                sub_query = """ 
                    SELECT 
                        '{col_name}' AS COLUMN_NAME,
                        '{DATA_TYPE}' as DATA_TYPE,
                        COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                        COUNT(1) AS TOTAL_COUNT, 
                        COALESCE(SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END),0) AS NULL_CNT 
                    FROM {table_name}
                """

                sub_query = sub_query.format(
                    col_name=row["column_name"],
                    table_name=full_table_name,
                    DATA_TYPE=row['data_type']
                )

                df_sub = self.executeQuery(sub_query)
                df = df_sub.copy() if index == 0 else pd.concat([df, df_sub])
                
                index += 1
            if df is not None:
                df.columns = df.columns.str.upper()
                date_cols = df.loc[(df['DATA_TYPE'].str.upper().str.contains('TIME*|DATE*'))]
                if not date_cols.empty:
                    date_cols = date_cols[date_cols['UNQ_VAL'] == date_cols['UNQ_VAL'].max()]
                
                int_cols = df.loc[(df['DATA_TYPE'].str.upper().str.contains('INT*'))]
                if not int_cols.empty:
                    int_cols = int_cols.loc[
                        int_cols['UNQ_VAL'] == int_cols['TOTAL_COUNT']]
                df = pd.concat([int_cols, date_cols], axis=0)
                df = df[['COLUMN_NAME', 'DATA_TYPE']]
            else:
                df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])
        except Exception as e:
            self.close()
            raise PostgresDMLException(e)

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
            select_clause = "select count(1) as CNT from " + tbl_name.lower()
        else:
            select_clause = "select count(1) as CNT from " + self.schema + "." + tbl_name.lower()        

        for con in on_condition:
            where_clause += condition.format(col_name = con["target_col"].lower(), value = row[con["source_col"]])

        qry = select_clause + where_clause

        print("find stmt :", qry)    
        df = self.executeQuery(qry, manage_connection=manage_connection)
        df.columns = map(str.upper, df.columns)
        if df["CNT"][0] > 0:
            found = True

        return found    

    def update_row(self, tbl_name, row, on_condition, matched_mapping, col_details, manage_connection=False):
        if isinstance(on_condition, str):
            try:
                on_condition = json.loads(on_condition)
            except Exception:
                pass

        condition = " and {col_name} = '{value}'"

        where_clause = " where 1=1 "
        set_clause = " set "

        if not self.schema:
            upd_clause = "update " + tbl_name
        else:
            upd_clause = "update " + self.schema + "." + tbl_name        

        for con in on_condition:
            where_clause += condition.format(col_name = con["target_col"], value = row[con["source_col"]])

        for key in matched_mapping.keys():
            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += merge_stmt_dict["POSTGRES"]["set"]["NULL"].format(col_name = key, value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += merge_stmt_dict["POSTGRES"]["set"][col_type].format(col_name = key, value = row[matched_mapping[key]].replace("'", "''"))                            
                else :
                    set_clause += merge_stmt_dict["POSTGRES"]["set"][col_type].format(col_name = key, value = row[matched_mapping[key]])                   

        set_clause = set_clause.rstrip(",")
        qry = upd_clause + set_clause + where_clause

        print("upd_stmt :", qry)
        return self.executeSql(qry, manage_connection=manage_connection)

    def insert_row(self, tbl_name, row, non_matched_mapping, col_details, manage_connection):

        '''
            INSERT INTO SCIKIQ_DEV.ORDERS
            (ID, CUSTOMER_ID, PRODUCT_ID, QUANTITY, PRICE, TOTAL_AMOUNT, STORE_ID, CREATED_DATE, CREATED_BY)
            VALUES(0, 0, 0, 0, 0, 0, 0, '', '');        
        '''

        if not self.schema:
            inst_clause = f"INSERT INTO {tbl_name} "
        else:
            inst_clause = f"INSERT INTO {self.schema}.{tbl_name}"

        inst_clause += " ({cols}) VALUES ({values})"

        cols = ""
        values = ""
        for key in non_matched_mapping.keys():
            cols += key + ","

            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if not pd.isnull(row[non_matched_mapping[key]]):
                if isinstance(row[non_matched_mapping[key]], str):
                    values += merge_stmt_dict["POSTGRES"]["insert"][col_type].format(value = row[non_matched_mapping[key]].replace("'", "''")) + ","
                else:
                    values += merge_stmt_dict["POSTGRES"]["insert"][col_type].format(value = row[non_matched_mapping[key]]) + ","
            else :
                values += merge_stmt_dict["POSTGRES"]["insert"]["NULL"].format(value = 'null') + ","

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection=manage_connection)

