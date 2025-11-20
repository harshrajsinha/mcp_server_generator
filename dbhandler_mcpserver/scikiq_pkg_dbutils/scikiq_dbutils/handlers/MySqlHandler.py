# PYTHON PACKAGES
import MySQLdb  ## MySQL

import pandas as pd
import uuid
import os
import json
from collections import OrderedDict
from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine,types as sqlalchemyTypes
from pypika import Table, Field,JoinType,Order
from pypika import Tables
from pypika.dialects import MySQLQuery
from pypika import functions as fn
from urllib.parse import quote

# CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.date_format import GetDBDateFormat
from scikiq_utils.file.fileFactory import FileFactory as ff
from scikiq_dbutils.handlers.DBConnection import clsDBConnection, ViewCreationError, where_recursive_condition, where_condition
from scikiq_dbutils.handlers.DataTypeConnectionMapping import merge_stmt_dict
from scikiq_dbutils.utils import remove_double_quotes, generateCustomColumnExpression


class UpdateMySQLException(BaseException):
    pass


class clsMySqlDB(clsDBConnection):
    """
        Usage:

    """
    def __init__(self, config):

        self.__ssl = False
        self.__ssh = False
        self.__ssl_cert_path = ""
        self.__ssl_key_path = ""
        self.__ssl_ca_path = ""

        self.__ssh_key_path = None
        self.__ssh_host = None
        self.__ssh_user = None
        self.__ssh_port = None

        self.resource_key = None
        if("resource_key" in config):
            self.resource_key = config["resource_key"]

        if "pem_path" in config and len(config["pem_path"]) > 0 :
            self.__ssl = True
            self.__ssl_ca_path = config["pem_path"]            
        elif "connectivity_mechanism" in config :
            if config["connectivity_mechanism"] == "S" :
                self.__ssl = True
                
                resource_key = config["resource_key"]
                if resource_key == "temp" :
                    self.__ssl_key_path = config["ssl_key_path"]
                    self.__ssl_cert_path = config["ssl_cert_path"]
                    self.__ssl_ca_path = config["ssl_ca_path"]
                else :
                    app_config = config["app_config"]
                    
                    file_obj = ff.get_object_file(app_config, use_dask = 0)
                    file_obj.connect()

                    root_path = os.path.dirname(__file__)

                    path_resource = os.path.join(root_path, resource_key)
                    path_ssl = os.path.join(path_resource, "ssl")

                    self.__ssl_key_path = os.path.join(path_ssl, "ssl_key.pem")
                    self.__ssl_cert_path = os.path.join(path_ssl, "ssl_cert.pem")
                    self.__ssl_ca_path = os.path.join(path_ssl, "ssl_ca.pem")

                    if not os.path.isdir(root_path + "/" + resource_key):
                        os.mkdir(root_path + "/" + resource_key)

                    if not os.path.isdir(root_path + "/" + resource_key + "/ssl" ):
                        os.mkdir(root_path + "/" + resource_key + "/ssl")                        

                    try :
                        ssl_key = file_obj.read_file( resource_key + "/ssl/ssl_key")
                        ssl_key_file = ssl_key.read()                
                        with open(self.__ssl_key_path, 'wb') as f:
                            f.write(ssl_key_file)    
                    except Exception as e :
                        print(e)
                        self.__ssl_key_path = ""

                    try :                        
                        ssl_cert = file_obj.read_file( resource_key + "/ssl/ssl_cert")
                        ssl_cert_file = ssl_cert.read()                
                        with open(self.__ssl_cert_path, 'wb') as f:
                            f.write(ssl_cert_file)                       
                    except Exception as e :
                        print(e)
                        self.__ssl_cert_path = ""

                    try :
                        ssl_ca = file_obj.read_file( resource_key + "/ssl/ssl_ca")                        
                        ssl_ca_file = ssl_ca.read()                
                        with open(self.__ssl_ca_path, 'wb') as f:
                            f.write(ssl_ca_file)
                    except Exception as e :
                        print(e)
                        self.__ssl_ca_path = ""
            elif config["connectivity_mechanism"] == "SSH":
                self.__ssh = True

                resource_key = config.get("resource_key", None)
                if  resource_key is None:
                    self.__ssh_key_path = config["ssh_key_path"]
                    self.__ssh_host = config["ssh_host"]
                    self.__ssh_user = config["ssh_user"]
                    self.__ssh_port = int(config["ssh_port"])

                else:
                    app_config = config["app_config"]
                    
                    file_obj = ff.get_object_file(app_config, use_dask = 0)
                    file_obj.connect()

                    root_path = os.path.dirname(__file__)

                    path_resource = os.path.join(root_path, resource_key)
                    path_ssh = os.path.join(path_resource, "ssh")

                    self.__ssh_key_path = os.path.join(path_ssh, "ssh_key.pem")

                    if not os.path.isdir(root_path + "/" + resource_key):
                        os.mkdir(root_path + "/" + resource_key)

                    if not os.path.isdir(root_path + "/" + resource_key + "/ssh" ):
                        os.mkdir(root_path + "/" + resource_key + "/ssh")  

                    try :
                        ssh_key = file_obj.read_file( resource_key + "/ssh/ssh_key")
                        ssh_key_file = ssh_key.read()                
                        with open(self.__ssh_key_path, 'wb') as f:
                            f.write(ssh_key_file)    
                    except Exception as e :
                        print(e)
                        self.__ssh_key_path = ""
                    
                    self.__ssh_host = config["ssh_host"]
                    self.__ssh_user = config["ssh_user"]
                    self.__ssh_port = int(config["ssh_port"])


        self.host = config["hostname"]
        self.port = config["port"]
        self.dbname = config["dbname"]
        self.user = config["dbuser"]
        self.password = config["pwd"]
        
        
        self.engine_statement = None
        self.connection = None
        self.cursor = None

        self.schema = None        
        if "schema" in config:
            self.schema = config["schema"]

        self.connection_type = None     
        if "connection_type" in config :
            self.connection_type = config["connection_type"]

        self.db_type="MYSQL"

    def update_column_comment(self, tbl_name, col_name, comment,**others):
            success = True
            results = self.getTableColumns(tbl_name)
            try:
                self.connect()
                if comment:
                    qry = ""
                    for row in results:
                        if row[0] == col_name:
                            col_name = row[0]
                            data_type = row[1]
                            qry = """ 
                                ALTER TABLE `{dbname}`.`{table_name}`
                                MODIFY COLUMN `{column_name}` {data_type} NULL COMMENT '{comment}';
                            """.format(
                                dbname = self.dbname,
                                table_name = tbl_name,
                                column_name = col_name,
                                data_type = data_type,
                                comment = comment
                            )
                            break
                else:
                    qry = "" 
                   
                    for row in results:
                        if row[0] == col_name:
                            col_name = row[0]
                            data_type = row[1]
                            qry = """
                                ALTER TABLE `{dbname}`.`{table_name}`
                                MODIFY COLUMN `{column_name}` {data_type} NULL;
                            """.format(
                                dbname = self.dbname,
                                table_name = tbl_name,
                                column_name = col_name,
                                data_type = data_type
                            )
                            break
                self.executeSql(qry)
            except Exception as e :
                self.close()
                print(e)
                success = False
            return success                    

    def getConnectionType(self):
        if self.connection_type is None :
            return "SR"
        else :
            return self.connection_type

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'
            
            if self.__ssl :
                self.connection = self.sslConnection()
            elif self.__ssh:
                self.connection = self.sshConnection()
            else :            
                self.connection = MySQLdb.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    passwd=self.password,
                    db=self.dbname,
                    connect_timeout=108000  # timeout of the data base and 108000 means 3 hours
                )

            self.cursor = self.connection.cursor()

            #callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsMySqlDB,self).callConnectionAudit(resp)   

        except Exception as e:
            #callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsMySqlDB,self).callConnectionAudit(resp)
            raise

    def close(self):
        if self.cursor :
            self.cursor.close()

        if self.connection :
            self.connection.close()

        # Stop the SSH tunnel if it's been started
        if hasattr(self, '__ssh_server') and self.__ssh_server:
            self.__ssh_server.stop()


    def sslConnection(self):
        ssl = {"ssl":{}}
        ## if ca file 
        if self.__ssl_ca_path :
            ssl["ssl"]["ca"] = self.__ssl_ca_path
        
        if self.__ssl_cert_path:
            ssl["ssl"]["cert"] = self.__ssl_cert_path

        if self.__ssl_key_path:
            ssl["ssl"]["key"] = self.__ssl_key_path

        db = MySQLdb.connect(
            host = self.host, 
            user = self.user, 
            passwd = self.password, 
            db = self.dbname,                    
            ssl=ssl
        )

        return db

    def sshConnection(self):
        #importing here to isolate the import in the case of ssh connection only
        from sshtunnel import SSHTunnelForwarder

        if self.__ssh_key_path and self.__ssh_host and self.__ssh_user and self.__ssh_port:
            
            self.__ssh_server = SSHTunnelForwarder(
                (self.__ssh_host,self.__ssh_port),  
                ssh_username=self.__ssh_user,  
                ssh_pkey=self.__ssh_key_path, 
                remote_bind_address=(self.host, self.port) 
            )


            self.__ssh_server.start()

            #in case of azure server we need to send the username in this manner in the format user@host. 
            # Connect to the database through the tunnel
            db = MySQLdb.connect(
                host='127.0.0.1',  # Connect to the local end of the tunnel
                user=self.user,  # Updated username with hostname for Azure
                passwd=self.password, 
                port=self.__ssh_server.local_bind_port,  # Local port to which the SSH tunnel is bound
                db=self.dbname                    
            )

            return db


    def testConnection(self):
        resp = {}
        try:
            if self.__ssl:
                db = self.sslConnection()
            elif self.__ssh:
                db = self.sshConnection()
            else :              
                db = MySQLdb.connect(
                    host = self.host,
                    port = self.port,
                    user = self.user,
                    passwd = self.password,
                    db = self.dbname,
                    connect_timeout = 10800  # timeout of the data base and 108000 means 3 hours
                )
            db.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS   
        except MySQLdb.Error as e :
            resp['error'] = 1
            if e.args[0] == 1045 :
                resp['msg'] = ScikiqMessages.MSG_INCORRECT_DB_CREDENTIALS
            elif e.args[0] == 3159 :
                resp['msg'] = ScikiqMessages.MSG_USE_SSL_FOR_CONNECTION
            else :
                resp['msg'] = e.args[1]
        except Exception as e:  
            resp['error'] = 1
            resp['msg'] = str(e)

        #callConnectionAudit using for audit the record.
        super(clsMySqlDB,self).callConnectionAudit(resp)

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
    
    def executeQueryOld(self, query, limit=None, manage_connection = True):
        results = None
        try : 
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
        except Exception as e :
            if manage_connection:
                self.close()
            print(e)
            raise            


        return results

    def executeSql(self, query,value=None, manage_connection=True):
        b_success = 0
        msg = ScikiqMessages.MSG_SUCCESS
        x = -1
        try:
            if manage_connection:
                self.connect()
            if value is not None:
                self.cursor.execute(query,value)
            else:
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
    
    def executeInsertUpdate(self, tablename, df, if_exists='replace',chunksize=1000,dtype={}):
        self.create_engine()

        dtypedict = {}

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
                else:  ## including object
                    mx_length = self.maxLengthColumn(df[src_col_name])
                    dtypedict.update({src_col_name: sqlalchemyTypes.VARCHAR(length=mx_length)})
        else:
            dtypedict = dtype

        df.to_sql(con=self.engine_statement,dtype=dtypedict,name=tablename, if_exists=if_exists, index=False,chunksize = chunksize,method='multi')
        return df

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()

        query = "SELECT TABLE_NAME, TABLE_TYPE, TABLE_SCHEMA FROM INFORMATION_SCHEMA.TABLES "

        if include_view == True:
            query += " WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW') "
        else:
            query += " WHERE TABLE_TYPE = 'BASE TABLE' "

        if search:
            query += " AND TABLE_NAME LIKE '%{}%'".format(search)

        query += " AND TABLE_SCHEMA = '{}'".format(self.dbname)

        query += " ORDER BY TABLE_NAME "

        self.cursor.execute(query)
        results = self.cursor.fetchall()
        self.close()
        return results

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)

        data_dict = []
        self.connect()
        query = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{}'".format(self.dbname)
        query += " AND TABLE_NAME = '{}' ORDER BY COLUMN_NAME "
        for dataTable in results:
            dictDynamic = {}
            dataTable = list(dataTable)[0]
            dictDynamic["tablename"] = dataTable
            self.cursor.execute(query.format(dataTable))
            dictDynamic["columnname"] = self.cursor.fetchall()
            data_dict.append(dictDynamic)

        self.close()
        return data_dict

    def getTableColumns(self, tablename, type = ''):
        query = """
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE   
            TABLE_SCHEMA = '{}' 
            AND TABLE_NAME = '{}' 
            ORDER BY TABLE_NAME ASC
        """.format(self.dbname, tablename)

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
                    cols.NUMERIC_PRECISION as "NUMERIC_PRECISION",
                    cols.NUMERIC_SCALE as "NUMERIC_SCALE",
                    cols.IS_NULLABLE as "IS_NULLABLE",
                    cols.CHARACTER_MAXIMUM_LENGTH as "CHARACTER_MAXIMUM_LENGTH",
                    cols.NUMERIC_PRECISION as "DATA_TYPE_LENGTH",
                    COALESCE(
                        cols.CHARACTER_OCTET_LENGTH,
                        cols.CHARACTER_MAXIMUM_LENGTH, 
                        cols.DATETIME_PRECISION,
                        concat(cols.NUMERIC_PRECISION,',',COALESCE(cols.NUMERIC_SCALE,0))
                    ) as "CHARACTER_MAX_LENGTH",
                    case when cols.COLUMN_COMMENT is null then '' else cols.COLUMN_COMMENT end as "COMMENT",
                    case when cols.COLUMN_DEFAULT is null then '' else cols.COLUMN_DEFAULT end as "COLUMN_DEFAULT", 
                    case when  upper(cols.COLUMN_KEY) = 'PRI' then 1 else 0 end as "IS_PRIMARYKEY",
                    case when  upper(cols.COLUMN_KEY) = 'UNI' then 1 else 0 end as "IS_UNIQUEKEY",
                    case when  upper(cols.COLUMN_KEY) = 'MUL' then 1 else 0 end as "IS_NONUNIQUEKEY",
                    case when lower(cols.EXTRA) = 'auto_increment' then 1 else 0 end as "AUTO_INCREMENT",
                    case 
                            when cols.character_maximum_length is not null
                                then cols.character_maximum_length
                            when cols.DATETIME_PRECISION is not null
                                then cols.DATETIME_PRECISION
                            else cols.numeric_precision 
                    end as "COLUMN_LENGTH",
                    case 
                        when cols.NUMERIC_SCALE > 0 
                            then cols.NUMERIC_SCALE
                        else
                            ''
                    end as "COLUMN_PRECISION",
                    case when cols.CHARACTER_SET_NAME is null then '' else cols.CHARACTER_SET_NAME end as "COLUMN_CHARACTERSET",
                    case when links.CONSTRAINT_NAME  is null then '' else links.CONSTRAINT_NAME  end as "CONSTRAINT_NAME",
                    case when links.referenced_table_name  is null then '' else links.referenced_table_name end as "REFERENCED_TABLENAME", 
                    case when links.referenced_column_name  is null then '' else links.referenced_column_name end as "REFERENCED_COLUMNNAME",
                    case when cols.COLUMN_KEY = '' then 'no' else 'yes' end as key_col
                FROM 
                    INFORMATION_SCHEMA.`COLUMNS` as cols
                LEFT JOIN INFORMATION_SCHEMA.`KEY_COLUMN_USAGE` AS links
                    ON cols.TABLE_NAME = links.TABLE_NAME 
                    AND cols.COLUMN_NAME = links.COLUMN_NAME
                    AND cols.table_schema = links.table_schema 
                    WHERE cols.TABLE_SCHEMA = '{}' 
                    AND cols.TABLE_NAME = '{}'""".format(t_type,self.dbname, tbl_name)

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
                tbls[alias] = Table(tblName, alias = alias)
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
                            lstFields.append( agg_func[value](eval('tbls[coltblName]' + "." + colName )))
                        else :
                            if " as " in colName:
                                lstFields.append(Field(colName.split(" as ")[0] ,table= tbls[coltblName], alias = colName.split(" as ")[1]))
                            else:
                                lstFields.append(Field(colName,table=tbls[coltblName]))
                    else :
                        if str(listItem['agg']).upper() =='DISTINCT COUNT' :
                            lstFields.append(fn.Count(Field(key),alias=listItem['alias']).distinct())
                        elif listItem['agg'] == 'total_record_count' :
                            lstFields.append(agg_func["COUNT"]('*',alias=listItem['alias']))
                        elif listItem['agg'] !='' :
                            lstFields.append(agg_func[str(listItem['agg']).upper()](Field(key),alias=listItem['alias']))
                        else:                                
                            lstFields.append(Field(key).as_(listItem['alias']))

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
                except:
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
        
        query=_query.get_sql(with_alias=True)
        query = self.formatQuery(tablename, groupby, query, filters, columnnames)
        query, expression_column_names_lst = self.createCustomColumnExpression(query, custom_column_names_dict)
        query = remove_double_quotes(query, expression_column_names_lst)
        
        return query
    
    def createCustomColumnExpression(self, query, custom_column_names_dict):
        expression_column_names_lst = []
        if custom_column_names_dict:
            for _key, _dict in custom_column_names_dict.items():
                action_type = _dict['action_type']
                format_string = GetDBDateFormat.get_dbdate_format(db_type="MYSQL", format_string=action_type)
                column_expression = generateCustomColumnExpression(action_type, format_string, _dict,db_type="MYSQL")
                if(not column_expression):
                    column_expression =  _dict['expression_value']
                query = query.replace(_key, column_expression, 1)
                expression_column_names_lst.append(column_expression)
        return (query, expression_column_names_lst)



    def formatQuery(self,tablename,groupby=None,query=None,filters=None,columnnames=None):

        if not (filters or groupby):
            return query

        for key in tablename.keys():
            table = key                
            alias =  tablename[key]
        selectClouse=query.split(' FROM ')[0]
        if filters is not None or groupby is not None:
            if  len(filters) !=0:
                 whereClouse=query.split('WHERE')[1]
            if groupby:
                if len(groupby)!=0  and  len(filters) !=0 :
                    whereClouse=whereClouse.split('GROUP BY')[0]
                    groupClouse=query.split('GROUP BY')[1]
                elif  len(groupby)!=0 :
                    groupClouse=query.split('GROUP BY')[1]
       
        # dateFormatPart="date_format(columnName,'colFormat') as alias"
        # dateFormatFilterPart="date_format(columnName,'colFormat')"
        stringFormatUpper="UPPER(columnName) as alias"
        stringFormatLower="LOWER(columnName) as alias"
        for key, value in columnnames.items():
            for item in value :
                if "type" in item :
                    if item['type'].upper()=='DATE':                 
                        format_string=GetDBDateFormat.get_dbdate_format(db_type="MYSQL",format_string=item['format'])
                        tempQuery=format_string
                        tempQuery=tempQuery.replace('columnName','`'+alias+'`'+'.'+'`'+key+'`')
                        selectClouse=selectClouse.replace('`'+key+'`',tempQuery,1)  
                    elif item['type'].upper()=='STRING' and  item['format'].upper()=="UPPER":
                        tempQuery=stringFormatUpper
                        tempQuery=tempQuery.replace('columnName','`'+alias+'`'+'.'+'`'+key+'`')
                        selectClouse=selectClouse.replace('`'+key+'`',tempQuery,1)  
                    elif item['type'].upper()=='STRING' and  item['format'].upper()=="LOWER":
                        tempQuery=stringFormatLower
                        tempQuery=tempQuery.replace('columnName','`'+alias+'`'+'.'+'`'+key+'`')
                        selectClouse=selectClouse.replace('`'+key+'`',tempQuery,1)
        
        if filters is not None: 
            if "rules" in filters:
                whereClouse=self.formatFilter(alias,filters["condition"],filters["rules"],whereClouse)           
                     
        if groupby is not None:
            if len(groupby)!=0:                
                for key,value in groupby.items():
                    if "type" in value :
                        if(value['type'].upper()=='DATE'):
                            format_string=GetDBDateFormat.get_dbdate_format(db_type="MYSQL",format_string=value['format'])
                            tempQuery=format_string
                            tempQuery=tempQuery.replace('columnName','`'+alias+'`'+'.'+'`'+key+'`')
                            groupClouse=groupClouse.replace('`'+alias+'`'+'.'+'`'+key+'`',tempQuery,1)

        if filters is not None and groupby is not None:
            if len(filters) !=0 and  len(groupby)==0:
                return selectClouse+' FROM '+ '`'+table+'`'+' '+'`'+alias+'`'+' WHERE '+whereClouse 
            elif len(filters) ==0 and len(groupby)!=0:
                return selectClouse+' FROM '+ '`'+table+'`'+' '+'`'+alias+'`'+' GROUP BY '+groupClouse
            elif len(filters) !=0 and len(groupby)!=0:
                return selectClouse+' FROM '+ '`'+table+'`'+' '+'`'+alias+'`'+' WHERE '+whereClouse+' GROUP BY '+groupClouse
            else:
                return selectClouse+' FROM '+query.split('FROM')[1]
        else:
            return selectClouse+' FROM '+ '`'+table+'`'+' '+'`'+alias+'`'

    def create_engine(self):
        driver = 'mysql+pymysql'
        self.url = URL.create(driver, self.user, self.password, self.host, self.port, self.dbname)

        connect_args = {}
        
        if self.__ssl:
            ssl_args = {}
            if self.__ssl_ca_path:
                ssl_args["ssl_ca"] = self.__ssl_ca_path
            if self.__ssl_cert_path:
                ssl_args["ssl_cert"] = self.__ssl_cert_path
            if self.__ssl_key_path:
                ssl_args["ssl_key"] = self.__ssl_key_path
            connect_args['ssl'] = ssl_args

        elif self.__ssh:
            from sshtunnel import SSHTunnelForwarder

            ssh_server = SSHTunnelForwarder(
                (self.__ssh_host, self.__ssh_port),
                ssh_username=self.__ssh_user,
                ssh_pkey=self.__ssh_key_path,
                remote_bind_address=(self.host, self.port)
            )
            ssh_server.start()
            self.host = '127.0.0.1'
            self.port = ssh_server.local_bind_port
            self.user = f"{self.user}@{self.host.split('.')[0]}"  # For Azure compatibility

        self.engine_statement = create_engine(self.url, echo=False, pool_pre_ping=True, future=True, connect_args=connect_args)
    
    def get_connection_statement(self):
        statement = f"mysql+pymysql://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/{self.dbname}"
        return statement

    def getUpdateQuery(self,targetTableName,columnnames={},filters=[],joins={},inputTableReplica='temp_table',sqlQuery=None):
       
        filters =  None if filters == [{"from":"","column": "","operator": "","value": ""}] or filters == [] else filters

        test, final = Tables(inputTableReplica, targetTableName)
        _query = MySQLQuery.update(final)

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
                    col_n = f"`{targetTableName}`.`{v}`"
                    _query = _query.set(Field(col_n,table = final), Field(k,table = test))
            else:
                for k,v in columnnames.items():
                    _query = _query.set(Field(v,table = final),k)

        if filters is not None:
            for index, filt in enumerate(filters):
                ##TODO
                node_from = filt['from']
                wherew = filt['column']
                if node_from =="source": ## test side 
                    where = f"{inputTableReplica}`.`{wherew}" 
                else:
                    ## final side
                    where = f"{targetTableName}`.`{wherew}"
                try:
                    where_val = eval(filt['value'])
                except:
                    where_val = filters[index]['value']

                where_op = filt['operator']
                _query = where_condition(where=where, query=_query, where_val=where_val, where_op=where_op)
        if sqlQuery is None:
            return _query.get_sql()
        else:
            return self.updateQueryUsingSubQuery(_query.get_sql(),inputTableReplica,sqlQuery)
    
    def updateQueryUsingSubQuery(self,updateQuery,inputTableReplica,subQuery):
        
        getJoinPart =updateQuery.split('JOIN')[1]
        getJoinOnPart=getJoinPart.split('ON')[1]
        newUpdateQuery=updateQuery.split('JOIN')[0] +' JOIN ('+subQuery+') '+inputTableReplica+ ' ON '+ getJoinOnPart 
        print(newUpdateQuery)  
        return newUpdateQuery

    # added tableDetails parameter to pass table columns data type
    def updateTable(self,df,targetTableName,columnnames={},filters=[],joins={},fromTable= None,sameSchema = False,tableDetails={},sqlQuery=None):
        ##found_rows=False https://stackoverflow.com/questions/12827519/how-do-i-get-the-number-of-rows-affected-with-sql-alchemy?noredirect=1&lq=1
        
        inputTableReplica = f'temp_table'+str(uuid.uuid1()) if fromTable is None else fromTable
        inputTableReplica=inputTableReplica.replace('-','_')
        print('Temp table used for update',inputTableReplica)
        sql= self.getUpdateQuery(targetTableName,columnnames,filters,joins,inputTableReplica,sqlQuery=sqlQuery)
        sql = sql.replace("``", "`")
        self.create_engine()
        if sameSchema:
            with self.engine_statement.begin() as conn:     # TRANSACTION
                t = conn.execute(sql)
                print("matched rows = {}".format(t.rowcount))
                
        elif inputTableReplica not in sql:
            with self.engine_statement.begin() as conn:     # TRANSACTION
                t = conn.execute(sql)
                print("matched rows = {}".format(t.rowcount))
        else:
                df.to_sql(inputTableReplica, self.engine_statement, if_exists='replace')
                res = self.executeSql(sql)
                if res["status"] == 0:
                    raise Exception(res["msg"])
                self.executeSql(f'DROP TABLE IF EXISTS "{inputTableReplica}"'  )

        return df,sql

    def readTable(self, tbl_name, limit, **others):
        manage_connection = others.get("manage_connection", True)
        #TODO:For use of random_sample keyword see readTable function of vertica.
        query = "SELECT * FROM " +  tbl_name

        res = {}
        res["df"] = self.executeQuery(query, limit, manage_connection = manage_connection)
        res["df_text"] = None 

        return res           

    def truncateTable(self,table_name):
        query = f'TRUNCATE TABLE {table_name} ;'
        self.executeSql(query)   

    def generateCreateTableScript(self, tableDetails):
        query = "CREATE TABLE " + tableDetails["tableName"] + "("

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
                
            if x['nullable'] == "true" :
                query += " NULL"
            else :
                query += " NOT NULL"      
                
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
        query = "SELECT DISTINCT `{col_name}` as 'values' FROM {tbl_name} WHERE 1 = 1 ORDER BY `{col_name}` {order};".format(
            col_name = col_name,
            tbl_name = table_name,
            order = order
        )          
        results = pd.read_sql(query, self.connection) 
        self.close()
        
        return results['values'].tolist()

    def getColumnsProfile(self, table_name, with_min_max = False, filter = None):        
        dfColDtls = self.getTableColumnsDetails(table_name, sort_on_position=True)
        df = pd.DataFrame()
        full_table_name = table_name

        index = 0
        for row in dfColDtls :
            if row["DATA_TYPE"].upper() in ['TIMESTAMP', 'TEXT' ,'NUMERIC', 'FLOAT', 'BIGINT', 'DATE', 'DECIMAL', 'DOUBLE', 'DOUBLE PRECISION', 'SMALLINT', 'INT', 'BIGINT', 'DECFLOAT', 'DECIMAL', 'REAL' ] :
                sub_query = """ SELECT 
                                    "{col_name}" AS COLUMN_NAME, 
                                    "{data_type}" AS DATA_TYPE, """
                if with_min_max :
                    sub_query += """  
                                    MAX(`{col_name}`) AS MAX_VAL, 
                                    MIN(`{col_name}`) AS MIN_VAL, """
                sub_query += """
                                    COUNT(DISTINCT `{col_name}`) AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN(`{col_name}` IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """
            else :
                sub_query = """ SELECT 
                                    "{col_name}" AS COLUMN_NAME, 
                                    "{data_type}" AS DATA_TYPE , """
                if with_min_max :
                    sub_query += """  
                                    MAX(0) AS MAX_VAL, 
                                    MIN(0) AS MIN_VAL, """
                sub_query += """
                                    COUNT(DISTINCT `{col_name}`) AS UNQ_VAL, 
                                    COUNT(1) AS TOTAL_COUNT, 
                                    SUM(CASE WHEN(`{col_name}` IS NULL) THEN 1 ELSE 0 END) AS NULL_CNT """

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
                round(((data_length + index_length) / 1024 / 1024), 2) as  SIZE_IN_MB,
                TABLE_TYPE,
                TABLE_COMMENT,
                IFNULL(c.TABLE_ROWS, 0) as NO_OF_ROWS,
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
            
        query += " and c.table_schema = '{table_schema}'".format(table_schema=self.dbname)

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
            
        query += " and c.table_schema = '{table_schema}'".format(table_schema=self.dbname)

        df = self.executeQuery(query, limit = None)
    
        return  df

    def getTableRelationships(self, table_name, bi_directional = False):

        if bi_directional :
            query = """
                SELECT 
                    `TABLE_NAME` as table_name, 
                    `COLUMN_NAME` as col_name,
                    `REFERENCED_TABLE_NAME` as ref_table_name,
                    `REFERENCED_COLUMN_NAME` as ref_col_name 
                FROM `information_schema`.`KEY_COLUMN_USAGE` 
                WHERE `CONSTRAINT_SCHEMA` = '{db}' 
                    AND `REFERENCED_TABLE_NAME` = '{table_name}' 
                
                UNION
                
                SELECT 
                    `REFERENCED_TABLE_NAME` as table_name, 
                    `REFERENCED_COLUMN_NAME` as col_name,
                    `TABLE_NAME` as ref_table_name,
                    `COLUMN_NAME` as ref_col_name                     
                FROM `information_schema`.`KEY_COLUMN_USAGE` 
                WHERE `CONSTRAINT_SCHEMA` = '{db}' 
                    AND `TABLE_NAME` = '{table_name}' 
                    AND `REFERENCED_TABLE_NAME` IS NOT NULL
            """         
        else :
            query = """
                SELECT 
                    `TABLE_NAME` as table_name,
                    `COLUMN_NAME` as col_name,                     
                    `REFERENCED_TABLE_NAME` as ref_table_name, 
                    `REFERENCED_COLUMN_NAME` as ref_col_name
                FROM `information_schema`.`KEY_COLUMN_USAGE` 
                WHERE `CONSTRAINT_SCHEMA` = '{db}' 
                    AND `TABLE_NAME` = '{table_name}' 
                    AND `REFERENCED_TABLE_NAME` IS NOT NULL
            """          

        query = query.format(db = self.dbname, table_name = table_name)

        df = self.executeQuery(query, limit = None)

        return  df
       
    def getDropTableQuery(self,table_name):
        return  f"DROP TABLE IF EXISTS {table_name}"

    def dropTable(self, table_name):
        query = self.getDropTableQuery(table_name)
        self.executeSql(query)     

    def getTableIndexDetails(self, tablename):
        query = """
            select s.TABLE_SCHEMA AS "TABLE_SCHEMA",
                s.TABLE_NAME as "TABLE_NAME", 
                s.COLUMN_NAME as "COLUMN_NAME",
                s.INDEX_NAME as "INDEX_NAME",
                s.INDEX_TYPE as "INDEX_TYPE",
                s.SEQ_IN_INDEX as "SEQUENCE"
                from information_schema.STATISTICS s 
                WHERE s.TABLE_SCHEMA = '{}' 
                AND s.TABLE_NAME = '{}'""".format(self.dbname, tablename)   

        df = self.executeQuery(query, limit = None)

        return  df  

    def dq_dashboard_data_freshness_query(self,tablename,columnname,fromdate,todate):
        query='''
            select CONVERT(%(col_name)s , date) date_col, count(1) row_added from %(table_name)s  
            where CONVERT(%(col_name)s, date) between '%(from_date)s' and '%(to_date)s' 
            group by 1 order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query

    def dq_dashboard_data_modify_query(self,tablename,columnname,fromdate,todate):
        query='''
            select CONVERT(%(col_name)s , date) date_col, count(1) row_added from %(table_name)s  
            where CONVERT(%(col_name)s, date) between '%(from_date)s' and '%(to_date)s'
            group by 1 order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query

    def dq_dashboard_data_delete_query(self,tablename,columnname,fromdate,todate):
        query='''
            select CONVERT(%(col_name)s , date) date_col ,count(1) row_added from %(table_name)s
            where CONVERT(%(col_name)s , date) is not null and CONVERT(%(col_name)s , date)
            between '%(from_date)s' and '%(to_date)s' 
            group by 1 order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate})
        
        return query

    def dq_dashboard_stk_query(self,tablename,columnname,fromdate,todate,datasources_col_name):
        query='''
            select CONVERT(%(col_name)s , date) date_col,IFNULL(%(datasources_col_name)s, 'Other')  src, count(1) row_added from %(table_name)s
            where CONVERT(%(col_name)s , date) between '%(from_date)s' and '%(to_date)s'
            group by 1,2 order by 1 asc
        '''% ({"col_name":columnname,"table_name":tablename,"from_date":fromdate,"to_date":todate,"datasources_col_name":datasources_col_name})
        
        return query

    def get_incremental_columns(self, table_name, **others):
        try:
            # added distinct for unique data
            query = """
                SELECT DISTINCT
                    cols.COLUMN_NAME as "COLUMN_NAME",
                    cols.DATA_TYPE as "DATA_TYPE"
                FROM INFORMATION_SCHEMA.`COLUMNS` as cols
                WHERE (
                    cols.IS_NULLABLE = 'NO' 
                    or (cols.IS_NULLABLE = 'YES' 
                         and cols.COLUMN_DEFAULT IS NOT NULL
                        )
                )
                AND (
                    (cols.DATA_TYPE LIKE 'date%' OR cols.DATA_TYPE LIKE 'time%')
                    OR ((upper(cols.COLUMN_KEY) = 'PRI' OR  upper(cols.COLUMN_KEY) = 'UNI')
                        AND cols.DATA_TYPE = 'int')
                    )                                            
                    AND cols.TABLE_NAME = '{table_name}' """.format(table_name=table_name)
            
            if self.dbname:
                query += " AND cols.TABLE_SCHEMA = '" + self.dbname + "'"
            
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
            df=None
            full_table_name = "`" + table_name + "`"
            if self.dbname is not None:
                full_table_name = "`" + self.dbname + "`" + "." + full_table_name
            index = 0
            for index, row in inc_columns.iterrows():
                sub_query = """ 
                    SELECT 
                        '{col_name}' AS COLUMN_NAME,
                        '{DATA_TYPE}' as DATA_TYPE,
                        COUNT(DISTINCT `{col_name}`) AS UNQ_VAL, 
                        COUNT(1) AS TOTAL_COUNT, 
                        COALESCE(SUM(CASE WHEN(`{col_name}` IS NULL) THEN 1 ELSE 0 END),0) AS NULL_CNT 
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
                    df_integer = df_integer.loc[df_integer['UNQ_VAL'] == df_integer['TOTAL_COUNT']]
                df = pd.concat([df_integer, df_date], axis=0)
                df = df[['COLUMN_NAME', 'DATA_TYPE']]
            else:
                df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])
            return df
        except Exception as e:
            self.close()
            print(e)
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
            select_clause = ' select count(1) as CNT from `{}` '.format(tbl_name)
        else:
            select_clause = ' select count(1) as CNT from `{}`.`{}` '.format(self.schema, tbl_name)        

        for con in on_condition:
            where_clause += condition.format(col_name = '`' + con["target_col"] + '`', value = row[con["source_col"]])

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
            upd_clause = ' update `{}` '.format(tbl_name)
        else:
            upd_clause = ' update `{}`.`{}` '.format(self.schema, tbl_name)        

        for con in on_condition:
            where_clause += condition.format(col_name = '`' + con["target_col"] + '`', value = row[con["source_col"]])

        for key in matched_mapping.keys():
            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if pd.isnull(row[matched_mapping[key]]):
                set_clause += merge_stmt_dict["MYSQL"]["set"]["NULL"].format(col_name = '`' + key + '`', value = 'null')                            
            else :
                if isinstance(row[matched_mapping[key]], str):
                    set_clause += merge_stmt_dict["MYSQL"]["set"][col_type].format(col_name = '`' + key + '`', value = row[matched_mapping[key]].replace("'", "''"))                            
                else :
                    set_clause += merge_stmt_dict["MYSQL"]["set"][col_type].format(col_name = '`' + key + '`', value = row[matched_mapping[key]])                           

        set_clause = set_clause.rstrip(",")
        qry = upd_clause + set_clause + where_clause

        print("upd_stmt :", qry)
        return self.executeSql(qry, manage_connection = manage_connection)

    def insert_row(self, tbl_name, row, non_matched_mapping, col_details, manage_connection):

        '''
            INSERT INTO SCIKIQ_DEV.ORDERS
            (ID, CUSTOMER_ID, PRODUCT_ID, QUANTITY, PRICE, TOTAL_AMOUNT, STORE_ID, CREATED_DATE, CREATED_BY)
            VALUES(0, 0, 0, 0, 0, 0, 0, '', '');        
        '''

        if not self.schema:
            inst_clause = f"INSERT INTO `{tbl_name}` "
        else:
            inst_clause = f"INSERT INTO `{self.schema}`.`{tbl_name}`"

        inst_clause += " ({cols}) VALUES ({values})"

        cols = ""
        values = ""
        for key in non_matched_mapping.keys():
            cols += f'`{key}`,'

            trgt_col_data = col_details[col_details['COLUMN_NAME'] == key].to_dict("records")   
            col_type = trgt_col_data[0]['DATA_TYPE']  
            col_type = col_type.split("(")[0].upper()           

            if not pd.isnull(row[non_matched_mapping[key]]):
                if isinstance(row[non_matched_mapping[key]], str):
                    values += merge_stmt_dict["MYSQL"]["insert"][col_type].format(value = row[non_matched_mapping[key]].replace("'", "''")) + ","
                else:
                    values += merge_stmt_dict["MYSQL"]["insert"][col_type].format(value = row[non_matched_mapping[key]]) + ","
            else :
                values += merge_stmt_dict["MYSQL"]["insert"]["NULL"].format(value = 'null') + ","

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
            UPDATE `{target_tbl}` i
            JOIN `{src_tbl}` i2 ON i.`{tgt_col}` = i2.`{src_col}`
            SET i.`{tgt_col}` = i2.`{src_col}`
            WHERE 1=1	

            -- where condition template
            AND {src_tgt_alias}.`{col}` {opr} {val}`
        '''

        main_tmpl = '''
            UPDATE `{target_tbl}` i
            JOIN `{src_tbl}` i2 
            ON {on_clause}
            SET {set_stmt}
            WHERE 1=1 {where_condition}
        '''

        on_condition_tmpl = ''' i.`{tgt_col}`= i2.`{src_col}` '''

        on_clause = self.get_on_condition(
            on_condition_tmpl, 
            on_condition=on_condition, 
            target_tbl=tgt_table_name
        )

        fltr_condition_tmpl = ''' AND {src_tgt_alias}.`{col}` {opr} {val}'''      
        where_clause = self.get_filter_condition(
            filter_condition_tmpl=fltr_condition_tmpl,
            filter_condition=filter_condition,
            src_alias="i2",
            tgt_alias="i"
        )

        ## get source col list
        set_stmt_template = '''i.`{tgt_col}` = i2.`{src_col}`'''
        set_stmt = self.set_stmt_forupdate(set_stmt_template, matched_mapping)

        qry = main_tmpl.format(
            target_tbl = tgt_table_name,
            set_stmt = set_stmt,
            src_tbl = src_table_name,
            where_condition = where_clause,
            on_clause=on_clause
        )

        print("Query: " + qry)

        return qry  
