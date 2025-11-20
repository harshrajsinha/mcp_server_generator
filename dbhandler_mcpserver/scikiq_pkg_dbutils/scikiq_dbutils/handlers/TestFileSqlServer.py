from SqlServerHandler import clsMSSqlServerDB

import pandas as pd

config = {}

config["hostname"] = ''
config["dbname"] = ""
config["dbuser"] = ''
config["schema"] = ''
config["pwd"] = ''
config["port"] = 60695

handle = clsMSSqlServerDB(config)

# print(handle.testConnection()) # pass
# print (handle.get_all_tables(search=None, type=None, limit=None, include_view=True)) # pass
# print (handle.getAllTablesWithColumns(search='auth')) # pass
# print (handle.getTableColumns(tablename='AccountOwnership')) # pass
# print (handle.getTableColumnsDetails(tbl_name='auth_permission')) # pass

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

# print (handle.readTable(tbl_name='BSID_TRADE_MAP', limit=20)) # pass

# print (handle.getTableDetails()) # pass

# print (handle.getColumnLOV(table_name='BSID_TRADE_MAP', col_name='INSTRUMENT_ID')) # pass

# table_name = 'BSID_TRADE_MAP'
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
# print (handle.formatQuery(tablename='auth_group_permissions'))
# print (handle.getTableRelationships(table_name='auth_group_permissions'))
# print (handle.getTableIndexDetails (tablename='auth_group_permissions'))
# print (handle.get_incremental_columns (table_name='BSID_TRADE_MAP'))

# print (handle.fetch_delta_columns (table_name='BSID_TRADE_MAP'))

# print (handle.dq_dashboard_data_freshness_query (tablename='BSID_TRADE_MAP',columnname='INSTRUMENT_ID',fromdate='20-06-2020',todate='20-06-2021'))

# print(handle.update_column_comment('test_conncection_mysql', 'Order_SK', ''))

# DONE

# tableDetails = {
#     "tableName": "MyTable",
#     "createColumnData": [
#         {'source_column': 'Population', 'target_column': 'Population_1', 'datatype': 'INT'},
#         {'source_column': 'SomeText', 'target_column': 'Description', 'datatype': 'VARCHAR', 'length': 200}
#     ]
# }
# print(handle.generateCreateTableScriptETL(tableDetails))


# tablename = "MyTable"
# # Create a DataFrame with example entries
# df = pd.DataFrame({
#     'ID': [124],
#     'Name': ['ajay'],
#     'Value': [67]
# })

# print(handle.executeInsertUpdate(tablename, df)) # PASS 15/2/2024

# -----------------------------------------------------------------------

# print(handle.getTableRelationships(table_name='borrowers_child_2')) 

# authors_parent

#     table_name              col_name        ref_table_name     ref_col_name
#     books_child      authorid_books_child   authors_parent    authorid_parent


# books_child
#     table_name              col_name           ref_table_name       ref_col_name
#     books_child      authorid_books_child       authors_parent     authorid_parent
#   borrowers_child_2  bookid_borrowers_child_2    books_child           bookid


# borrowers_child_2
#       table_name           col_name            ref_table_name   ref_col_name
#   borrowers_child_2  bookid_borrowers_child_2    books_child       bookid

# -----------------------------------------------------------------------
