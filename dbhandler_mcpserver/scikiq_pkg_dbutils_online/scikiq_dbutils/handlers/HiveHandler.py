
#PYTHON PACKAGES
import pandas as pd
import uuid
import json
from collections import OrderedDict
from pyhive import hive
from sqlalchemy import create_engine, types as sqlalchemyTypes
from pypika import Table, Field,JoinType,Order,Tables
from pypika import VerticaQuery
from pypika import PostgreSQLQuery
from pypika import functions as fn
from urllib.parse import quote

#CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.handlers.DBConnection import clsDBConnection, ViewCreationError, where_recursive_condition, where_condition,where_Colcondition, ins_stmt, set_stmt
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression

class clsHiveDB(clsDBConnection):
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
            self.schema = config["schema"]
        else :
            self.schema = None

        if "connection_type" in config :
            self.connection_type = config["connection_type"]
        else :
            self.connection_type = None      

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        return False                  

    def getConnectionType(self):
        if self.connection_type is None :
            return "SR"
        else :
            return self.connection_type

    def connect(self):
        resp = {}
        resp['resource_call'] = 'connect'
        try:
            self.connection = hive.Connection(host=self.host , port=self.port, username=self.user, password=self.password, auth="CUSTOM")
            self.cursor = self.connection.cursor()

            #callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsHiveDB,self).callConnectionAudit(resp)   
        except Exception as e:
            #callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsHiveDB,self).callConnectionAudit(resp)
            raise

    def close(self):
        if self.connection :
            self.connection.close()        

    def testConnection(self):
        resp = {}
        try:
            conn = hive.Connection(host=self.host , port=self.port, username=self.user, password=self.password, auth="CUSTOM")
            conn.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS
        except Exception as e:
            resp['msg'] = str(e)
            resp['error'] = 1

        #callConnectionAudit using for audit the record.
        super(clsHiveDB,self).callConnectionAudit(resp)

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
    
    def executeQueryOld(self, query, limit=None, manage_connection=False):
        results = None
        try : 
            if manage_connection:
                self.connect()
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

    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=10000):
        self.create_engine()
        for col in df.select_dtypes('O'):
            try:
                df[col] = df[col].str.replace(',', '')
                df[col] = df[col].str.replace('"', '')
                df[col] = df[col].str.replace('\\', '')
            except Exception as e:
                print(e)
        dtypedict = {}

        for sourceColumnName, sourceColumnType in zip(df.columns, df.dtypes):
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

        with self.engine_statement.connect() as connection:
            ## TODO: verify set schema command
            connection.execute("SET SEARCH_PATH TO " + self.schema)        
            df.to_sql(con=connection, name=tablename, dtype=dtypedict, if_exists=if_exists, index=False)        

        return df

    def get_all_tables(self, search=None, type=None, limit=None):
        self.connect()

        query = "SHOW TABLES"

        self.cursor.execute(query)
        results = self.cursor.fetchall()

        return results

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)

        query = "SHOW TABLES"

        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        # self.cursor.close()
        col_dtls = []
        for dataTable in results:
            dictDynamic = {}
            dataTable = list(dataTable)[0]
            dictDynamic["tablename"] = dataTable
            try:
                query = "DESCRIBE " + self.dbname + "." +  dataTable
                
                dictDynamic["columnname"] = pd.read_sql(query, con=self.connection).values.tolist()
            except Exception as e:
                print(e)
                dictDynamic["columnname"] = ""

            col_dtls.append(dictDynamic)
        self.close()
        return col_dtls

    def getTableColumns(self, tablename, type = ''):
        query = "SELECT COLUMN_NAME FROM SYSIBM.COLUMNS WHERE TABLE_CATALOG = '{}' AND TABLE_NAME = '{}'".format(self.dbname, tablename)  

        if self.schema:
            query += " AND TABLE_SCHEMA='{}'".format(self.schema)

        query += " ORDER BY COLUMN_NAME "       

        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()

        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        query = """
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                ORDINAL_POSITION, 
                CHARACTER_MAXIMUM_LENGTH, 
                DATA_TYPE_LENGTH, 
                NUMERIC_PRECISION,
                NUMERIC_SCALE, 
                '' AS COMMENT 
            FROM SYSIBM.columns 
            WHERE TABLE_CATALOG = '{}' 
            AND TABLE_NAME = '{}'
        """.format(self.dbname, tbl_name)

        if self.schema:
            query += " AND TABLE_SCHEMA = '{}'".format(self.schema)

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
        col_idx_lst = {}
        if config_details:
            #Get column key and alias name with list of vlaues
            for key, col_details in config_details.items():
                    for lst in col_details:
                        col_dict[key] = lst['alias']
                        col_lst.append(key)
            #Get column occurences of the data.
            for key, _ in col_dict.items():
                indices = [index for index, element in enumerate(col_lst) if element == key]
                col_idx_lst[key] = indices
        return col_idx_lst

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
                _query = VerticaQuery.from_(tbls[key])
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

            #Add column names which is derived/custom columns by user
            custom_column_names_dict = {}

            for key, value in columnnames.items():
                ## Change input pattern now value will be list
                for listItem in value:
                    ## if condition to handle json from build model
                    ## "dim_project0.projectid" : ""  ## alisa.colname : agg fun and
                    ## else condtion to handle json from ETL
                    ## "projectid":"SUM" ## colname:AGG fun
                    if "." in key:
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

                    
                    #Add custom column in the list.
                    if 'column_type' in  listItem.keys():
                        if listItem['column_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = listItem['expression']
                    elif 'col_type' in  listItem.keys():
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
                        col_idx_lst = self.getRenamesColMetricsDict(columnnames)
                        if key in __column_names_list:
                            if key in col_idx_lst:
                                for _index in col_idx_lst[key]:
                                    _query  = _query.orderby(_index+1,order=order_asc)

            elif isinstance(orderby,list):
                for dct in orderby:
                    for col,asc_desc in dct.items():
                        order_asc = Order.asc if asc_desc == 'ASC' else Order.desc
                        _query  = _query.orderby(col,order=order_asc)

                                    

        if filters is not None:
            if "rules" in filters:
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
                formatString = GetDBDateFormat.get_dbdate_format(db_type="HIVE", format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, formatString, _dict,db_type="HIVE")
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

        if "ORDER BY" in query:
            orderByClouse = query.split('ORDER BY')[1]
            orderByClouse = orderByClouse.replace('"' + alias + '".', "")
            query = query.split('ORDER BY')[0] + " ORDER BY " + orderByClouse

        selectClouse = query.split(' FROM ')[0]
        if filters is not None or groupby is not None:
            if len(filters) != 0:
                whereClouse = query.split('WHERE')[1]
            if groupby:
                if len(groupby) != 0 and len(filters) != 0:
                    whereClouse = whereClouse.split('GROUP BY')[0]
                    groupClouse = query.split('GROUP BY')[1]
                elif len(groupby) != 0:
                    groupClouse = query.split('GROUP BY')[1]

        # dateFormatPart = "To_Char(columnName,'colFormat') as alias"
        # dateFormatFilterPart = "To_Char(columnName,'colFormat')"
        stringFormatUpper = "UPPER(columnName) as alias"
        stringFormatLower = "LOWER(columnName) as alias"
        stringFormatInItCap = "INITCAP(columnName) as alias"
        for key, value in columnnames.items():
            for item in value:
                if "type" in item :
                    if item['type'].upper() == 'DATE' and item['format'] != '':
                        formatString = GetDBDateFormat.get_dbdate_format(db_type="HIVE", format_string=item['format'])
                        tempQuery = formatString
                        tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        # tempQuery=tempQuery+' AS '+'"'+item['alias']+'"'
                        selectClouse = selectClouse.replace('"' + key + '"', tempQuery, 1)
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "UPPER":
                        tempQuery = stringFormatUpper
                        tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        # tempQuery=tempQuery.replace('alias','"'+item['alias']+'"')
                        selectClouse = selectClouse.replace('"' + key + '"', tempQuery, 1)
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "LOWER":
                        tempQuery = stringFormatLower
                        tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        # tempQuery=tempQuery.replace('alias','"'+item['alias']+'"')
                        selectClouse = selectClouse.replace('"' + key + '"', tempQuery, 1)
                    elif item['type'].upper() == 'STRING' and item['format'].upper() == "INITCAP":
                        tempQuery = stringFormatInItCap
                        tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                        # tempQuery=tempQuery.replace('alias','"'+item['alias']+'"')
                        selectClouse = selectClouse.replace('"' + key + '"', tempQuery, 1)

        if filters is not None:
            if "rules" in filters:
                whereClouse = self.formatFilter(alias, filters["condition"], filters["rules"], whereClouse)

        if groupby is not None:
            if len(groupby) != 0:
                for key, value in groupby.items():
                    if "type" in value :
                        if (value['type'].upper() == 'DATE' and value['format'] != ''):
                            formatString = GetDBDateFormat.get_dbdate_format(db_type="HIVE", format_string=value['format'])
                            tempQuery = formatString
                            tempQuery = tempQuery.replace('columnName', '"' + alias + '"' + '.' + '"' + key + '"')
                            groupClouse = groupClouse.replace('"' + alias + '"' + '.' + '"' + key + '"', tempQuery, 1)

        if not self.schema:
            if filters is not None and groupby is not None:
                if len(filters) != 0 and len(groupby) == 0:
                    return selectClouse + ' FROM ' + '"' + table + '"' + ' ' + '"' + alias + '"' + ' WHERE ' + whereClouse
                elif len(filters) == 0 and len(groupby) != 0:
                    return selectClouse + ' FROM ' + '"' + table + '"' + ' ' + '"' + alias + '"' + ' GROUP BY ' + groupClouse
                elif len(filters) != 0 and len(groupby) != 0:
                    return selectClouse + ' FROM ' + '"' + table + '"' + ' ' + '"' + alias + '"' + ' WHERE ' + whereClouse + ' GROUP BY ' + groupClouse
                else:
                    return selectClouse + ' FROM ' + query.split('FROM')[1]
            else:
                return selectClouse + ' FROM ' + '"' + table + '"' + ' ' + '"' + alias + '"'
        else:
            if filters is not None and groupby is not None:
                if len(filters) != 0 and len(groupby) == 0:
                    return selectClouse + ' FROM "' + schema + '".' + '"' + table + '"' + ' ' + '"' + alias + '"' + ' WHERE ' + whereClouse
                elif len(filters) == 0 and len(groupby) != 0:
                    return selectClouse + ' FROM "' + schema + '".' + '"' + table + '"' + ' ' + '"' + alias + '"' + ' GROUP BY ' + groupClouse
                elif len(filters) != 0 and len(groupby) != 0:
                    return selectClouse + ' FROM "' + schema + '".' + '"' + table + '"' + ' ' + '"' + alias + '"' + ' WHERE ' + whereClouse + ' GROUP BY ' + groupClouse
                else:
                    return selectClouse + ' FROM ' + query.split('FROM')[1]
            else:
                return selectClouse + ' FROM ' + '"' + table + '"' + ' ' + '"' + alias + '"'

    def create_engine(self):
        # it requires pip install psycopg2
        self.engine_statement = create_engine(f'presto://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}')

    def get_connection_statement(self):
        statement = f"presto://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}"
        return statement

    def readTable(self, tbl_name, limit, **others):
        manage_connection = others.get("manage_connection", True)
        #TODO:For use of random_sample keyword see readTable function of vertica.
        if not self.schema:
            query = "SELECT * FROM " + tbl_name
        else:
            query = "SELECT * FROM " + self.schema + "." + tbl_name

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection = manage_connection)
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
        for sourceColumnName, sourceColumnType in zip(df.columns, df.dtypes):
            if sourceColumnName in mappedColumn:
                targetMappedColumn = mappedColumn[sourceColumnName]
                # getting target column name mapped with source
                if targetMappedColumn != '' or targetMappedColumn is not None:
                    targetColumnDetail = next(
                        filter(lambda x: (x[0] == targetMappedColumn), tableDetails['columnName']))
                    # split column datatype value in case of varchar to remove detail part of length
                    targetColumnDataType = targetColumnDetail[1].split('(')[0]
                    if targetColumnDataType == 'varchar' or targetColumnDataType == 'long varchar':
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.VARCHAR})
                    elif targetColumnDataType == 'int':
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.BIGINT})
                    elif targetColumnDataType == 'float':
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.FLOAT})
                    elif targetColumnDataType == 'boolean':
                        dtypedict.update({sourceColumnName: sqlalchemyTypes.BOOLEAN})
                    elif targetColumnDataType == 'timestamp' or targetColumnDataType == 'date':
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

    def updateTable(self, df, targetTableName, columnnames={}, filters=[], joins={}, fromTable=None, sameSchema=False,
                    tableDetails={}, sqlQuery=None):
        ##found_rows=False https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1

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
        #createColumnData =[{'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'} ..]


        sep = '`'
        sep_e = '`'
        createQuery = f'CREATE TABLE   {tableName}  '

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

        if self.schema is not None :
            full_table_name = '"' + self.schema + '".' + table_name        

        query = "SELECT DISTINCT '{col_name}' as values FROM {tbl_name} WHERE 1 = 1 ORDER BY '{col_name}' {order};".format(
            col_name = col_name,
            tbl_name = full_table_name,
            order = order
        )        
        results = pd.read_sql(query, self.connection)
        self.close()

        return results['values'].tolist()


    def getColumnsProfile(self, table_name, with_min_max = False, filter = None):        
        dfColDtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = table_name
        if self.schema is not None :
            full_table_name = self.schema + "." + full_table_name

        index = 0
        for row in dfColDtls :
            if row["DATA_TYPE"] in ['TIMESTAMP' ,'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'DOUBLE PRECISION', 'SMALLINT', 'INTEGER', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL', ] :
                sub_query = """ SELECT 
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE  , """
                if with_min_max :
                    sub_query += """  
                                    MAX({col_name}) AS MAX_VAL, 
                                    MIN({col_name}) AS MIN_VAL, """
                sub_query += """  COUNT(DISTINCT {col_name}) AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN({col_name} IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """
            else :
                sub_query = """ SELECT  
                                    '{col_name}' AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE , """
                if with_min_max :
                    sub_query += """  
                                    MAX(0) AS MAX_VAL, 
                                    MIN(0) AS MIN_VAL, """
                sub_query += """ 
                                    COUNT(DISTINCT {col_name}) AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN({col_name} IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """


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

    def getTableDetails(self, table_name, type = {}):     

        sep = "','"
        if isinstance(table_name, list) :
            table_name = "'{}'" .format(sep.join(table_name))
        else :
            table_name = "'{}'".format(table_name)           

        query = """SELECT  "" as TABLE_SCHEMA,
                "" AS TABLE_NAME, 
                0 as NO_OF_COLS,                
                4096 as SIZE_IN_MB,                 
                "" as TABLE_TYPE,                
                "" as TABLE_COMMENT,
                0 as NO_OF_ROWS,
                null as LAST_UPDATED  FROM """ + table_name + ";"

        df = self.executeQuery(query, limit = None)
        #df = pd.read_sql(query, con=self.connection)

        return  df


    def getTableRelationships(self, table_name, bi_directional = False):
        ##TODO: below query need to be updated for hive
        if bi_directional:
            query = """
                SELECT 
                REFTABNAME as table_name,
                '' as col_name,
                '' as ref_table_name,
                '' as ref_col_name 
                FROM SYSCAT.REFERENCES WHERE TABNAME = '{table_name}'
                UNION
                SELECT 
                TABNAME as table_name,
                '' as col_name,
                '' as ref_table_name,
                '' as ref_col_name 
                FROM SYSCAT.REFERENCES WHERE REFTABNAME = '{table_name}'        
            """         
        else :
            query = """
                SELECT 
                REFTABNAME as table_name,
                '' as col_name,
                '' as ref_table_name,
                '' as ref_col_name  
                FROM SYSCAT.REFERENCES WHERE TABNAME = '{table_name}'
            """         

        query = query.format(table_name = table_name)

        if self.schema :
            sub_qry = " AND TABSCHEMA  = '{schema}' AND REFTABSCHEMA = '{schema}' ".format(schema = self.schema)
            query += sub_qry

        df = self.executeQuery(query, limit = None)

        return  df      


    def getTableIndexDetails(self, tablename):
        pass

    def get_incremental_columns(self, table_name,**others):
        try:
            df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])
        except Exception as e:
            self.close()
            print(e)
            raise
        return df

    def fetch_delta_columns(self, table_name, **others):
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
            col_type = col_type.split("(")[0]           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += set_stmt["NULL"].format(col_name = key, value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += set_stmt[col_type].format(col_name = key, value = row[matched_mapping[key]].replace("'", "''"))                            
                else :
                    set_clause += set_stmt[col_type].format(col_name = key, value = row[matched_mapping[key]])                         

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
            col_type = col_type.split("(")[0]           

            if not pd.isnull(row[non_matched_mapping[key]]):
                if isinstance(row[non_matched_mapping[key]], str):
                    values += ins_stmt[col_type].format(value = row[non_matched_mapping[key]].replace("'", "''")) + ","
                else:
                    values += ins_stmt[col_type].format(value = row[non_matched_mapping[key]]) + ","
            else :
                values += ins_stmt["NULL"].format(value = 'null') + ","

        values = values.rstrip(",")
        cols = cols.rstrip(",")

        insert_stmt = inst_clause.format(cols = cols, values = values) 

        print("insert_stmt :",  insert_stmt)
        return self.executeSql(insert_stmt, manage_connection=manage_connection)
