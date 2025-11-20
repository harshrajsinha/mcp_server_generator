from RedshiftHandler import clsRedshiftDB
import pandas as pd

config = {}

config["hostname"] = ''
config["dbuser"] = ''
config["pwd"] = ''
config["schema"] = ""
config["port"] = 5439
config["dbname"] = ""

handle = clsRedshiftDB(config)

# print(handle.testConnection()) # PASS 22/2/24
# print (handle.get_all_tables(search=None, type=None, limit=None, include_view=True)) # PASS 22/2/24
# print (handle.getAllTablesWithColumns(search='category'))  # PASS 22/2/24
# print (handle.getTableColumns(tablename='date')) # PASS 22/2/24
# print (handle.getTableDetails()) # PASS 22/2/24 ("TABLE_COMMENT, NO_OF_ROWS, LAST_UPDATED" [null])
# print (handle.getTableColumnsDetails(tbl_name='date')) # PASS 23/2/24(mssql)

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
# print (handle.generateCreateTableScript(tableDetails=tableDetails))# PASS 23/2/24 (schema name not there)

# tableDetails = {
#     "tableName": "employees_7",
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
# print (handle.generateCreateTableScriptETL(tableDetails)) # PASS 23/2/24

# print (handle.createTable(tableDetails,etl=True)) # PASS 23/2/24
# executeSql(successfull) (tested for createtable()) # PASS 23/2/24

# print (handle.readTable(tbl_name='category', limit=10)) # PASS 23/2/24
# executeQuery(successfull) (tested for readTable()) # PASS 23/2/24

# print (handle.getColumnLOV(table_name='category', col_name='catgroup')) # PASS 23/2/24

# table_name = 'category'
# _filter = None          # (col name)
# df = handle.getColumnsProfile(table_name, with_min_max=False, filter=_filter) # PASS 23/2/24 #(did data_type and column_name in small case)
# print(df)

# #############################################################################
# tablename = {"category": "t"}
# groupby = {"catid": {"type": "int2"}}
# query = "SELECT catid FROM category order by catid asc"
# filters = "catid=1" 
# columnnames = {
#     "id": [{"type": "int2"}]
# }
# schema = 'public'  
# print (handle.formatQuery(tablename=tablename, 
#                           groupby=groupby, 
#                           filters=filters,
#                           query=query,
#                           columnnames=columnnames, 
#                           schema=schema)) # FAILED 23/2/24 for group[1] where[1] # SELECT catid FROM "category" "t" WHERE SELECT catid FROM category order by catid asc GROUP BY SELECT catid FROM category order by catid asc (wrong query generated)
# formatFilter() # not_checked formatQuery(part) 23/2/24
# #############################################################################

# print (handle.getTableIndexDetails (tablename='card')) # PASS 23/2/24 
# print (handle.get_incremental_columns (table_name='card')) # PASS 23/2/24
# print (handle.fetch_delta_columns (table_name='date')) # PASS 23/2/24
# print(handle.update_column_comment('date', 'caldate', comment=None)) # PASS 23/2/24


# print(handle.get_connection_statement()) # PASS 26/2/2024   o/p   postgresql+psycopg2://awsuser:Scikiq123@skq-redshift-cluster-2.cwrcj7vqccns.ap-south-1.redshift.amazonaws.com:5439/dev

# tablename = "employees_4"               # example-1
# df = pd.DataFrame({
#     'id': ['100','110','120']
# })

# tablename = "date"                      # example-2
# # Create a DataFrame with example entries
# df = pd.DataFrame({
#     'dateid': [5, 6, 7],
#     'caldate': ['2024-02-1', '2024-02-2', '2024-02-3'],
#     'day': ['sunday', 'Tuesday', 'Wednesday'],
#     'week': [5, 2, 4],
#     'month': ['june', 'dec', 'February'],
#     'qtr': ['Q2', 'Q1', 'Q3'],
#     'year': [2024, 2024, 2024],
#     'holiday': [True, False, True]
# })
# print(handle.executeInsertUpdate(tablename, df)) # PASS 26/2/2024

# create_engine(successful) # PASS 26/2/2024


# view_name = "example_view"
# sql_query = "SELECT * FROM date"
# print(handle.createView(view_name, sql_query)) # PASS 26/2/2024

# #############################################################################
# print(handle.generateQuery(
#     tablename={"date": "t1", "listing": "t2"},
#     columnnames={"t1.dateid": "SUM", "t2.listid": "AVG"},
#     limit=10,
#     orderby={"t1.dateid": "ASC"},
#     filters={"condition": "t1.dateid > 10"},
#     groupby={"t2.dateid": "dateid"},
#     joins={"listing": "inner"},
#     joinCondition="t1.dateid = t2.listid",
#     distinct=1,
#     offset=20
# ))   # FAILED 26/2/2024
# getRenamesColMetricsDict()     # not_checked generateQuery(part) 26/2/2024
# where_recursive_condition()    # not_checked generateQuery(part) 26/2/2024
# formatQuery()                  # not_checked generateQuery(part) 26/2/2024
# createCustomColumnExpression() # not_checked generateQuery(part) 26/2/2024
# remove_double_quotes()         # not_checked generateQuery(part) 26/2/2024
# #############################################################################

# #############################################################################
# print(handle.updateTable()) # not_checked 26/2/2024
# updateType() not_checked updateTable(part) 26/2/2024
# getUpdateQuery() not_checked updateTable(part) 26/2/2024
# updateQueryUsingSubQuery() not_checked getUpdateQuery(part) 26/2/2024
# #############################################################################

# print(handle.truncateTable(table_name='employees_4')) # PASS 26/2/2024

# ############################################################################
# print(handle.getMergeQuery())      # not_checked 26/2/2024
# print(handle.find_row())           # not_checked 26/2/2024
# print(handle.insert_row())         # not_checked 26/2/2024
# print(handle.update_row())         # not_checked 26/2/2024
# print(handle.join_upd_query())     # not_checked 26/2/2024
# ############################################################################


# print(handle.dropTable(table_name='employees_4')) # PASS 26/2/2024
# getDropTableQuery() # successful dropTable(part) 26/2/2024


# ############################################################################
# print(handle.dq_dashboard_data_delete_query())        # not_checked 26/2/2024
# print(handle.dq_dashboard_data_freshness_query())     # not_checked 26/2/2024
# print(handle.dq_dashboard_data_modify_query())        # not_checked 26/2/2024
# print(handle.dq_dashboard_stk_query())                # not_checked 26/2/2024
# ############################################################################


# print (handle.getTableRows())

# -----------------------------------------------------------------------

# print (handle.getTableRelationships(table_name='projects_ch2')) # PASS 23/2/24 

# departments_p

#     table_name           col_name         ref_table_name      ref_col_name
#   employees_ch_1     department_id_ch1     departments_p     department_id_p


# employees_ch_1

#    table_name           col_name          ref_table_name       ref_col_name
#  employees_ch_1     department_id_ch1      departments_p     department_id_p
#   projects_ch2         manager_id          employees_ch_1    employee_id_ch1


# projects_ch2

#      table_name     ol_name     ref_table_name     ref_col_name
#     projects_ch2   manager_id   employees_ch_1    employee_id_ch1

# -----------------------------------------------------------------------

# DONE






















