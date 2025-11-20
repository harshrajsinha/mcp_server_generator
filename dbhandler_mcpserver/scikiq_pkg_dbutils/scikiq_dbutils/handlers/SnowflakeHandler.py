# PYTHON PACKAGES.
import pandas as pd
import uuid
import json
import math as math
from pypika.dialects import SnowflakeQuery
from pypika import Table, Field,JoinType,Order,Tables
from pypika import functions as fn
import snowflake.connector
import snowflake.connector.errors
from collections import OrderedDict
from sqlalchemy import create_engine, types as sqlalchemyTypes
from urllib.parse import quote

#CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression
from scikiq_dbutils.handlers.DBConnection import ( 
    clsDBConnection, ViewCreationError, where_recursive_condition, where_condition, 
    where_recursive_condition_col_dict, where_Colcondition, getReqSrcCols, MergeStatement
)
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict

class clsSnowflake(clsDBConnection):
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

        self.warehouse = "WH_DATALAKE"
        if "warehouse" in config :
            self.warehouse = config["warehouse"]        

        if ("resource_key" in config):
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None

        if "schema" in config and config["schema"]:
            self.schema = config["schema"].upper()
        else:
            self.schema = 'PUBLIC'

        if "connection_type" in config:
            self.connection_type = config["connection_type"]
        else:
            self.connection_type = None

        self.db_type = "SNOWFLAKE"

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
                qry = """COMMENT ON COLUMN
                         {dbname}."{schema}"."{table_name}"."{column_name}" IS '{comment}';""".format(
                         comment=comment,
                         schema=self.schema,
                         table_name=tbl_name,
                         column_name=col_name,
                         dbname=self.dbname
                )    
                
            else :
                qry = """COMMENT ON COLUMN
                         {dbname}."{schema}"."{table_name}"."{column_name}" IS '';""".format(
                         schema=self.schema,
                         table_name=tbl_name,
                         column_name=col_name,
                         dbname=self.dbname
                )    
                
            self.executeSql(qry)
            self.close()
        except Exception as e :
            self.close()
            print(e)
            success = False
        return success            

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'

            self.connection = snowflake.connector.connect(
                user=self.user,
                password=self.password,
                account=self.host,
                database=self.dbname,
                schema=self.schema
            )

            self.cursor = self.connection.cursor()
            self.cursor.execute('use warehouse {}'.format(self.warehouse))            

            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsSnowflake, self).callConnectionAudit(resp)

        # except DatabaseError as db_ex:
        #     resp['msg'] = str(e)

        #     if db_ex.errno == 250001:
        #         resp['msg'] = (f"Invalid username/password, please re-enter username and password...")
                
        #     resp['error'] = 1
        #     super(clsSnowflake, self).callConnectionAudit(resp)

        #     raise
        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsSnowflake, self).callConnectionAudit(resp)
            raise

    def close(self):
        if self.cursor:
            self.cursor.close()

        if self.connection:
            self.connection.close()

    def testConnection(self):
        resp = {}
        try:
            db = snowflake.connector.connect(
                user=self.user,
                password=self.password,
                account=self.host,
                database=self.dbname,
                schema=self.schema
            )

            db.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS
        # except DatabaseError as db_ex:
        #     if db_ex.errno == 250001:
        #         print(f"Invalid username/password, please re-enter username and password...")
        #         # code for user to re-enter username & pass
        #     else:
        #         raise
        except Exception as ex:
            # Log this
            print(f"Error while connecting to Snowflake database: {ex}")
            raise

        # callConnectionAudit using for audit the record.
        super(clsSnowflake, self).callConnectionAudit(resp)

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
            print(e)
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
                self.close()
        except Exception as e:
            if manage_connection:
                self.close()
            print(e)
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
                    # df[col] = df[col].str.replace(';','')
                    df[col] = df[col].str.replace(':', '')
            except Exception as e:
                print(e)

        if len(dtype) == 0:
            dtypedict = {}
            for sourceColumnName, sourceColumnType in zip(df.columns, df.dtypes):
                if "object" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.VARCHAR})
                elif "int" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.BIGINT})
                elif "float" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.FLOAT})
                elif "bool" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.BOOLEAN})
                elif "date" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.DATETIME})
                else:
                    ##
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.VARCHAR})
        else:
            dtypedict = dtype

        self.create_engine()
        with self.engine_statement.connect() as connection:
            ## When table name in caps then pandas throwing error 
            ## sqlalchemy.exc.InvalidRequestError: Could not reflect: requested table(s) not 
            ## available in Engine(snowflake://HARISH8010:***@qactyjb-vqb78060/DATALAKE/PUBLIC): (BSEG)
            tablename = tablename.lower()            

            connection.execute("ALTER SESSION SET QUOTED_IDENTIFIERS_IGNORE_CASE = TRUE;")                
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
                        print('start :' + str(start))
                        print('end :' + str(end))
                        df2 = df.iloc[start:end, :].copy()
                        ## for debug
                        ##df2.to_csv("Df2_"+str(start)+ "_" + str(end) + ".csv")
                        df2.to_sql(con=connection, name=tablename, dtype=dtypedict, if_exists=if_exists,chunksize = chunksize, index=False)
                        start = end
                        idx += 1
                else :
                    df.to_sql(con=connection, name=tablename, dtype=dtypedict, if_exists=if_exists,chunksize = chunksize, index=False)
            
        return df

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()

        query = """
                SELECT 
                    TABLE_NAME, 
                    CASE WHEN TABLE_TYPE = 'BASE TABLE' THEN 'TABLE' ELSE 'VIEW' END AS TABLE_TYPE,
                    TABLE_SCHEMA
                FROM {dbname}.INFORMATION_SCHEMA.TABLES""".format(dbname=self.dbname)

        if include_view == True:
            query += " WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')"
        else:
            query += " WHERE TABLE_TYPE = 'BASE TABLE'"

        if search:
            query += " AND TABLE_NAME LIKE UPPER('%{}%')".format(search.upper())

        if self.schema:
            query += " AND TABLE_SCHEMA = UPPER('{}')".format(self.schema)

        query += " ORDER BY TABLE_NAME ASC;"
        self.cursor.execute(query)

        results = self.cursor.fetchall()
        self.close()
        return tuple(tuple(x) for x in results)

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)
        dataDict = []
        for dataTable in results:
            dictDynamic = {}
            dataTable = list(dataTable)[0]
            dictDynamic["tablename"] = dataTable
            query = """
                SELECT COLUMN_NAME, DATA_TYPE as DATA_TYPE 
                FROM {}.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = UPPER('{}')""".format(self.dbname, dataTable.upper())

            if self.schema:
                query += " AND TABLE_SCHEMA = UPPER('{}')".format(self.schema)

            query += " ORDER BY COLUMN_NAME "

            self.connect()
            self.cursor.execute(query)               

            result = tuple(tuple(x) for x in self.cursor.fetchall())
            dictDynamic["columnname"] = result
            dataDict.append(dictDynamic)

        self.close()
        return dataDict

    def getTableColumns(self, tablename, type = ''):
        query = "SELECT COLUMN_NAME, DATA_TYPE as DATA_TYPE FROM {}.INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = UPPER('{}')".format(self.dbname, tablename.upper())

        if self.schema:
            query += " AND TABLE_SCHEMA = UPPER('{}')".format(self.schema)

        query += " ORDER BY COLUMN_NAME "
        print(query)
        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        results = tuple(tuple(x) for x in results)

        self.close()
        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        test_type= self.getTableDetails(table_name=tbl_name)
        t_type = test_type['TABLE_TYPE'][0]

        query = """ SELECT	
                c.TABLE_SCHEMA AS "TABLE_SCHEMA",
                c.TABLE_NAME as "TABLE_NAME",
                '{t_type}' as "TABLE_TYPE",
                c.COLUMN_NAME as "COLUMN_NAME",
                c.DATA_TYPE as "DATA_TYPE",
                c.ORDINAL_POSITION as "ORDINAL_POSITION",
                case when c.NUMERIC_PRECISION is null then 0 else c.NUMERIC_PRECISION end as "NUMERIC_PRECISION",
                case when c.NUMERIC_SCALE is null then 0 else c.NUMERIC_SCALE end as "NUMERIC_SCALE",
                c.IS_NULLABLE  as "IS_NULLABLE",
                case when c.CHARACTER_MAXIMUM_LENGTH is null then 0 else c.CHARACTER_MAXIMUM_LENGTH end as "CHARACTER_MAXIMUM_LENGTH",
                case when c.CHARACTER_MAXIMUM_LENGTH is null then 0 else c.CHARACTER_MAXIMUM_LENGTH end as "DATA_TYPE_LENGTH",
                case when c.DATA_TYPE = 'NUMBER' then concat(concat(c.NUMERIC_PRECISION,','),COALESCE(c.NUMERIC_SCALE,0)) 
                else cast(COALESCE(c.CHARACTER_MAXIMUM_LENGTH,c.DATETIME_PRECISION) as varchar) end as "CHARACTER_MAX_LENGTH",
                case when c.COMMENT  is null then '' else c.COMMENT end as "COMMENT",
                case when c.COLUMN_DEFAULT is null then '' else c.COLUMN_DEFAULT end as "COLUMN_DEFAULT",
                case when upper(ff.CONSTRAINT_TYPE) = 'PRIMARY KEY' then 1 else 0 end as "IS_PRIMARYKEY",
                case when upper(ff.CONSTRAINT_TYPE) = 'UNIQUE KEY' then 1 else 0 end as "IS_UNIQUEKEY",
                '' as "IS_NONUNIQUEKEY",
                case when c.IS_IDENTITY = 'YES' then 1 else 0 end as "AUTO_INCREMENT",
                case when c.CHARACTER_MAXIMUM_LENGTH is null then 0 else c.CHARACTER_MAXIMUM_LENGTH end as "COLUMN_LENGTH",
                case when c.NUMERIC_SCALE  is null then 0 else c.NUMERIC_SCALE  end as "COLUMN_PRECISION",
                case when c.CHARACTER_SET_NAME is null then '' else c.CHARACTER_SET_NAME end as "COLUMN_CHARACTERSET",
                case when ff.CONSTRAINT_NAME is null then '' else ff.CONSTRAINT_NAME end as "CONSTRAINT_NAME",
                '' as "REFERENCED_TABLENAME",
                '' as "REFERENCED_COLUMNNAME",
                case when ff.CONSTRAINT_NAME is null then 'no' else 'yes' end as "KEY_COL"
                FROM			
                {dbname}.INFORMATION_SCHEMA.COLUMNS AS c
                LEFT JOIN
                {dbname}.INFORMATION_SCHEMA.TABLES t
                    ON c.TABLE_NAME = t.TABLE_NAME
                    AND c.TABLE_SCHEMA = t.TABLE_SCHEMA
                LEFT JOIN 
                {dbname}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS ff
                ON c.TABLE_NAME = ff.TABLE_NAME AND c.TABLE_SCHEMA = ff.TABLE_SCHEMA
                WHERE UPPER(c.TABLE_NAME) = '{tbl_name}'
        """.format(t_type=t_type,dbname=self.dbname,tbl_name=tbl_name.upper())

        if self.schema:
            query += " AND c.TABLE_SCHEMA = UPPER('{}')".format(self.schema)

        if sort_on_position:
            query += " ORDER BY ORDINAL_POSITION "
        else:
            query += " ORDER BY COLUMN_NAME "

        self.connect()
        self.cursor.execute(query)        
        desc_value = [d[0] for d in self.cursor.description]
        desc = [item.upper() for item in desc_value]
        results = [dict(zip(desc, res)) for res in self.cursor.fetchall()]
        
        self.close()

        return results

    def getRenamesColMetricsDict(self, config_details=OrderedDict()):
        renameDimMetricsColDict = OrderedDict()
        renameDimMetricsColLst = []
        colIndexDct = {}
        if config_details:
            # Get column key and alias name with list of vlaues
            for key, col_details in config_details.items():
                for lst in col_details:
                    renameDimMetricsColDict[key] = lst['alias']
                    renameDimMetricsColLst.append(key)
            # Get column occurences of the data.
            for key, _ in renameDimMetricsColDict.items():
                indices = [index for index, element in enumerate(renameDimMetricsColLst) if element == key]
                colIndexDct[key] = indices
        return colIndexDct

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
                if not self.schema:
                    tbls[alias] = Table(tblName, alias=alias)
                else:
                    tbls[alias] = Table(tblName, alias=alias, schema=self.schema)
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
                    # _query = _query.join(tbls[key], how).on(tbls[list(joinCondition[0]['left'].keys())[0]] == tbls[list(joinCondition[0]['right'].keys())[0]] )
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
                except:
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

        ## to enclose column in  double quotes({"id"})
        query = _query.get_sql(quote_char = '"')

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
                formatString = GetDBDateFormat.get_dbdate_format(db_type = "SNOWFLAKE", format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, formatString, _dict,db_type = "SNOWFLAKE")
                if (not column_expression):
                    column_expression = _dict['expression_value']
                query = query.replace(_key, column_expression, 1)
                expression_column_names_lst.append(column_expression)
        return (query, expression_column_names_lst)



    def formatQuery(self, tablename, groupby=None, query=None, filters=None, columnnames=None, schema=None):
        ## if no filters or group by then no need to format query
        # if filters is None and groupby is None:
        if not (filters or groupby):
            return query

        elif len(filters) == 0 and len(groupby.keys()) == 0:
            return query

        for key in tablename.keys():
            table = key
            alias = tablename[key]

        selectClause = query.split(' FROM ')[0]

        if filters is not None or groupby is not None:
            if len(filters) != 0:
                whereClause = query.split('WHERE')[1]
            if groupby:
                if len(groupby) > 0 and len(filters) > 0:
                    whereClause = whereClause.split('GROUP BY')[0]
                    groupClause = query.split('GROUP BY')[1]
                elif len(groupby) > 0:
                    groupClause = query.split('GROUP BY')[1]

        for key, value in columnnames.items():
            for item in value:
                if "type" in item:
                    if item['type'] == 'date' and item['format'] != '':
                        formatString = GetDBDateFormat.get_dbdate_format(dbType="SNOWFLAKE", format_string=item['format'])
                        tempQuery = formatString
                        tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        tempQuery = tempQuery.replace('alias', '"' + item['alias'] + '"')
                        tempQuery = tempQuery.replace('colFormat', formatString)
                        selectClause = selectClause.replace('"' + key + '"', tempQuery, 1)

        if filters is not None:
            if "rules" in filters:
                whereClause = self.formatFilter(alias, filters["condition"], filters["rules"], whereClause)

        if groupby:
            if len(groupby) != 0:
                for key, value in groupby.items():
                    if "type" in value:
                        if (value['type'].upper() == 'DATE' and value['format'] != ''):
                            formatString = GetDBDateFormat.get_dbdate_format(dbType="SNOWFLAKE", format_string=value['format'])
                            tempQuery = formatString
                            tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                            tempQuery = tempQuery.replace('alias', '"' + key + '"')
                            tempQuery = tempQuery.replace('colFormat', formatString)
                            groupClause = groupClause.replace('"' + alias + '"' + '.' + '"' + key + '"', tempQuery, 1)

        ## schema not used in this function as schema already added while creating connection
        if len(filters) > 0:
            selectClause += ' FROM "{table_name}" "{alias}" WHERE {where_clause}'.format(table_name=table, alias=alias,
                                                                                         where_clause=whereClause)
        else:
            selectClause += ' FROM "{table_name}" "{alias}" '.format(table_name=table, alias=alias)

        if groupby:
            if len(groupby) > 0:
                selectClause += ' GROUP BY {}'.format(groupClause)

        return selectClause

    def create_engine(self):
        # it requires pip install snowflake-sqlalchemy

        conn_string = 'snowflake://{user}:{password}@{account_identifier}/{database}/{schema}'.format(
            user=quote(self.user),
            password=quote(self.password),
            account_identifier=self.host,
            database=self.dbname,
            schema=self.schema
        )        
        self.engine_statement = create_engine(conn_string)

    def get_connection_statement(self):
        statement = 'snowflake://{user}:{password}@{account_identifier}/{database}/{schema}'.format(
                        user=quote(self.user),
                        password=quote(self.password),
                        account_identifier=self.host,
                        database=self.dbname,
                        schema=self.schema
                    )   
        return statement

    def readTable(self, tbl_name, limit, **others):
        random_sample = others.get("random_sample", False)   
        manage_connection = others.get("manage_connection", True)
        tbl_name = tbl_name.upper()
        if self.schema:
            tbl_name = self.schema + "." + tbl_name

        query = "SELECT * FROM " + tbl_name

        if random_sample:
            query += " ORDER BY RANDOM() "

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection=manage_connection)
        res["df_text"] = None 

        return res               


    def getUpdateQuery(self, targetTableName, columnnames={}, filters=[], joins={}, inputTableReplica='temp_table',
                        sqlQuery=None):
        filters = None if filters == [
            {"from": "", "column": "", "operator": "", "value": ""}] or filters == [] else filters

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
        dtypedict = {}  # create and empty dictionary
        for sourceColumnName, sourceColumnType in zip(df.columns, df.dtypes):
            if sourceColumnName in mappedColumn:
                targetMappedColumn = mappedColumn[sourceColumnName]
                # getting target column name mapped with source
                if targetMappedColumn != '' or targetMappedColumn is not None:
                    targetColumnDetail = next(
                        filter(lambda x: (x[0] == targetMappedColumn), tableDetails['columnName']))
                    if targetColumnDetail:
                        # split column datatype value in case of varchar to remove detail part of length
                        targetColumnDataType = targetColumnDetail[1].split('(')[0]
                        if len(targetColumnDetail) > 2:
                            trgtColDTypeLen = targetColumnDetail[3]
                        else:
                            trgtColDTypeLen = 8000

                        targetColumnDataType = targetColumnDataType.upper()
                        if targetColumnDataType in ('TEXT', 'STR', 'VARCHAR', 'LONG VARCHAR'):
                            dtypedict.update({sourceColumnName: sqlalchemyTypes.VARCHAR(length=int(trgtColDTypeLen))})
                        elif targetColumnDataType in ('NVARCHAR'):
                            dtypedict.update({sourceColumnName: sqlalchemyTypes.NVARCHAR(length=int(trgtColDTypeLen))})
                        elif targetColumnDataType == 'INT':
                            dtypedict.update({sourceColumnName: sqlalchemyTypes.BIGINT})
                        elif targetColumnDataType in ('FLOAT', 'DEC'):
                            dtypedict.update({sourceColumnName: sqlalchemyTypes.FLOAT})
                        elif targetColumnDataType in ('BOOLEAN', 'BOL'):
                            dtypedict.update({sourceColumnName: sqlalchemyTypes.BOOLEAN})
                        elif targetColumnDataType in ('TIMESTAMP', 'DATE', 'DAT', 'TMS'):
                            dtypedict.update({sourceColumnName: sqlalchemyTypes.DATETIME})
            else:
                if "object" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.VARCHAR})
                elif "int64" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.BIGINT})
                elif "float64" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.FLOAT})
                elif "bool" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.BOOLEAN})
                elif "datetime64[ns]" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.DATETIME})

        return dtypedict

    # added tableDetails parameter to pass table columns data type
    def updateTable(self, df, targetTableName, columnnames={}, filters=[], joins={}, fromTable=None, sameSchema=False,
                    tableDetails={}, sqlQuery=None):
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
                            # df[col] = df[col].str.replace(';','')
                            df[col] = df[col].str.replace(':', '')
                    except Exception as e:
                        print(e)

                with self.engine_statement.connect() as connection:
                    if self.schema:
                        connection.execute("SET SEARCH_PATH TO " + self.schema)

                    data_types = self.updateType(df, tableDetails, columnnames)

                    df.to_sql(inputTableReplica, connection, if_exists='replace', dtype=data_types, index=False)

                # this code will change the sql to support snowflake update for two table
                sqlBuffer = sql.split('WHERE')
                whereClouse = ' WHERE ' + sqlBuffer[1]
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
                sql = updateClouse + columnMap + fromClouse + whereClouse
                # end here the snowflake update section
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
        table_name = table_name.upper()
        if not self.schema:
            query = f'TRUNCATE TABLE {table_name}'
        else:
            query = "TRUNCATE TABLE " + self.schema + "." + table_name
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
        
        tableName = tableDetails["tableName"].upper()
        createColumnData = tableDetails['createColumnData']
        #createColumnData =[{'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'} ..]

        sep = '"'
        sep_e = '"'
        createQuery = f'CREATE TABLE   "{tableName}"  '

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


    def createTable(self, tableDetails,etl=False):
        if etl ==True:
            query = self.generateCreateTableScriptETL(tableDetails)
            return self.executeSql(query)
        else:
            query = self.generateCreateTableScript(tableDetails)
        self.executeSql(query)

        return True    

    def getColumnLOV(self, table_name, col_name, order='ASC'):
        self.connect()
        full_table_name = table_name.upper()

        if isinstance(full_table_name, dict):
            for t_name, alias_name in full_table_name.items():
                full_table_name = t_name

        if self.schema is not None:
            full_table_name = '"' + self.schema + '".' + full_table_name

        full_table_name = full_table_name.upper()
        query = "SELECT DISTINCT '{col_name}' as values FROM {tbl_name} WHERE 1 = 1 ORDER BY '{col_name}' {order};".format(
            col_name = col_name,
            tbl_name = full_table_name,
            order = order
        )          
        
        results = pd.read_sql(query, self.connection)
        self.close()

        return results['values'].tolist()

    def getColumnsProfile(self, table_name, with_min_max=False, filter = None):
        table_name = table_name.upper()
        dfColDtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = table_name
        if self.schema is not None:
            full_table_name = self.schema + "." + full_table_name

        index = 0
        for row in dfColDtls:
            ## splitted DB Type as db type contains precison & length also ex varchar(255), numeric(17,3)
            x = row["DATA_TYPE"]
            if x.upper() in ['VARCHAR', 'TIMESTAMP', 'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'NUMBER'
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
                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT 
                """

            sub_query += " FROM {table_name} "

            if filter :
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

    def getTableDetails(self, table_name=None, type = {}):
        ### TABLE NAME CAN BE A LIST OR STRING

        if self.schema is not None:
            schema = self.schema

        sep = "','"

        if table_name:
            if isinstance(table_name, list) :
                table_name = "'{}'" .format(sep.join(table_name))
            else :
                table_name = "'{}'".format(table_name)

        if table_name:
            table_name = table_name.upper()

        query = """
                SELECT 
                t1.TABLE_SCHEMA AS SCHEMA_NAME, 
                t1.TABLE_NAME, 
                t2.NO_OF_COLS, 
                t1.TABLE_TYPE,
                CASE 
                   WHEN t1.TABLE_TYPE = 'BASE TABLE' THEN t1.ROW_COUNT ELSE 0 
                END AS NO_OF_ROWS,
                CASE 
                   WHEN t1.TABLE_TYPE = 'BASE TABLE' THEN  ((t1.BYTES ) / 1024/1024 ) ELSE 0 
                END AS SIZE_IN_MB,
                t1.LAST_ALTERED as LAST_UPDATED ,
                t1."COMMENT" as COMMENT 
                FROM {dbname}.INFORMATION_SCHEMA.TABLES t1
                INNER JOIN (
                                SELECT TABLE_NAME, TABLE_SCHEMA, COUNT(1) AS NO_OF_COLS
                                FROM {dbname}.INFORMATION_SCHEMA.COLUMNS
                                GROUP BY TABLE_NAME, TABLE_SCHEMA
                            ) t2
                ON t1.table_name=t2.table_name
                AND t1.TABLE_SCHEMA=t2.TABLE_SCHEMA
                WHERE 1=1
                """
        
        if table_name:
            query += " and t1.table_name in ({table_name}) "

        if self.schema:
            query += "and t1.TABLE_SCHEMA  = UPPER('{schema}')"

        query = query.format(schema=schema, table_name=table_name, dbname = self.dbname)

        df = self.executeQuery(query, limit=None)

        return df

    def getTableRelationships(self, table_name, bi_directional = False):
        table_name = table_name.upper()
        query = """
            select 
                fk_tco.table_name as table_name,
                '' AS col_name,
                pk_tco.table_name as ref_table_name,
                '' as ref_col_name  
                from {dbname}.information_schema.referential_constraints rco
                join {dbname}.information_schema.table_constraints fk_tco 
                    on fk_tco.constraint_name = rco.constraint_name
                    and fk_tco.constraint_schema = rco.constraint_schema
                join information_schema.table_constraints pk_tco
                    on pk_tco.constraint_name = rco.unique_constraint_name
                    and pk_tco.constraint_schema = rco.unique_constraint_schema
                where pk_tco.table_name= '{table_name}'
                OR 
                fk_tco.table_name= '{table_name}'
        """

        if self.schema:
            sub_qry = " and table_schema = UPPER('{schema}')"
            query = query.format(dbname = self.dbname, table_name=table_name, schema=sub_qry)
        else:
            query = query.format(dbname = self.dbname, table_name=table_name, schema="")

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
            target_encloser = ''
        ):

        mrgstmt = MergeStatement(
            source_table=src_table_name,
            target_table=tgt_table_name,
            on_condition=on_condition,
            matched_mapping=matched_mapping,
            non_matched_mapping=non_matched_mapping,
            on_match=on_match,
            on_not_match=on_not_match,
            filter_condition=filter_condition,
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

    def getSqlAlchemyDtype(self, src_df, target_tbl_name, src_target_mapping):
        dtypedict = {}
        target_col_dtype, col_dtype_len = self.getTableColumnDtypes(target_tbl_name)
        for sourceColumnName, sourceColumnType in zip(src_df.columns, src_df.dtypes):

            if sourceColumnName in src_target_mapping:
                targetMappedColumn = src_target_mapping[sourceColumnName]
                # getting target column name mapped with source

                if targetMappedColumn != '' or targetMappedColumn is not None:
                    targetColumnDataType = target_col_dtype[targetMappedColumn]
                    trgtColDTypeLen = col_dtype_len[targetMappedColumn]

                    if targetColumnDataType in ('TEXT', 'STR', 'VARCHAR', 'LONG VARCHAR'):
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.VARCHAR(length=int(trgtColDTypeLen))})
                    elif targetColumnDataType in ('NVARCHAR'):
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.NVARCHAR(length=int(trgtColDTypeLen))})
                    elif targetColumnDataType == 'INT':
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.BIGINT})
                    elif targetColumnDataType in ('FLOAT', 'DEC', 'NUMERIC', 'NUMBER'):
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.FLOAT})
                    elif targetColumnDataType in ('BOOLEAN', 'BOL'):
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.BOOLEAN})
                    elif targetColumnDataType in ('TIMESTAMP', 'DATE', 'DAT', 'TMS'):
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.DATETIME})

            else:
                if "object" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.VARCHAR})
                elif "int" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.BIGINT})
                elif "float" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.FLOAT})
                elif "bool" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.BOOLEAN})
                elif "date" in str(sourceColumnType):
                    dtypedict.update({sourceColumnName: sqlalchemyTypes.DATETIME})
        return dtypedict

    def getTableIndexDetails(self, tablename):
        pass

    def dq_dashboard_data_freshness_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select DATE(%(col_name)s) date_col,count (1) row_added from %(table_name)s
            where DATE(%(col_name)s) between '%(from_date)s' and  '%(to_date)s'
            group by DATE(%(col_name)s) order by 1 asc
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})

        return query

    def dq_dashboard_data_modify_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select DATE(%(col_name)s) date_col ,count (1) row_added from %(table_name)s 
            where DATE(%(col_name)s) between '%(from_date)s' and '%(to_date)s'
            group by %(col_name)s order by 1 asc
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})

        return query

    def dq_dashboard_data_delete_query(self, tablename, columnname, fromdate, todate):
        query = '''
            select DATE(%(col_name)s) date_col ,count (1) row_added from %(table_name)s
            where %(col_name)s is not null and  DATE(%(col_name)s) between '%(from_date)s' and '%(to_date)s'
            group by DATE(%(col_name)s) order by 1 asc
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate})

        return query

    def dq_dashboard_stk_query(self, tablename, columnname, fromdate, todate, datasources_col_name):
        query = '''
            select DATE(%(col_name)s) date_col,IFNULL(%(datasources_col_name)s, 'Other') src, count (1) row_added from %(table_name)s
            where DATE(%(col_name)s) between '%(from_date)s' and  '%(to_date)s'
            group by DATE(%(col_name)s),2 order by 1 asc
        ''' % ({"col_name": columnname, "table_name": tablename, "from_date": fromdate, "to_date": todate,
                "datasources_col_name": datasources_col_name})

        return query

    def get_connection_statement(self):
        statement = f"snowflake://{self.user}:{self.password}@{self.host}/{self.dbname}"
        return statement

    def get_incremental_columns(self, table_name, **others):
        try:
            self.connect()
            # added distinct for unique data
            query = """SELECT DISTINCT c.COLUMN_NAME as "COLUMN_NAME",
                c.DATA_TYPE as "DATA_TYPE"
                FROM			
                {dbname}.INFORMATION_SCHEMA.COLUMNS AS c
                LEFT JOIN
                {dbname}.INFORMATION_SCHEMA.TABLES t
                    ON c.TABLE_NAME = t.TABLE_NAME
                    AND c.TABLE_SCHEMA = t.TABLE_SCHEMA
                LEFT JOIN 
                {dbname}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS ff
                ON c.TABLE_NAME = ff.TABLE_NAME AND c.TABLE_SCHEMA = ff.TABLE_SCHEMA
                WHERE 
                (
                (upper(c.DATA_TYPE) like ('TIME%') 
                or upper(c.DATA_TYPE)  like 'DATE%')
                or 
                (	(upper(ff.CONSTRAINT_TYPE) = 'PRIMARY KEY' 
                        or upper(ff.CONSTRAINT_TYPE) = 'UNIQUE KEY') 
                    AND upper(c.data_type) IN ( 'INT', 'NUMBER')
                )
             )
             AND c.TABLE_NAME = '{table_name}'""".format(dbname = self.dbname, table_name=table_name)
            if self.schema:
                query += " AND c.TABLE_SCHEMA= UPPER('" + self.schema + "')"

            self.cursor.execute(query)
            desc_value = [d[0] for d in self.cursor.description]
            desc = [item.upper() for item in desc_value]
            results = pd.DataFrame([dict(zip(desc, res)) for res in self.cursor.fetchall()])

            self.close()
        except Exception as e:
            self.close()
            print(e)
            raise
        return results

    def fetch_delta_columns(self, table_name,**others):
        try:
            df = None
            inc_columns = self.get_incremental_columns(table_name)
            full_table_name = table_name
            if self.schema is not None:
                full_table_name = '"{}"."{}"'.format(self.schema, full_table_name)

            index = 0
            for index, row in inc_columns.iterrows():
                sub_query = """ 
                    SELECT 
                        '{col_name}' AS COLUMN_NAME,
                        '{data_type}' as DATA_TYPE,
                        COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                        COUNT(1) AS TOTAL_COUNT, 
                        NVL(SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END),0) AS NULL_CNT 
                    FROM {table_name}
                """

                sub_query = sub_query.format(
                    col_name = row["COLUMN_NAME"],
                    table_name = full_table_name,
                    data_type = row['DATA_TYPE']
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
            upd_clause = 'update "{}"'.format(tbl_name)
        else:
            upd_clause = 'update "{}"."{}"'.format(self.schema, tbl_name)

        for con in on_condition:
            where_clause += condition.format(col_name = '"' + con["target_col"] + '"', value = row[con["source_col"]])

        for key in matched_mapping.keys():
            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += merge_stmt_dict["SNOWFLAKE"]["set"]["NULL"].format(col_name = '"' + key + '"', value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += merge_stmt_dict["SNOWFLAKE"]["set"][col_type].format(col_name = '"' + key + '"', value = row[matched_mapping[key]].replace("'", "''"))                            
                else :
                    set_clause += merge_stmt_dict["SNOWFLAKE"]["set"][col_type].format(col_name = '"' + key + '"', value = row[matched_mapping[key]])                         

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
            inst_clause = f'INSERT INTO "{tbl_name}" '
        else:
            inst_clause = f'INSERT INTO "{self.schema}"."{tbl_name}"'

        inst_clause += "({cols}) VALUES ({values})"

        cols = ""
        values = ""
        for key in non_matched_mapping.keys():
            cols += f'"{key}",'

            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if not pd.isnull(row[non_matched_mapping[key]]):
                if isinstance(row[non_matched_mapping[key]], str):
                    values += merge_stmt_dict["SNOWFLAKE"]["insert"][col_type].format(value = row[non_matched_mapping[key]].replace("'", "''")) + ","
                else:
                    values += merge_stmt_dict["SNOWFLAKE"]["insert"][col_type].format(value = row[non_matched_mapping[key]]) + ","
            else :
                values += merge_stmt_dict["SNOWFLAKE"]["insert"]["NULL"].format(value = 'null') + ","

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection)
