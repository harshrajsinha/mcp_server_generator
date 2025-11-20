# from SAPAppServerHandler import clsSAPAppServer
# from SapHanaHandler import clsSapHana
# from RFCHandler import clsRFCDB
# from OracleHandler import clsOracleDB
# import pandas as pd
# from scikiq_dbutils.handlers.SnowflakeHandler import clsSnowflake

# config = {}

# config["hostname"] = ''
# config["dbuser"] = ''
# config["pwd"] = ''
# config["port"] = 443
# config["dbType"] = ""
# config["dbname"] = ""
# config["schema"] = ""
# config["warehouse"] = ""

# handle = clsSnowflake(config)

# print(handle.testConnection())
# handle.connect()
# query = "SELECT MANDT, KURST, FCURR, TCURR, GDATU, UKURS, FFACT, TFACT, SKQ_CREATED_AT FROM PUBLIC.TCURR"

# ResultProxy = handle.cursor.execute(query)
# columns = [col_desc[0] for col_desc in  handle.cursor.description]
# print(columns)
# df = None
# counter = 0
# flag = True
# while flag:
#     partial_results = ResultProxy.fetchmany(10000)

#     if(partial_results == []): 
#         flag = False
#     else :
#         df_p = pd.DataFrame(partial_results)
#         df_p.columns = columns

#         df_p.to_parquet("c:/DAAS/tcurr_all_{}.parquet".format(str(counter)), coerce_timestamps='us', allow_truncated_timestamps=True)
#     print(counter)    
#     counter += 1
        

# for i in range(0,counter-1):
#     df = pd.read_parquet("c:/DAAS/tcurr_all_{}.parquet".format(str(i)))
#     print(df.shape[0])

# ResultProxy.close()

