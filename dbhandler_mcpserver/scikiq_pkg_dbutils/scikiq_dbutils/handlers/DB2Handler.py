# PYTHON PACKAGES
import pandas as pd
import uuid
import json
from collections import OrderedDict
import ibm_db
import ibm_db_dbi
from sqlalchemy import create_engine, types as sqlalchemyTypes
from pypika import Order,Table, Field, JoinType,Tables
from pypika import VerticaQuery
from pypika import PostgreSQLQuery
from pypika import functions as fn
from urllib.parse import quote
from sqlalchemy.sql import quoted_name
from sqlalchemy import Table as Tbl, Column, MetaData, insert, text
from sqlalchemy.sql import sqltypes as sqlalchemyTypes

# CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression
from scikiq_dbutils.handlers.DBConnection import (
    clsDBConnection, ViewCreationError, where_recursive_condition, where_condition, 
    where_Colcondition, MergeStatement
)
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict

class clsDB2DB(clsDBConnection):
    """
        Usage:

    """

    #def __init__(self, user, password, host, port, dbname, schema=None):
    def __init__(self, config):

        self.host = config["hostname"]
        self.port = config["port"]
        self.dbname = config["dbname"]
        self.user = config["dbuser"]
        self.password = config["pwd"]

        self.engine_statement = None
        self.connection = None
        self.cursor = None

        if("resource_key" in config):
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None

        if "schema" in config :
            self.schema = config["schema"].upper()
        else :
            self.schema = None

        if "connection_type" in config :
            self.connection_type = config["connection_type"]
        else :
            self.connection_type = None            

        self.db_type = "DB2"            

    def getConnectionType(self):
        if self.connection_type is None :
            return "SR"
        else :
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

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'

            ibm_db_conn = ibm_db.connect("ATTACH=FALSE;DATABASE="+ self.dbname +";HOSTNAME="+ self.host +";PORT="+ str(self.port) + ";PROTOCOL=TCPIP;UID="+ self.user +";PWD="+self.password+";AUTHENTICATION=SERVER", "", "")
            self.connection = ibm_db_dbi.Connection(ibm_db_conn)

            self.cursor = self.connection.cursor()
            if self.schema :
                self.cursor.execute("SET CURRENT SCHEMA = '{}'".format(self.schema))

            #callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsDB2DB,self).callConnectionAudit(resp)   

        except Exception as e:
            #callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsDB2DB,self).callConnectionAudit(resp)
            raise       


    def close(self):
        if self.connection :
            self.connection.close()        

    def testConnection(self):
        resp = {}
        try:
            ibm_db_conn = ibm_db.connect("ATTACH=FALSE;DATABASE="+ self.dbname +";HOSTNAME="+ self.host +";PORT="+ str(self.port) + ";PROTOCOL=TCPIP;UID="+ self.user +";PWD="+self.password+";AUTHENTICATION=SERVER", "", "")

            conn = ibm_db_dbi.Connection(ibm_db_conn)
            conn.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS
        except Exception as e:
            resp['msg'] = str(e)
            resp['error'] = 1

        #callConnectionAudit using for audit the record.
        super(clsDB2DB,self).callConnectionAudit(resp)

        return resp

    def executeQueryOld(self, query, limit=None, manage_connection =True):
        results = None
        try : 
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
        except Exception as e :
            if manage_connection:
                self.close()
            print(e)
            raise

        return results

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
            print(e)
            raise
        return view_name

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
    
    def maxLengthColumn(self,df_column):
        try:
            mx_length = df_column.str.len().max()
            if mx_length < 80:
                mx_length = 80
            return mx_length
        except Exception as e:
            return 80
        


    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=10000, dtype={}):
        self.create_engine()

        # Clean string columns
        for col in df.select_dtypes('O'):
            try:
                df[col] = df[col].str.replace(',', '')
                df[col] = df[col].str.replace('"', '')
                df[col] = df[col].str.replace('\\', '')
            except Exception as e:
                print(e)

        # Infer SQLAlchemy data types if dtype is not provided
        dtypedict = {}
        if not dtype:
            for col_name, col_type in zip(df.columns, df.dtypes):
                print(col_name, col_type)
                if "object" in str(col_type):
                    mx_length = self.maxLengthColumn(df[col_name])
                    dtypedict[col_name] = sqlalchemyTypes.VARCHAR(length=mx_length)
                elif "int64" in str(col_type):
                    dtypedict[col_name] = sqlalchemyTypes.BIGINT
                elif "int8" in str(col_type):
                    dtypedict[col_name] = sqlalchemyTypes.SMALLINT                 
                elif "float64" in str(col_type):
                    dtypedict[col_name] = sqlalchemyTypes.FLOAT
                elif "bool" in str(col_type):
                    dtypedict[col_name] = sqlalchemyTypes.BOOLEAN
                elif "datetime64[ns]" in str(col_type):
                    dtypedict[col_name] = sqlalchemyTypes.DATETIME
        else:
            dtypedict = dtype

        metadata = MetaData(schema=self.schema)
        quoted_tbl_name = quoted_name(tablename, quote=True)

        # Define the table structure
        table_columns = [Column(col, dtypedict[col]) for col in df.columns]
        table = Tbl(quoted_tbl_name, metadata, *table_columns, extend_existing=True)

        with self.engine_statement.connect() as conn:
            if self.schema:
                conn.execute(text(f"SET CURRENT SCHEMA = '{self.schema}'"))

            # Drop and recreate table if requested
            if if_exists == 'replace':
                table.drop(conn, checkfirst=True)
                table.create(conn)
            elif if_exists == 'append':
                table.create(conn, checkfirst=True)

            # Convert DataFrame rows to dictionaries for insert
            records = df.where(df.notnull(), None).to_dict(orient='records')

            # Insert in chunks
            for i in range(0, len(records), chunksize):
                chunk = records[i:i + chunksize]
                stmt = insert(table)
                conn.execute(stmt, chunk)

        return df


    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()
        
        query = "SELECT TABLE_NAME,TABLE_TYPE,TABLE_SCHEMA FROM SYSIBM.TABLES WHERE TABLE_CATALOG= '{dbname}' ".format(
            dbname=self.dbname.upper()
        )

        if include_view == True:
            query += " AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')"
        else:
            query += " AND TABLE_TYPE = 'BASE TABLE'"

        if search:
            query += " AND TABLE_NAME LIKE '{}'".format(search)

        if self.schema:
            query += " AND  TABLE_SCHEMA = '{schema}'".format(schema=self.schema)

        query += " ORDER BY TABLE_NAME"
 
        self.cursor.execute(query)
        results = self.cursor.fetchall()

        self.close()
        
        return results

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)

        data_dict = []
        self.connect()
        query = " SELECT COLUMN_NAME,DATA_TYPE FROM SYSIBM.COLUMNS WHERE TABLE_CATALOG = '{}'".format(self.dbname.upper()) 
        
        if self.schema :
            query += " AND TABLE_SCHEMA = '{}'".format(self.schema.upper())

        query += " AND TABLE_NAME = '{}' ORDER BY COLUMN_NAME"

        for data_tbl in results:
            dict_dynamic = {}
            data_tbl = list(data_tbl)[0]
            dict_dynamic["tablename"] = data_tbl
            try:
                query = query.format(data_tbl)
                self.cursor.execute(query)
                results = self.cursor.fetchall()                
                dict_dynamic["columnname"] = self.cursor.fetchall()
            except Exception as e:
                print(e)
                dict_dynamic["columnname"] = ""

            data_dict.append(dict_dynamic)

        self.close()

        return data_dict
    

    def getTableColumns(self, tablename, type = ''):
        query = "SELECT COLUMN_NAME FROM SYSIBM.COLUMNS WHERE TABLE_CATALOG = '{}'  AND TABLE_NAME = '{}'".format(
            self.dbname.upper(), 
            tablename.upper()
        )
        
        if self.schema:
            query += " AND TABLE_SCHEMA = '{}'".format(self.schema.upper())

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

            ## DATA_TYPE_LENGTH added to make this query result set in sync with other DB
            query = '''
                SELECT 
                    c.TABLE_CATALOG AS "TABLE_CATALOG" ,
                    c.TABLE_SCHEMA AS "TABLE_SCHEMA",
                    c.TABLE_NAME AS "TABLE_NAME",
                    '{t_type}' as "TABLE_TYPE",
                    c.COLUMN_NAME AS "COLUMN_NAME",
                    c.ORDINAL_POSITION AS "ORDINAL_POSITION",
                    CASE WHEN c.COLUMN_DEFAULT IS NULL THEN '' ELSE c.COLUMN_DEFAULT END AS "COLUMN_DEFAULT",
                    CASE WHEN t.REMARKS IS NULL THEN '' ELSE t.REMARKS END AS "COMMENT",
                    c.IS_NULLABLE AS "IS_NULLABLE",
                    c.DATA_TYPE AS "DATA_TYPE",
                    c.CHARACTER_MAXIMUM_LENGTH AS "CHARACTER_MAXIMUM_LENGTH",
                    c.CHARACTER_OCTET_LENGTH AS "CHARACTER_OCTET_LENGTH",
                    c.NUMERIC_PRECISION AS "NUMERIC_PRECISION",
                    c.NUMERIC_PRECISION_RADIX AS "NUMERIC_PRECISION_RADIX",
                    c.NUMERIC_SCALE AS "NUMERIC_SCALE",
                    c.DATETIME_PRECISION AS "DATETIME_PRECISION",
                    c.INTERVAL_TYPE AS "INTERVAL_TYPE" ,
                    c.INTERVAL_PRECISION AS "INTERVAL_PRECISION",
                    c.CHARACTER_SET_CATALOG AS "CHARACTER_SET_CATALOG",
                    c.CHARACTER_SET_SCHEMA AS "CHARACTER_SET_SCHEMA ",
                    c.CHARACTER_SET_NAME AS "CHARACTER_SET_NAME",
                    c.COLLATION_CATALOG AS "COLLATION_CATALOG"  ,
                    c.COLLATION_SCHEMA AS "COLLATION_SCHEMA" ,
                    c.COLLATION_NAME AS "COLLATION_NAME" ,
                    c.DOMAIN_CATALOG AS "DOMAIN_CATALOG",
                    c.DOMAIN_SCHEMA AS "DOMAIN_SCHEMA" ,
                    c.DOMAIN_NAME AS "DOMAIN_NAME",
                    c.UDT_CATALOG AS "UDT_CATALOG",
                    c.UDT_SCHEMA AS "UDT_SCHEMA",
                    c.UDT_NAME AS "UDT_NAME",
                    c.SCOPE_CATALOG AS "SCOPE_CATALOG",
                    c.SCOPE_SCHEMA AS "SCOPE_SCHEMA",
                    c.SCOPE_NAME AS "SCOPE_NAME",
                    c.MAXIMUM_CARDINALITY AS "MAXIMUM_CARDINALITY",
                    c.DTD_IDENTIFIER AS "DTD_IDENTIFIER",
                    c.IS_SELF_REFERENCING AS "IS_SELF_REFERENCING",
                    c.CHARACTER_MAXIMUM_LENGTH AS "DATA_TYPE_LENGTH",
                    COALESCE(cast(COALESCE(c.CHARACTER_OCTET_LENGTH,c.CHARACTER_MAXIMUM_LENGTH,c.DATETIME_PRECISION) as varchar), CONCAT(concat(c.NUMERIC_PRECISION,','),COALESCE(c.NUMERIC_SCALE,0))) AS CHARACTER_MAX_LENGTH,
                    CASE WHEN upper(tc."TYPE") = 'P' THEN 1 ELSE 0 END AS "IS_PRIMARYKEY",
                    CASE WHEN upper(tc."TYPE") = 'U' THEN 1 ELSE 0 END AS "IS_UNIQUEKEY",
                    '' AS "IS_NONUNIQUEKEY",
                    CASE WHEN c2."IDENTITY" = 'Y' AND GENERATED ='A' THEN 1 ELSE 0 END AS "AUTO_INCREMENT",
                    CASE 
                        WHEN c.CHARACTER_MAXIMUM_LENGTH IS NOT NULL 
                            THEN c.CHARACTER_MAXIMUM_LENGTH 
                        WHEN c.DATETIME_PRECISION IS NOT NULL
                            THEN c.DATETIME_PRECISION 
                        ELSE c.NUMERIC_PRECISION 
                    END AS "COLUMN_LENGTH",
                    CASE WHEN c.NUMERIC_SCALE IS NULL THEN 0 ELSE c.NUMERIC_SCALE END AS "COLUMN_PRECISION",
                    CASE WHEN c.CHARACTER_SET_NAME IS NULL THEN '' ELSE c.CHARACTER_SET_NAME END AS "COLUMN_CHARACTERSET",
                    CASE WHEN c3.CONSTNAME IS NULL THEN '' ELSE c3.CONSTNAME END AS "CONSTRAINT_NAME",
                    CASE WHEN r.REFTABNAME IS NULL THEN '' ELSE r.REFTABNAME END AS "REFERENCED_TABLENAME",
                    CASE WHEN r.PK_COLNAMES IS NULL THEN '' ELSE r.PK_COLNAMES END AS "REFERENCED_COLUMNNAME",
                    CASE WHEN c3.CONSTNAME IS NULL THEN 'no' ELSE 'yes' END AS "KEY_COL"
                FROM "SYSIBM".COLUMNS c 
                LEFT JOIN SYSCAT.TABLES t ON t.TABNAME = c.TABLE_NAME AND t.TABSCHEMA = c.TABLE_SCHEMA 
                LEFT JOIN SYSCAT.TABCONST tc ON  tc.TABNAME = c.TABLE_NAME AND tc.TABSCHEMA = c.TABLE_SCHEMA 
                LEFT JOIN SYSCAT.COLUMNS c2 ON c.TABLE_SCHEMA = c2.TABSCHEMA AND c.TABLE_NAME = c2.TABNAME AND c.COLUMN_NAME = c2.COLNAME
                LEFT JOIN SYSCAT.CHECKS c3 ON c.TABLE_SCHEMA = c3.TABSCHEMA AND c.TABLE_NAME = c3.TABNAME 
                LEFT JOIN SYSCAT."REFERENCES" r ON c.TABLE_SCHEMA = r.TABSCHEMA AND c.TABLE_NAME = r.TABNAME 
                WHERE c.TABLE_CATALOG = '{dbname}' AND c.TABLE_NAME = '{tbl_name}' 
            '''.format(t_type=t_type,dbname=self.dbname.upper(), tbl_name=tbl_name.upper())   

            if self.schema is not None:
                query += " AND c.TABLE_SCHEMA = '{}'".format(self.schema.upper())

            if sort_on_position :
                query +=  " ORDER BY ORDINAL_POSITION "
            else :
                query += " ORDER BY COLUMN_NAME "            

            self.connect()
            self.cursor.execute(query)
            desc = [d[0] for d in self.cursor.description]
            results = [dict(zip(desc, res)) for res in self.cursor.fetchall()]
            self.close()

            return results


    def getRenamesColMetricsDict(self, config_details=OrderedDict()):
        col_dict = OrderedDict()
        col_lst = []
        col_idx_dict = {}

        if config_details:
            #Get column key and alias name with list of vlaues
            for key, col_details in config_details.items():
                    for lst in col_details:
                        col_dict[key] = lst['alias']
                        col_lst.append(key)

            #Get column occurences of the data.
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
        tbls_name = {}
        ## table name is a key value pair {"dim_projects" : "dp"} tablename and alias
        if tablename is not None:
            for key in tablename.keys():
                tbl_name = key
                alias = tablename[tbl_name]
                if not self.schema:
                    tbls[alias] = Table(tbl_name, alias=alias)
                else:
                    tbls[alias] = Table(tbl_name, alias=alias, schema=self.schema)

                tbls_name[alias] = tbl_name

        index = 0
        
        for key in tbls.keys():
            if index == 0:
                _query = VerticaQuery.from_(tbls[key])
            else:
                if tbls_name[key] in joins:
                    join_type = joins[tbls_name[key]]
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

            lst_fields = []

            #Add column names which is derived/custom columns by user
            custom_column_names_dict = {}

            for key, value in columnnames.items():
                ## Change input pattern now value will be list
                for lst_item in value:
                    ## if condition to handle json from build model
                    ## "dim_project0.projectid" : ""  ## alisa.colname : agg fun and
                    ## else condtion to handle json from ETL
                    ## "projectid":"SUM" ## colname:AGG fun
                    if "." in key:
                        key = key.split(".")
                        col_tbl_name = key[0]
                        col_name = key[1]
                        if value != '':
                            # lst_fields.append(Field(tbls[col_tbl_name], agg_func[value](col_name)))
                            lst_fields.append(agg_func[value](eval('tbls[col_tbl_name]' + "." + col_name)))
                        else:
                            if " as " in col_name:
                                lst_fields.append(Field(
                                    col_name.split(" as ")[0], 
                                    table=tbls[col_tbl_name],
                                    alias=col_name.split(" as ")[1])
                                )
                            else:
                                lst_fields.append(Field(col_name, table=tbls[col_tbl_name]))
                    else:
                        if str(lst_item['agg']).upper() == 'DISTINCT COUNT':
                            lst_fields.append(fn.Count(Field(key), alias=lst_item['alias']).distinct())
                        elif lst_item['agg'] != '':
                            lst_fields.append(
                                agg_func[str(lst_item['agg']).upper()](Field(key), alias=lst_item['alias']))
                        else:
                            lst_fields.append(Field(key).as_(lst_item['alias']))

                    #Add custom column in the list.
                    if 'col_type' in  lst_item.keys():
                        if lst_item['col_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = lst_item['expression']
                    elif 'column_type' in  lst_item.keys():
                        if lst_item['column_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = lst_item['expression']

        if distinct:
            _query = _query.select(*lst_fields).distinct()
        else:
            _query = _query.select(*lst_fields)

        if limit is not None:
            if isinstance(limit, list) and len(limit) == 1:
                limit = int(limit[0])
                _query = _query.limit(limit)
            elif isinstance(limit, str):
                limit = int(limit)
                _query = _query.limit(limit)
            else :
                _query = _query.limit(limit)

        # add offset
        if offset is not None:
            _query = _query.offset(offset)
            
                
        if orderby is not None:

            if isinstance(orderby,dict): ## deprecated in new version 2021/08/31
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
                                    _query  = _query.orderby(_index+1,order=order_asc)

            elif isinstance(orderby,list):
                for dct in orderby:
                    for col,asc_desc in dct.items():
                        order_asc = Order.asc if asc_desc == 'ASC' else Order.desc
                        _query  = _query.orderby(col,order=order_asc)
                                    

        if filters is not None and "rules" in filters:
            _query = _query.where(where_recursive_condition(filters["condition"], filters["rules"]))

        if groupby is not None:
            for key, value in groupby.items():
                _query = _query.groupby(key)

        query = _query.get_sql()
        query = self.formatQuery(tablename, groupby, query, filters, columnnames, schema=self.schema)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)
    
        return query

    
    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                format_string = GetDBDateFormat.get_dbdate_format(db_type="DB2", format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, format_string, _dict,db_type="DB2")

                if(not column_expression):
                    column_expression =  _dict['expression_value']
                
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
        if "LIMIT" in query :
            limit = query.split('LIMIT')[1]            

        if "ORDER BY" in query:
            order_by_clause = query.split('ORDER BY')[1]
            order_by_clause = order_by_clause.replace('"' + alias + '".', "")
            query = query.split('ORDER BY')[0] + " ORDER BY " + order_by_clause


        select_clause = query.split('FROM')[0]
        if filters is not None and groupby is not None:
            if len(filters) != 0:
                where_clause = query.split('WHERE')[1]
            if len(groupby) != 0 and len(filters) != 0:
                where_clause = where_clause.split('GROUP BY')[0]
                group_clause = query.split('GROUP BY')[1]
            elif len(groupby) != 0:
                group_clause = query.split('GROUP BY')[1]

        string_format_upper = "UPPER(columnName) as alias"
        string_format_lower = "LOWER(columnName) as alias"
        string_format_initcap = "INITCAP(columnName) as alias"

        for key, value in columnnames.items():
            for item in value:
                temp_query = ""
                if "type" in item :
                    if item['type'].upper() == 'DATE' and item['format'] != '':
                        format_string = GetDBDateFormat.get_dbdate_format(db_type="DB2", format_string=item['format'])
                        temp_query = format_string
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "UPPER":
                        temp_query = string_format_upper
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "LOWER":
                        temp_query = string_format_lower
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "INITCAP":
                        temp_query = string_format_initcap
                    
                    if len(temp_query) :
                        alias_name = '"{}"."{}"'.format(alias, key)
                        temp_query = temp_query.replace('columnName', alias_name)
                        select_clause = select_clause.replace('"' + key + '"', temp_query, 1)

        if filters is not None and "rules" in filters:
            where_clause = self.formatFilter(alias, filters["condition"], filters["rules"], where_clause)

        if groupby is not None and len(groupby) != 0:
            for key, value in groupby.items():
                if "type" in value :
                    if (value['type'].upper() == 'DATE' and value['format'] != ''):
                        format_string = GetDBDateFormat.get_dbdate_format(db_type="DB2", format_string=value['format'])
                        temp_query = format_string
                        temp_query = temp_query.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        group_clause = group_clause.replace('"' + alias + '"' + '.' + '"' + key + '"', temp_query, 1)

        ## schema not used in this function as schema already added while creating connection
        if len(filters) > 0:
            select_clause += ' FROM "{table_name}" "{alias}" WHERE {where_clause}'.format(
                table_name = table, 
                alias = alias, 
                where_clause = where_clause
            )  
        else :
            select_clause += ' FROM "{table_name}" "{alias}" '.format(table_name = table, alias = alias)              
        
        if len(groupby)> 0:
            select_clause += ' GROUP BY {}'.format(group_clause) 

        if len(limit) > 0 :
            select_clause += " LIMIT " + limit            

        return select_clause

    def create_engine(self):
        # it requires pip install psycopg2
        self.engine_statement = create_engine(f'db2+ibm_db://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}')


    def readTable(self, tbl_name, limit, **others):
        #TODO:For use of random_sample keyword see readTable function of vertica.
        manage_connection = others.get("manage_connection", True)   

        if not self.schema:
            query = "SELECT * FROM " + tbl_name
        else:
            query = "SELECT * FROM " + self.schema + "." + tbl_name
            
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
        join_part = updateQuery.split('WHERE')[1]
        new_upd_qry = updateQuery.split('WHERE')[
                             0] + ' FROM (' + subQuery + ') as ' + inputTableReplica + ' WHERE ' + join_part
        return new_upd_qry

    def updateType(self, df, tableDetails, mappedColumn):
        dtypedict = {}  # create and empty dictionary
        for src_col_name, src_col_type in zip(df.columns, df.dtypes):
            if src_col_name in mappedColumn:
                trgt_mapped_col = mappedColumn[src_col_name]
                # getting target column name mapped with source
                if trgt_mapped_col != '' or trgt_mapped_col is not None:
                    trgt_col_detail = next(
                        filter(lambda x: (x[0] == trgt_mapped_col), tableDetails['columnName']))
                    # split column datatype value in case of varchar to remove detail part of length
                    trgt_col_dtype = trgt_col_detail[1].split('(')[0]
                    if trgt_col_dtype == 'varchar' or trgt_col_dtype == 'long varchar':
                        dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR})
                    elif trgt_col_dtype == 'int':
                        dtypedict.update({src_col_name: sqlalchemyTypes.BIGINT})
                    elif trgt_col_dtype == 'float':
                        dtypedict.update({src_col_name: sqlalchemyTypes.FLOAT})
                    elif trgt_col_dtype == 'boolean':
                        dtypedict.update({src_col_name: sqlalchemyTypes.BOOLEAN})
                    elif trgt_col_dtype == 'timestamp' or trgt_col_dtype == 'date':
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

    def updateTable(
            self, 
            df, 
            targetTableName, 
            columnnames={}, 
            filters=[], 
            joins={}, 
            fromTable=None, 
            sameSchema=False,
            tableDetails={}, 
            sqlQuery=None
        ):
        '''
            https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1
        '''

        inputTableReplica = f'temp_table' + str(uuid.uuid1()) if fromTable is None else fromTable
        inputTableReplica = inputTableReplica.replace('-', '_')
        print('Temp table used for update', inputTableReplica)
        sql = self.getUpdateQuery(targetTableName, columnnames, filters, joins, inputTableReplica, sqlQuery=sqlQuery)
        self.create_engine()
        if sameSchema:
            with self.engine_statement.begin() as conn:  # TRANSACTION
                t = conn.execute(sql)
                print("matched rows = {}".format(t.rowcount))
                return df, sql
        elif inputTableReplica not in sql:
            with self.engine_statement.begin() as conn:  # TRANSACTION
                t = conn.execute(sql)
                print("matched rows = {}".format(t.rowcount))
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
                df.to_sql(inputTableReplica, self.engine_statement, if_exists='replace',
                          dtype=self.updateType(df, tableDetails, columnnames), index=False)
                # this code will change the sql to support vertica update for two table
                sqlBuffer = sql.split('WHERE')
                where_clause = ' WHERE ' + sqlBuffer[1]
                fromClouse = ' FROM ' + inputTableReplica
                setClouse = sqlBuffer[0].split('SET')
                updateClouse = setClouse[0]
                setClouse = setClouse[1]
                columnMap = ' SET '

                for column in setClouse.split(','):
                    setClouse = column.split('=')
                    if columnMap == ' SET ':
                        # when set close varibale have where clouse then appending taht where clouse also
                        columnMap = columnMap + setClouse[0] + '=' + inputTableReplica + '.' + setClouse[1]
                    else:
                        columnMap = columnMap + ',' + setClouse[0] + '=' + inputTableReplica + '.' + setClouse[1]
                sql = updateClouse + columnMap + fromClouse + where_clause
                # end here the vertica update section
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    t = conn.execute(sql)
                    print("matched rows = {}".format(t.rowcount))
                    s = conn.execute("DROP TABLE IF EXISTS " + inputTableReplica)
                return df, sql
            except Exception as e:
                with self.engine_statement.begin() as conn:  # TRANSACTION
                    sql = f'DROP TABLE IF EXISTS "' + inputTableReplica + '"'
                    s = conn.execute(sql)
                raise Exception(e)

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

        sep = '"'
        createQuery = f'CREATE TABLE   "{tableName}"  '

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

        if self.schema is not None :
            full_table_name = '"' + self.schema + '".' + full_table_name     

        query = "SELECT DISTINCT {col_name} as values FROM {tbl_name} WHERE 1 = 1 ORDER BY {col_name} {order};".format(
            col_name = col_name,
            tbl_name = full_table_name,
            order = order
        )
        
        results = pd.read_sql(query, self.connection)
        
        self.close()

        return results

    def getColumnsProfile(self, table_name, with_min_max = False, filter = None):        
        dfColDtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = table_name
        if self.schema :
            full_table_name = '"' + self.schema + '".' + full_table_name

        index = 0
        for row in dfColDtls :

            if row["DATA_TYPE"].upper() in ['CHARACTER VARYING', 'TIMESTAMP' ,'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'DOUBLE PRECISION', 'SMALLINT', 'INTEGER', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL', ] :
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE  , """
                if with_min_max :
                    sub_query += """  VARCHAR_FORMAT(max("{col_name}")) AS MAX_VAL, 
                                    VARCHAR_FORMAT(min("{col_name}")) AS MIN_VAL, """
                sub_query += """ COUNT(distinct "{col_name}") AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """
            else :
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE , """
                if with_min_max :
                    sub_query += """ VARCHAR_FORMAT(max(0)) AS MAX_VAL, 
                                    VARCHAR_FORMAT(min(0)) AS MIN_VAL, """

                sub_query += """ COUNT(distinct "{col_name}") AS UNQ_VAL, 
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


    def getTableDetails(self, table_name=None, type = {}):


        sep = "','"

        if table_name:
            if isinstance(table_name, list) :
                table_name = "'{}'" .format(sep.join(table_name))
            else :
                table_name = "'{}'".format(table_name)

        query = """ SELECT 
                    t.TABSCHEMA AS TABLE_SCHEMA,
                    t.TABNAME AS TABLE_NAME,
                    card AS NO_OF_ROWS,
                    COLCOUNT AS NO_OF_COLS,
                    LASTUSED AS LAST_UPDATED,
                    CASE WHEN TYPE='T' THEN 'BASE TABLE'
                    end as TABLE_TYPE,
                    sz.SIZE AS SIZE_IN_MB ,
                    owner AS TABLE_COMMENT
                    FROM syscat.tables t
                    INNER JOIN ( SELECT TABSCHEMA ,TABNAME,
                               (DATA_OBJECT_P_SIZE + INDEX_OBJECT_P_SIZE + LONG_OBJECT_P_SIZE + LOB_OBJECT_P_SIZE +
                               XML_OBJECT_P_SIZE)/1024 AS SIZE
                    FROM SYSIBMADM.ADMINTABINFO) Sz ON sz.TABSCHEMA = t.TABSCHEMA 
                    AND sz.TABNAME = t.TABNAME
                """

        if self.schema :
            query += " WHERE t.TABSCHEMA = '"+ self.schema +"'"

        if table_name:
            query += """ and t.TABNAME IN ({table_name})""".format(table_name = table_name)

        query += """
                    UNION
                    SELECT 
                    v.VIEWSCHEMA AS TABLE_SCHEMA,
                    v.VIEWNAME AS TABLE_NAME,
                    0 AS NO_OF_ROWS,
                    c.n_columns as NO_OF_COLS,  
                    NULL AS LAST_UPDATED,  
                    'VIEW'as TABLE_TYPE,
                    0 AS SIZE_IN_MB ,
                    owner AS TABLE_COMMENT
                    FROM syscat.views v
                    left join (
                                    SELECT 
                                    TABLE_NAME,
                                    count(COLUMN_NAME) as n_columns 
                                    FROM "SYSIBM".COLUMNS c
                                    group by TABLE_NAME
                              ) c on c.TABLE_NAME = v.VIEWNAME
                """

        if self.schema :
            query += " WHERE v.VIEWSCHEMA = '"+ self.schema +"'"
        
        if table_name:
            query += """ and v.VIEWNAME IN ({table_name})""".format(table_name = table_name)

        df = self.executeQuery(query, limit = None)
        return  df


    def getTableRelationships(self, table_name, bi_directional = False):

        if bi_directional :
            query = """
                SELECT
                    TABNAME as table_name,
                    FK_COLNAMES as col_name,
                    REFTABNAME as ref_table_name,
                    PK_COLNAMES as ref_col_name  
                    FROM SYSCAT.REFERENCES WHERE TABNAME = '{table_name}'
                UNION
                SELECT 
                    TABNAME as table_name,
                    FK_COLNAMES as col_name,
                    REFTABNAME as ref_table_name,
                    PK_COLNAMES as ref_col_name  
                    FROM SYSCAT.REFERENCES WHERE REFTABNAME = '{table_name}'        
            """         
        else :
            query = """
                SELECT 
                    TABNAME as table_name,
                    FK_COLNAMES as col_name,
                    REFTABNAME as ref_table_name,
                    PK_COLNAMES as ref_col_name 
                    FROM SYSCAT.REFERENCES WHERE TABNAME = '{table_name}'
            """         
                
        query = query.format(table_name = table_name)

        if self.schema :
            sub_qry = " AND TABSCHEMA  = '{schema}' AND REFTABSCHEMA = '{schema}' ".format(schema = self.schema)
            query += sub_qry

        df = self.executeQuery(query, limit = None)
        
        return  df

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
            non_matched_mapping =non_matched_mapping,
            on_match =on_match,
            on_not_match= on_not_match,
            filter_condition=filter_condition,
            encloser='"',
            target_encloser = target_encloser
        )
        merge_query =mrgstmt.get_query()
        return merge_query+";"

    def getDropTableQuery(self,table_name):
        return  f'DROP TABLE IF EXISTS "{table_name}"'

    def dropTable(self, table_name):
        query = self.getDropTableQuery(table_name)
        self.executeSql(query)

    def getTableIndexDetails(self, tablename):
        query = '''
            select
            c.TABLE_SCHEMA AS "TABLE_SCHEMA",
            c.TABLE_NAME AS "TABLE_NAME",
            c.COLUMN_NAME AS "COLUMN_NAME",
            i.INDNAME AS "INDEX_NAME",
            i.INDEXTYPE AS "INDEX_TYPE",
            ic.COLSEQ  AS "SEQUENCE"
            FROM SYSCAT.INDEXES i
            LEFT JOIN "SYSIBM".COLUMNS c  ON i.COLNAMES LIKE  '%'||c.COLUMN_NAME ||'%' AND i.TABNAME = c.TABLE_NAME AND i.TABSCHEMA  = c.TABLE_SCHEMA 
            LEFT JOIN syscat.indexcoluse ic ON ic.COLNAME = c.COLUMN_NAME AND i.INDNAME = ic.INDNAME AND i.INDSCHEMA = ic.INDSCHEMA 
            WHERE c.TABLE_CATALOG = '{}' AND c.TABLE_NAME = '{}' '''.format(self.dbname.upper(), tablename.upper())  

        if self.schema:
            query += " AND c.TABLE_SCHEMA = '{}'".format(self.schema.upper())

        df = self.executeQuery(query, limit = None)

        return  df

    def get_incremental_columns(self, table_name,**others):
        try:
            # added distinct for unique data
            query = """SELECT DISTINCT c.COLUMN_NAME AS "COLUMN_NAME",
                        c.DATA_TYPE AS "DATA_TYPE"
                        FROM "SYSIBM".COLUMNS c 
                        LEFT JOIN SYSCAT.TABLES t 
                        ON t.TABNAME = c.TABLE_NAME 
                        AND t.TABSCHEMA = c.TABLE_SCHEMA 
                        LEFT JOIN SYSCAT.TABCONST tc 
                        ON  tc.TABNAME = c.TABLE_NAME 
                        AND tc.TABSCHEMA = c.TABLE_SCHEMA 
                        WHERE (c.IS_NULLABLE = 'NO' 
                                or (c.IS_NULLABLE = 'YES' 
                                    and c.COLUMN_DEFAULT IS NOT NULL))
                                AND ((upper(c.DATA_TYPE) LIKE 'DATE%' 
                                        OR upper(c.DATA_TYPE) LIKE 'TIME%' )
                                    OR ((upper(tc."TYPE") = 'P' 
                                            OR  upper(tc."TYPE") = 'U')
				                AND upper(c.DATA_TYPE) LIKE  'INT%' ))
                            AND c.table_name = '{table_name}' """.format(table_name=table_name)
            if self.schema:
                query += " AND c.TABLE_CATALOG = '" + self.schema + "'"
            
            self.connect()
            df = self.executeQuery(query, limit=None)
            df = df[['COLUMN_NAME', 'DATA_TYPE']]
        except Exception as e:
            self.close()
            print(e)
            raise
        return df

    def fetch_delta_columns(self, table_name, **others):
        try:
            inc_columns = self.get_incremental_columns(table_name)
            full_table_name = table_name
            
            if self.schema is not None:
                full_table_name = self.schema + "." + full_table_name
            
            df=None
            index = 0
            
            for index, row in inc_columns.iterrows():
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
                    col_name=row["COLUMN_NAME"],
                    table_name=full_table_name,
                    DATA_TYPE=row['DATA_TYPE']
                )
                
                df_sub = self.executeQuery(sub_query)
                df = df_sub.copy() if index == 0 else pd.concat([df, df_sub])
                
                index += 1
            
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
            where_clause += condition.format(col_name = '"' + con["target_col"] + '"' , value = row[con["source_col"]])

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
                set_clause +=  merge_stmt_dict["DB2"]["set"]["NULL"].format(col_name = '"' + key + '"', value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause +=  merge_stmt_dict["DB2"]["set"][col_type].format(
                        col_name = '"' + key + '"', 
                        value = row[matched_mapping[key]].replace("'", "''")
                    )                            
                else :
                    set_clause +=  merge_stmt_dict["DB2"]["set"][col_type].format(
                        col_name = '"' + key + '"', 
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

        if not self.schema:
            inst_clause = f'INSERT INTO "{tbl_name}"'
        else:
            inst_clause = f'INSERT INTO {self.schema}."{tbl_name}"'

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
                    values += merge_stmt_dict["DB2"]["insert"][col_type].format(
                        value = row[non_matched_mapping[key]].replace("'", "''")
                    ) + ","
                else:
                    values += merge_stmt_dict["DB2"]["insert"][col_type].format(
                        value = row[non_matched_mapping[key]]
                    ) + ","
            else :
                values += merge_stmt_dict["DB2"]["insert"]["NULL"].format(value = 'null') + ","

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection=manage_connection)
