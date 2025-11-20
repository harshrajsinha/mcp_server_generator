# PYTHON PACKAGES
import os
import requests
import pandas as pd
import numpy as np
from pyrfc import Connection

# CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.handlers.DBConnection import clsDBConnection

class clsRFCDB(clsDBConnection):
    """
        Usage:
    """

    def __init__(self, config):
        self.__ssl = False
        if ("resource_key" in config):
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None

        self.host = config["hostname"]
        self.port = config["port"]
        self.user = config["dbuser"]
        self.password = config["pwd"]
        self.client = config["client"]
        self.router = config["router"]
        self.sysnr = config["sysnr"]

        self.engine_statement = None
        self.connection = None
        self.cursor = None

        if "connection_type" in config:
            self.connection_type = config["connection_type"]
        else:
            self.connection_type = None

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

            self.connection = Connection(
                user=self.user,
                passwd=self.password,
                ashost=self.host,
                sysnr=self.sysnr,
                saprouter=self.router,
                client=self.client,
            )

            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsRFCDB, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsRFCDB, self).callConnectionAudit(resp)
            raise

    def close(self):
        if self.connection:
            self.connection.close()

    def testConnection(self):
        resp = {}
        try:
            connection = Connection(
                user=self.user,
                passwd=self.password,
                ashost=self.host,
                sysnr=self.sysnr,
                saprouter=self.router,
                client=self.client,
            )

            connection.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS

        except Exception as e:
            resp['error'] = 1
            resp['msg'] = str(e)

        # callConnectionAudit using for audit the record.
        super(clsRFCDB, self).callConnectionAudit(resp)
        return resp

    def createView(self, view_name, sql_query):
        pass

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=10000, profile=False):
        results = None
        return results

    def executeSql(self, query, value=None, manage_connection=True):
        pass

    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=1000):
        pass
        return df

    def get_all_tables(self, search=None, type=None, limit=None):
        pass

    def getAllTablesWithColumns(self, search):
        pass

    def getTableColumns(self, tablename, type = ''):
        pass

    def getTableColumnsDetails(self, tbl_name, **others):

        api_base_url = '{}{}:{}'.format(
            os.environ.get('API_HTTP'),
            os.environ.get('API_IP'),
            os.environ.get('API_PORT'),
        )
        headers = {'Authorization': ""}
        url = api_base_url + "/base/datasource/erp/rfc/attributes"
        data = {"object_name": tbl_name}

        df = None
        r = requests.post(url=url, data=data,headers=headers)
        if r.status_code == 200:
            details = r.json()
            if details['error']==0:
                df = pd.DataFrame(details['data']) 

                df.rename(columns = {
                    'attribute_name' : 'COLUMN_NAME',
                    'data_type' : 'DATA_TYPE',
                    'data_type_length' : 'DATA_TYPE_LENGTH',
                    'data_type_precision' : 'NUMERIC_PRECISION'
                }, inplace = True)         

                df["IS_NULLABLE"] = False
                df["CHARACTER_MAX_LENGTH"] = df["DATA_TYPE_LENGTH"]
                df["CHARACTER_MAXIMUM_LENGTH"] = df["DATA_TYPE_LENGTH"]
                df["NUMERIC_SCALE"] = df["DATA_TYPE_LENGTH"]
                
                df['ORDINAL_POSITION'] = np.arange(len(df))
                df['COMMENT'] = ""


                df.fillna(0, inplace = True)          
                df = df.to_dict(orient="records")  
            else:
                raise ValueError("Error  in API --{}".format(details['msg']))
        else:
            raise ValueError("Error in API-- Status Code : "+ str(r.status_code))               

        return df

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
            distinct=0
    ):
        pass

    def create_engine(self):
       pass

    def readTable(self, tbl_name, limit = None, **others):

        idx_name = 'itab'
   
        results = None
        try : 
            self.connect()
            results = self.connection.call(tbl_name)
            results = pd.DataFrame(results[idx_name.upper()])     
            self.close()
        except Exception as e :
            self.close()
            print(e)
            raise   

        res = {}
        res["df"] = results
        res["df_text"] = None 

        return res   

    def truncateTable(self, table_name):
        pass

    def generateCreateTableScriptETL(self, tableDetails):
        pass

    def createTable(self, tableDetails, etl=False):
        pass

    def getColumnLOV(self, table_name, col_name):
        pass

    def getColumnsProfile(self, table_name, with_min_max=False, filter=None):
        pass

    def getTableDetails(self, table_name, type = {}):
        return pd.DataFrame()

    def getTableRelationships(self, table_name):
        pass

    def getDropTableQuery(self, table_name):
        pass

    def dropTable(self, table_name):
        pass

    def getTableIndexDetails(self, tablename):
        pass

    def get_incremental_columns(self, table_name,**others):
        try:
            df = pd.DataFrame(columns=['COLUMN_NAME'])
        except Exception as e:
            self.close()
            print(e)
            raise
        return df

    def fetch_delta_columns(self, table_name, **others):
        df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])
        return df
    

    def find_row(self, tbl_name, row, on_condition, manage_connection):
        return False    

    def update_row(self, tbl_name, row, on_condition, matched_mapping, col_details, manage_connection):
        return False

    def insert_row(self, tbl_name, row, non_matched_mapping, col_details, manage_connection):

        '''
            INSERT INTO SCIKIQ_DEV.ORDERS
            (ID, CUSTOMER_ID, PRODUCT_ID, QUANTITY, PRICE, TOTAL_AMOUNT, STORE_ID, CREATED_DATE, CREATED_BY)
            VALUES(0, 0, 0, 0, 0, 0, 0, '', '');        
        '''
        return False
