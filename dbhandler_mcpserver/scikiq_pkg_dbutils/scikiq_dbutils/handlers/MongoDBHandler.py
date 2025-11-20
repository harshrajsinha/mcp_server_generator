# PYTHON PACKAGES
import pandas as pd
from pymongo import MongoClient
import math as math
import datetime
import json
from collections import OrderedDict
from typing import Any, Dict, List, Optional
import timeit
from urllib.parse import quote

from datetime import datetime, date, time
from bson.decimal128 import Decimal128
from bson import ObjectId  # To handle ObjectId from MongoDB

#CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.handlers.DBConnection import clsDBConnection

class clsMongoDB(clsDBConnection):
    """
        Usage:

    """
    def __init__(self, config):
        self.host = config["hostname"]
        self.port = config.get("port")
        self.dbname = config["dbname"]
        self.user = config["dbuser"]
        self.password = config["pwd"]

        # Construct connection string based on port and authSource
        if "authSource" in self.host:
            self._connection_string = f"mongodb://{self.user}:{self.password}@{self.host}"
        elif self.port:
            self._connection_string = f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/"
        else:
            self._connection_string = f"mongodb+srv://{self.user}:{self.password}@{self.host}/"
        self.resource_key = config.get("resource_key")

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        '''
        syntax              : COMMENT ON COLUMN [[database.]schema.]table.column IS {'comment' | NULL}
        [database.]schema	: Database and schema. The default schema is public. If you specify a database, it must be the current database.
        table.column	    : The name of the table and column with which to associate the comment.
        comment	            : Specifies the comment text to add. If a comment already exists for this column, this comment overwrites the previous comment.
                              Comments can be up to 8192 characters in length. If a comment exceeds that limitation, Vertica truncates the comment and 
                              alerts the user with a message.
        NULL	            : Removes an existing comment.        
        
        '''

        success = True

        return success      

    def get_data_type(self, value: Any) -> str:
        if isinstance(value, dict):
            return "Dictionary"
        elif isinstance(value, list):
            return "List"
        elif isinstance(value, int):
            return "Integer"
        elif isinstance(value, float):
            return "Decimal"
        elif isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, str):
            return "String"
        elif isinstance(value, datetime):
            return "DateTime"
        elif isinstance(value, date):
            return "Date"
        elif isinstance(value, time):
            return "Time"
        elif isinstance(value, Decimal128):
            return "Decimal"
        else:
            return "Unknown"      
                  

    def connect(self,errors='ignore'):
        resp = dict()
        try:
            resp['resource_call'] = 'connect'
            self._client = MongoClient(self._connection_string, connect=False)

            #callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsMongoDB,self).callConnectionAudit(resp)   

        except Exception as e:
            #callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsMongoDB,self).callConnectionAudit(resp)
            raise
             

    def close(self):
        self._client.close()

    def testConnection(self):
        resp = {}
        try:
            client = MongoClient(self._connection_string)
            client.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS   
        except Exception as e:
            #callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsMongoDB,self).callConnectionAudit(resp)
            raise

        return resp

    def createView(self, view_name, sql_query):
        '''
           @Description : View is the result set of a stored query on the data.
           param:
           view_name: view name (required)
           sql_query: query for view(required)
        '''

        return False

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=10000, profile=False):
        results = None

        return results

    def executeSql(self, query, manage_connection=True):
        b_success = 0
        msg = ScikiqMessages.MSG_SUCCESS
        x = -1

        res = {}
        res["status"] = b_success
        res["result"] = x
        res["msg"] = msg
        return res
        
            
    def executeInsertUpdate(self, tablename, df, if_exists='append', chunksize=10000, dtype={}):

        self.connect()
        collection = self._client[self.dbname][tablename]

        if isinstance(df, pd.DataFrame):
            start = timeit.default_timer()
            print("The start time is :", start)

            for col in df.columns:
                if  str(df[col].dtype) =='object':
                    df[col] = df[col].apply(lambda x: str(x) if isinstance(x, date) else x)

            df.update(df.loc[:, df.dtypes.astype(str).str.contains('date')].apply(
                lambda x: x.dt.strftime("%Y-%m-%d %H:%M:%S")
                )
            )              
            print("The difference of time is :", timeit.default_timer() - start)
            start = timeit.default_timer()
            data = df.to_dict(orient="record") 
            print("The Mongo Write start time is :", start)
            collection.insert_many(data, ordered = False)
            print("The difference of time is :", timeit.default_timer() - start)

        elif isinstance(df,dict) : ## if dict
            json_data = json.loads(json.dumps(df))
            collection.insert_many([json_data], ordered=False)
        else : ## if list of dict
            json_data = json.loads(json.dumps(df))
            collection.insert_many(json_data, ordered=False)
        self.close()

        return df

    def get_all_tables(self, search=None, type=None, limit=None, include_view=None):
        self.connect()
        collections = self._client[self.dbname].list_collection_names()

        lst = []
        ## dummy values for TABLE_TYPE & TABLE_SCHEMA
        for collection in collections :
            lst.append([collection, 'TABLE', ''])
        self.close()

        return lst

    def getAllTablesWithColumns(self, search):
        results = self.get_all_tables(search)
        tbl_data = []
        self.connect()
        for tbl in results:
            tbl_cols = {}
            tbl = list(tbl)[0]
            tbl_cols["tablename"] = tbl

            columns = []
            collection = self._client[self.dbname][tbl]
            # Get column names, types, and metadata
            sample_document = collection.find_one()
            for field, field_value in sample_document.items():
                columns.append([field, self.get_data_type(field_value)])            

            tbl_cols["columnname"] = columns
            tbl_data.append(tbl_cols)

        self.close()

        return tbl_data

    def getTableColumns(self, tablename, type = '', **others):
        _filter = others.get("filter", {})           
        self.connect()

        results = []
        collection = self._client[self.dbname][tablename]
        # Get column names, types, and metadata
        sample_document = collection.find_one(_filter)
        for field, field_value in sample_document.items():
            results.append([field, self.get_data_type(field_value)])            

        self.close()

        return results

    def getTableColumnsDetails(self, tbl_name, **others):
        _filter = others.get("filter", {})   

        self.connect()
        cols = []
     
        collection = self._client[self.dbname][tbl_name]
        # Get column names, types, and metadata
        sample_document = collection.find_one(_filter)
        pos = 0
        if sample_document :
            for field, field_value in sample_document.items():
                col_dtls = {
                    'TABLE_SCHEMA': '', 
                    'TABLE_NAME': tbl_name, 
                    'TABLE_TYPE': 'TABLE', 
                    'COLUMN_NAME': field, 
                    'DATA_TYPE': self.get_data_type(field_value), 
                    'ORDINAL_POSITION': pos, 
                    'NUMERIC_PRECISION': None, 
                    'NUMERIC_SCALE': None, 
                    'IS_NULLABLE': True, 
                    'CHARACTER_MAXIMUM_LENGTH': 100000, 
                    'DATA_TYPE_LENGTH': 100000, 
                    'CHARACTER_MAX_LENGTH': '100000', 
                    'COMMENT': '', 
                    'COLUMN_DEFAULT': '', 
                    'IS_PRIMARYKEY': 0, 
                    'IS_UNIQUEKEY': 0, 
                    'IS_NONUNIQUEKEY': '', 
                    'AUTO_INCREMENT': 0, 
                    'COLUMN_LENGTH': 100000, 
                    'COLUMN_PRECISION': 0, 
                    'COLUMN_CHARACTERSET': '', 
                    'REFERENCED_TABLENAME': '', 
                    'REFERENCED_COLUMNNAME': ''
                }

                pos+=1

                cols.append(col_dtls)            

        self.close()
        return cols

    def getRenamesColMetricsDict(self, config_details=OrderedDict()):
        return False


    def generateQuery(self, tablename=None, columnnames=None, limit=None, orderby=None,  filters=None, 
        groupby=None, joins=None, joinCondition=None, distinct=0):
        return ""

    def createCustomColumnExpression(self, query, custom_column_names_dict):
        return ""

    def formatFilter(self,alias,condition="AND",rules=None,query=None):
        return ""

    def formatQuery(self, tablename, groupby=None, query=None, filters=None, columnnames=None, schema=None):
        return ""


    def create_engine(self):
        self.engine_statement = f"mongodb://{quote(self.user)}:{quote(self.password)}@{self.host}:{self.port}/"

    def readTable(self, tbl_name, limit, **others):
        _filter = others.get("filter", "{}")
        if isinstance(_filter, str) and len(_filter.strip()) == 0:
            _filter = {}
        elif not isinstance(_filter, dict) :
            _filter = json.loads(_filter)

        self.connect()
        collection = self._client[self.dbname][tbl_name]        

        cols = others.get("cols", {})
        order_by = others.get("order_by", {})
        group_by = others.get("group_by", {})
        distinct = others.get("distinct", {})

        '''
            cols format :
            {
                '_id': [{'fn': '', 'expr': '', 'agg': '', 'format': 'NA', 'alias': '_id', 'data_type': 'Unknown', 'col_type': 'native', 'col_key': 'PDEMCLNT0015018369', 'tbl_key': 'TABLCLNT0015000803', 'table_name': 'Preauth'}],
                'account_address_activities': [{'fn': '', 'expr': '', 'agg': '', 'format': 'NA', 'alias': 'account_address_activities', 'data_type': 'List', 'col_type': 'native', 'col_key': 'PDEMCLNT0015018370', 'tbl_key': 'TABLCLNT0015000803', 'table_name': 'Preauth'}], 
                'account_address_assert_history': [{'fn': '', 'expr': '', 'agg': 'COUNT', 'format': 'NA', 'alias': 'account_address_assert_history', 'data_type': 'List', 'col_type': 'native', 'col_key': 'PDEMCLNT0015018371', 'tbl_key': 'TABLCLNT0015000803', 'table_name': 'Preauth'}]
            }
        '''
        
        sel_cols = {}
        alias_col = {}
        for col in cols.keys():        
            sel_cols[col] = 1
            alias_col[col] = cols[col][0]["alias"]

        if isinstance(limit, list):
            limit = int(limit[0])

        if limit :
            datapoints = list(collection.find(_filter, sel_cols).limit(limit))
        else :
            datapoints = list(collection.find(_filter, sel_cols))

        # df = pd.json_normalize(datapoints)
        # Given list of JSON-like dictionaries
        # Convert each dictionary to a flattened dictionary
        flattened_dicts = []
        for json_data in datapoints:
            data_dict = {
                key: value if not isinstance(value, ObjectId) else str(value)
                for key, value in json_data.items()
            }
            flattened_dicts.append(data_dict)

        # Create a pandas DataFrame from the flattened dictionaries
        df = pd.DataFrame(flattened_dicts)

        ## in case of MongoDB is the filters collection does not have a key, but that is available in some other document
        ## then it will not return the key in the filtered result.
        ## below code will add that missing key
        df_cols = df.columns
        for col in cols.keys():
            if col not in df_cols:
                df[col] = ""
        df = df.rename(columns=alias_col)

        # Display the DataFrame
        res = dict()
        res["df"] = df
        res["df_text"] = flattened_dicts 

        self.close()
        return res               
     
    def getUpdateQuery(self,targetTableName,columnnames={},filters=[],joins={},inputTableReplica='temp_table',sqlQuery=None):
        return False


    def updateQueryUsingSubQuery(self,updateQuery,inputTableReplica,subQuery):
        return False
    
    def updateType(self,df,tableDetails,mappedColumn):
        return False

    # added tableDetails parameter to pass table columns data type
    def updateTable(self,df,targetTableName,columnnames={},filters=[],joins={},fromTable= None,sameSchema = False,tableDetails={},sqlQuery=None):
        return False
            
    def truncateTable(self,table_name):
        return False
    
    #TODO: generateCreateTableScript function need to be tested for Vertica
    def generateCreateTableScript(self, tableDetails):
        return False

    def generateCreateTableScriptETL(self, tableDetails):
        return False

    def createTable(self, tableDetails, etl=False):
        res = dict()
        res["status"] = 1
        res["result"] = ""
        res["msg"] = "success"
        return res
    
    def getColumnLOV(self, table_name, col_name, order='ASC'):
        return False

    def getColumnsProfile(self, table_name, with_min_max = False, filter = None):        
        return pd.DataFrame()
    
    def getTableDetails(self, table_name = None, type = {}, **others):
        _filter = others.get("filter", {})           
        self.connect()
             
        col_name = ['TABLE_SCHEMA', 'TABLE_NAME', 'NO_OF_COLS', 'SIZE_IN_MB', 'NO_OF_ROWS', 'LAST_UPDATED', 'TABLE_TYPE', 'COMMENT']
        df = None

        if not table_name :
            collection_names = self._client[self.dbname].list_collection_names()
        else :
            collection_names = [table_name]

        for tbl in collection_names:
            try :
                collection = self._client[self.dbname][tbl]   
                row_count = collection.count_documents(_filter)    
                sample_document = collection.find_one(_filter)         
                
                data = [['', tbl, len(sample_document.items()), -1, row_count, None, 'TABLE', '']]
                if df is None :
                    df = pd.DataFrame(data, columns=col_name)
                else :
                    df1 = pd.DataFrame(data, columns=col_name)
                    df_list = [df]
                    df_list.append(df1)
                    df = pd.concat(df_list, ignore_index=True)
            except Exception :
                print("Exception while fetching details of the table :" + tbl)

        self.close()

        return df

    def getTableRelationships(self, table_name, bi_directional = False):
        return  pd.DataFrame()

    def getDropTableQuery(self,table_name):
        return  False

    def dropTable(self, table_name):
        return False

    def getTableColumnDtypes(self,table_name):
        return False

    def getSqlAlchemyDtype(self,src_df,target_tbl_name,src_target_mapping):
        return pd.DataFrame()

    def dq_dashboard_data_freshness_query(self, tablename, columnname, fromdate, todate):
        return ""

    def dq_dashboard_data_modify_query(self, tablename, columnname, fromdate, todate):
        return ""

    def dq_dashboard_data_delete_query(self, tablename, columnname, fromdate, todate):
        return ""

    def dq_dashboard_stk_query(self, tablename, columnname, fromdate, todate, datasources_col_name):
        return ""

    def get_connection_statement(self):
        return self._connection_string

    def get_incremental_columns(self, table_name):
        return pd.DataFrame()

    def fetch_delta_columns(self, table_name, **others):
        return pd.DataFrame()

    def find_row(self, tbl_name, row, on_condition, manage_connection):
        found = False

        return found    

    def update_row(self, tbl_name, row, on_condition, matched_mapping, col_details, manage_connection):
 
        return False

    def insert_row(self, tbl_name, row, non_matched_mapping, col_details, manage_connection):

        '''
            INSERT INTO SCIKIQ_DEV.ORDERS
            (ID, CUSTOMER_ID, PRODUCT_ID, QUANTITY, PRICE, TOTAL_AMOUNT, STORE_ID, CREATED_DATE, CREATED_BY)
            VALUES(0, 0, 0, 0, 0, 0, 0, '', '');        
        '''
        return False
