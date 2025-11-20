# PYTHON PACKAGES
import pyathena 

import json
import uuid
import pandas as pd
from collections import OrderedDict
from pypika import Table, Field,JoinType,Tables
from pypika import MSSQLQuery
from pypika.dialects import MySQLQuery
from pypika import functions as fn
from pypika import Order
from urllib.parse import quote

#CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_dbutils.handlers.DBConnection import clsDBConnection, where_recursive_condition, where_condition, MergeStatement, ExecuteQueryException
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression



class clsAthena(clsDBConnection):

     
    def __init__(self, config):
        
        self.s3_staging_dir = config["hostname"]
        self.region_name = config["region_name"]
        self.aws_access_key_id = config["dbuser"]
        self.aws_secret_access_key = config["pwd"]
        self.work_group = None
        
        self.engine_statement = None
        self.connection = None
        self.cursor = None

        self.resource_key = None
        if("resource_key" in config):
            self.resource_key = config["resource_key"]
            
        self.schema = None
        if "schema" in config and config["schema"]:
            self.schema = config["schema"]

        self.dbname = None 
        if "dbname" in config :
            self.dbname = config["dbname"]

        self.db_type="ATHENA"       

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        return False                       

    def connect(self):
        resp = {}
        resp['resource_call'] = 'connect'
        
        try:
            self.connection = pyathena.connect(
                s3_staging_dir = self.s3_staging_dir,
                region_name = self.region_name, 
                aws_access_key_id = self.aws_access_key_id,
                aws_secret_access_key = self.aws_secret_access_key,
                work_group=self.work_group      
            )

            self.cursor = self.connection.cursor()

            #callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsAthena,self).callConnectionAudit(resp)   

        except Exception as e:
            #callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsAthena,self).callConnectionAudit(resp)
            raise

    def close(self):
        if self.cursor :
            self.cursor.close()

        if self.connection :
            self.connection.close()
        
    def testConnection(self):
        resp = {}
        
        try:
            db =pyathena.connect(
                s3_staging_dir = self.s3_staging_dir,
                region_name = self.region_name,
                aws_access_key_id = self.aws_access_key_id,
                aws_secret_access_key = self.aws_secret_access_key,
                work_group=self.work_group
            )

            db.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS   
        except pyathena.Error as e:
                print(e.args[0][0])
                if (e.args[0][0] == 18456) :
                    resp['error'] = 1
                    resp['msg'] = ScikiqMessages.MSG_INCORRECT_DB_CREDENTIALS
                elif(e.args[0][0] == 20009) :
                    resp['error'] = 1
                    resp['msg'] = ScikiqMessages.MSG_UNABLE_TO_CONNECT_DATA_SOURCE
                else :
                    resp['error'] = 1
                    resp['msg'] = str(e)
        except Exception as e:  
            resp['error'] = 1
            resp['msg'] = str(e)

        #callConnectionAudit using for audit the record.
        super(clsAthena,self).callConnectionAudit(resp)

        return resp

    def createView(self, view_name, sql_query):
        return False

    def executeQueryOld(self, query, limit=None, manage_connection=True):
        try:
            if manage_connection:
                self.connect()

            if limit is not None:
                if ";" in query :
                    query = query.replace(";", " limit " + str(limit) + ";")
                else :           
                    query = query +  " limit " + str(limit) + ";"

            results = pd.read_sql(query, self.connection) 

            if manage_connection:
                self.close()
            return results

        except Exception as e:
            if manage_connection:
                self.close()
            
            raise ExecuteQueryException(e)

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

    def executeInsertUpdate(self, tablename, df, if_exists='append', chunksize=10000,dtype={}):
        self.create_engine()
       
        df.to_sql(con = self.engine_statement,name= tablename, if_exists = if_exists, index = False, chunksize = chunksize, method = 'multi')

        return df

    def getAllTablesWithColumns(self, search):
        query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')"
        
        if(search):
            query += " AND TABLE_NAME LIKE '%{}%'".format(search) 
            
        if self.schema :        
            query += " AND TABLE_SCHEMA LIKE '%{}%'".format(self.schema)

        if self.dbname :        
            query += " AND TABLE_CATALOG = '{}'".format(self.dbname) 


        query += " ORDER BY TABLE_NAME"

        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        #self.cursor.close()
        dataDict = []
        for dataTable in results:
            dictDynamic = {}
            dataTable = list(dataTable)[0]
            dictDynamic["tablename"] = dataTable
            try:
                query = "SELECT COLUMN_NAME,DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}'".format(dataTable)
                
                if self.dbname :        
                     query += " AND TABLE_CATALOG = '{}'".format(self.dbname) 
                
                if self.schema : 
                    query += " AND TABLE_SCHEMA = '{}'".format(self.schema) 
                query += " ORDER BY COLUMN_NAME"
                dictDynamic["columnname"] =  pd.read_sql(query,con=self.connection).values.tolist()
            except Exception as e:
                print("getAllTablesWithColumns : Fetch Table column : " + str(e))          
                dictDynamic["columnname"] = ""        
            
            dataDict.append(dictDynamic)
        self.close()
        return dataDict

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        query = "SELECT TABLE_NAME, TABLE_TYPE, TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES WHERE 1=1"

        if include_view:
            query += " AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')"
        else:
            query += " AND TABLE_TYPE = 'BASE TABLE'"

        if search:
            query += " AND TABLE_NAME LIKE '%{}%'".format(search)         

        if self.schema:
            query += " AND TABLE_SCHEMA = '{}'".format(self.schema)

        if self.dbname :        
            query += " AND TABLE_CATALOG = '{}'".format(self.dbname) 
        
        query += " ORDER BY TABLE_NAME "
        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()

        return results

    def getTableColumns(self, tablename, type = ''):
        query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}'".format(tablename)

        if self.dbname :        
            query += " AND TABLE_CATALOG = '{}'".format(self.dbname) 

        if self.schema :        
            query += " AND TABLE_SCHEMA LIKE '%{}%'".format(self.schema)                

        query += " ORDER BY COLUMN_NAME"
        self.connect()
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()

        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        sort_on_position = others.get("sort_on_position", False)

        test_type= self.getTableDetails(table_name=tbl_name)
        t_type= test_type['TABLE_TYPE'][0]

        query = """SELECT 
                    cols.TABLE_SCHEMA as "TABLE_SCHEMA",
                    cols.TABLE_NAME as "TABLE_NAME", 
                    '{}' as "TABLE_TYPE",
                    cols.COLUMN_NAME as "COLUMN_NAME",
                    cols.DATA_TYPE as "DATA_TYPE",
                    cols.ORDINAL_POSITION as "ORDINAL_POSITION",
                    '' as "NUMERIC_PRECISION",
                    '' as "NUMERIC_SCALE",
                    cols.IS_NULLABLE as "IS_NULLABLE",
                    '' as "CHARACTER_MAXIMUM_LENGTH",
                    '' as "DATA_TYPE_LENGTH",
                    '' as "CHARACTER_MAX_LENGTH",
                    case when cols.COLUMN_COMMENT is null then '' else cols.COLUMN_COMMENT end as "COMMENT",
                    case when cols.COLUMN_DEFAULT is null then '' else cols.COLUMN_DEFAULT end as "COLUMN_DEFAULT",
                    '' as "COLUMN_LENGTH",
                    '' as "COLUMN_PRECISION",
                    '' as "COLUMN_CHARACTERSET",
                    '' as "CONSTRAINT_NAME",
                    '' as "REFERENCED_TABLENAME",
                    '' as "REFERENCED_COLUMNNAME",
                    '' as key_col
                FROM
                    INFORMATION_SCHEMA."COLUMNS" as cols
                    WHERE cols.TABLE_NAME = '{}'""".format(t_type,tbl_name) 

        if self.schema :        
            query += " AND TABLE_SCHEMA LIKE '%{}%'".format(self.schema) 
         
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
        renameDimMetricsColDict = OrderedDict()
        renameDimMetricsColLst = []
        colIndexDct = {}
        if config_details:
            #Get column key and alias name with list of vlaues
            for key, col_details in config_details.items():
                    for lst in col_details:
                        renameDimMetricsColDict[key] = lst['alias']
                        renameDimMetricsColLst.append(key)
            #Get column occurences of the data.
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
                alias =  tablename[tblName]

                if not self.schema:
                    tbls[alias] = Table(tblName, alias=alias.replace('"', ''))
                else:
                    tbls[alias] = Table(tblName, alias=alias.replace('"', ''), schema=self.schema)
                tblsName[alias] = tblName

        index = 0
        for key in tbls.keys():
            if index == 0:
                _query = MySQLQuery.from_(tbls[key])
            else :
                if tblsName[key] in joins:
                    joinType = joins[tblsName[key]]
                    if joinType == "inner" :
                        how=JoinType.inner
                    elif joinType == "right" :
                        how=JoinType.right
                    elif joinType == "left" :
                        how=JoinType.left
                    elif joinType == "full" :
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

                    ## if . found in column and but doesn't have table json format, raises error on eval
                    ## validation should be at front end level also
                    if "." in key and key.split(".")[0] in tbls:
                        key = key.split(".")
                        coltblName = key[0]
                        colName = key[1]
                        if value !='' :
                            #lstFields.append(Field(tbls[coltblName], agg_func[value](colName)))
                            lstFields.append( agg_func[value](eval('tbls[coltblName]' + "." + colName )).as_(listItem['alias']))
                        else :
                            if " as " in colName:
                                lstFields.append(Field(colName.split(" as ")[0] ,table= tbls[coltblName], alias = colName.split(" as ")[1]))
                            else:
                                lstFields.append(Field(f'"colName"',table=f'"tbls[coltblName]"',alias=listItem['alias']))
                    else :
                        if str(listItem['agg']).upper() =='DISTINCT COUNT' :
                            lstFields.append(fn.Count(Field(key),alias=listItem['alias']).distinct())
                        elif listItem['agg'] == 'total_record_count' :
                            lstFields.append(agg_func["COUNT"]('*',alias=listItem['alias']))
                        elif listItem['agg'] !='' :
                            lstFields.append(agg_func[str(listItem['agg']).upper()](Field(key),alias=listItem['alias']))
                        else:                                
                            lstFields.append(Field(key))

                    #Add custom column in the list.
                    if 'column_type' in  listItem.keys():
                        if listItem['column_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = listItem['expression']
                    elif 'col_type' in  listItem.keys():
                        if listItem['col_type'] in ['custom', 'derived']:
                            custom_column_names_dict[key] = listItem['expression']                            


        #_query = _query.select(*(cols))
        if distinct:
            _query = _query.select(*lstFields).distinct()
        else :
            _query = _query.select(*lstFields)

        if limit  is not None:
            if isinstance(limit,list) and len(limit)==1:
                limit = int(limit[0])
                _query = _query.limit(limit)
            elif isinstance(limit,str):
                limit = int(limit)
                _query = _query.limit(limit)     
            elif isinstance(limit,int): ## limit is int
                _query = _query.limit(limit)
        #add offset
        if offset  is not None:
            _query = _query.offset(offset)

        if orderby is not None :
            if isinstance(orderby,dict): ## deprecated in new version 2021/08/31

                try:
                    order_asc = Order.asc if orderby['direction'] == 'ASC' else Order.desc 
                    _query  = _query.orderby(*orderby['columns'],order=order_asc)
                except Exception:
                    __column_names_list = columnnames.keys()
                    for key, value in orderby.items():                        
                        order_asc = Order.asc if value == 'ASC' else Order.desc
                        colIndexDct = self.getRenamesColMetricsDict(columnnames)
                        if key in __column_names_list:
                            if key in colIndexDct:
                                for _index in colIndexDct[key]:
                                    _query  = _query.orderby(_index+1,order=order_asc)
            elif isinstance(orderby,list):
                for dct in orderby:
                    for col,asc_desc in dct.items():
                        order_asc = Order.asc if asc_desc == 'ASC' else Order.desc
                        _query  = _query.orderby(col,order=order_asc)


        if filters is not None:
            if "rules" in filters:
                _query=_query.where(where_recursive_condition(filters["condition"],filters["rules"]))

        if groupby is not None:
            for key ,value in groupby.items():
                _query = _query.groupby(key)
        
        query=_query.get_sql(with_alias=False).replace('`', '"')
        query = self.formatQuery(tablename, groupby, query, filters, columnnames)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)
        
        return query
    

    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                format_string = GetDBDateFormat.get_dbdate_format(db_type="ATHENA",format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, format_string, _dict,db_type="ATHENA")
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
                        format_string=GetDBDateFormat.get_dbdate_format(db_type="ATHENA",format_string=item['format'])
                        temp_qry = format_string
                        temp_qry = temp_qry.replace('columnName','"'+alias+'"'+'.'+'"'+key+'"')
                        temp_qry = temp_qry.replace('alias', '"' + item.get('alias', '') + '"')
                        temp_qry = temp_qry.replace('colFormat',format_string)
                        select_clause=select_clause.replace('"'+key+'"',temp_qry,1)                

        if filters is not None and "rules" in filters:
            where_clause = self.formatFilter(alias,filters["condition"],filters["rules"], where_clause)        

        if groupby and len(groupby)!=0:                
            for key,value in groupby.items():
                if "type" in value :
                    if(value['type'].upper()=='DATE' and  value['format']!=''):
                        format_string = GetDBDateFormat.get_dbdate_format(db_type="ATHENA",format_string=value['format'])
                        temp_qry = format_string
                        temp_qry = temp_qry.replace('columnName','"'+alias+'"'+'.'+'"'+key+'"')
                        temp_qry = temp_qry.replace('alias','"'+key+'"')
                        temp_qry = temp_qry.replace('colFormat',format_string)
                        group_clause = group_clause.replace('"'+alias+'"'+'.'+'"'+key+'"',temp_qry,1)
        
        table_name = '"' + table + '"'
        if self.schema :
            table_name =  '"' + self.schema +  '".' + table_name

        ## schema not used in this function as schema already added while creating connection
        if len(filters) > 0:
            select_clause += ' FROM {table_name} "{alias}" WHERE {where_clause}'.format(
                table_name = table_name, 
                alias = alias, 
                where_clause = where_clause
            )  
        else :
            select_clause += ' FROM {table_name} "{alias}" '.format(table_name = table_name, alias = alias)              
        
        if groupby and len(groupby)> 0:
            select_clause += ' GROUP BY {}'.format(group_clause)

        return select_clause

    
    def create_engine(self):
        self.engine_statement = f'awsathena+rest://{quote(self.aws_access_key_id)}:{quote(self.aws_secret_access_key)}@athena.{self.region_name}.amazonaws.com/{self.schema}?s3_staging_dir={self.s3_staging_dir}'

    def get_connection_statement(self):
        statement = f'awsathena+rest://{quote(self.aws_access_key_id)}:{quote(self.aws_secret_access_key)}@athena.{self.region_name}.amazonaws.com/{self.schema}?s3_staging_dir={self.s3_staging_dir}'
        return statement

    def getUpdateQuery(self,targetTableName,columnnames={},filters=[],joins={},inputTableReplica='temp_table'):
        filters =  None if filters == [{"from":"","column": "","operator": "","value": ""}] or filters == [] else filters
        test, final = Tables(inputTableReplica, targetTableName)
        _query = MSSQLQuery.update(final)

        if joins:
            _query = _query.join(test,JoinType.inner)
            joinslist = []
            for k,v in joins.items():
                joinslist.append(Field(v,table=final) == Field(k,table=test))
            strss = ''
            strs = 'joinslist'
            for i in range(len(joinslist)):
                s = "["+ str(i) + "]" 
                word = strs + s
                if i+1 != len(joinslist):
                    word += " & "
                strss += word    
            _query = _query.on(eval(strss))

        if columnnames:
            if joins:
                for k,v in columnnames.items():
                    _query = _query.set(Field(v,table = final), Field(k,table = test))
            else:
                for k,v in columnnames.items():
                    _query = _query.set(Field(v,table = final), k)

        if filters is not None:
            for filt in filters:
                ##TODO
                node_from = filt['from']
                wherew = filt['column']
                if node_from =="source": ## test side 
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
    def updateTable(self,df,targetTableName,columnnames={},filters=[],joins={},fromTable= None,sameSchema = False,tableDetails={},sqlQuery=None):
        ##found_rows=False https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1        
        inputTableReplica = f'temp_table'+str(uuid.uuid1()) if fromTable is None else fromTable
        inputTableReplica = inputTableReplica.replace('-','_')
        
        sql= self.getUpdateQuery(targetTableName,columnnames,filters,joins,inputTableReplica)
        self.create_engine()
        if inputTableReplica not in sql:
            with self.engine_statement.begin() as conn:     # TRANSACTION
                conn.execute(sql)
        else:
            try:
                df.to_sql(inputTableReplica, self.engine_statement, if_exists='replace')
                with self.engine_statement.begin() as conn:     # TRANSACTION
                    conn.execute(sql)
                    conn.execute("DROP TABLE IF EXISTS "+ inputTableReplica)
            except Exception as e:                    
                    with self.engine_statement.begin() as conn:   # TRANSACTION   
                        sql=f'DROP TABLE IF EXISTS "'+ inputTableReplica+'"'                
                        conn.execute(sql) 
                    
                    raise Exception(e)
        return df, sql

    def readTable(self, tbl_name, limit, **others):

        manage_connection = others.get("manage_connection", True)
        full_table_name = '"' + tbl_name +  '"'
        if self.schema :
            full_table_name =  '"' + self.schema + '".' + full_table_name        
        #TODO:For use of random_sample keyword see readTable function of vertica.
        query = "SELECT * FROM " +  full_table_name 

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection=manage_connection)
        res["df_text"] = None 

        return res                       

    def truncateTable(self,table_name):
        query = f'DELETE FROM "{self.schema}"."{table_name}";'
        self.executeSql(query)    
    
    def generateCreateTableScript(self, tableDetails):
        query = "CREATE External TABLE " + tableDetails["tableName"] + "("

        lenCol = len(tableDetails["colDetails"])
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
                
            if 'default' in x :
                if len(x["default"]) > 0 :
                    query += " DEFAULT " + x["default"]
                
            if(index < lenCol) :
                query += ","     
            else :
                ## Add FK contraints
                if 'fk' in tableDetails :
                    lenFK = len(tableDetails["fk"])
                    fkIndex = 0
                    fkQuery = ","
                    for y in tableDetails["fk"] :
                        fkIndex += 1
                        #CONSTRAINT `daas_assets_created_by_4ce65b17_fk_daas_user_id` FOREIGN KEY (`created_by`) REFERENCES `daas_user` (`id`),
                        fkQuery += " CONSTRAINT " + y['keyName'] + " FOREIGN KEY (`" + y['columnFK'] + "`) REFERENCES `" + y['table'] + "` (`" + y['column'] + '`)'
                        if(fkIndex < lenFK) :
                            fkQuery += ","
                            
                    query += fkQuery                                            
                query += ")"
                query += " LOCATION " + "'" + self.s3_staging_dir + "'"    
        return query
    
    def generateCreateTableScriptETL(self, tableDetails):
        tableName = tableDetails["tableName"]
        createColumnData = tableDetails['createColumnData']

        """
        createColumnData =[{'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'} ..]
        """
        sep = '`'
        sep_e = '`'
        createQuery = f'CREATE External TABLE   {tableName}  '

        lst_cols = []
        if len(createColumnData)>0:
            for inpDict in createColumnData:
                col = inpDict['target_column']
                datatype = inpDict['datatype']
                col_query = f' {sep}{col}{sep_e} {datatype}'
                lst_cols.append(col_query)

        cols_query = ",".join(lst_cols)
        query = f'''{createQuery} ( {cols_query} ) '''
        query += " LOCATION " + "'" + self.s3_staging_dir + "'" 

        return query


    def createTable(self, tableDetails,etl=False):
        if etl:
            query = self.generateCreateTableScriptETL(tableDetails)
            return self.executeSql(query)
        else:
            query = self.generateCreateTableScript(tableDetails)

        self.executeSql(query)

        return True        

    def getColumnLOV(self, table_name, col_name, order = 'ASC'):

        full_table_name = '"' + table_name + '"'
        if self.schema :
            full_table_name = '"' + self.schema + '".' + full_table_name

        self.connect()
        query = 'SELECT DISTINCT "{col_name}" as value FROM {tbl_name} WHERE 1 = 1 ORDER BY "{col_name}" {order};'.format(
            col_name = col_name,
            tbl_name = full_table_name,
            order = order
        )

        results = pd.read_sql(query, self.connection) 
        self.close()
        
        return results['value'].tolist()

    def getColumnsProfile(self, table_name, with_min_max = False, filter = None):        
        dfColDtls = self.getTableColumnsDetails(table_name, sort_on_position=True)

        full_table_name = '"' + table_name + '"'
        if self.schema :
            full_table_name = '"' + self.schema + '".' + full_table_name

        index = 0
        for row in dfColDtls :
            if row["DATA_TYPE"].upper() in ['TIMESTAMP', 'TEXT' ,'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'DOUBLE', 'DOUBLE PRECISION', 'SMALLINT', 'INT', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL' ] :
                sub_query = """ SELECT 
                                    "{col_name}" AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE, """
                if with_min_max :
                    sub_query += """  
                                    MAX("{col_name}") AS MAX_VAL, 
                                    MIN("{col_name}") AS MIN_VAL, """
                sub_query += """
                                    COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """
            else :
                sub_query = """ SELECT 
                                    "{col_name}" AS COLUMN_NAME, 
                                    '{data_type}' AS DATA_TYPE , """
                if with_min_max :
                    sub_query += """  
                                    MAX(0) AS MAX_VAL, 
                                    MIN(0) AS MIN_VAL, """
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

    def getTableDetails(self, table_name=None, type = {}):

        sep = "','"
        if table_name:
            if isinstance(table_name, list) :
                table_name = "'{}'" .format(sep.join(table_name))
            else :
                table_name = "'{}'".format(table_name)

        query = """
            select
                c.TABLE_SCHEMA,	
                c.TABLE_NAME,
                sub.no_of_cols as NO_OF_COLS,
                0 as  SIZE_IN_MB,
                TABLE_TYPE,
                TABLE_COMMENT,
                0 as NO_OF_ROWS,
                '' as LAST_UPDATED
            from information_schema.tables c
            inner join (
                select table_schema, table_name, COUNT(*) AS no_of_cols
                from information_schema.columns
                group by 1,2
            ) as sub 
                on c.table_name= sub.table_name  
                and c.table_schema = sub.table_schema
            where 1=1 
        """

        if table_name:
            query += " and  c.table_name in ({table_name})".format(table_name=table_name)
            
        query += " and c.table_schema = '{table_schema}'".format(table_schema=self.schema)

        query += """
        union

        select
            c.TABLE_SCHEMA,	
            c.TABLE_NAME,
            sub.no_of_cols as NO_OF_COLS,
            0 as  SIZE_IN_MB,
            'VIEW',
            '' AS TABLE_COMMENT,
            0 as NO_OF_ROWS,
            '' as LAST_UPDATED
        from information_schema.VIEWS c
        inner join (
            select table_schema, table_name, COUNT(*) AS no_of_cols
            from information_schema.columns
            group by 1,2
        ) as sub 
            on c.table_name= sub.table_name  
            and c.table_schema = sub.table_schema
        """

        if table_name:
            query += " and  c.table_name in ({table_name})".format(table_name=table_name)
            
        query += " and c.table_schema = '{table_schema}'".format(table_schema=self.schema)

        df = self.executeQuery(query, limit = None)
    
        return  df                


    def getTableRelationships(self, table_name, bi_directional = False):
        # query = """
        #     SELECT
        #         tr.name as table_name
        #     FROM 
        #         sys.foreign_keys fk 
        #     INNER JOIN 
        #         sys.tables tp  ON fk.parent_object_id = tp.object_id
        #     INNER JOIN 
        #         sys.tables tr ON fk.referenced_object_id = tr.object_id
        #     where  tp.name = '{table_name}' {schema}
        #     union
        #     SELECT
        #         tp.name as table_name
        #     FROM 
        #         sys.foreign_keys fk 
        #     INNER JOIN 
        #         sys.tables tp  ON fk.parent_object_id = tp.object_id
        #     INNER JOIN 
        #         sys.tables tr ON fk.referenced_object_id = tr.object_id
        #     where  tr.name = '{table_name}' {schema} 
        # """         

        # if self.schema :
        #     sub_qry = " and SCHEMA_NAME(tp.schema_id) = '{schema}' ".format(schema = self.schema)
        #     query = query.format(schema = sub_qry, table_name = table_name)
        # else :
        #     query = query.format(schema = "", table_name = table_name)            

        # df = self.executeQuery(query, limit = None)

        # return  df
        pass

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
        target_encloser = ''
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
            target_encloser = target_encloser
        )

        merge_query =mrgstmt.get_query()
        
        return merge_query+";"

    def getDropTableQuery(self,table_name):
        full_table_name = "`" + table_name + "`"
        if self.schema :
            full_table_name = "`" + self.schema + "`." + full_table_name    

        return  f"DROP TABLE {full_table_name}"

    def dropTable(self, table_name):
        query = self.getDropTableQuery(table_name)
        self.executeSql(query)    

    def getTableIndexDetails(self, tablename):
        query= '''
            select c.TABLE_SCHEMA as "TABLE_SCHEMA",
                c.TABLE_NAME as "TABLE_NAME", 
                c.COLUMN_NAME as "COLUMN_NAME",
                '' as "INDEX_NAME" ,
                '' as "INDEX_TYPE",
                c.ordinal_position as "SEQUENCE"
            from INFORMATION_SCHEMA.COLUMNS c 
            WHERE c.TABLE_CATALOG = '{}' AND c.TABLE_NAME = '{}'
        '''.format(self.dbname, tablename)     

        if self.schema:
            query += " AND c.TABLE_SCHEMA ='{}'".format(self.schema)
        
        df = self.executeQuery(query, limit = None)

        return  df  

    def dq_dashboard_data_freshness_query(self,tablename,columnname,fromdate,todate):
        query='''
            select CONVERT(date,%(col_name)s) date_col,count (1) row_added from %(table_name)s WITH(NOLOCK)
            where CONVERT(date,%(col_name)s) between '%(from_date)s' and  '%(to_date)s'  
            group by CONVERT(date,%(col_name)s) order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query

    def dq_dashboard_data_modify_query(self,tablename,columnname,fromdate,todate):
        query='''
            select CONVERT(date,%(col_name)s) date_col ,count (1) row_added from %(table_name)s WITH(NOLOCK)
            where CONVERT(date,%(col_name)s) between '%(from_date)s' and '%(to_date)s' 
            group by %(col_name)s order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query

    def dq_dashboard_data_delete_query(self,tablename,columnname,fromdate,todate):
        query='''
            select CONVERT(date,%(col_name)s) date_col ,count (1) row_added from %(table_name)s WITH(NOLOCK)
            where %(col_name)s is not null and  CONVERT(date,%(col_name)s) 
            between '%(from_date)s' and '%(to_date)s'
            group by CONVERT(date,%(col_name)s) order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query

    def dq_dashboard_stk_query(self,tablename,columnname,fromdate,todate,datasources_col_name):
        query='''
            select CONVERT(date,%(col_name)s) date_col,ISNULL(%(datasources_col_name)s, 'Other') src, count (1) row_added from %(table_name)s
            where CONVERT(date,%(col_name)s) between '%(from_date)s' and  '%(to_date)s' 
            group by CONVERT(date,%(col_name)s),ISNULL(%(datasources_col_name)s, 'Other') order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate,"datasources_col_name":datasources_col_name})
        
        return query

    def get_incremental_columns(self, table_name, **others):
        try:
            # added distinct for unique data
            query = """SELECT DISTINCT cols.COLUMN_NAME as "COLUMN_NAME",cols.DATA_TYPE 
		               FROM 
                       INFORMATION_SCHEMA.COLUMNS as cols 
                       WHERE 
                      (
                          (cols.data_type like ('time%') 
                          or cols.data_type like 'date%')
                          or cols.data_type in ('bigint','integer')
                
                      )
            
                      AND cols.TABLE_CATALOG = '{table_catalog}' 
                      AND cols.TABLE_NAME = '{table_name}'""".format(table_catalog = self.dbname, table_name=table_name)
            
            if self.schema:
                query += " AND cols.TABLE_SCHEMA= '" + self.schema + "'"
            
            self.connect()
            df = self.executeQuery(query, limit=None)
            df = df[['COLUMN_NAME', 'DATA_TYPE']]
        except Exception as e:
            self.close()
            print(e)
            raise
        return df

    def fetch_delta_columns(self, table_name,**others):
        df = None
        try:
            inc_cols = self.get_incremental_columns(table_name)
            
            full_table_name = '"' + table_name + '"'
            
            if self.schema is not None:
                full_table_name = '"' + self.schema + '".' + full_table_name
            
            index = 0
            for index, row in inc_cols.iterrows():
                sub_query = """ 
                    SELECT 
                        '{col_name}' AS COLUMN_NAME,
                        '{data_type}' as DATA_TYPE,
                        COUNT(DISTINCT "{col_name}") AS UNQ_VAL, 
                        COUNT(1) AS TOTAL_COUNT, 
                        COALESCE(SUM(CASE WHEN("{col_name}" IS NULL) THEN 1 ELSE 0 END),0) AS NULL_CNT 
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
                df_dates = df.loc[(df['DATA_TYPE'].str.upper().str.contains('TIME*|DATE*'))]
                
                if df_dates.empty:
                    df_dates = df_dates[df_dates['UNQ_VAL'] == df_dates['UNQ_VAL'].max()]
                    
                df_int = df.loc[df['DATA_TYPE'].str.contains('bigint|integer')]
                
                if df_int.empty:
                    df_int = df_int.loc[
                        df_int['UNQ_VAL'] == df_int['TOTAL_COUNT']]

                df = pd.concat([df_int, df_dates], axis=0)
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
            upd_clause = 'update "{}" '.format(tbl_name)
        else:
            upd_clause = 'update "{}"."{}" '.format(self.schema, tbl_name)    

        for con in on_condition:
            where_clause += condition.format(col_name = '"' +  con["target_col"] + '"', value = row[con["source_col"]])

        for key in matched_mapping.keys():
            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += merge_stmt_dict["SQLSERVER"]["set"]["NULL"].format(col_name = '"' + key + '"', value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += merge_stmt_dict["SQLSERVER"]["set"][col_type].format(col_name = '"' + key + '"', value = row[matched_mapping[key]].replace("'", "''"))                            
                else :
                    set_clause += merge_stmt_dict["SQLSERVER"]["set"][col_type].format(col_name = '"' + key + '"', value = row[matched_mapping[key]])                         

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
                    values += merge_stmt_dict["SQLSERVER"]["insert"][col_type].format(value = row[non_matched_mapping[key]].replace("'", "''")) + ","
                else:
                    values += merge_stmt_dict["SQLSERVER"]["insert"][col_type].format(value = row[non_matched_mapping[key]]) + ","
            else :
                values += merge_stmt_dict["SQLSERVER"]["insert"]["NULL"].format(value = 'null') + ","

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
            -- template update 
            UPDATE i 
            SET i."{tgt_col}" = i2."{src_col}" 
            FROM "{target_tbl}" i
            JOIN "{src_tbl}" i2 ON i."{tgt_col}" = i2."{src_col}"
            WHERE 1=1	

            -- where condition template
            AND {src_tgt_alias}.`{col}` {opr} {val}`
        '''

        main_tmpl = '''
            UPDATE i
            SET {set_stmt}
            FROM "{target_tbl}" i
            JOIN "{src_tbl}" i2 
            ON {on_clause}
            WHERE 1=1 {where_condition}
        '''

        on_condition_tmpl = ''' i."{tgt_col}"= i2."{src_col}" '''

        on_clause = self.get_on_condition(
            on_condition_tmpl, 
            on_condition=on_condition, 
            target_tbl=tgt_table_name
        )

        fltr_condition_tmpl = ''' AND {src_tgt_alias}."{col}" {opr} {val}'''      
        where_clause = self.get_filter_condition(
            filter_condition_tmpl=fltr_condition_tmpl,
            filter_condition=filter_condition,
            src_alias="i2",
            tgt_alias="i"
        )

        ## get source col list
        set_stmt_template = '''i."{tgt_col}" = i2."{src_col}"'''
        set_stmt = self.set_stmt_forupdate(set_stmt_template, matched_mapping)

        qry = main_tmpl.format(
            target_tbl = tgt_table_name,
            set_stmt = set_stmt,
            src_tbl = src_table_name,
            where_condition = where_clause,
            on_clause=on_clause
        )

        return qry