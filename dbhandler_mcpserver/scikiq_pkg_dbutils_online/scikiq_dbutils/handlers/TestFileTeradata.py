from TeraDataHandler import clsTeraDataDB
from TeraDataHandler import TeraDataQueryBuilder
from TeraDataHandler import TeraDataQuery

import pandas as pd

config = {}

config["hostname"] = ''
config["dbname"] = ""
config["dbuser"] = ''
config["pwd"] = ''
config["port"] = 1025
config["schema"]=''


handle = clsTeraDataDB(config)

print(handle.testConnection()) # pass

# print(handle.getAllTables(search=None, type=None, limit=None, include_view=True)) # pass

# print(handle.getAllTablesWithColumns(search='Acc')) # pass

# print (handle.getTableColumns(tablename='AccountInfo')) # pass only space is there with datatype

# print (handle.getTableColumnsDetails(tbl_name='AccessRights')) # pass only space is there with datatype

# tableDetails = {
#     "tableName": "employees d",
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

# print (handle.readTable(tbl_name='Accounts', limit=20)) # pass

# print (handle.getTableDetails()) # pass

# print (handle.getColumnLOV(table_name='Accounts', col_name='AccountName')) # pass

# table_name = 'Accounts'
# _filter = None #"GJAHR = 2013"
# df = handle.getColumnsProfile(table_name, with_min_max=False, filter=_filter) ## PASS
# print(df)

# tableDetails = {
#     "tableName": "My Table",
#     "createColumnData": [
#         {'source_column': 'Population', 'target_column': 'Population 1', 'datatype': 'INT'}
#     ]
# }
# print (handle.generateCreateTableScriptETL(tableDetails)) 

# print(handle.fetch_delta_columns(table_name='AccessRights'))

# print(handle.update_column_comment('AccessRights', 'DatabaseId', ''))

# print(handle.dq_dashboard_data_freshness_query(tablename='AccessRights',columnname='CreateTimeStamp',fromdate='2021-05-20',todate='2023-05-25'))


# print(handle.dq_dashboard_data_modify_query(tablename='AccessRights',columnname='CreateTimeStamp',fromdate='2021-05-20',todate='2023-05-25'))

# print(handle.dq_dashboard_data_delete_query(tablename='AccessRights',columnname='CreateTimeStamp',fromdate='2021-05-20',todate='2023-05-25'))


# print(handle.dq_dashboard_stk_query(tablename='AccessRights',columnname='CreateTimeStamp',fromdate='2021-05-20',todate='2023-05-25',datasources_col_name='AccessRight'))

# ---------------------------------------------------------------------------------------------

# print(handle.getTableRelationships(table_name='child_table',bi_directional =False))

# grandparent_table

#    table_name         col_name        ref_table_name     ref_col_name
#   parent_table    grandparent_id_pt  grandparent_table   grandparent_id


# parent_table

#   table_name           col_name         ref_table_name      ref_col_name
#   child_table         parent_id_ct        parent_table        parent_id
#   parent_table     grandparent_id_pt   grandparent_table    grandparent_id



# child_table

#     table_name      col_name      ref_table_name    ref_col_name
#     child_table    parent_id_ct    parent_table       parent_id

# ---------------------------------------------------------------------------------------------
