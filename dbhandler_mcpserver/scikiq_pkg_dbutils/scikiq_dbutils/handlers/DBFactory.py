import os
import requests

from scikiq_dbutils.utils import decodeData





class clsDBHandler():
    def __init__(self):
        self.host = ""
        self.port = None
        self.usr = ""
        self.pwd = ""
        self.db = ""
        self.schema = ""
        self.db_type = ""
        self.dbHandle = None

    @staticmethod
    def getConnectionDetails(conn_key):

        api_base_url = '{}{}:{}'.format(
            os.environ.get('API_HTTP'),
            os.environ.get('API_IP'),
            os.environ.get('API_PORT'),
        )
        headers = {'Authorization': ""}
        url = api_base_url + "/base/datasource/get/config"
        data = {"conn_key": conn_key, "category": 'RDBMS', "action": 'READCONFIG', "role": "client_admin"}
        r = requests.post(url=url, data=data, headers=headers)
        if r.status_code == 200:
            details = r.json()
            if details['error'] == 0:
                return details['data']
            else:
                raise ValueError("Error  in API --{}".format(details['msg']))
        else:
            raise ValueError("Error in API-- Status Code : " + str(r.status_code))

    @staticmethod
    def getInstanceByConfig(config):
        dbconfig = config.copy()
        db_type = dbconfig["dbType"]
        if db_type not in ("BIGQUERY", 'SAGEMAKER'):
            # Check encryption flag - default to 1 (encrypted) for backward compatibility
            encryption_enabled = dbconfig.get('password_encrypted', 1)
            if encryption_enabled == 1:
                dbconfig["pwd"] = decodeData(dbconfig['dbpassword'])
            else:
                dbconfig["pwd"] = dbconfig['dbpassword']

        if 'port' in dbconfig and len(str(dbconfig["port"])) > 0:
            dbconfig["port"] = int(config["port"])
            port = str(dbconfig['port'])
            if not port.isnumeric():
                raise AssertionError(" : Port should be Number not String")

        if db_type == "MYSQL":
            from scikiq_dbutils.handlers.MySqlHandler import clsMySqlDB            
            return clsMySqlDB(dbconfig)
        elif db_type == "SQLSERVER":
            from scikiq_dbutils.handlers.SqlServerHandler import clsMSSqlServerDB            
            return clsMSSqlServerDB(dbconfig)
        elif db_type in ["ORACLE", "ORACLE-EBS", "ORACLE-FUSION"]:
            from scikiq_dbutils.handlers.OracleHandler import clsOracleDB            
            return clsOracleDB(dbconfig)
        elif db_type == "VERTICA":
            from scikiq_dbutils.handlers.VerticaHandler import clsVerticaDB            
            return clsVerticaDB(dbconfig)
        elif db_type == "POSTGRES":
            from scikiq_dbutils.handlers.PostgresHandler import clsPostgresDB            
            return clsPostgresDB(dbconfig)
        elif db_type == "DB2":
            from scikiq_dbutils.handlers.DB2Handler import clsDB2DB            
            return clsDB2DB(dbconfig)
        elif db_type == "TERADATA":
            from scikiq_dbutils.handlers.TeraDataHandler import clsTeraDataDB            
            return clsTeraDataDB(dbconfig)
        elif db_type in ["SAPHANA"]:
            from scikiq_dbutils.handlers.SapHanaHandler import clsSapHana            
            return clsSapHana(dbconfig)
        elif db_type == "SNOWFLAKE":
            from scikiq_dbutils.handlers.SnowflakeHandler import clsSnowflake            
            return clsSnowflake(dbconfig)
        elif db_type == "RFC":
            from scikiq_dbutils.handlers.RFCHandler import clsRFCDB            
            return clsRFCDB(dbconfig)
        elif db_type in ["S4HANA","BW4HANA","SAP-ECC"]:
            from scikiq_dbutils.handlers.SAPAppServerHandler import clsSAPAppServer            
            return clsSAPAppServer(dbconfig)
        elif db_type == "BIGQUERY":
            from scikiq_dbutils.handlers.BigQueryHandler import clsBigQuery            
            return clsBigQuery(dbconfig)
        elif db_type == "MONGODB":
            from scikiq_dbutils.handlers.MongoDBHandler import clsMongoDB            
            return clsMongoDB(dbconfig)
        elif db_type == "CHROMADB":
            from scikiq_dbutils.handlers.ChromaDBHandler import clsChromaDB            
            return clsChromaDB(dbconfig)
        elif db_type == "ATHENA":
            from scikiq_dbutils.handlers.AthenaHandler import clsAthena
            return clsAthena(dbconfig)
        elif db_type == "REDSHIFT":
            from scikiq_dbutils.handlers.RedshiftHandler import clsRedshiftDB            
            return clsRedshiftDB(dbconfig)   
        elif db_type == "AURORADB-MYSQL":
            from scikiq_dbutils.handlers.MySqlHandler import clsMySqlDB            
            return clsMySqlDB(dbconfig)
        elif db_type == "AURORADB-POSTGRES":
            from scikiq_dbutils.handlers.PostgresHandler import clsPostgresDB            
            return clsPostgresDB(dbconfig)    
        elif db_type == "SAGEMAKER":
            from scikiq_dbutils.handlers.SageMakerHandler import clsSageMaker            
            return clsSageMaker(config)
        elif db_type == "DUCKDB":
            from scikiq_dbutils.handlers.DuckDBHandler import clsDuckDB            
            return clsDuckDB(dbconfig)           

        raise AssertionError("Unsupported Database Type : " + db_type)

    @staticmethod
    def getInstanceFromAPI(config_param):

        config = clsDBHandler.getConnectionDetails(conn_key=config_param['conn_key'])

        db_type = config["dbType"]
        if db_type not in ("BIGQUERY", "SAGEMAKER"):
            # Check encryption flag - default to 1 (encrypted) for backward compatibility
            encryption_enabled = config.get('password_encrypted', 1)
            if encryption_enabled == 1:
                config["pwd"] = decodeData(config['dbpassword'])
            else:
                config["pwd"] = config['dbpassword']

        if 'port' in config and len(str(config["port"])) > 0:
            config["port"] = int(config["port"])

        config['resource_key'] = config_param['conn_key']

        if db_type == "MYSQL":
            from scikiq_dbutils.handlers.MySqlHandler import clsMySqlDB            
            return clsMySqlDB(config)
        elif db_type == "SQLSERVER":
            from scikiq_dbutils.handlers.SqlServerHandler import clsMSSqlServerDB            
            return clsMSSqlServerDB(config)
        elif db_type in ["ORACLE", "ORACLE-EBS", "ORACLE-FUSION"]:
            from scikiq_dbutils.handlers.OracleHandler import clsOracleDB                        
            return clsOracleDB(config)
        elif db_type == "VERTICA":
            from scikiq_dbutils.handlers.VerticaHandler import clsVerticaDB            
            return clsVerticaDB(config)
        elif db_type == "POSTGRES":
            from scikiq_dbutils.handlers.PostgresHandler import clsPostgresDB            
            return clsPostgresDB(config)
        elif db_type == "DB2":
            from scikiq_dbutils.handlers.DB2Handler import clsDB2DB            
            return clsDB2DB(config)
        elif db_type == "TERADATA":
            from scikiq_dbutils.handlers.TeraDataHandler import clsTeraDataDB            
            return clsTeraDataDB(config)
        elif db_type == "SAPHANA":
            from scikiq_dbutils.handlers.SapHanaHandler import clsSapHana            
            return clsSapHana(config)
        elif db_type == "SNOWFLAKE":
            from scikiq_dbutils.handlers.SnowflakeHandler import clsSnowflake            
            return clsSnowflake(config)
        elif db_type == "RFC":
            from scikiq_dbutils.handlers.RFCHandler import clsRFCDB            
            return clsRFCDB(config)
        elif db_type in ["S4HANA", "BW4HANA", "SAP-ECC"]:
            from scikiq_dbutils.handlers.SAPAppServerHandler import clsSAPAppServer            
            return clsSAPAppServer(config)
        elif db_type == "BIGQUERY":
            from scikiq_dbutils.handlers.BigQueryHandler import clsBigQuery            
            return clsBigQuery(config)
        elif db_type == "MONGODB":
            from scikiq_dbutils.handlers.MongoDBHandler import clsMongoDB            
            return clsMongoDB(config)
        elif db_type == "CHROMADB":
            from scikiq_dbutils.handlers.ChromaDBHandler import clsChromaDB            
            return clsChromaDB(config)        
        elif db_type == "ATHENA": 
            from scikiq_dbutils.handlers.AthenaHandler import clsAthena
            return clsAthena(config)
        elif db_type == "REDSHIFT":
            from scikiq_dbutils.handlers.RedshiftHandler import clsRedshiftDB            
            return clsRedshiftDB(config)
        elif db_type == "AURORADB-MYSQL":
            from scikiq_dbutils.handlers.MySqlHandler import clsMySqlDB            
            return clsMySqlDB(config)
        elif db_type == "AURORADB-POSTGRES":
            from scikiq_dbutils.handlers.PostgresHandler import clsPostgresDB            
            return clsPostgresDB(config)            
        elif db_type == "SAGEMAKER":
            from scikiq_dbutils.handlers.SageMakerHandler import clsSageMaker            
            return clsSageMaker(config)
        elif db_type == "DUCKDB":
            from scikiq_dbutils.handlers.DuckDBHandler import clsDuckDB            
            return clsDuckDB(config)   
                          
        raise AssertionError("Unsupported Database Type : " + db_type)
