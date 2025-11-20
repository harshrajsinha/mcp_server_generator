from AthenaHandler import clsAthena

import pandas as pd

config = {}

config["hostname"] = ''
config["region_name"] = ''
config["dbuser"] = ''
config["pwd"] = ''
config["schema"] = ""
config["dbname"] = ""

handle = clsAthena(config)

# print(handle.testConnection()) # PASS 8/2/24
# print (handle.get_all_tables(search=None, type=None, limit=None, include_view=True)) # PASS 8/2/24
# print (handle.getAllTablesWithColumns(search='factory'))  # PASS 8/2/24
# print (handle.getTableColumns(tablename='factory')) # PASS 8/2/24
# print (handle.getTableDetails(table_name=None)) # PASS 8/2/24 (size_in_mb,"TABLE_COMMENT","NO_OF_ROWS","LAST_UPDATED")
# print (handle.getTableColumnsDetails(tbl_name='factory')) # PASS 9/2/24

# tableDetails = {
#     "tableName": "employees_4",
#     "colDetails": [
#         {
#             "columnName": "id",
#             "dbType": "varchar",
#             "isPrimaryKey": 0,
#             "isAutoIncrement": 0,
#             "length": 10
#         }
#     ]
# }
# print (handle.generateCreateTableScript(tableDetails=tableDetails))  # PASS 14/2/24

# tableDetails = {
#     "tableName": "employees_4",
#     "colDetails": [
#         {
#             "columnName": "id",
#             "dbType": "varchar",
#             "isPrimaryKey": 0,
#             "isAutoIncrement": 0,
#             "length": 10
#         }
#     ],
#      "createColumnData": [
#                 {"source_column": "id", "target_column": "id1", "datatype": "VARCHAR(10)"}
#             ]
# }
# print (handle.generateCreateTableScriptETL(tableDetails)) # PASS 14/2/24

# print (handle.createTable(tableDetails,etl=False)) # PASS 14/2/24

# print (handle.readTable(tbl_name='telco2', limit=10)) # PASS 14/2/24
# executeQuery(successfull) (tested for this readTable() and made changes for limit) 14/2/24

# print (handle.getColumnLOV(table_name='telco2', col_name='event_description')) # PASS 14/2/24

# table_name = 'telco2'
# _filter = None (col name)
# df = handle.getColumnsProfile(table_name, with_min_max=False, filter=_filter) # PASS 14/2/24
# print(df)

# tablename = {"telco2": "t"}
# groupby = {"id": {"type": "bigint"}}
# query = "SELECT id FROM telco2 order by id asc"
# filters = "id=160" 
# columnnames = {
#     "id": [{"type": "bigint"}],
#     "event_description": [{"type": "string", "format": "INITCAP"}],
#     "ip_address": [{"type": "string", "format": "LOWER"}],
#     "resource": [{"type": "string"}],
#     "action": [{"type": "string"}],
#     "timestamp": [{"type": "date", "format": "yy-mm-dd hh:mm:ss"}],
#     "log_type": [{"type": "string"}],
#     "description": [{"type": "string"}],
#     "unique_key": [{"type": "string"}],
#     "product": [{"type": "string"}],
#     "gender": [{"type": "string"}],
#     "region": [{"type": "string"}],
#     "username": [{"type": "string"}],
#     "login_fraud": [{"type": "string"}],
#     "transactions": [{"type": "string"}]
# }
# schema = 'default'  
# print (handle.formatQuery(tablename=tablename, 
#                           groupby=groupby, 
#                           filters=filters,
#                           query=query,
#                           columnnames=columnnames, 
#                           schema=schema)) # FAILED 15/2/2024 for group[1] where[1] #SELECT id FROM "default"."telco2" "t" WHERE SELECT id FROM telco2 order by id asc GROUP BY SELECT id FROM telco2 order by id asc (wrong query generated)

# print (handle.getTableRelationships(table_name='telco2')) # FAILED 15/2/2024 (function passed as per now there is no forgien key in athena)
# print (handle.getTableIndexDetails (tablename='telco2')) # PASS 15/2/2024
# print (handle.get_incremental_columns (table_name='employees')) # PASS 15/2/2024
# print (handle.fetch_delta_columns (table_name='telco2')) # PASS 15/2/2024
# print(handle.update_column_comment('telco2', 'event_description', 'hello')) # FAILED 15/2/2024 (function passed as per now there i didnt got comment code in athena)
# print(handle.get_connection_statement()) # PASS 15/2/2024   o/p   awsathena+rest://access_key:secret_key@athena.ap-south-1.amazonaws.com/default?s3_staging_dir=s3://sonalisharma/factory/

# tablename = "telco2"
# df = pd.DataFrame({
#     'id': [100,110,120],
#     'event_description' :['a','b','c']
# })
# print(handle.executeInsertUpdate(tablename, df)) # PASS 15/2/2024
# create_engine(successful) 15/2/2024

# DONE





# createView(passed) # 15/2/2024
# executeQuery(once checked in readtable()) # 15/2/2024
# executeSql(once checked in createtable()) # 15/2/2024

# getRenamesColMetricsDict(not checked generatequery(part)) # 16/2/2024
# print(handle.generateQuery(
#     tablename={"employees": "t1", "employees_1": "t2"},
#     columnnames={"t1.id": "SUM", "t2.id": "AVG"},
#     limit=10,
#     orderby={"t1.id": "ASC"},
#     filters={"condition": "t1.id > 10"},
#     groupby={"t2.id": "id"},
#     joins={"employees_1": "inner"},
#     joinCondition="t1.id = t2.id",
#     distinct=1,
#     offset=20
# ))# FAILED 16/2/2024 (used mysql one)
# createCustomColumnExpression (not checked generatequery(part))

# formatFilter(not checked part of formatquery) # 16/2/2024

# updateTable(not checked) # 16/2/2024
# getUpdateQuery(not checked part of updatetable) # 16/2/2024

# print(handle.truncateTable(table_name='employees')) # FAILED 16/2/2024 (dbeaver)SQL Error [100071] [HY000]: [Simba][AthenaJDBC](100071) An error has been thrown from the AWS Athena client. NOT_SUPPORTED: Cannot delete from non-managed Hive table [Execution ID: b83e6f51-8a85-463a-ba51-2e2035cfb071]

# getMergeQuery(not checked) # 16/2/2024
# find_row (not checked) # 16/2/2024
# insert_row (not checked) # 16/2/2024
# update_row (not checked) # 16/2/2024
# join_upd_query (not checked) # 16/2/2024

# print(handle.getDropTableQuery(table_name='employees_4')) # PASS 16/2/2024
# dropTable(successfull) # 16/2/2024

# dq_dashboard_data_delete_query(not checked) # 16/2/2024
# dq_dashboard_data_freshness_query(not checked) # 16/2/2024
# dq_dashboard_data_modify_query(not checked) # 16/2/2024
# dq_dashboard_stk_query(not checked) # 16/2/2024



