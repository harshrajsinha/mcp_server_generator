from DB2Handler import clsDB2DB

import pandas as pd

config = {}

config["hostname"] = ''
config["dbname"] = ""
config["dbuser"] = ''
config["pwd"] = ''
config["port"] = 60694
config["schema"] = ''

handle = clsDB2DB(config)

# print (handle.getAllTables(search=None, type=None, limit=None, include_view=True)) # pass
# print (handle.getTableDetails(table_name = 'DAILY_BUG_REPORT_CSV')) # pass

# print(handle.update_column_comment('DAILY_BUG_REPORT_CSV', 'TASK', ''))

# tableDetails = {
#     "tableName": "MyTable",
#     "createColumnData": [
#         {'source_column': 'Population', 'target_column': 'Population_1', 'datatype': 'INT'},
#         {'source_column': 'SomeText', 'target_column': 'Description', 'datatype': 'VARCHAR(200)'}
#     ]
# }
# print(handle.generateCreateTableScriptETL(tableDetails))


# ---------------------------------------------------------------------------------------
# print(handle.getTableRelationships(table_name='EMPLOYEES_CHILD_ADDRESS',bi_directional =True))

# OUTPUT
# Tables

## DEPARTMENTS_PARENT

#   TABLE_NAME        COL_NAME             REF_TABLE_NAME     REF_COL_NAME
# EMPLOYEES_CHILD   DEPTID_CHILD         DEPARTMENTS_PARENT   DEPTID_PARENT      

## EMPLOYEES_CHILD

#    TABLE_NAME                  COL_NAME             REF_TABLE_NAME          REF_COL_NAME
# EMPLOYEES_CHILD              DEPTID_CHILD         DEPARTMENTS_PARENT        DEPTID_PARENT
# EMPLOYEES_CHILD_ADDRESS        EMPID_A              EMPLOYEES_CHILD            EMPID


## EMPLOYEES_CHILD_ADDRESS

#      TABLE_NAME              COL_NAME               REF_TABLE_NAME          REF_COL_NAME
#   EMPLOYEES_CHILD_ADDRESS     EMPID_A              EMPLOYEES_CHILD             EMPID

# ---------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------
# print(handle.getTableRelationships(table_name='EMPLOYEES_CHILD_ADDRESS',bi_directional =False))

# OUTPUT
# Tables


## DEPARTMENTS_PARENT

## EMPLOYEES_CHILD

#   TABLE_NAME        COL_NAME             REF_TABLE_NAME          REF_COL_NAME
# EMPLOYEES_CHILD   DEPTID_CHILD         DEPARTMENTS_PARENT        DEPTID_PARENT


## EMPLOYEES_CHILD_ADDRESS

#      TABLE_NAME              COL_NAME              REF_TABLE_NAME          REF_COL_NAME
# EMPLOYEES_CHILD_ADDRESS       EMPID_A              EMPLOYEES_CHILD            EMPID


# ---------------------------------------------------------------------------------------