import json
from collections import OrderedDict
from decimal import Decimal
from urllib.parse import quote

import pandas as pd
from google.api_core import exceptions
from google.cloud import bigquery
from google.cloud.bigquery import dbapi
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account
from pypika import Field, JoinType, Order, Tables
from pypika import Table as PikaTable
from pypika import functions as fn
from pypika.dialects import SnowflakeQuery
from sqlalchemy import create_engine
from sqlalchemy import types as sqlalchemyTypes

from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict
from scikiq_dbutils.handlers.DBConnection import (
	MergeStatement,
	clsDBConnection,
    ViewCreationError,
	where_Colcondition,
	where_condition,
	where_recursive_condition,
	where_recursive_condition_col_dict,
)
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.utils import generateCustomColumnExpression, remove_double_quotes


class BigQueryConnectException(Exception):
	pass

class clsBigQuery(clsDBConnection):
    def __init__(self, config):
        try:
            self.cred = {}
            self.cred['type'] = config['type']
            self.cred['project_id'] = config['project_id']
            self.cred['private_key_id'] = config['private_key_id']
            self.cred['private_key'] = config['private_key']
            self.cred['client_email'] = config['client_email']
            self.cred['client_id'] = config['client_id']
            self.cred['auth_uri'] = config['auth_uri']
            self.cred['token_uri'] = config['token_uri']
            self.cred['auth_provider_x509_cert_url'] = config['auth_provider_x509_cert_url']
            self.cred['client_x509_cert_url'] = config['client_x509_cert_url']
            self.project_id = config['project_id']
            self.dataset_id = config['dataset_id']
            self.df = None
            self.compute_result = None
            self.credentials = None
            self.storage_client = None
            self.resource_key = None
            if ("resource_key" in config):
                self.resource_key = config["resource_key"]
        
            self.db_type = "BIGQUERY"
        
        except AttributeError as e:
            raise BigQueryConnectException("BigQuery Connection details are not provided. Msg : " + str(e))

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        success = True
        try :
            self.connect()

            if comment :
                qry = """ALTER TABLE `{dataset_id}.{table_name}`
                         ALTER COLUMN `{column_name}`
                         SET OPTIONS (
                         description="{comment}"
                         );""".format(
                    dataset_id=self.dataset_id,
                    comment=comment,
                    table_name=tbl_name,
                    column_name=col_name
                )            
            else :
               qry = """ALTER TABLE `{dataset_id}.{table_name}`
                         ALTER COLUMN `{column_name}`
                         SET OPTIONS (
                         description= NULL
                         );""".format(
                    dataset_id=self.dataset_id,
                    table_name=tbl_name,
                    column_name=col_name
                )             
            self.executeSql(qry)
        except Exception as e :
            self.close()
            print(e)
            success = False
        return success                   

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'
            self.cred = json.loads(json.dumps(self.cred))
            self.credentials = service_account.Credentials.from_service_account_info(self.cred)
            self.bigquery_client = bigquery.Client(credentials=self.credentials)
            self.connection = dbapi.Connection(self.bigquery_client)
            self.cursor = self.connection.cursor()
            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsBigQuery, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsBigQuery, self).callConnectionAudit(resp)
            raise

    def testConnection(self):
        result = {}
        self.connect()
        try:
            data = self.bigquery_client.get_dataset(self.dataset_id)  # Make an API request.
            result['msg'] = "Success"
            result['status'] = 200
            result['data'] = data
            result['error'] = 0
        except NotFound:
            result['msg'] = "Dataset {} is not found".format(self.dataset_id)
            result['status'] = 404
            result['error'] = 1

        super(clsBigQuery, self).callConnectionAudit(result)

        return result

    def createView(self, view_name, sql_query):
        '''
           @Description : View is the result set of a stored query on the data.
           param:
           view_name: view name (required)
           sql_query: query for view(required)
        '''
        try:
            crt_stmt = "CREATE OR REPLACE VIEW {}.{} AS {}".format(self.dataset_id, view_name, sql_query)
            res = self.executeSql(crt_stmt)
            if not res['status']:
                print(res['msg'])
                # Raise an exception with the response message
                raise ViewCreationError(f"Failed to create view '{view_name}': {res['msg']}")
        except Exception as e:
            print(e)
            raise
        return view_name

    def close(self):
        if self.cursor:
            self.cursor.close()

        if self.connection:
            self.connection.close()

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=100000, profile=False):
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
                self.close()
        except Exception as e:
            if manage_connection:
                self.close()
            print(e)
            raise

        if use_polars:
            import polars as pl
            results = pl.from_pandas(results)

        return results

    def executeSql(self, query, manage_connection=True):
        success  = 0
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
            success  = 1
        except Exception as e:
            if manage_connection:
                self.close()
            msg = str(e)
            success  = 0

        res = {}
        res["status"] = success 
        res["result"] = x
        res["msg"] = msg

        return res

    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=10000, dtype={}):
        self.connect()
        self.create_engine()
        if self.dataset_id is not None:
            tablename = "{dataset_id}.{tablename}".format(dataset_id=self.dataset_id, tablename=tablename)
            
        df.to_sql(con=self.engine, name=tablename, if_exists='append', index=False, chunksize=chunksize)
        return df

    def load_table_from_dataframe(self, tablename, df, if_exists='replace', chunksize=10000, schema={}):
        try:
            #10/09/24 if insertion fails, schema is persisted. lead to datatype errors for next time.
            table_columns = self.getTableColumns(tablename)
            
            if not table_columns and not schema:
                # Table doesn't exist, create it with DataFrame schema
                schema = [bigquery.SchemaField(col, self.get_bq_dtype(df[col].dtype)) for col in df.columns]
            else:
                # Table schema is like STRING(250) failing.. (table_columns schema)

                # df dtype like int and schema strning failing.. need to convert 
                for col, field_type in table_columns:
                    if col in df.columns:
                        try:
                            df[col] = df[col].apply(lambda x: self.convert_bigquery_dtype(x, field_type))

                        except Exception as e:
                            raise ValueError(f"Error converting column '{col}' to {field_type}: {str(e)}")

            job_config = bigquery.LoadJobConfig(
                schema=schema,
                write_disposition="WRITE_APPEND"
            )

            self.connect()
            load_job = self.bigquery_client.load_table_from_dataframe(
                df, f"{self.dataset_id}.{tablename}", job_config=job_config
            )
            job_result = load_job.result()  # Waits for the job to complete

            return job_result

        except exceptions.NotFound as e:
            raise BigQueryConnectException(f"Table or dataset not found: {str(e)}")
        except exceptions.BadRequest as e:
            raise BigQueryConnectException(f"Invalid request: {str(e)}")
        except exceptions.Forbidden as e:
            raise BigQueryConnectException(f"Insufficient permissions: {str(e)}")
        except ValueError as e:
            raise BigQueryConnectException(f"Data conversion error: {str(e)}")
        except Exception as e:
            raise BigQueryConnectException(f"Unexpected error occurred: {str(e)}")


    def convert_bigquery_dtype(self, value, target_type):
        if pd.isna(value):
            return None
        
        try:
            if target_type == 'DATETIME':
                return pd.to_datetime(value)
            elif target_type == 'DATE':
                return pd.to_datetime(value).date()
            elif target_type == 'TIME':
                return pd.to_datetime(value).time()
            elif target_type == 'TIMESTAMP':
                return pd.to_datetime(value)
            elif target_type == 'INT64':
                return int(value)
            elif target_type == 'INTEGER':
                return int(value)
            elif target_type == 'FLOAT64':
                return float(value)
            elif target_type == 'FLOAT':
                return float(value)
            elif target_type == 'NUMERIC':
                return Decimal(str(value))
            elif target_type == 'BIGNUMERIC':
                return Decimal(str(value))
            elif target_type == 'BOOL':
                return bool(value)
            elif target_type == 'BOOLEAN':
                return bool(value)
            elif target_type == 'STRING':
                return str(value)
            elif target_type == 'BYTES':
                return str(value).encode()
            elif target_type.startswith('ARRAY'):
                if isinstance(value, str):
                    return json.loads(value)
                return list(value)
            elif target_type == 'STRUCT':
                if isinstance(value, str):
                    return json.loads(value)
                return dict(value)
            elif target_type == 'GEOGRAPHY':
                return str(value)  # Assuming GeoJSON string
            else:
                return str(value)
        except Exception as e:
            raise ValueError(f"Error converting value '{value}' to {target_type}: {str(e)}")

    def get_bq_dtype(self, pd_dtype):
        if pd.api.types.is_datetime64_any_dtype(pd_dtype):
            return 'DATETIME'
        elif pd.api.types.is_integer_dtype(pd_dtype):
            return 'INT64'
        elif pd.api.types.is_float_dtype(pd_dtype):
            return 'FLOAT64'
        elif pd.api.types.is_bool_dtype(pd_dtype):
            return 'BOOL'
        else:
            return 'STRING'

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()
        query = "SELECT TABLE_NAME,TABLE_TYPE, table_schema as TABLE_SCHEMA FROM {dataset_id}.INFORMATION_SCHEMA.TABLES".format(dataset_id=self.dataset_id)

        if include_view == True:
            query += " WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')"
        else:
            query += " WHERE TABLE_TYPE = 'BASE TABLE'"

        if search:
            query += " AND TABLE_NAME LIKE ('%{}%')".format(search)




        query += " ORDER BY TABLE_NAME ASC;"
        try:
            self.cursor.execute(query)
        except Exception as e:
            print(e)

        results = self.cursor.fetchall()
        # self.close()
        return tuple(tuple(x) for x in results)

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)
        tbls_data = []
        for tbl in results:
            tdata = {}
            tbl = list(tbl)[0]
            tdata["tablename"] = tbl
            query = """ 
                SELECT 
                   COLUMN_NAME,
                   DATA_TYPE as DATA_TYPE 
                FROM {}.INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ('{}')
            """.format(self.dataset_id,tbl)

            query += " ORDER BY COLUMN_NAME "

            self.connect()
            self.cursor.execute(query)

            result = tuple(tuple(x) for x in self.cursor.fetchall())
            tdata["columnname"] = result
            tbls_data.append(tdata)

        self.close()
        return tbls_data

    def getTableColumns(self, tablename, type=''):
        query = """
                SELECT
                     COLUMN_NAME,
                     DATA_TYPE as DATA_TYPE
                     FROM {}.INFORMATION_SCHEMA.COLUMNS
                     WHERE TABLE_NAME = ('{}')
                """.format(self.dataset_id, tablename)
        
        query += " ORDER BY COLUMN_NAME "
        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        results = tuple(tuple(x) for x in results)

        self.close()
        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        test_type= self.getTableDetails(table_name=tbl_name)
        t_type=test_type['TABLE_TYPE'][0]

        query = """
            SELECT
                table_schema as TABLE_SCHEMA,
                table_name as TABLE_NAME,
                column_name as COLUMN_NAME,
                '{t_type}' as TABLE_TYPE,
                data_type as DATA_TYPE,
                ordinal_position as ORDINAL_POSITION,
                is_nullable as IS_NULLABLE,
                65535 as DATA_TYPE_LENGTH, 
                100 as NUMERIC_PRECISION, 
                65535 as CHARACTER_MAX_LENGTH, 
                65535 as CHARACTER_MAXIMUM_LENGTH, 
                100 as NUMERIC_SCALE, 
                '' as COMMENT            
            FROM
                `{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table_name}' 
        """.format(t_type=t_type,dataset_id = self.dataset_id, table_name = tbl_name)

        if sort_on_position:
            query += " ORDER BY ordinal_position"
        else:
            query += " ORDER BY column_name"        

        self.connect()
        self.cursor.execute(query)
        desc_value = [d[0] for d in self.cursor.description]
        desc = [item.upper() for item in desc_value]
        results = [dict(zip(desc, res)) for res in self.cursor.fetchall()]
        self.close()

        return results


    def getRenamesColMetricsDict(self, config_details=OrderedDict()):
        pass

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
        tblsName = {}
        ## table name is a key value pair {"dim_projects" : "dp"} tablename and alias
        if tablename is not None:
            for key in tablename.keys():
                tblName = key
                alias = tablename[tblName]
                # if not self.dataset_id:
                #     tbls[alias] = Table(tblName, alias=alias)
                # else:
                #     tbls[alias] = Table(tblName, alias=alias, schema=self.dataset_id)
                tbls[alias] = PikaTable(tblName, alias=alias, schema=self.dataset_id)
                tblsName[alias] = tblName

        index = 0
        for key in tbls.keys():
            if index == 0:
                _query = SnowflakeQuery.from_(tbls[key])
            else:
                if tblsName[key] in joins:
                    joinType = joins[tblsName[key]]
                    if joinType == "inner":
                        how = JoinType.inner
                    elif joinType == "right":
                        how = JoinType.right
                    elif joinType == "left":
                        how = JoinType.left
                    elif joinType == "full":
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
            ##cols = [agg_func[v](k) if v !='' else k for k,v in columnnames.items()]
            lstFields = []
            # Add column names which is derived/custom columns by user
            custom_column_names_dict = {}

            for key, value in columnnames.items():
                ## Change input pattern now value will be list
                for listItem in value:
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
                            # lstFields.append(Field(tbls[coltblName], agg_func[value](colName)))
                            lstFields.append(agg_func[value](eval('tbls[coltblName]' + "." + colName)))
                        else:
                            if " as " in colName:
                                lstFields.append(Field(colName.split(" as ")[0], table=tbls[coltblName],
                                                       alias=colName.split(" as ")[1]))
                            else:
                                lstFields.append(Field(colName, table=tbls[coltblName]))
                    else:
                        if str(listItem['agg']).upper() == 'DISTINCT COUNT':
                            lstFields.append(fn.Count(Field(key), alias=listItem['alias']).distinct())
                        elif listItem['agg'] != '':
                            lstFields.append(
                                agg_func[str(listItem['agg']).upper()](Field(key), alias=listItem['alias']))
                        else:
                            lstFields.append(Field(key).as_(listItem['alias']))

                    # Add custom column in the list.
                    if 'column_type' in listItem.keys():
                        if listItem['column_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = listItem['expression']
                    elif 'col_type' in listItem.keys():
                        if listItem['col_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = listItem['expression']

                            # _query = _query.select(*(cols))
        if distinct:
            _query = _query.select(*lstFields).distinct()
        else:
            _query = _query.select(*lstFields)

        if limit is not None:
            if isinstance(limit, list) and len(limit) == 1:
                limit = int(limit[0])
                _query = _query.limit(limit)
            elif isinstance(limit, str):
                limit = int(limit)
                _query = _query.limit(limit)
            elif isinstance(limit, int):
                _query = _query.limit(limit)

        # add offset
        if offset is not None:
            _query = _query.offset(offset)

        if orderby is not None:
            if isinstance(orderby,dict): ## deprecated in new version 2021/08/31

                try:
                    order_asc = Order.asc if orderby['direction'] == 'ASC' else Order.desc
                    for index, order_by_column_name in enumerate(orderby['columns'], start=0):
                        for column_name, column_config in columnnames.items():
                            if column_name == order_by_column_name:
                                orderby['columns'][index] = column_config[0]['alias']
                    _query = _query.orderby(*orderby['columns'], order=order_asc)
                except Exception:
                    __column_names_list = columnnames.keys()
                    for key, value in orderby.items():
                        order_asc = Order.asc if value == 'ASC' else Order.desc
                        colIndexDct = self.getRenamesColMetricsDict(columnnames)
                        if key in __column_names_list:
                            if key in colIndexDct:
                                for _index in colIndexDct[key]:
                                    _query = _query.orderby(_index + 1, order=order_asc)

            elif isinstance(orderby,list):
                for dct in orderby:
                    for col,asc_desc in dct.items():
                        order_asc = Order.asc if asc_desc == 'ASC' else Order.desc
                        _query  = _query.orderby(col,order=order_asc)


        whre_cond_col_dict = {}
        if filters is not None:
            if "rules" in filters:
                _query = _query.where(
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
                    dbType="SNOWFLAKE",
                    col_date_format_dict=col_date_format_dict,
                    col_date_format_list=col_date_format_list,
                    colDict=columnnames
                )

        if groupby is not None:
            for key, value in groupby.items():
                _query = _query.groupby(key)

        query = _query.get_sql(alias_quote_char = "`")

        # replacing string from last occurance.
        for col in whre_cond_col_dict:
            if col:
                col_count = whre_cond_col_lst.count(col)
                split_lst = query.rsplit(col, col_count)
                if len(split_lst) > 0:

                    if len(split_lst) == 2:
                        split_lst[0] = split_lst[0][:-2] + ' '
                        split_lst[1] = ' ' + split_lst[1][1:]
                        query = col.join(split_lst)

                    elif len(split_lst) == 3:
                        split_lst[0] = split_lst[0][:-2] + ' '
                        split_lst[1] = ' ' + split_lst[1][1:len(split_lst[1]) - 1] + ' '
                        split_lst[2] = ' ' + split_lst[2][1:]
                        query = col.join(split_lst)

        query = self.formatQuery(tablename, groupby, query, filters, columnnames, dataset_id=self.dataset_id)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)
        return query

    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                format_string = GetDBDateFormat.get_dbdate_format(db_type="BIGQUERY", format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, format_string, _dict,db_type="BIGQUERY")
                if (not column_expression):
                    column_expression = _dict['expression_value']
                query = query.replace(_key, column_expression, 1)
                expression_column_names_lst.append(column_expression)
        return (query, expression_column_names_lst)


    def formatQuery(self, tablename, groupby=None, query=None, filters=None, columnnames=None, dataset_id=None):
        ## if no filters or group by then no need to format query
        # if filters is None and groupby is None:
        if not (filters or groupby):
            return query

        elif len(filters) == 0 and len(groupby.keys()) == 0:
            return query

        for key in tablename.keys():
            table = key
            alias = tablename[key]

        select_clause = query.split(' FROM ')[0]

        if filters is not None or groupby is not None:
            if len(filters) != 0:
                where_clause = query.split('WHERE')[1]
            if groupby:
                if len(groupby) > 0 and len(filters) > 0:
                    where_clause = where_clause.split('GROUP BY')[0]
                    group_clause = query.split('GROUP BY')[1]
                elif len(groupby) > 0:
                    group_clause = query.split('GROUP BY')[1]

        for key, value in columnnames.items():
            for item in value:
                if "type" in item:
                    if item['type'] == 'date' and item['format'] != '':
                        format_string = GetDBDateFormat.get_dbdate_format(db_type="BIGQUERY", format_string=item['format'])
                        temp_query = format_string
                        temp_query = temp_query.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        temp_query = temp_query.replace('alias', '"' + item['alias'] + '"')
                        temp_query = temp_query.replace('colFormat', format_string)
                        select_clause = select_clause.replace('"' + key + '"', temp_query, 1)

        if filters is not None:
            if "rules" in filters:
                where_clause = self.formatFilter(alias, filters["condition"], filters["rules"], where_clause)

        if groupby:
            if len(groupby) != 0:
                for key, value in groupby.items():
                    if "type" in value:
                        if (value['type'].upper() == 'DATE' and value['format'] != ''):
                            format_string = GetDBDateFormat.get_dbdate_format(db_type="BIGQUERY", format_string=value['format'])
                            temp_query = format_string
                            temp_query = temp_query.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                            temp_query = temp_query.replace('alias', '"' + key + '"')
                            temp_query = temp_query.replace('colFormat', format_string)
                            group_clause = group_clause.replace('"' + alias + '"' + '.' + '"' + key + '"', temp_query, 1)
        
        ## schema not used in this function as schema already added while creating connection
        if len(filters) > 0:
            select_clause += ' FROM `{dataset_id}`.`{table_name}` `{alias}` WHERE {where_clause}'.format(
                dataset_id=dataset_id, 
                table_name=table, 
                alias=alias,
                where_clause=where_clause
            )
        else:
            select_clause += ' FROM `{dataset_id}`.`{table_name}` `{alias}` '.format(
                dataset_id=dataset_id,
                table_name=table, 
                alias=alias)

        if groupby:
            if len(groupby) > 0:
                select_clause += ' GROUP BY {}'.format(group_clause)

        return select_clause


    def create_engine(self):
        self.engine = create_engine("bigquery://", credentials_info=self.cred)

    def readTable(self, tbl_name, limit, **others):
        random_sample = others.get("random_sample", False)
        manage_connection = others.get("manage_connection", True)   
        query = "SELECT * FROM {}.{}".format(self.dataset_id, tbl_name)

        if random_sample:
            query += " ORDER BY RAND() "

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection = manage_connection)
        res["df_text"] = None

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
        filters = None if filters == [{"from": "", "column": "", "operator": "", "value": ""}] or filters == [] else filters

        test, final = Tables(inputTableReplica, targetTableName)

        _query = SnowflakeQuery.update(final)
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
                    _query = _query.set(Field(v, table=final), k)

        if filters is not None:

            for index, filt in enumerate(filters):
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
                    where_val = filters[index]['value']

                where_op = filt['operator']
                _query = where_condition(where=where, query=_query, where_val=where_val, where_op=where_op)
        if sqlQuery is None:
            return _query.get_sql()
        else:
            return self.updateQueryUsingSubQuery(_query.get_sql(), inputTableReplica, sqlQuery)

    def updateQueryUsingSubQuery(self, updateQuery, inputTableReplica, subQuery):
        # split query by where clause.
        split_qury = updateQuery.split('WHERE')

        if len(split_qury) > 1:
            where_clause = split_qury[1]
        else:
            where_clause = ' 1=1 '

        newUpdateQuery = split_qury[0] + ' FROM (' + subQuery + ') as ' + inputTableReplica + ' WHERE ' + where_clause

        return newUpdateQuery

    def updateType(self, df, tableDetails, mappedColumn):
        pass

    # added tableDetails parameter to pass table columns data type
    def updateTable(self, df, targetTableName, columnnames={}, filters=[], joins={}, fromTable=None, sameSchema=False,
                    tableDetails={}, sqlQuery=None):
        pass

    def truncateTable(self, table_name):
        if not self.dataset_id:
            query = f'TRUNCATE TABLE {table_name}'
        else:
            query = "TRUNCATE TABLE " + self.dataset_id + "." + table_name
        self.executeSql(query)

    # TODO: generateCreateTableScript function need to be tested for Snowflake
    def generateCreateTableScript(self, tableDetails):
        query = "CREATE TABLE " + tableDetails["tableName"] + "("

        lenCol = len(tableDetails["colDetails"])
        index = 0
        for x in tableDetails["colDetails"]:
            index += 1
            query = query + " `" + x['columnName'] + '`'
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

            if 'default' in x:
                if len(x["default"]) > 0:
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
                        # CONSTRAINT `daas_assets_created_by_4ce65b17_fk_daas_user_id` FOREIGN KEY (`created_by`) REFERENCES `daas_user` (`id`),
                        fkQuery += " CONSTRAINT " + y['keyName'] + " FOREIGN KEY (`" + y[
                            'columnFK'] + "`) REFERENCES `" + y['table'] + "` (`" + y['column'] + '`)'
                        if (fkIndex < lenFK):
                            fkQuery += ","

                    query += fkQuery
                query += ")"

        return query

    def generateCreateTableScriptETL(self, tableDetails):
        tableName = tableDetails["tableName"]
        createColumnData = tableDetails['createColumnData']
        # createColumnData =[{'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'} ..]

        target_columns = [column["target_column"].replace(" ", "_") for column in tableDetails["createColumnData"]]
        df = pd.DataFrame(target_columns, columns=["target_column"])

        sep = '`'
        createQuery = "CREATE TABLE   `{dataset_id}.{tableName}`".format(dataset_id=self.dataset_id, tableName=tableName)

        if len(createColumnData) > 0:
            convertedColumnData = self.convert_dtype(createColumnData)

            cols_query = ",".join([f'{col} {datatype}' for col, datatype in
                                   zip(df["target_column"], [col["datatype"] for col in convertedColumnData])])
            query = f'''{createQuery} ( {cols_query} ) '''

        return query

    def createTable(self, tableDetails, etl=False):
        if etl == True:
            query = self.generateCreateTableScriptETL(tableDetails)
            return self.executeSql(query)
        else:
            query = self.generateCreateTableScript(tableDetails)
        self.executeSql(query)

        return True

    def getColumnLOV(self, full_table_name, col_name, order='ASC'):
        self.connect()

        if isinstance(full_table_name, dict):
            for t_name, alias_name in full_table_name.items():
                full_table_name = t_name

        full_table_name = '`' + self.dataset_id + '`.' + "`"+full_table_name+ "`"

        query = "SELECT DISTINCT `{col_name}` as values FROM {tbl_name} WHERE 1 = 1 ORDER BY `{col_name}` {order};".format(
            col_name=col_name,
            tbl_name=full_table_name,
            order=order

        )
        results = pd.read_sql(query, self.connection)
        self.close()

        return results['values'].tolist()

    def getColumnsProfile(self, table_name, with_min_max=False, filter=None):
        df_col_dtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = self.dataset_id + "." + "`"+table_name+ "`"

        index = 0
        for row in df_col_dtls:
            ## splitted DB Type as db type contains precison & length also ex varchar(255), numeric(17,3)
            x = row["DATA_TYPE"]
            if x.upper() in ['VARCHAR', 'TIMESTAMP', 'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 
                'NUMBER', 'DOUBLE PRECISION', 'SMALLINT', 'INTEGER', 'BIGINT', 
                'DECFLOAT', 'DECIMAL', 'REAL', 'INT'
            ]:
                sub_query = """ 
                    SELECT 
                        '{col_name}' AS COLUMN_NAME, 
                        '{data_type}' AS DATA_TYPE  , 
                """
                
                if with_min_max:
                    sub_query += """  
                                    TO_CHAR(max("{col_name}")) AS MAX_VAL, 
                                    TO_CHAR(min("{col_name}")) AS MIN_VAL, """
                sub_query += """ 
                                    COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
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
                                    COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """

            sub_query += """ FROM {table_name}  """

            if filter:
                sub_query += " WHERE " + filter

            sub_query += " GROUP BY 1 "

            sub_query = sub_query.format(
                col_name=row["COLUMN_NAME"], 
                data_type=row["DATA_TYPE"],
                table_name=full_table_name
            )
            
            df_sub = self.executeQuery(sub_query)

            if index == 0:
                df = df_sub.copy()
            else:
                df = pd.concat([df, df_sub])

            index += 1

        return df

    def getTableDetails(self, table_name=None, type={}):
        ### TABLE NAME CAN BE A LIST OR STRING

        sep = "','"
        if table_name:
            if isinstance(table_name, list):
                table_name = "'{}'".format(sep.join(table_name))

            else:
                table_name = "'{}'".format(table_name)


        query = """
            SELECT 
                table_id as TABLE_NAME,
                CASE WHEN type = 1 THEN ' BASE TABLE' 
                     WHEN type = 2 THEN 'VIEW' 
                     ELSE NULL END AS TABLE_TYPE ,
                c.n_columns as NO_OF_COLS,
                ROUND(size_bytes/POW(10,9),2) AS SIZE_IN_MB, 
                TIMESTAMP_MILLIS(creation_time) AS creation_time,
                TIMESTAMP_MILLIS(last_modified_time) AS last_modified_time, 
                row_count as NO_OF_ROWS,
        """

        if table_name:
            query += """
            FROM `{dataset_id}`.__TABLES__ s
            left join (
                        SELECT 
                        TABLE_NAME,
                        count(COLUMN_NAME) as n_columns 
                        FROM `{dataset_id}.INFORMATION_SCHEMA.COLUMNS` c
                        group by TABLE_NAME
                       ) c on c.TABLE_NAME = s.table_id
            where table_id in ({table_name}) ORDER BY SIZE_IN_MB DESC
            """
        else:
            query += """
            FROM `{dataset_id}`.__TABLES__ s
            left join (
                        SELECT 
                        TABLE_NAME,
                        count(COLUMN_NAME) as n_columns 
                        FROM `{dataset_id}.INFORMATION_SCHEMA.COLUMNS` c
                        group by TABLE_NAME
                       ) c on c.TABLE_NAME = s.table_id
            ORDER BY SIZE_IN_MB DESC
            """

        query = query.format(dataset_id=self.dataset_id,table_name=table_name)

        df = self.executeQuery(query, limit=None)

        return df

    def getTableRelationships(self, table_name, bi_directional=False):
        table_name = table_name.upper()
        
        query = """
            SELECT `table_name` as table_name,
            `column_name` as col_name,
            '' as ref_table_name,
            '' as ref_col_name  
            from `{dataset_id}.INFORMATION_SCHEMA.KEY_COLUMN_USAGE` 
            where table_name='{table_name}'
        """.format(dataset_id=self.dataset_id, table_name=table_name)

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
            source_table= f" `{self.dataset_id}.{src_table_name}` ",
            target_table= f" `{self.dataset_id}.{tgt_table_name}` ",
            on_condition=on_condition,
            matched_mapping=matched_mapping,
            non_matched_mapping=non_matched_mapping,
            on_match=on_match,
            on_not_match=on_not_match,
            filter_condition=filter_condition,
            target_encloser=target_encloser
        )

        merge_query = mrgstmt.get_query()

        return merge_query

    def getDropTableQuery(self, table_name):
        return f"DROP TABLE IF EXISTS {self.dataset_id}{table_name}".format(
            self.dataset_id, 
            table_name
        )

    def dropTable(self, table_name):
        query = self.getDropTableQuery(table_name)
        self.executeSql(query)

    def getTableColumnDtypes(self, table_name):
        list_of_dict = self.getTableColumnsDetails(table_name)
        
        col_dtype = {x['COLUMN_NAME']: (x['DATA_TYPE']).upper() for x in list_of_dict}
        col_dtype_len = {k: v[v.find("(") + 1:].rstrip(")") if "(" in v else None for k, v in col_dtype.items()}
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
                    trgt_col_datatype = target_col_dtype[trgt_mapped_col]
                    trgt_col_dtype_len = col_dtype_len[trgt_mapped_col]

                    if trgt_col_datatype in ('TEXT', 'STR', 'VARCHAR', 'LONG VARCHAR'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR(length=int(trgt_col_dtype_len))})
                    elif trgt_col_datatype in ('NVARCHAR'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.NVARCHAR(length=int(trgt_col_dtype_len))})
                    elif trgt_col_datatype == 'INT':
                        dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                    elif trgt_col_datatype in ('FLOAT', 'DEC', 'NUMERIC', 'NUMBER'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                    elif trgt_col_datatype in ('BOOLEAN', 'BOL'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                    elif trgt_col_datatype in ('TIMESTAMP', 'DATE', 'DAT', 'TMS'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})

            else:
                if "object" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                elif "int" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                elif "float" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                elif "bool" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                elif "date" in str(src_col_type):
                    dtypedict.update({src_col_name: sqlalchemyTypes.DATETIME})
        return dtypedict

    def getTableIndexDetails(self, tablename):
        pass

    def dq_dashboard_data_freshness_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select 
                DATE(%(col_name)s) date_col,count (1) row_added 
            from %(dataset_id)s.%(table_name)s
            where 
                DATE(%(col_name)s) between '%(from_date)s' and  '%(to_date)s'
            group by DATE(%(col_name)s) order by 1 asc
        ''' % ({
            "dataset_id": self.dataset_id, 
            "col_name": columnname, 
            "table_name": tablename, 
            "from_date": fromdate, 
            "to_date": todate
        })

        return query

    def dq_dashboard_data_modify_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select 
                DATE(%(col_name)s) date_col ,count (1) row_added 
            from %(dataset_id)s.%(table_name)s 
            where 
                DATE(%(col_name)s) between '%(from_date)s' and '%(to_date)s'
            group by %(col_name)s order by 1 asc
        ''' % ({
            "dataset_id": self.dataset_id,
            "col_name": columnname, 
            "table_name": tablename, 
            "from_date": fromdate, 
            "to_date": todate
        })

        return query

    def dq_dashboard_data_delete_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select DATE(%(col_name)s) date_col ,count (1) row_added 
            from %(dataset_id)s.%(table_name)s
            where %(col_name)s is not null and  DATE(%(col_name)s) between '%(from_date)s' and '%(to_date)s'
            group by DATE(%(col_name)s) order by 1 asc
        ''' % ({
            "dataset_id": self.dataset_id,
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
                IFNULL(%(datasources_col_name)s, 'Other') src, 
                count (1) row_added 
            from %(table_name)s.%(table_name)s
            where DATE(%(col_name)s) between '%(from_date)s' and  '%(to_date)s'
            group by DATE(%(col_name)s),2 order by 1 asc
        ''' % ({
            "dataset_id": self.dataset_id, 
            "col_name": columnname, 
            "table_name": tablename, 
            "from_date": fromdate, 
            "to_date": todate,
            "datasources_col_name": datasources_col_name
        })

        return query

    def get_connection_statement(self):
        ## handle case when dataset_id contains project_id with dot(.)
        dataset_id = self.dataset_id
        dataset_id = ''.join(dataset_id.split('.')[1:]) if '.' in dataset_id else dataset_id
        statement = f"bigquery://{self.cred['project_id']}/{dataset_id}"
        return statement

    def get_incremental_columns(self, table_name, **others):
        try:
            # added distinct for unique data
            query = """
                SELECT DISTINCT c.column_name as COLUMN_NAME,
                    c.data_type as DATA_TYPE
                FROM			
                    {dataset_id}.INFORMATION_SCHEMA.COLUMNS AS c
                LEFT JOIN
                    {dataset_id}.INFORMATION_SCHEMA.TABLES t
                        ON c.table_name = t.table_name
                        AND c.table_schema = t.table_schema 
                WHERE 
                    (upper(c.data_type) like ('TIME%') 
                    or upper(c.data_type)  like 'DATE%')
                    AND c.table_name = '{table_name}'
            """.format(dataset_id=self.dataset_id, table_name=table_name)

            self.connect()
            self.cursor.execute(query)
            desc_value = [d[0] for d in self.cursor.description]
            desc = [item.upper() for item in desc_value]
            results = pd.DataFrame([dict(zip(desc, res)) for res in self.cursor.fetchall()])

            self.close()
        except Exception:
            self.close()
            raise

        return results

    def fetch_delta_columns(self, table_name, **others):
        try:
            df = None
            inc_columns = self.get_incremental_columns(table_name)
            full_table_name = table_name

            if self.dataset_id is not None:
                full_table_name = self.dataset_id + "." + full_table_name

            index = 0

            sub_query = """ 
                SELECT '{col_name}' AS COLUMN_NAME,
                    '{DATA_TYPE}' as DATA_TYPE,
                    COUNT(DISTINCT `{col_name}`) AS UNQ_VAL, 
                    COUNT(1) AS TOTAL_COUNT, 
                    COALESCE(SUM(CASE WHEN(`{col_name}` IS NULL) THEN 1 ELSE 0 END),0) AS NULL_CNT 
                FROM `{table_name}`
            """

            for index, row in inc_columns.iterrows():
                sub_query = sub_query.format(
                    col_name=row["COLUMN_NAME"],
                    table_name=full_table_name,
                    DATA_TYPE=row['DATA_TYPE']
                )
                
                df_sub = self.executeQuery(sub_query)
                df = df_sub.copy() if index == 0 else pd.concat([df, df_sub])
                index += 1

            if df is not None:
                dataframe_date = df.loc[(df['DATA_TYPE'].str.upper().str.contains('TIME*|DATE*'))]

                if not dataframe_date.empty:
                    dataframe_date = dataframe_date[dataframe_date['UNQ_VAL'] == dataframe_date['UNQ_VAL'].max()]
                
                dataframe_integer = df.loc[(df['DATA_TYPE'].str.upper().str.contains('INT*'))]
                if not dataframe_integer.empty:
                    dataframe_integer = dataframe_integer.loc[dataframe_integer['UNQ_VAL'] == dataframe_integer['TOTAL_COUNT']]
                    
                df = pd.concat([dataframe_integer, dataframe_date], axis=0)
                df = df[['COLUMN_NAME', 'DATA_TYPE']]
            else:
                df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])
        except Exception:
            self.close()
            raise

        return df


    def convert_dtype(self, column_list):
        dst_big_query = {}
        dst_big_query["VARCHAR"] = "STRING"
        dst_big_query["NUMERIC"] = "NUMERIC"
        dst_big_query["BOOLEAN"] = "BOOL"
        dst_big_query["BYTE"] = "BYTES"
        dst_big_query["DATE"] = "DATE"
        dst_big_query["DATETIME"] = "DATETIME"
        dst_big_query["FLOAT"] = "FLOAT64"
        dst_big_query["VARBINARY"] = "GEOGRAPHY"
        dst_big_query["INT"] = "INT64"
        dst_big_query["TIME"] = "STRING"
        dst_big_query["TIMESTAMP"] = "TIMESTAMP"
        dst_big_query["DECIMAL"] = "NUMERIC"
        dst_big_query["CHAR"] = "STRING"
        dst_big_query["TEXT"] = "STRING"
        dst_big_query["NVARCHAR"] = "STRING"
        dst_big_query["DATETIMEOFFSET"] = "TIMESTAMP"
        dst_big_query["SMALLMONEY"] = "INT"
        dst_big_query["MONEY"] = "INT"
        dst_big_query["XML"] = "STRING"
        dst_big_query["UNIQUEIDENTIFIER"] = "STRING"
        dst_big_query["REAL"] = "FLOAT64"

        # Convert the datatypes
        converted_data = []
        for item in column_list:
            source_column = item['source_column']
            target_column = item['target_column']
            datatype = item['datatype']

            # Check if the datatype is VARCHAR
            if datatype.startswith('VARCHAR') or datatype.startswith('NVARCHAR') or datatype.startswith('CHAR'):
                varchar_length = datatype.split('(')[1].split(')')[0]  # Extract the length dynamically
                bq_datatype = dst_big_query['VARCHAR']
                bq_datatype_with_length = f"{bq_datatype}({varchar_length})"
            else:
                bq_datatype = dst_big_query.get(datatype, 'STRING')
                bq_datatype_with_length = bq_datatype

            # Create a new dictionary with converted datatype
            converted_item = {
                'source_column': source_column,
                'target_column': target_column,
                'datatype': bq_datatype_with_length
            }

            converted_data.append(converted_item)
        
        return converted_data
    

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

        if not self.dataset_id:
            select_clause = "select count(1) as CNT from " + tbl_name
        else:
            select_clause = "select count(1) as CNT from " + self.dataset_id + "." + tbl_name        

        for con in on_condition:
            where_clause += condition.format(col_name = con["target_col"], value = row[con["source_col"]])

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

        if not self.dataset_id:
            upd_clause = "update " + tbl_name
        else:
            upd_clause = "update " + self.dataset_id + "." + tbl_name        

        for con in on_condition:
            where_clause += condition.format(col_name = con["target_col"], value = row[con["source_col"]])

        for key in matched_mapping.keys():
            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += merge_stmt_dict["BIGQUERY"]["set"]["NULL"].format(col_name = key, value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += merge_stmt_dict["BIGQUERY"]["set"][col_type].format(
                        col_name = key, 
                        value = row[matched_mapping[key]].replace("'", "''")
                    )                            
                else :
                    set_clause += merge_stmt_dict["BIGQUERY"]["set"][col_type].format(
                        col_name = key, 
                        value = row[matched_mapping[key]]
                    )                        

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

        if not self.dataset_id:
            inst_clause = f"INSERT INTO {tbl_name} "
        else:
            inst_clause = f"INSERT INTO {self.dataset_id}.{tbl_name}"

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
                    values += merge_stmt_dict["BIGQUERY"]["insert"][col_type].format(
                        value = row[non_matched_mapping[key]].replace("'", "''")
                    ) + ","
                else:
                    values += merge_stmt_dict["BIGQUERY"]["insert"][col_type].format(
                        value = row[non_matched_mapping[key]]
                    ) + ","
            else :
                values += merge_stmt_dict["BIGQUERY"]["insert"]["NULL"].format(value = 'null') + ","            

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection=manage_connection)
