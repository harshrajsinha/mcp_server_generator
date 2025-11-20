from SapHanaHandler import clsSapHana


config = {}
config["hostname"] = ''
config["dbuser"] = ''
config["pwd"] = ''
config["schema"] = ""
config["port"] = 30215
config["dbname"] = ""

handle = clsSapHana(config)

# print(handle.testConnection())

# tableDetails = {
#     "tableName": "example_table",
#     "createColumnData": [
#         {'source_column': 'Country', 'target_column': 'Country1', 'datatype': 'VARCHAR(255)'},
#         {'source_column': 'Population', 'target_column': 'Population1', 'datatype': 'INT'},
#         # Add more columns as needed
#     ]
# }

# print(handle.generateCreateTableScriptETL(tableDetails))

# ------------------------------------------------------------------------------------------- 

# print(handle.getTableRelationships(table_name='BORROWERS')) 

# AUTHORS

#   TABLE_NAME       COL_NAME           REF_TABLE_NAME      REF_COL_NAME
#     BOOKS        AUTHOR_ID_CHILD          AUTHORS        AUTHOR_ID_PARENT


# BOOKS

#    TABLE_NAME         COL_NAME         REF_TABLE_NAME      REF_COL_NAME
#    BORROWERS       BOOK_ID_CHILD2         BOOKS               BOOK_ID
#      BOOKS         AUTHOR_ID_CHILD        AUTHORS         AUTHOR_ID_PARENT


# BORROWERS

#   TABLE_NAME       COL_NAME          REF_TABLE_NAME   REF_COL_NAME
#    BORROWERS     BOOK_ID_CHILD2          BOOKS          BOOK_ID

# ------------------------------------------------------------------------------------------- 
