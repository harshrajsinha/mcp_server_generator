from OracleHandler import clsOracleDB
import pandas as pd
      
config = {}

config["hostname"] = ''
config["dbuser"] = ''
config["pwd"] = ''
config["port"] = 1522
config["dbType"] = ""
config["dbname"] = ""
config["schema"] = ""

handle = clsOracleDB(config)

# print(handle.testConnection())

# res = handle.readTable("ORDERS", 1)
# print(res["df"])

# df = res["df"]

# condition = [{
#     "target_col": "ID",
#     "condition": "=",
#     "source_col": "ID"
# }]

# col_dtls = handle.getTableColumnsDetails("ORDERS")
# col_dtls = pd.DataFrame(col_dtls)

# matched_mapping = {
#     "CREATED_BY": "CREATED_BY",
#     "CREATED_DATE": "CREATED_DATE",
#     "CUSTOMER_ID": "CUSTOMER_ID",
#     "ID": "ID",
#     "PRICE": "PRICE",
#     "PRODUCT_ID": "PRODUCT_ID",
#     "QUANTITY": "QUANTITY",
#     "STORE_ID": "STORE_ID",
#     "TOTAL_AMOUNT": "TOTAL_AMOUNT"
# }

# for index, row in df.iterrows():
#     print(handle.insert_row("ORDERS", row, matched_mapping, col_dtls))
#     # if handle.find_row("ORDERS", row, condition) :
#     #     handle.update_row("ORDERS", row, condition, matched_mapping, col_dtls)


# -----------------------------------------------------------------------

print(handle.getTableRelationships(table_name='USERS'))

# Tables

# USERS

#   TABLE_NAME    COL_NAME      REF_TABLE_NAME    REF_COL_NAME
#   ORDERS_CH      USERID          USERS              USERID


# ORDERS_CH

#       TABLE_NAME      COL_NAME        REF_TABLE_NAME      REF_COL_NAME
#       ORDERITEMS_CH    ORDERID            ORDERS_CH           ORDERID


# ORDERITEMS_CH


# -----------------------------------------------------------------------