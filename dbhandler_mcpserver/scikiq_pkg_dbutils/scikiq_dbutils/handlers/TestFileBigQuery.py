from BigQueryHandler import clsBigQuery
import pandas as pd

config = {
  "type": "",
  "project_id": "",
  "private_key_id": "",
  "private_key": "",
  "client_email": "",
  "client_id": "",
  "auth_uri": "",
  "token_uri": "",
  "auth_provider_x509_cert_url": "",
  "client_x509_cert_url": "",
  "dataset_id": "",
  "region": ""
}


handle = clsBigQuery(config)

print(handle.testConnection()) # pass

# print(handle.getAllTables(include_view=True))

# print(handle.update_column_comment('Sonali', 'Age', ''))

# print(handle.getTableDetails(table_name='application_data'))
# print (handle.getAllTablesWithColumns(search='dim3')) # pass
# print (handle.getTableColumns(tablename='dim3')) # pass
# print (handle.getTableColumnsDetails(tbl_name='dim3')) # pass

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

# print (handle.readTable(tbl_name='dim3', limit=20)) # pass
# print (handle.getColumnLOV(full_table_name='dim3', col_name='Cluster')) # pass

# table_name = 'dim3'
# # _filter = None #"GJAHR = 2013"
# df = handle.getColumnsProfile(table_name, with_min_max=False) ## PASS
# print(df)

# tableDetails = {
#     "tableName": "My Table",
#     "createColumnData": [
#         {'source_column': 'Population', 'target_column': 'Population 1', 'datatype': 'INT'}
#     ]
# }
# print (handle.generateCreateTableScriptETL(tableDetails)) # pass


tablename = "my_table"
df = pd.DataFrame({
    'column1': [1, 2, 3],
    'column2': ['A', 'B', 'C'],
    'column3': [True, False, True]
})
print(handle.executeInsertUpdate(tablename, df))

# print(handle.executeInsertUpdate())
# DONE
