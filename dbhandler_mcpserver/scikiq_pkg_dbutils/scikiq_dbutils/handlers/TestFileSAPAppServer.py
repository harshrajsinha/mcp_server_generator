from SAPAppServerHandler import clsSAPAppServer

import pandas as pd

config = {}

# config["hostname"]= ''
# config["dbuser"]=''
# config["pwd"]=''
# config["client"]=''
# config["router"]=''
# config["sysnr"]=''
# config["dbType"] = ""

#sanbox
# config["hostname"]= ''
# config["dbuser"]=''
# config["pwd"]=''
# config["client"]=''
# config["router"]=''
# config["sysnr"]=''
# config["dbType"] = ""


handle = clsSAPAppServer(config)

print(handle.testConnection()) # pass

# tbl_name  = "TCURR" 
# src_type = "TBL"
# search = ""

# print(handle.getAllTables(search=search, type=src_type, limit = 100)) ## PASS

# print(handle.readTable(tbl_name="BSEG", limit=2000)) ## PASS

# print(handle.getTableColumnsDetails(tbl_name="TCURR", type="tbl" )) ## PASS

# print(handle.getTableColumns(tablename="TCURR", type="tbl")) ## PASS

# print(handle.getTableRowCount(table_name=tbl_name, type=src_type, filter=filter)) ## PASS
# print(handle.getTableDetails(table_name=tbl_name, type=src_type))

## not implemented print(handle.getAllTablesWithColumns(search='ZRT_ADSO'))
## not implemented  print(handle.getColumnLOV(table_name='ZRT_ADSO',col_name='4ZRT_ADSO_STOREDISCOUNTMASKED'))
## not implemented print(handle.getColumnsProfile(table_name='ZEM_DATA', type='ADSO'))

# print(handle.fetch_delta_columns(table_name="TCURR",type="tbl"))

# print(handle.get_incremental_columns(tablename="TCURR",type="tbl"))