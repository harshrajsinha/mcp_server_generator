# from SAPAppServerHandler import clsSAPAppServer

# import pandas as pd

# config = {}

# config["hostname"] = ''
# config["dbuser"] = ''
# config["pwd"] = ''
# config["client"] = ''
# config["router"] = ''
# config["sysnr"] = ''
# config["dbType"] = ""
# config["port"] = 8876

# ## bw MACHINE
# config["hostname"] = ''
# config["dbuser"] = ''
# config["pwd"] = ''
# config["client"] = ''
# config["router"] = ''
# config["sysnr"] = ''
# config["dbType"] = ""
# config["port"] = 8876


# handle = clsSAPAppServer(config)

# '''
# ADSO use cases
# '''

# tbl_name  = "ZEM_DATA"
# src_type = "ADSO"
# search = "EMP"
# filter = "1=1" 

# '''
# DSO use cases
# '''

# tbl_name  = "0BP_CUST" ## "0PA_DS04"  #"0PA_DS01" #"0GN_BP" #"0BP_VEND"  #"0BP_REL"  #"0AS_DS01" #"0BP_ID"  #"0BP_CUST"  ##"ZEMP_DSO"
# src_type = "DSO"
# search = "ZEMP"
# filter = "1=1" 

# '''
# IC use cases
# '''

# tbl_name  =  "0PA_C01" ## "0TCT_VC01"   ## "0PA_C01" ## has data
# src_type = "IC"
# search = ""
# filter = "CALMONTH = '199708'" 

# _range = [
#     dict(
#         CHANM = 'CALMONTH',
#         SIGN = 'E',
#         COMPOP = 'EQ',
#         LOW = '199708',
#         HIGH = ''
#     ),
#     dict(
#         CHANM = 'REQUID',
#         SIGN = 'I',
#         COMPOP = 'EQ',
#         LOW = 'DTPR_D9WBRDL8GCGACF3IYRMMRVZI5',
#         HIGH = ''
#     )
#     ,
#     dict(
#         CHANM = 'EMPLOYEE',
#         SIGN = 'I',
#         COMPOP = 'BT',
#         LOW = '00900124',
#         HIGH = '00900131'
#     )
# ]

# df = handle.readTable(tbl_name, limit = 1000, src_type = src_type, range = _range) ## PASS

# print(df)

