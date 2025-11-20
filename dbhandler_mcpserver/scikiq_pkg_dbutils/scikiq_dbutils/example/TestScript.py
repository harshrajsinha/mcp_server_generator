# from SAPAppServerHandler import clsSAPAppServer
# from SapHanaHandler import clsSapHana
# from RFCHandler import clsRFCDB
# import pandas as pd

# config = {}

# config["hostname"] = ''
# config["dbuser"] = ''
# config["pwd"] = ''
# config["client"] = ''
# config["router"] = ''
# config["sysnr"] = ''
# config["dbType"] = ""

# config["hostname"] = ''
# config["dbuser"] = ''
# config["pwd"] = ''
# config["client"] = ''
# config["router"] = ''
# config["sysnr"] = ''
# config["dbType"] = ""
# config["port"] = 8876

# config["hostname"] = ''
# config["dbuser"] = ''
# config["pwd"] = ''
# config["dbType"] = ""
# config["schema"] = ""
# config["port"] = 30515
# config["dbname"] = ""
# config["catalog_name"] = ""
# config["is_bw4hana"] = ""


# handle = clsRFCDB(config)
#handle = clsSapHana(config)
# handle = clsSAPAppServer(config)

# print(handle.getTableColumnsDetails(tablename='ZDL_FM_AP'))

# '''
# ADSO use cases
# '''

# # tbl_name  = "ZEM_DATA"
# # src_type = "ADSO"
# # search = "EMP"
# # filter = "1=1" 

# '''
# DSO use cases
# '''

# tbl_name  = "0PA_DS04"  #"0PA_DS01" #"0GN_BP" #"0BP_VEND"  #"0BP_REL"  #"0AS_DS01" #"0BP_ID"  #"0BP_CUST"  ##"ZEMP_DSO"
# src_type = "DSO"
# search = ""
# filter = "1=1" 

# '''
# IC use cases
# '''

# tbl_name  = "0TCT_VC01"   ## "0PA_C01" ## has data
# src_type = "IC"
# search = ""
# filter = "1=1" 

# '''
# IO use cases
# '''

# tbl_name  = "TCURR" ##"/CPMB/RULE"   ##  "0HC_CATIND1" error info object not found
# src_type = "TBL"
# search = ""
# filter = "1=1" 

# column_name = ['TCURR', 'FCURR']
# filter = "TCURR = 'USD'"

# tbl_name  = "0EMPLOYEE"   ##  "0HC_CATIND1" error info object not found
# src_type = "IO"
# search = ""
# filter = "1=1" 

# print(handle.testConnection())
# print(handle.get_all_tables(search=search, type=src_type, limit = 100)) ## PASS
# print(handle.readTable(tbl_name, 2000, src_type=src_type, filter = filter, column_name=column_name)) ## PASS
# print(handle.readTable(tbl_name, 2000, src_type=src_type)) ## PASS
# print(handle.getTableColumnsDetails(tablename=tbl_name, type=src_type)) ## PASS
# print(handle.getTableColumns(tablename=tbl_name, type=src_type)) ## PASS
# print(handle.getTableRowCount(table_name=tbl_name, type=src_type, filter=filter)) ## PASS
# print(handle.getTableDetails(table_name=tbl_name, type=src_type))

# not implemented print(handle.getAllTablesWithColumns(search='ZRT_ADSO'))
# not implemented  print(handle.getColumnLOV(table_name='ZRT_ADSO',col_name='4ZRT_ADSO_STOREDISCOUNTMASKED'))
# not implemented print(handle.getColumnsProfile(table_name='ZEM_DATA', type='ADSO'))

# ## ------------------------------------------- *************************** -------------------------------------------

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

# print(handle.get_all_tables(options, 'EXT', 1000))


# options = "DDLNAME LIKE 'I_SALESORDERITE%'" ## DD02T  SAP S4 Table
# import pdb; pdb.set_trace()
# print(handle.get_all_tables(options, 'CDS', 200))

# options = "DATAEXTRACTIONVIEWNAME LIKE '%'" ## DD02T  SAP S4 Table
# print(handle.get_all_tables(options, 'EXT', 200))

##"P_EXCHANGERATETYPE = 'P', P_DISPLAYCURRENCY = 'EUR'"
# params = {'P_EXCHANGERATETYPE' : 'P', 'P_DISPLAYCURRENCY' : 'EUR'}
# print(handle.readTable('I_SALESORDERITEMCUBE', filter = None, limit = 10, src_type = 'CDS', params = params))
# print(handle.readTable('I_PROFITCENTERDETAILS', filter = None, limit = 10, src_type = 'CDS', params = {}))

