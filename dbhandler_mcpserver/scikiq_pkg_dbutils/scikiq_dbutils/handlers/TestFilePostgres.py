from PostgresHandler import clsPostgresDB
import pandas as pd

config = {}

config["hostname"] = ''
config["dbuser"] = ''
config["pwd"] = ''
# config["dbType"] = "POSTGRES"
config["schema"] = ""
config["port"] = 60696
config["dbname"] = ""

handle = clsPostgresDB(config)

# print(handle.testConnection()) # pass
# print (handle.getAllTables(search=None, type=None, limit=None, include_view=True)) # pass
# print (handle.getAllTablesWithColumns(search='fact')) # pass
# print (handle.getTableColumns(tablename='BOOK')) # pass
# print (handle.getTableColumnsDetails(tbl_name="ORDERS")) # pass

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

# print (handle.readTable(tbl_name='Events', limit=20)) # pass

# print (handle.getTableDetails(table_name='daily_bug_report_csv')) # pass

# print (handle. getColumnLOV(table_name='daily_bug_report_csv', col_name='bug', order='ASC')) # pass
# print (handle.getColumnsProfile(table_name='b_table_test')) # pass

# tableDetails = {
#     "tableName": "My Table",
#     "createColumnData": [
#         {'source_column': 'Population', 'target_column': 'Population 1', 'datatype': 'INT'}
#     ]
# }
# print (handle.generateCreateTableScriptETL(tableDetails)) # pass

# print(handle.fetch_delta_columns(table_name='counterparty'))



# print(handle.update_column_comment('counterparty', 'id', ''))

# Assuming you have an instance of YourDatabaseClass named 'database_instance'

# # Example row and conditions
# row_data = {"Event_id": "1"}
# conditions = [
#     {"target_col": "Event_id", "condition": "=", "source_col": "Event_id"}
# ]

# print(handle.find_row( tbl_name="Events",row=row_data,on_condition=conditions,manage_connection=True))

# ---------------------------------------------------------------------------------------------------------

# print(handle.getTableRelationships(table_name='order_items')) 

# OUTPUT
# Tables 

# customers_parent

    # table_name                  col_name                ref_table_name        ref_col_name
    # orders_child        customer_id_orders_child       customers_parent     customer_id_parent


# orders_child

#      table_name                col_name            ref_table_name        ref_col_name
#     orders_child      customer_id_orders_child   customers_parent      customer_id_parent
#      order_items      order_id_order_items_child   orders_child            order_id


# order_items

#     table_name             col_name               ref_table_name    ref_col_name
#     order_items    order_id_order_items_child      orders_child       order_id

# ------------------------------------------------------------------------------------------- 

# DONE









