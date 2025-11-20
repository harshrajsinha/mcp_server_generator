from SnowflakeHandler import clsSnowflake

config = {}

config["hostname"] = ''
config["dbuser"] = ''
config["pwd"] = ''
config["port"] = 443
config["dbType"] = ""
config["dbname"] = ""
config["schema"] = ""
config["warehouse"] = ""

handle = clsSnowflake(config)

# print(handle.testConnection())

# print(handle.getAllTables(include_view=True)) 

# print(handle.update_column_comment('SCIKIQ_ETL_DATA25033', 'FLAG_OWN_REALTY', ''))

# print(handle.readTable(tbl_name, 2000, src_type=src_type, filter = filter, column_name=column_name)) ## PASS

# res = handle.readTable(tbl_name, 2000, src_type=src_type, filter = filter)
# print(res["df"])
# print(handle.getTableColumnsDetails(tbl_name='SCIKIQ_ETL_DATA25033')) ## PASS
# print(handle.getTableColumns(tablename=tbl_name, type=src_type)) ## PASS
# print(handle.getTableRowCount(table_name=tbl_name, type=src_type, filter=filter)) ## PASS

# print(handle.getTableRelationships(table_name=tbl_name))


# print(handle.getTableDetails(table_name=tbl_name, type=src_type))

## not implemented print(handle.getAllTablesWithColumns(search='ZRT_ADSO'))
## not implemented  print(handle.getColumnLOV(table_name='ZRT_ADSO',col_name='4ZRT_ADSO_STOREDISCOUNTMASKED'))
# import pdb; pdb.set_trace()
# print(handle.getColumnsProfile(table_name='TCURR_lowercase'))

## ------------------------------------------- *************************** -------------------------------------------

# handle = clsSAPAppServer(config)
# print(handle.testConnection())

# filter = "GDATU >= '79918776'"
# #filter = "TCURR = 'USD'"
# print(handle.readTable('TCURR', filter = filter, limit = 200, src_type = 'TBL'))


#print(handle.getColumnsProfile(table_name='TCURR'))
# cols = handle.getTableColumnsDetails('TCURR')
# df_col_dtls = pd.DataFrame.from_dict(cols, orient='columns')
# df_col_curr = df_col_dtls[(df_col_dtls['DATA_TYPE'] =='CURR') & (df_col_dtls['CONVEXIT'] =='')]   
# df_col_dtls = df_col_dtls[df_col_dtls['CONVEXIT']!='']
# print(df_col_dtls)
# print(df_col_curr)
# data = handle.getTableDetails(['BSEG'], type = 'TBL')
# print(data)

## column data
# data = handle.getTableColumnsDetails('VBAK')
# #print(df)
# df = pd.DataFrame.from_dict(data, orient='columns')
# print(df[df['COLUMN_NAME']=='ZABDATH'])
# #print(df)

## row count with filter
# data = handle.getTableRowCount('BSEG', "GJAHR = 2020" )
# print(data)

#print(df['CONVEXIT'].unique())
# print(df['DATA_TYPE_LENGTH'].agg(['sum']))s

# print("','".join(df['COLUMN_NAME']))

# options = "TABNAME like 'PCL1'" ## DD02T  SAP S4 Table
# options = "DATASOURCE BETWEEN '0DIS' AND '0Z'" ## BW4HANA EXT SEARCH

# print(handle.getAllTables(options, 'EXT', 1000))


# options = "DDLNAME LIKE 'I_SALESORDERITE%'" ## DD02T  SAP S4 Table
# import pdb; pdb.set_trace()
# print(handle.getAllTables(options, 'CDS', 200))

# options = "DATAEXTRACTIONVIEWNAME LIKE '%'" ## DD02T  SAP S4 Table
# print(handle.getAllTables(options, 'EXT', 200))

##"P_EXCHANGERATETYPE = 'P', P_DISPLAYCURRENCY = 'EUR'"
# params = {'P_EXCHANGERATETYPE' : 'P', 'P_DISPLAYCURRENCY' : 'EUR'}
# print(handle.readTable('I_SALESORDERITEMCUBE', filter = None, limit = 10, src_type = 'CDS', params = params))
# print(handle.readTable('I_PROFITCENTERDETAILS', filter = None, limit = 10, src_type = 'CDS', params = {}))

# print(handle.generateQuery(tablename={'VW_REP_DATE_DIMENSION' : 'a'},distinct=0))

# ----------------------------------------------------------

# print(handle.getTableRelationships(table_name='ORDERDETAILS'))

# CUSTOMERS

#   TABLE_NAME  COL_NAME   REF_TABLE_NAME   REF_COL_NAME
#     ORDERS                 CUSTOMERS


# ORDERS

#    TABLE_NAME     COL_NAME      REF_TABLE_NAME     REF_COL_NAME
#   ORDERDETAILS                     ORDERS
#     ORDERS                        CUSTOMERS


# ORDERDETAILS

#    TABLE_NAME      COL_NAME    REF_TABLE_NAME   REF_COL_NAME
#   ORDERDETAILS                    ORDERS

# ----------------------------------------------------------