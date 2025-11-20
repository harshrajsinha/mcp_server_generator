from MySqlHandler import clsMySqlDB

import pandas as pd

config = {}

config["hostname"] = ''
config["dbname"] = ""
config["dbuser"] = ''
config["pwd"] = ''
config["dbType"] = ""
config["port"] = 3306



handle = clsMySqlDB(config)

print(handle.testConnection()) # pass

# print (handle.getAllTables(search=None, type=None, limit=None, include_view=True)) # pass

# print (handle.getAllTablesWithColumns(search='CityMaster')) # pass

# print (handle.getTableColumns(tablename='accounts_test_data')) # pass

# print (handle.getTableColumnsDetails(tbl_name='BSID_TRADE_MAP')) # pass

# tableDetails = {
#     "tableName": "employees",
#     "colDetails": [
#         {
#             "columnName": "id",
#             "dbType": "int",
#             "isPrimaryKey": 1,
#             "isAutoIncrement": 1,
#             "length": 10,
#             "nullable":"false"
#         }
#     ]
# }
# print (handle.generateCreateTableScript(tableDetails=tableDetails)) # pass

# print (handle.readTable(tbl_name='BSID_TRADE_MAP', limit=20,column_name='ANFAE')) # pass
# print (handle.getTableDetails()) # pass
# print (handle.getColumnLOV(table_name='BSID_TRADE_MAP', col_name='INSTRUMENT_ID')) # pass

# table_name = 'Emp_Information'
# _filter = None #"GJAHR = 2013"
# df = handle.getColumnsProfile(table_name, with_min_max=False, filter=_filter) ## PASS
# print(df)

# tableDetails = {
#     "tableName": "My Table",
#     "createColumnData": [
#         {'source_column': 'Population', 'target_column': 'Population 1', 'datatype': 'INT'}
#     ]
# }
# print (handle.generateCreateTableScriptETL(tableDetails)) # pass

# print(handle.update_column_comment('accounts_test_data', 'MONAT', ''))
