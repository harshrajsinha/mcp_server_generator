# PYTHON PACKAGES
import pandas as pd
import uuid
import math as math
import json
from collections import OrderedDict
from sqlalchemy import create_engine
from sqlalchemy import types as sqlalchemyTypes
from pypika import Order
from pypika import Table, Field, JoinType
from pypika import Tables
from pypika import VerticaQuery
from pypika import functions as fn
from hdbcli import dbapi
from urllib.parse import quote


# CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression
from scikiq_dbutils.handlers.DBConnection import (
    clsDBConnection, ViewCreationError, where_Colcondition, where_recursive_condition_col_dict, 
    where_recursive_condition, where_condition, getReqSrcCols, MergeStatement
)
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict

TBL_NME_FRMT = '"{}"."{}/{}"'

class DMLException(Exception):
    pass

class ConnectionException(Exception):
    pass

class DDLException(Exception):
    pass

class clsSapHana(clsDBConnection):
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
        self.is_bw4hana = False
        self.catalog_name = None

        if "is_bw4hana" in config and config["is_bw4hana"] == "on" :
            self.is_bw4hana = True

        if "catalog_name" in config :
            self.catalog_name = config["catalog_name"]

        if ("resource_key" in config):
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None

        if "schema" in config and config["schema"]:
            self.schema = config["schema"]
        else:
            self.schema = 'public'

        if "connection_type" in config:
            self.connection_type = config["connection_type"]
        else:
            self.connection_type = None

        self.db_type="SAPHANA"

    def getConnectionType(self):
        if self.connection_type is None:
            return "SR"
        else:
            return self.connection_type
        
    def update_column_comment(self, tbl_name, col_name, comment, **others):
        return False        

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'

            self.connection = dbapi.connect(
                # Option 1, retrieve the connection parameters from the hdbuserstore
                # key='USER1UserKey', # address, port, user and password are retrieved from the hdbuserstore

                # Option2, specify the connection parameters
                address=self.host,
                port=self.port,
                user=self.user,
                password=self.password

                # Additional parameters
                # encrypt=True, # must be set to True when connecting to HANA as a Service
                # As of SAP HANA Client 2.6, connections on port 443 enable encryption by default (HANA Cloud)
                # sslValidateCertificate=False #Must be set to false when connecting
                # to an SAP HANA, express edition instance that uses a self-signed certificate.
            )

            self.cursor = self.connection.cursor()

            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsSapHana, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsSapHana, self).callConnectionAudit(resp)
            raise ConnectionException(e)

    def close(self):
        if self.cursor:
            self.cursor.close()

        if self.connection:
            self.connection.close()

    def testConnection(self):
        resp = {}
        try:
            db = dbapi.connect(
                address=self.host,
                port=self.port,
                user=self.user,
                password=self.password
                # timeout of the data base and 108000 means 3 hours
            )

            db.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS
            # except dbapi.errors.Error as exc:
        except dbapi.Error as exc:
            error = exc.args
            resp['error'] = 1
            if '3781' in error:
                resp['msg'] = ScikiqMessages.MSG_INCORRECT_DB_CREDENTIALS
            elif '2983' in error:
                resp['msg'] = "Please check the name of Database"
            else:
                error_value = error[1]
                resp['msg'] = "Database Error |" + error_value[6] + "|" + error_value[1]

        # callConnectionAudit using for audit the record.
        super(clsSapHana, self).callConnectionAudit(resp)

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
        except Exception as e :
            raise DMLException(e)

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
                self.close()
        except Exception as e:
            if manage_connection:
                self.close()
            
            raise DDLException(e)

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

        res = {}
        res["status"] = b_success
        res["result"] = x
        res["msg"] = msg
        return res

    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=10000, dtype={}):

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
                else:
                    ##
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
        else:
            dtypedict = dtype

        self.create_engine()
        with self.engine_statement.connect() as connection:
            if self.schema :
                connection.execute("SET SCHEMA " + self.schema)        
            
            if chunksize is None:
                df.to_sql(con=connection, name=tablename, dtype=dtypedict, if_exists=if_exists,chunksize = chunksize, index=False)
            else:
                cnt = df.shape[0]
                batch_size = 1000
                if isinstance(chunksize,int):
                    batch_size = chunksize
                
                bt_cnt = int(math.ceil(cnt/batch_size))

                start = 0
                end = 0
                idx = 1
                if cnt > batch_size :
                    for i in range(bt_cnt) :
                        if idx == bt_cnt:
                            end = cnt
                        else:
                            end = (idx * batch_size)

                        df2 = df.iloc[start:end, :].copy()
                        df2.to_sql(con=connection, name=tablename, dtype=dtypedict, if_exists=if_exists,chunksize = chunksize, index=False)
                        start = end
                        idx += 1
                else :
                    df.to_sql(con=connection, name=tablename, dtype=dtypedict, if_exists=if_exists,chunksize = chunksize, index=False)
       
        return df


    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()

        if self.is_bw4hana :
            ''' SELECT * FROM "_SYS_BI"."BIMC_CUBES" WHERE CATALOG_NAME  = 'system-local.bw.bw2hana' AND CUBE_NAME = 'ZRT_ADSO' '''
            
            query = 'SELECT CUBE_NAME FROM  "_SYS_BI"."BIMC_CUBES" where 1=1 '

            if search:
                query += " AND CUBE_NAME LIKE '%{}%'".format(search)

            if self.schema:
                query += " AND SCHEMA_NAME = '{}'".format(self.schema)

            if self.catalog_name:
                query += " AND CATALOG_NAME = '{}'".format(self.catalog_name)                

            query += " ORDER BY CUBE_NAME ASC;"           
        else :
            query = "SELECT TABLE_NAME AS TABLE_NAME,'TABLE' AS TABLE_TYPE, SCHEMA_NAME AS TABLE_SCHEMA FROM TABLES WHERE 1=1"

            if search:
                query += " AND TABLE_NAME LIKE '%{}%'".format(search)

            if self.schema:
                query += " AND SCHEMA_NAME = '{}'".format(self.schema)
           
            if include_view == True:
                query += " UNION SELECT VIEW_NAME AS TABLE_NAME, 'VIEW' AS TABLE_TYPE FROM VIEWS WHERE 1=1"

                if search:
                    query += " AND VIEW_NAME LIKE '%{}%'".format(search)

                if self.schema:
                    query += " AND SCHEMA_NAME = '{}'".format(self.schema)

            query += " ORDER BY TABLE_NAME ASC;"


        self.cursor.execute(query)

        results = self.cursor.fetchall()
        res = tuple(tuple(x) for x in results)
        
        self.close()

        return res

    def getAllTablesWithColumns(self, search):
        
        tbls = self.get_all_tables(search)
        tbl_data = []

        self.connect()        

        for tbl in tbls:
            tbl_dtls = {}
            tbl = list(tbl)[0]
            tbl_dtls["tablename"] = tbl

            if self.is_bw4hana :
                qry =  """ SELECT 
                            COLUMN_NAME, COLUMN_SQL_TYPE as  DATA_TYPE 
                        FROM "_SYS_BI".BIMC_PROPERTIES bp 
                        WHERE CUBE_NAME = '{}' 
                        AND SCHEMA_NAME = '{}'
                        AND COLUMN_TYPE_D IS NOT null
                    """.format(tbl, self.schema)

                if self.catalog_name:
                    qry += " AND CATALOG_NAME = '{}'".format(self.catalog_name)                


                self.cursor.execute(qry)
            else :
                self.cursor.execute(
                    """ SELECT 
                            COLUMN_NAME, 
                            DATA_TYPE_NAME as  DATA_TYPE 
                        FROM TABLE_COLUMNS 
                        WHERE TABLE_NAME = '{}' 
                        ORDER BY COLUMN_NAME
                    """.format(tbl)
                )

            result = tuple(tuple(x) for x in self.cursor.fetchall())
            tbl_dtls["columnname"] = result

            tbl_data.append(tbl_dtls)

        self.close()

        return tbl_data

    def getTableColumns(self, tablename, type = ''):

        if self.is_bw4hana :
            query = """ 
                SELECT 
                    COLUMN_NAME, 
                    COLUMN_SQL_TYPE as DATA_TYPE 
                FROM "_SYS_BI".BIMC_PROPERTIES 
                WHERE COLUMN_TYPE_D IS NOT null 
                AND CUBE_NAME = '{}'""".format(tablename)

            if self.catalog_name:
                query += " AND CATALOG_NAME = '{}'".format(self.catalog_name)                            
        else :
            query = """ SELECT 
                            COLUMN_NAME, 
                            DATA_TYPE_NAME as DATA_TYPE 
                        FROM TABLE_COLUMNS 
                        WHERE TABLE_NAME = '{}'""".format(tablename)
        

        if self.schema:
            query += " AND SCHEMA_NAME = '{}'".format(self.schema)

        query += " ORDER BY COLUMN_NAME "

        self.connect()
        self.cursor.execute(query)

        results = self.cursor.fetchall()
        results = tuple(tuple(x) for x in results)

        self.close()
        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        self.connect()

        if self.is_bw4hana :
            query = """
                SELECT tc.SCHEMA_NAME AS "TABLE_SCHEMA",
                    tc.CUBE_NAME AS "TABLE_NAME",
                    tc.COLUMN_NAME AS "COLUMN_NAME",
                    tc.COLUMN_SQL_TYPE AS "DATA_TYPE",
                    CAST(tc."ORDER" AS INT) AS "ORDINAL_POSITION",
                    tc."NUMERIC_PRECISION" AS "NUMERIC_PRECISION",
                    tc."NUMERIC_SCALE" AS "NUMERIC_SCALE",
                    tc.IS_NULLABLE AS "IS_NULLABLE",
                    CASE WHEN COLUMN_TYPE_D = 'STRING' THEN replace_regexpr('\D' in COLUMN_SQL_TYPE with '') ELSE 0 END as "CHARACTER_MAXIMUM_LENGTH",
                    CASE WHEN COLUMN_TYPE_D = 'STRING' THEN replace_regexpr('\D' in COLUMN_SQL_TYPE with '') ELSE 0 END as "DATA_TYPE_LENGTH",
                    CASE WHEN COLUMN_TYPE_D = 'STRING' THEN replace_regexpr('\D' in COLUMN_SQL_TYPE with '') ELSE 0 END as  "CHARACTER_MAX_LENGTH",
                    CASE WHEN tc.PROPERTY_CAPTION IS NULL THEN '' ELSE tc.PROPERTY_CAPTION END AS "COMMENT",
                    '' AS "COLUMN_DEFAULT",
                    0 AS "IS_PRIMARYKEY",
                    0 AS "IS_UNIQUEKEY",
                    0 "IS_NONUNIQUEKEY",
                    0 "AUTO_INCREMENT",
                    CASE WHEN COLUMN_TYPE_D = 'STRING' THEN replace_regexpr('\D' in COLUMN_SQL_TYPE with '') ELSE 0 END AS "COLUMN_LENGTH",
                    CASE WHEN tc."SCALE" > 0 THEN tc."SCALE" ELSE 0 END AS "COLUMN_PRECISION",
                    '' AS "COLUMN_CHARACTERSET",
                    '' AS "CONSTRAINT_NAME",
                    '' AS "REFERENCED_TABLENAME",
                    '' AS "REFERENCED_COLUMNNAME",
                    'no' AS "KEY_COL"
                FROM "_SYS_BI".BIMC_PROPERTIES tc 
                WHERE CUBE_NAME = '{}' 
                AND COLUMN_TYPE_D IS NOT NULL
                 
            """.format(tbl_name)            
        else :
            query = """SELECT tc.SCHEMA_NAME AS "TABLE_SCHEMA",
                tc.TABLE_NAME AS "TABLE_NAME",
                tc.COLUMN_NAME AS "COLUMN_NAME",
                tc.DATA_TYPE_NAME AS "DATA_TYPE",
                tc.POSITION AS "ORDINAL_POSITION",
                tc.LENGTH AS "NUMERIC_PRECISION",
                tc.SCALE AS "NUMERIC_SCALE",
                tc.IS_NULLABLE AS "IS_NULLABLE",
                tc.LENGTH as "CHARACTER_MAXIMUM_LENGTH",
                tc.LENGTH as "DATA_TYPE_LENGTH",
                tc.LENGTH as  "CHARACTER_MAX_LENGTH",
                CASE WHEN tc.COMMENTS IS NULL THEN '' ELSE tc.COMMENTS END AS "COMMENT",
                CASE WHEN tc.DEFAULT_VALUE IS NULL THEN '' ELSE tc.DEFAULT_VALUE END AS "COLUMN_DEFAULT",
                CASE WHEN upper(c.IS_PRIMARY_KEY) = 'TRUE' THEN 1 ELSE 0 END AS "IS_PRIMARYKEY",
                CASE WHEN upper(c.IS_UNIQUE_KEY) = 'TRUE' THEN 1 ELSE 0 END AS "IS_UNIQUEKEY",
                CASE WHEN ic."CONSTRAINT" = 'NOT NULL UNIQUE' THEN 1 ELSE 0 END AS "IS_NONUNIQUEKEY",
                CASE WHEN upper(tc.GENERATION_TYPE) LIKE '%IDENTITY%' THEN 1 ELSE 0 END AS "AUTO_INCREMENT",
                tc."LENGTH" AS "COLUMN_LENGTH",
                CASE WHEN tc."SCALE" > 0 THEN tc."SCALE" ELSE 0 END AS "COLUMN_PRECISION",
                CASE WHEN tc."COLLATION" IS NULL THEN '' ELSE tc."COLLATION" END AS "COLUMN_CHARACTERSET",
                CASE WHEN c.CONSTRAINT_NAME IS NULL THEN '' ELSE c.CONSTRAINT_NAME END AS "CONSTRAINT_NAME",
                CASE WHEN rc.REFERENCED_TABLE_NAME IS NULL THEN '' ELSE rc.REFERENCED_TABLE_NAME END AS "REFERENCED_TABLENAME",
                CASE WHEN rc.REFERENCED_COLUMN_NAME IS NULL THEN '' ELSE rc.REFERENCED_COLUMN_NAME END AS "REFERENCED_COLUMNNAME",
                CASE WHEN c.CONSTRAINT_NAME IS NOT NULL THEN 'yes' ELSE 'no' END AS "KEY_COL"
                FROM sys.COLUMNS tc
                LEFT JOIN SYS."CONSTRAINTS" c ON tc.SCHEMA_NAME = c.SCHEMA_NAME AND tc.TABLE_NAME = c.TABLE_NAME AND tc.COLUMN_NAME = c.COLUMN_NAME 
                LEFT JOIN SYS.REFERENTIAL_CONSTRAINTS rc ON tc.SCHEMA_NAME = rc.SCHEMA_NAME AND tc.TABLE_NAME = rc.TABLE_NAME AND tc.COLUMN_NAME = rc.COLUMN_NAME 
                LEFT JOIN SYS.INDEX_COLUMNS ic ON ic.SCHEMA_NAME = tc.SCHEMA_NAME AND tc.COLUMN_NAME = ic.COLUMN_NAME AND tc.TABLE_NAME = ic.TABLE_NAME 
                WHERE tc.TABLE_NAME = '{}'""".format(tbl_name)

        if self.schema:
            query += " AND tc.SCHEMA_NAME = '{}'".format(self.schema)
        
        if self.is_bw4hana and self.catalog_name :
            query += " AND tc.CATALOG_NAME = '{}'".format(self.catalog_name)

        if sort_on_position:
            if self.is_bw4hana : 
                query += ' ORDER BY CAST(tc."ORDER" AS INT)'
            else :
                query += " ORDER BY tc.POSITION "
        else:
            query += " ORDER BY COLUMN_NAME "

        self.cursor.execute(query)
        
        desc_value = [d[0] for d in self.cursor.description]
        desc = [item.upper() for item in desc_value]
        results = [dict(zip(desc, res)) for res in self.cursor.fetchall()]
        
        self.close()
        
        return results

    def getRenamesColMetricsDict(self, config_details=OrderedDict()):
        dim_metrics = OrderedDict()
        dim_metrics_cols = []
        
        col_indx = {}

        if config_details:
            # Get column key and alias name with list of vlaues
            for key, col_details in config_details.items():
                for lst in col_details:
                    dim_metrics[key] = lst['alias']
                    dim_metrics_cols.append(key)
            # Get column occurences of the data.
            for key, _ in dim_metrics.items():
                indices = [index for index, element in enumerate(dim_metrics_cols) if element == key]
                col_indx[key] = indices

        return col_indx

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
                tbl_name = key
                alias = tablename[tbl_name]
                
                if not self.schema:
                    tbls[alias] = Table(tbl_name, alias=alias)
                else:
                    if self.is_bw4hana and self.catalog_name :
                        tbls[alias] = Table('{}/{}'.format(self.catalog_name, tbl_name), alias=alias, schema=self.schema)
                    else :
                        tbls[alias] = Table(tbl_name, alias=alias, schema=self.schema)

                tbl_names[alias] = tbl_name

        index = 0
        for key in tbls.keys():
            if index == 0:
                _query = VerticaQuery.from_(tbls[key])
            else:
                if tbl_names[key] in joins:
                    join_type = joins[tbl_names[key]]

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
                             list(joinCondition[index - 1]["right"].values())[0]
                        )
                    )

            index = index + 1

        if columnnames is not None:
            agg_func = {
                "SUM": fn.Sum,
                "AVG": fn.Avg,
                "MIN": fn.Min,
                "MAX": fn.Max,
                "COUNT": fn.Count
            }
            
            fld_lst = []
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
                            fld_lst.append(agg_func[value](eval('tbls[col_tbl_name]' + "." + col_name)))
                        else:
                            if " as " in col_name:
                                fld_lst.append(Field(
                                    col_name.split(" as ")[0], 
                                    table=tbls[col_tbl_name],
                                    alias=col_name.split(" as ")[1]
                                ))
                            else:
                                fld_lst.append(Field(
                                    col_name, 
                                    table=tbls[col_tbl_name]
                                ))
                    else:
                        if str(lst_item['agg']).upper() == 'DISTINCT COUNT':
                            fld_lst.append(fn.Count(Field(key), alias=lst_item['alias']).distinct())
                        elif lst_item['agg'] != '':
                            fld_lst.append(
                                agg_func[str(lst_item['agg']).upper()](Field(key), alias=lst_item['alias'])
                            )
                        else:
                            fld_lst.append(Field(key).as_(lst_item['alias']))

                    # Add custom column in the list.
                    if 'column_type' in lst_item.keys():
                        if lst_item['column_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = lst_item['expression']
                    elif 'col_type' in lst_item.keys():
                        if lst_item['col_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = lst_item['expression']

        if distinct:
            _query = _query.select(*fld_lst).distinct()
        else:
            _query = _query.select(*fld_lst)

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
                        col_idx = self.getRenamesColMetricsDict(columnnames)
                        if key in __column_names_list:
                            if key in col_idx:
                                for _index in col_idx[key]:
                                    _query = _query.orderby(_index + 1, order=order_asc)

            elif isinstance(orderby,list):
                for dct in orderby:
                    for col,asc_desc in dct.items():
                        order_asc = Order.asc if asc_desc == 'ASC' else Order.desc
                        _query  = _query.orderby(col,order=order_asc)


        whre_cond_col_dict = {}
        if filters is not None and "rules" in filters:
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
                dbType="VERTICA",
                col_date_format_dict=col_date_format_dict,
                col_date_format_list=col_date_format_list,
                colDict=columnnames
            )

        if groupby is not None:
            for key, value in groupby.items():
                _query = _query.groupby(key)

        query = _query.get_sql()

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

        query = self.formatQuery(tablename, groupby, query, filters, columnnames, schema=self.schema)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)

        return query

    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                
                fmt_str = GetDBDateFormat.get_dbdate_format(db_type="SAPHANA", format_string=action_type)
                
                column_expression = generateCustomColumnExpression(action_type, fmt_str, _dict,db_type="SAPHANA")
                
                if (not column_expression):
                    column_expression = _dict['expression_value']
                
                query = query.replace(_key, column_expression, 1)
                
                expression_column_names_lst.append(column_expression)

        return (query, expression_column_names_lst)

    def formatFilter(self, alias, condition="AND", rules=None, query=None):
        for rule in rules:
            if "rules" in rule:
                query = self.formatFilter(alias, rule["condition"], rule["rules"], query)
            else:
                if (rule["type"].upper() == "DATE" and "format" in rule):
                    fmt_str = GetDBDateFormat.get_dbdate_format(db_type="SAPHANA", format_string=rule['format'])
                    tmp_qry = fmt_str
                    tmp_qry = tmp_qry.replace('columnName', '"' + alias + '"' + '.' + '"' + rule['field'] + '"')
                    query = query.replace('"' + rule['field'] + '"', tmp_qry, 1)
                elif (rule["type"].upper() == "DATE"):
                    fmt_str = GetDBDateFormat.get_dbdate_format(db_type="SAPHANA", format_string="yy-mm-dd")
                    tmp_qry = fmt_str
                    tmp_qry = tmp_qry.replace('columnName', '"' + alias + '"' + '.' + '"' + rule['field'] + '"')
                    query = query.replace('"' + rule['field'] + '"', tmp_qry, 1)
        
        return query

    def formatQuery(self, tablename, groupby=None, query=None, filters=None, columnnames=None, schema=None):
        ## if no filters or group by then no need to format query
        # if filters is None and groupby is None:
        if not (filters or groupby) or (len(filters) == 0 and len(groupby.keys()) == 0)  :
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
                    grp_clause = query.split('GROUP BY')[1]
                elif len(groupby) > 0:
                    grp_clause = query.split('GROUP BY')[1]

        for key, value in columnnames.items():
            for item in value:
                if "type" in item:
                    if item['type'] == 'date' and item['format'] != '':
                        fmt_str = GetDBDateFormat.get_dbdate_format(db_type="SAPHANA", format_string=item['format'])
                        
                        tmp_qry = fmt_str
                        tmp_qry = tmp_qry.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        tmp_qry = tmp_qry.replace('alias', '"' + item['alias'] + '"')
                        tmp_qry = tmp_qry.replace('colFormat', fmt_str)
                        
                        select_clause = select_clause.replace('"' + key + '"', tmp_qry, 1)

        if filters is not None and "rules" in filters:
            where_clause = self.formatFilter(alias, filters["condition"], filters["rules"], where_clause)

        if groupby and len(groupby) != 0:
            for key, value in groupby.items():
                if "type" in value:
                    if (value['type'].upper() == 'DATE' and value['format'] != ''):
                        fmt_str = GetDBDateFormat.get_dbdate_format(db_type="SAPHANA", format_string=value['format'])
                        
                        tmp_qry = fmt_str
                        tmp_qry = tmp_qry.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        tmp_qry = tmp_qry.replace('alias', '"' + key + '"')
                        tmp_qry = tmp_qry.replace('colFormat', fmt_str)

                        grp_clause = grp_clause.replace('"' + alias + '"' + '.' + '"' + key + '"', tmp_qry, 1)

        if self.is_bw4hana and self.catalog_name :
            table = TBL_NME_FRMT.format(self.schema, self.catalog_name, table)

            ## schema not used in this function as schema already added while creating connection
            if len(filters) > 0:
                select_clause += ' FROM {table_name} "{alias}" WHERE {where_clause}'.format(
                    table_name=table, 
                    alias=alias,
                    where_clause=where_clause
                )
            else:
                select_clause += ' FROM {table_name} "{alias}" '.format(table_name=table, alias=alias)
        else :
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
            select_clause += ' GROUP BY {}'.format(grp_clause)

        return select_clause

    def create_engine(self):
        # it requires pip install sqlalchemy-vertica
        self.engine_statement = create_engine(f'hana://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}')

    def get_connection_statement(self):
        statement = f"hana://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}"
        return statement

    def readTable(self, tbl_name, limit, **others):
        random_sample = others.get("random_sample", False)   

        manage_connection = others.get("manage_connection", True)
        if self.schema:
            if self.is_bw4hana and self.catalog_name :
                tbl_name = TBL_NME_FRMT.format(self.schema, self.catalog_name, tbl_name)
            else :
                tbl_name = f'"{self.schema}"."{tbl_name}"'

        query = "SELECT * FROM " + tbl_name
        
        if random_sample:
            query += " ORDER BY RAND() "

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection=manage_connection)
        res["df_text"] = None 

        return res               

    def getUpdateQuery(self, 
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

        _query = VerticaQuery.update(final)
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
                except Exception:
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

        upd_qry = split_qury[0] + ' FROM (' + subQuery + ') as ' + inputTableReplica + ' WHERE ' + where_clause

        return upd_qry

    def updateType(self, df, tableDetails, mappedColumn):
        dtypedict = {}  # create and empty dictionary
        for src_col_name, src_col_type in zip(df.columns, df.dtypes):
            if src_col_name in mappedColumn:
                tgt_mapped_col = mappedColumn[src_col_name]
                # getting target column name mapped with source
                if tgt_mapped_col != '' or tgt_mapped_col is not None:
                    tgt_col_dtls = next(filter(lambda x: (x[0] == tgt_mapped_col), tableDetails['columnName']))
                    if tgt_col_dtls:
                        # split column datatype value in case of varchar to remove detail part of length
                        tgt_col_dtype = tgt_col_dtls[1].split('(')[0]
                        
                        if len(tgt_col_dtls) > 2:
                            tgt_col_dtype_len = tgt_col_dtls[3]
                        else:
                            tgt_col_dtype_len = 8000

                        tgt_col_dtype = tgt_col_dtype.upper()
                        if tgt_col_dtype in ('TEXT', 'STR', 'VARCHAR', 'LONG VARCHAR'):
                            dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR(length=int(tgt_col_dtype_len))})
                        elif tgt_col_dtype in ('NVARCHAR'):
                            dtypedict.update({src_col_name: sqlalchemyTypes.NVARCHAR(length=int(tgt_col_dtype_len))})
                        elif tgt_col_dtype == 'INT':
                            dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                        elif tgt_col_dtype in ('FLOAT', 'DEC'):
                            dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                        elif tgt_col_dtype in ('BOOLEAN', 'BOL'):
                            dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                        elif tgt_col_dtype in ('TIMESTAMP', 'DATE', 'DAT', 'TMS'):
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

    # added tableDetails parameter to pass table columns data type
    def updateTable(self, df, targetTableName, 
            columnnames={}, filters=[], joins={}, 
            fromTable=None, sameSchema=False,
            tableDetails={}, sqlQuery=None
        ):
        
        
        ##found_rows=False https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1

        src_used_cols = getReqSrcCols(columnnames, filters, joins)

        ## selected only those columns where are either in join or columns
        df = df[src_used_cols]

        inputTableReplica = f'temp_table' + str(uuid.uuid1()) if fromTable is None else fromTable
        inputTableReplica = inputTableReplica.replace('-', '_')
        print('Temp table used for update', inputTableReplica)
        sql = self.getUpdateQuery(targetTableName, columnnames, filters, joins, inputTableReplica, sqlQuery=sqlQuery)
        self.create_engine()

        if sameSchema:
            with self.engine_statement.begin() as conn:  # TRANSACTION
                t = conn.execute(sql)
                return df, sql
        elif inputTableReplica not in sql:
            with self.engine_statement.begin() as conn:  # TRANSACTION
                t = conn.execute(sql)
                return df, sql
        else:
            try:
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

                with self.engine_statement.connect() as connection:
                    if self.schema:
                        connection.execute("SET SCHEMA " + self.schema)

                    data_types = self.updateType(df, tableDetails, columnnames)

                    df.to_sql(inputTableReplica, connection, if_exists='replace', dtype=data_types, index=False)

                # this code will change the sql to support vertica update for two table
                sql_buffer = sql.split('WHERE')
                where_clause = ' WHERE ' + sql_buffer[1]
                from_clause = ' FROM ' + inputTableReplica
                set_clause = sql_buffer[0].split('SET')
                update_clause = set_clause[0]
                set_clause = set_clause[1]
                
                col_map = ' SET '

                for column in set_clause.split(','):
                    set_clause = column.split('=')
                    if col_map == ' SET ':
                        # when set close varibale have where clouse then appending taht where clouse also
                        col_map = col_map + set_clause[0] + '=' + inputTableReplica + '.' + set_clause[1]
                    else:
                        col_map = col_map + ',' + set_clause[0] + '=' + inputTableReplica + '.' + set_clause[1]

                sql = update_clause + col_map + from_clause + where_clause
                # end here the vertica update section
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    if self.schema:
                        conn.execute("SET SCHEMA " + self.schema)

                    conn.execute(sql)

                    conn.execute("DROP TABLE IF EXISTS " + inputTableReplica)
                return df, sql
            except Exception as e:
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    if self.schema:
                        conn.execute("SET SCHEMA " + self.schema)

                    sql = f'DROP TABLE IF EXISTS "' + inputTableReplica + '"'
                    conn.execute(sql)
                
                raise DMLException(e)

    def truncateTable(self, table_name):
        if not self.schema:
            query = f'TRUNCATE TABLE {table_name}'
        else:
            query = "TRUNCATE TABLE " + self.schema + "." + table_name
        self.executeSql(query)


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
                        # CONSTRAINT `daas_assets_created_by_4ce65b17_fk_daas_user_id` FOREIGN KEY (`created_by`) REFERENCES `daas_user` (`id`),
                        fkQuery += " CONSTRAINT " + y['keyName'] + " FOREIGN KEY (`" + y[
                            'columnFK'] + "`) REFERENCES `" + y['table'] + "` (`" + y['column'] + '`)'
                        if (fkIndex < lenFK):
                            fkQuery += ","

                    query += fkQuery
                query += ")"

        return query

    def generateCreateTableScriptETL(self, tableDetails):
        tbl_name = tableDetails["tableName"]
        createColumnData = tableDetails['createColumnData']
        
        '''
        Example : 
            createColumnData =[{'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'} ..]
        '''


        sep = '"'
        sep_e = '"'
        createQuery = f'CREATE TABLE   {tbl_name}  '

        lst_cols = []
        if len(createColumnData)>0:
            for inpDict in createColumnData:
                col = inpDict['target_column']
                datatype = inpDict['datatype']
                col_query = f' {sep}{col}{sep_e} {datatype}'
                lst_cols.append(col_query)

        cols_query = ",".join(lst_cols)
        query = f'''{createQuery} ( {cols_query} ) '''

        return query


    def createTable(self, tableDetails, etl=False):
        if etl ==True:
            query = self.generateCreateTableScriptETL(tableDetails)
            return self.executeSql(query)
        else:
            query = self.generateCreateTableScript(tableDetails)

        self.executeSql(query)

        return True    

    def getColumnLOV(self, table_name, col_name, order='ASC'):
        self.connect()
        full_table_name = table_name

        if isinstance(full_table_name, dict):
            for t_name, alias_name in full_table_name.items():
                full_table_name = t_name

        if self.schema:
            if self.is_bw4hana and self.catalog_name :
                full_table_name = TBL_NME_FRMT.format(self.schema, self.catalog_name, table_name)
            else :
                full_table_name = '"' + self.schema + '".' + full_table_name

        query = 'SELECT DISTINCT "{col_name}" as "values" FROM {tbl_name} WHERE 1 = 1 ORDER BY "{col_name}" {order};'.format(
            col_name = col_name,
            tbl_name = full_table_name,
            order = order
        )  

        results = pd.read_sql(query, self.connection)
        self.close()

        return results['values'].tolist()

    def getColumnsProfile(self, table_name, with_min_max=False, filter = None):
        
        df_col_dtls = self.getTableColumnsDetails(tbl_name = table_name, sort_on_position=True)

        full_table_name = table_name
        if self.schema:
            if self.is_bw4hana and self.catalog_name :
                full_table_name = TBL_NME_FRMT.format(self.schema, self.catalog_name, table_name)
            else :                
                full_table_name = self.schema + "." + full_table_name

        index = 0
        for row in df_col_dtls:
            ## splitted DB Type as db type contains precison & length also ex varchar(255), numeric(17,3)
            x = row["DATA_TYPE"]
            x = x.split("(")[0]
            if x.upper() in ['VARCHAR', 'TIMESTAMP', 'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL',
                             'DOUBLE PRECISION', 'SMALLINT', 'INTEGER', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL', 'INT']:
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE  , """
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

            sub_query += f""" FROM "{table_name}"  """

            if filter :
                sub_query += " WHERE " + filter

            sub_query += " GROUP BY 1 "    

            sub_query = sub_query.format(col_name=row["COLUMN_NAME"], data_type=row["DATA_TYPE"], table_name=full_table_name)

            df_sub = self.executeQuery(sub_query)

            if index == 0:
                df = df_sub.copy()
            else:
                df = pd.concat([df, df_sub])

            index += 1

        return df

    def getTableDetails(self, table_name=None, type = {}):
        schema = "public"
        if self.schema is not None:
            schema = self.schema

        sep = "','"
        if table_name:
            if isinstance(table_name, list) :
                table_name = "'{}'" .format(sep.join(table_name))
            else :
                table_name = "'{}'".format(table_name)

        if self.is_bw4hana :
            query = """
                select 
                    t1.SCHEMA_NAME AS "TABLE_SCHEMA",
                    t1.CUBE_NAME AS "TABLE_NAME",
                    t2.NO_OF_COLS,
                    0 as NO_OF_ROWS,
                    1024 as SIZE_IN_MB,
                    t1.LAST_SCHEMA_UPDATE as LAST_UPDATED , 
                    t1.DESCRIPTION as COMMENT 
                    
                FROM "_SYS_BI"."BIMC_CUBES"  t1
                inner join (
                        select 
                            SCHEMA_NAME, 
                            CUBE_NAME, 
                            CATALOG_NAME, 
                            COUNT(1) AS NO_OF_COLS 
                        from "_SYS_BI".BIMC_PROPERTIES
                        group by SCHEMA_NAME, CATALOG_NAME, CUBE_NAME
                    ) t2 
                        on t1.CUBE_NAME=t2.CUBE_NAME 
                        and t1.SCHEMA_NAME = t2.SCHEMA_NAME
                        AND t1.CATALOG_NAME = t2.CATALOG_NAME
                    where t1.CUBE_NAME in ({table_name})
                    and t1.SCHEMA_NAME = '{schema}'
                    and t1.CATALOG_NAME = '{catalog}'
            """
        else :
            query = """
                select 
                    t1.SCHEMA_NAME AS "TABLE_SCHEMA",
                    t1.TABLE_NAME AS "TABLE_NAME",
                    'TABLE' AS "TABLE_TYPE",
                    t2.NO_OF_COLS AS "NO_OF_COLS",
                    t1.RECORD_COUNT AS "NO_OF_ROWS",
                    ((t1.LAST_ESTIMATED_MEMORY_SIZE ) / 1024/1024 ) AS "SIZE_IN_MB",
                    t1.LAST_MERGE_TIME AS "LAST_UPDATED",
                    '' AS "COMMENT" from SYS.M_CS_TABLES t1
                    inner join (
                        select 
                            SCHEMA_NAME, 
                            TABLE_NAME, 
                            COUNT(schema_name) AS NO_OF_COLS 
                        from SYS.M_CS_COLUMNS  
                        group by schema_name,table_name
                    ) t2 
                        on t1.table_name=t2.table_name 
                        and t1.schema_name = t2.schema_name
                    where 1=1
            """

            if self.schema :
                query += """ and t1.schema_name = '{schema}'"""

            if table_name:
                query += """ and t1.table_name in ({table_name}) """

            query += """
                    union
                    select 
                    t1.SCHEMA_NAME AS "TABLE_SCHEMA",
                    t1.VIEW_NAME AS "TABLE_NAME",
                    'VIEW' AS "TABLE_TYPE",
                    t2.NO_OF_COLS AS "NO_OF_COLS",
                    0 AS "NO_OF_ROWS",
                    0 AS "SIZE_IN_MB",
                    NULL AS "LAST_UPDATED",
                    '' AS "COMMENT" from VIEWS t1
                    inner join (
                        select 
                            SCHEMA_NAME, 
                            TABLE_NAME, 
                            COUNT(schema_name) AS NO_OF_COLS 
                        from SYS.COLUMNS  
                        group by schema_name,table_name
                    ) t2 
                        on t1.VIEW_NAME=t2.table_name 
                        and t1.schema_name = t2.schema_name
                    where 1=1
                 """
            
            if self.schema :
                query += """ and t1.schema_name = '{schema}'"""

            if table_name:
                query += """ and t1.VIEW_NAME in ({table_name}) """

        if self.is_bw4hana :
            query = query.format(schema=schema, table_name=table_name, catalog = self.catalog_name)
        else : 
            query = query.format(schema=schema, table_name=table_name)
    
        df = self.executeQuery(query, limit=None)

        return df

    def getTableRelationships(self, table_name, bi_directional = False):
        query = """
            SELECT 
            TABLE_NAME AS table_name,
            COLUMN_NAME AS col_name,
            REFERENCED_TABLE_NAME AS ref_table_name,
            REFERENCED_COLUMN_NAME AS ref_col_name  
            FROM 
                REFERENTIAL_CONSTRAINTS
            WHERE 
                TABLE_NAME = '{table_name}' 
            OR 	
                REFERENCED_TABLE_NAME='{table_name}'
        """

        if self.schema:
            sub_qry = " AND SCHEMA_NAME = '{schema}'"
            query = query.format(table_name=table_name, schema=sub_qry)
        else:
            query = query.format(table_name=table_name, schema="")

        df = self.executeQuery(query, limit=None)

        return df

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
            on_condition = on_condition,
            matched_mapping = matched_mapping,
            non_matched_mapping = non_matched_mapping,
            on_match = on_match,
            on_not_match = on_not_match,
            filter_condition = filter_condition,
            encloser='"',
            target_encloser = target_encloser
        )

        merge_query = mrgstmt.get_query()
        
        return merge_query

    def getDropTableQuery(self, table_name):
        return f"DROP TABLE IF EXISTS {table_name}"

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
                tgt_mapped_col = src_target_mapping[src_col_name]
                # getting target column name mapped with source

                if tgt_mapped_col != '' or tgt_mapped_col is not None:
                    tgt_col_dtype = target_col_dtype[tgt_mapped_col]
                    tgt_col_dtype_len = col_dtype_len[tgt_mapped_col]

                    if tgt_col_dtype in ('TEXT', 'STR', 'VARCHAR', 'LONG VARCHAR'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR(length=int(tgt_col_dtype_len))})
                    elif tgt_col_dtype in ('NVARCHAR'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.NVARCHAR(length=int(tgt_col_dtype_len))})
                    elif tgt_col_dtype == 'INT':
                        dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                    elif tgt_col_dtype in ('FLOAT', 'DEC', 'NUMERIC', 'NUMBER'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                    elif tgt_col_dtype in ('BOOLEAN', 'BOL'):
                        dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                    elif tgt_col_dtype in ('TIMESTAMP', 'DATE', 'DAT', 'TMS'):
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
        query = """
            SELECT 
                ic.SCHEMA_NAME AS "TABLE_SCHEMA",
                ic.TABLE_NAME AS "TABLE_NAME",
                ic.COLUMN_NAME AS "COLUMN_NAME",
                ic.INDEX_NAME AS "INDEX_NAME",
                i.INDEX_TYPE AS "INDEX_TYPE",
                ic."POSITION" AS "SEQUENCE"
            FROM SYS.INDEX_COLUMNS ic
            LEFT JOIN SYS.INDEXES i 
                ON i.TABLE_NAME = ic.TABLE_NAME 
                AND ic.INDEX_OID = i.INDEX_OID 
                AND ic.INDEX_NAME = i.INDEX_NAME
            WHERE ic.TABLE_NAME = '{}'""".format(tablename)

        if self.schema:
            query += " AND ic.SCHEMA_NAME = '{}'".format(self.schema)

        df = self.executeQuery(query, limit = None)

        return  df

    def dq_dashboard_data_freshness_query(self,tablename,columnname,fromdate,todate):
        query='''
            SELECT TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') date_col, 
            count(1) row_added FROM %(table_name)s
            WHERE TO_DATE(TO_VARCHAR(%(col_name)s,'YYYY-MM-DD'),'YYYY-MM-DD') 
            BETWEEN TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            GROUP BY TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD')
            ORDER BY 1
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query 

    def dq_dashboard_data_modify_query(self,tablename,columnname,fromdate,todate):
        query='''
            SELECT TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') date_col, 
            count(1) row_added FROM %(table_name)s
            WHERE TO_DATE(TO_VARCHAR(%(col_name)s,'YYYY-MM-DD'),'YYYY-MM-DD') 
            BETWEEN TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            GROUP BY TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD')
            ORDER BY 1
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query 

    def dq_dashboard_data_delete_query(self,tablename,columnname,fromdate,todate):
        query='''
            SELECT TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') date_col, 
            count(1) row_added FROM %(table_name)s
            WHERE TO_DATE(TO_VARCHAR(%(col_name)s,'YYYY-MM-DD'),'YYYY-MM-DD') IS NOT NULL AND 
            TO_DATE(TO_VARCHAR(%(col_name)s,'YYYY-MM-DD'),'YYYY-MM-DD') BETWEEN TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            GROUP BY TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD')
            ORDER BY 1
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query

    def dq_dashboard_stk_query(self,tablename,columnname,fromdate,todate,datasources_col_name):
        query='''
            SELECT TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD') date_col, 
            IFNULL(%(datasources_col_name)s,'Other')  src, 
            count(1) row_added FROM %(table_name)s
            WHERE TO_DATE(TO_VARCHAR(%(col_name)s,'YYYY-MM-DD'),'YYYY-MM-DD') BETWEEN TO_DATE('%(from_date)s','YYYY-MM-DD') and TO_DATE('%(to_date)s','YYYY-MM-DD')
            GROUP BY TO_DATE(TO_VARCHAR(%(col_name)s, 'YYYY-MM-DD'),'YYYY-MM-DD'), IFNULL(%(datasources_col_name)s,'Other')
            ORDER BY 1
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate,"datasources_col_name":datasources_col_name})
        
        return query

    def get_incremental_columns(self, table_name, **others):
        pass

    def fetch_delta_columns(self, table_name, **others):
        df = None
        df = self.getColumnsProfile(table_name, with_min_max=False, filter=None)
        if not df.empty:
            df_date = df.loc[(df['DATA_TYPE'].str.upper().str.contains('TMS*|DAT*|TIME*'))]
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
            select_clause = "select count(1) as CNT from " + tbl_name
        else:
            select_clause = "select count(1) as CNT from " + self.schema + "." + tbl_name        

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
                set_clause += merge_stmt_dict["SAPHANA"]["set"]["NULL"].format(col_name = key, value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += merge_stmt_dict["SAPHANA"]["set"][col_type].format(col_name = key, value = row[matched_mapping[key]].replace("'", "''"))                            
                else :
                    set_clause += merge_stmt_dict["SAPHANA"]["set"][col_type].format(col_name = key, value = row[matched_mapping[key]])                     

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
                    values += merge_stmt_dict["SAPHANA"]["insert"][col_type].format(value = row[non_matched_mapping[key]].replace("'", "''")) + ","
                else:
                    values += merge_stmt_dict["SAPHANA"]["insert"][col_type].format(value = row[non_matched_mapping[key]]) + ","
            else :
                values += merge_stmt_dict["SAPHANA"]["insert"]["NULL"].format(value = 'null') + ","

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection=manage_connection)

