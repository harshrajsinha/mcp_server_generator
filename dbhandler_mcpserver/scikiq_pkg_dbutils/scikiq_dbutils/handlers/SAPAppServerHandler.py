# PYTHON PACKAGES
from asyncio.subprocess import PIPE
from unittest import result
from pyrfc import Connection
import pandas as pd
import json

# CUSTOM PACKAGES
from scikiq_dbutils.messages import ScikiqMessages
from scikiq_dbutils.handlers.DBConnection import clsDBConnection
from scikiq_dbutils.handlers.DataTypeConversion import convertDataType


class SAPObjType():
    DSO         = "DSO"
    ADSO        = "ADSO"
    INFOCUBE    = "IC"
    INFOOBJECT  = "IO"
    TABLE       = "TBL"
    CDSVIEW     = "CDS"
    EXTRACTOR   = "EXT"
    TRANS_TBL   = "TRANSP" 
    BAPI        = "BAPI"   
    ## OP-11490 T030 table is not a transparent table, it is a pool table
    POOL        = "POOL"


class SAPDelimiter() :
    HASH = "###"
    HASH2 = "#$^"
    PIPE = "|"
    EOL  = chr(30)

class SAPOptions()  :
    BLNK = []    

class clsSAPAppServer(clsDBConnection):
    """
        Usage:
    """

    def __init__(self, config):
        if ("resource_key" in config):
            self.resource_key = config["resource_key"]
        else:
            self.resource_key = None

        self.host = config["hostname"]
        self.user = config["dbuser"]
        self.password = config["pwd"]
        self.client = config["client"]
        self.router = config["router"]
        self.sysnr = config["sysnr"]

        self.engine_statement = None
        self.connection = None
        self.cursor = None
        self.db_type = config["dbType"]

        if "connection_type" in config:
            self.connection_type = config["connection_type"]
        else:
            self.connection_type = None

    def getConnectionType(self):
        if self.connection_type is None:
            return "SR"
        else:
            return self.connection_type

    def connect(self):
        try:
            resp = {}
            resp['resource_call'] = 'connect'

            self.connection = Connection(
                user=self.user,
                passwd=self.password,
                ashost=self.host,
                sysnr=self.sysnr,
                saprouter=self.router,
                client=self.client,
            )

            # callConnectionAudit using for audit the record.
            resp['msg'] = 'successfully connected.'
            resp['error'] = 0
            super(clsSAPAppServer, self).callConnectionAudit(resp)

        except Exception as e:
            # callConnectionAudit using for audit the record.
            resp['msg'] = str(e)
            resp['error'] = 1
            super(clsSAPAppServer, self).callConnectionAudit(resp)
            raise

    def close(self):
        if self.connection:
            self.connection.close()

    def update_column_comment(self, tbl_name, col_name, comment, **others):
        return False            

    def testConnection(self):
        resp = {}

        try:
            connection = Connection(
                user=self.user,
                passwd=self.password,
                ashost=self.host,
                sysnr=self.sysnr,
                saprouter=self.router,
                client=self.client,
            )

            connection.close()
            resp['error'] = 0
            resp['msg'] = ScikiqMessages.MSG_SUCCESS

        except Exception as e:
            resp['error'] = 1
            resp['msg'] = str(e)

        # callConnectionAudit using for audit the record.
        # super(clsSAPAppServer, self).callConnectionAudit(resp)
        return resp

    def createView(self, view_name, sql_query):
        pass

    def executeQuery(self, query, limit=None, manage_connection=True, use_polars=False, batch_size=10000, profile=False):
        results = None
        return results

    def executeSql(self, query, value=None, manage_connection=True):
        pass

    def executeInsertUpdate(self, tablename, df, if_exists='replace', chunksize=1000, dtype={}):
        """
        Insert pandas DataFrame into SAP table via custom RFC.
        
        Parameters
        ----------
        table_name : str
            Target SAP table
        df : pd.DataFrame
            DataFrame with rows to insert
        column_list : list
            List of DataFrame columns to insert
        rfc_name : str
            RFC name (Z_INSERT_DYNAMIC_ECC or Z_INSERT_DYNAMIC_ADBC)
        chunk_size : int
            Batch size for insert
        """

        # Step 1: fetch SAP table metadata
        self.connect()
        field_info = self.connection.call("DDIF_FIELDINFO_GET", TABNAME=tablename)
        sap_fields = {f["FIELDNAME"]: f for f in field_info["DFIES_TAB"]}


        column_list = df.columns.tolist() 
        # Step 2: build IT_COLUMNS
        it_columns = []
        for col in column_list:
            if col not in sap_fields:
                raise ValueError(f"Column {col} not found in SAP table {tablename}")
            fmeta = sap_fields[col]
            start_index = fmeta["OFFSET"]
            end_index = fmeta["OFFSET"] + fmeta["LENG"]
            it_columns.append({
                "COL_NAME": col,
                "START_INDEX": start_index,
                "END_INDEX": end_index
            })

        # Step 3: prepare data in chunks
        total_rows = len(df)
        for start in range(0, total_rows, chunksize):
            subset = df.iloc[start:start+chunksize]
            it_data = []
            row_length = max([c["END_INDEX"] for c in it_columns])

            for _, row in subset.iterrows():
                buffer = [" "] * row_length
                for col in column_list:
                    fmeta = sap_fields[col]
                    start_idx = fmeta["OFFSET"]
                    length = fmeta["LENG"]
                    value = str(row[col])[:length]
                    buffer[start_idx:start_idx+len(value)] = value
                it_data.append("".join(buffer))

            # Step 4: call custom RFC
            result = self.connection.call(
                "Z_INSERT_DYNAMIC_ECC",
                IV_TABLE_NAME=tablename,
                IT_DATA=it_data,
                IT_COLUMNS=it_columns
            )

        self.close()
        return df

    def generateSAPSearch(self,search,type):
        if type == SAPObjType.EXTRACTOR and self.db_type == "S4HANA":
            tabname = 'DATAEXTRACTIONVIEWNAME'
        elif type == SAPObjType.EXTRACTOR and self.db_type == "BW4HANA":
            tabname = 'DATASOURCE'
        elif type == SAPObjType.CDSVIEW:
            tabname = 'DDLNAME'     
        elif type == SAPObjType.BAPI:
            tabname = 'FUNCNAME'     
        else:
            tabname = 'TABNAME'

        #generate search filter from advance option
        table_name = search['table_name']
        option  = "{} like '{}%'".format(tabname, table_name)
        if 'adv_search' in search and search['adv_search']:
            adv_search = json.loads(search['adv_search'])
            if adv_search['search_type'] == 'single':
                for s_data in adv_search['search_data']:
                    option += " OR {} = '{}'".format(tabname, s_data['from'])
            if adv_search['search_type'] == 'multi':
                for s_data in adv_search['search_data']:
                    option += " OR {} BETWEEN '{}' AND '{}'".format(tabname, s_data['from'], s_data['to'])
        return option

    def get_all_tables(self, search, type, limit):
        #options = [{'TEXT': "TABNAME LIKE 'BSEG%'"}] ## DD02T  SAP S4 Table
        #adv_search: {'table_name':'TCURR','adv_search':{"search_type": "single", "search_data": [{"from": "MAST"}]}
        # if search type list of dict
        if isinstance(search, dict):
            search = self.generateSAPSearch(search, type)
        
        tbl_name = ''
        
        c_type = type
        if type in (SAPObjType.TABLE, SAPObjType.TRANS_TBL, SAPObjType.POOL):
            tbl_name = 'DD02L'
        elif type == SAPObjType.EXTRACTOR and self.db_type == "S4HANA" :
            tbl_name = 'IXTRCTNENBLDVW'
        elif type == SAPObjType.EXTRACTOR and self.db_type == "BW4HANA" :
            tbl_name = 'RSDS'
        elif type == SAPObjType.CDSVIEW :
            tbl_name = 'DDDDLSRCT'
        elif type == SAPObjType.BAPI :
            tbl_name = 'TFTIT'            
            c_type = SAPObjType.TABLE
        elif type in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT, SAPObjType.DSO, SAPObjType.ADSO]:  ###'IC', 'IO', 'DSO', 'ADSO']:
            tbl_name = ""

        result = self.readTable(tbl_name, limit=limit, filter = search, src_type=c_type)
        result = result["df"]
        
        if type == SAPObjType.EXTRACTOR :
            result['TABLE_TYPE'] = type            
            result.rename(columns = {
                'DATAEXTRACTIONVIEWNAME' : 'TABLE_NAME'
            }, inplace = True) 
            result.rename(columns = {
                'DATASOURCE' : 'TABLE_NAME'
            }, inplace = True)    
        elif  type == SAPObjType.CDSVIEW :
            result['TABLE_TYPE'] = type         
            result.rename(columns = {
                'DDLNAME' : 'TABLE_NAME'
            }, inplace = True)  
        elif  type == SAPObjType.BAPI :
            result['TABLE_TYPE'] = type         
            result.rename(columns = {
                'FUNCNAME' : 'TABLE_NAME'
            }, inplace = True)              
        elif type in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT, SAPObjType.DSO, SAPObjType.ADSO]:
            result['TABLE_TYPE'] = type            
            result.rename(columns = {
                'TECHNICAL_NAME' : 'TABLE_NAME'
            }, inplace = True) 
        else :
            result.rename(columns = {
                'TABNAME' : 'TABLE_NAME',
                'TABCLASS' : 'TABLE_TYPE'
            }, inplace = True)  

        result['TABLE_SCHEMA'] = ''  ## dummy value for TABLE_SCHEMA

        return result.to_dict(orient="records") 

    def getAllTablesWithColumns(self, search):
        pass

    def getTableColumns(self, tablename, type = SAPObjType.TABLE):
        df = None        
        col_name = ['COLUMN_NAME', 'DATA_TYPE']        
        self.connect()

        if type in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT, SAPObjType.DSO, SAPObjType.ADSO]:
            result = self.connection.call(
                'Z_DM_SCIKIQ',
                CATEGORY            =   type,
                SEARCH_TECHNICAL    =   "",
                SEARCH_NAME         =   "",
                NAME                =   tablename,
                DELIMITER           =   SAPDelimiter.HASH,
                NO_DATA             =   "",
                OPTIONS             =   SAPOptions.BLNK,
                ROWSKIPS            =   0,
                ROWCOUNT            =   1,
                COUNT_ONLY          =   "",
                DELTA               =   "",
                DELTA_START_DATE    =   None,
                DELTA_END_DATE      =   None                                                        
            ) 

            col_lst = result['METADATA']

            '''
            {
                'COUNT_DATA': 1, 
                'COUNT_LIST': 0, 
                'COUNT_TEXT': 0, 
                'RETURN': '', 
                'LIST': [], 
                'METADATA': [   
                    {'FIELDNAME': 'PERNR', 'OFFSET': '000000', 'LENGTH': '000008', 'TYPE': 'N', 'FIELDTEXT': 'Personnel number', 'KEYFIELD': 'X'}, 
                    {'FIELDNAME': 'SLART', 'OFFSET': '000011', 'LENGTH': '000002', 'TYPE': 'C', 'FIELDTEXT': 'Educational establishment', 'KEYFIELD': 'X'}, 
                    {'FIELDNAME': 'DATETO', 'OFFSET': '000016', 'LENGTH': '000008', 'TYPE': 'D', 'FIELDTEXT': 'End Date', 'KEYFIELD': 'X'}, 
                    {'FIELDNAME': 'RECORDMODE', 'OFFSET': '000027', 'LENGTH': '000001', 'TYPE': 'C', 'FIELDTEXT': 'BW Delta Process: Record Mode', 'KEYFIELD': ''}, 
                    {'FIELDNAME': 'DATEFROM', 'OFFSET': '000031', 'LENGTH': '000008', 'TYPE': 'D', 'FIELDTEXT': 'Start Date', 'KEYFIELD': ''}, 
                    {'FIELDNAME': 'JBEZ1', 'OFFSET': '000163', 'LENGTH': '000011', 'TYPE': 'P', 'FIELDTEXT': 'Course fees', 'KEYFIELD': ''}, 
                ], 
                'METADATA_TEXT': [], 
                'OPTIONS': [], 
                'OPTIONS_TEXT': [], 
                'RANGE': [], 
                'TAB': [{'WA': '00000111###51###99991231###N###00000000###  ###   ###00000000###  ###00000###00000###   0.00 ###     ### ###  ###  ######'}], 
                'TAB_TEXT': []
            }

            '''

            for col in col_lst :
                data = [[col['FIELDNAME'].strip(), col['TYPE'].strip()]]

                if df is None :
                    df = pd.DataFrame(data, columns = col_name)
                else :
                    df1 = pd.DataFrame(data, columns = col_name)
                    df_list = [df]
                    df_list.append(df1)
                    df = pd.concat(df_list, ignore_index=True)

            df.fillna(0, inplace = True)       

        else :
            res = self.connection.call('DDIF_FIELDINFO_GET', TABNAME= tablename)
            col_lst = res['DFIES_TAB']

            '''
            Sample data from DDIF_FIELDINFO_GET key DFIES_TAB
            {
                'TABNAME': 'TCURR', 'FIELDNAME': 'MANDT', 'LANGU': 'E', 
                'POSITION': '0001', 'OFFSET': '000000', 'DOMNAME': 'MANDT',
                'ROLLNAME': 'MANDT', 'CHECKTABLE': 'T000', 'LENG': '000003', 
                'INTLEN': '000006', 'OUTPUTLEN': '000003', 'DECIMALS': '000000', 'DATATYPE': 'CLNT', 
                'INTTYPE': 'C', 'REFTABLE': '', 'REFFIELD': '', 'PRECFIELD': 'TCURR', 'AUTHORID': '', 
                'MEMORYID': '', 'LOGFLAG': '', 'MASK': '', 'MASKLEN': '0000', 'CONVEXIT': '', 'HEADLEN': '03', 
                'SCRLEN1': '10', 'SCRLEN2': '15', 'SCRLEN3': '20', 'FIELDTEXT': 'Client', 'REPTEXT': 'Cl.',
                'SCRTEXT_S': 'Client', 'SCRTEXT_M': 'Client', 'SCRTEXT_L': 'Client', 'KEYFLAG': 'X', 
                'LOWERCASE': '', 'MAC': '', 'GENKEY': '', 'NOFORKEY': '', 'VALEXI': '', 
                'NOAUTHCH': '', 'SIGN': '', 'DYNPFLD': 'X', 'F4AVAILABL': 'X', 
                'COMPTYPE': 'E', 'LFIELDNAME': 'MANDT', 'LTRFLDDIS': '', 'BIDICTRLC': '',
                'OUTPUTSTYLE': '00', 'NOHISTORY': '', 'AMPMFORMAT': ''
            }        
            '''

            for col in col_lst :
                data = [[col['FIELDNAME'].strip(), col['DATATYPE'].strip()]]

                if df is None :
                    df = pd.DataFrame(data, columns = col_name)
                else :
                    df1 = pd.DataFrame(data, columns = col_name)
                    df_list = [df]
                    df_list.append(df1)
                    df = pd.concat(df_list, ignore_index=True)

            df.fillna(0, inplace = True)       

        self.close()   
        return df.to_dict(orient="records")  

    def getTableColumnsDetails(self, tbl_name, **others):

        type_ = others.get("type", SAPObjType.TABLE)

        df = None
        col_name = [
            'TABLE_SCHEMA',
            'TABLE_NAME', 
            'COLUMN_NAME', 
            'DATA_TYPE', 
            'DATA_TYPE_LENGTH', 
            'NUMERIC_PRECISION', 
            'IS_NULLABLE', 
            'CHARACTER_MAX_LENGTH', 
            'CHARACTER_MAXIMUM_LENGTH', 
            'NUMERIC_SCALE', 
            'ORDINAL_POSITION',
            'CONVEXIT',
            'COMMENT'
        ]

        self.connect()

        if type_ in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT, SAPObjType.DSO, SAPObjType.ADSO]:
            result = self.connection.call(
                'Z_DM_SCIKIQ',
                CATEGORY            =   type_,
                SEARCH_TECHNICAL    =   "",
                SEARCH_NAME         =   "",
                NAME                =   tbl_name,
                DELIMITER           =   SAPDelimiter.HASH,
                NO_DATA             =   "",
                OPTIONS             =   SAPOptions.BLNK,
                ROWSKIPS            =   0,
                ROWCOUNT            =   1,
                COUNT_ONLY          =   "",
                DELTA               =   "",
                DELTA_START_DATE    =   None,
                DELTA_END_DATE      =   None                                                        
            ) 

            col_lst = result['METADATA']

            '''
            {
                'COUNT_DATA': 1, 
                'COUNT_LIST': 0, 
                'COUNT_TEXT': 0, 
                'RETURN': '', 
                'LIST': [], 
                'METADATA': [   
                    {'FIELDNAME': 'PERNR', 'OFFSET': '000000', 'LENGTH': '000008', 'TYPE': 'N', 'FIELDTEXT': 'Personnel number', 'KEYFIELD': 'X'}, 
                    {'FIELDNAME': 'SLART', 'OFFSET': '000011', 'LENGTH': '000002', 'TYPE': 'C', 'FIELDTEXT': 'Educational establishment', 'KEYFIELD': 'X'}, 
                    {'FIELDNAME': 'DATETO', 'OFFSET': '000016', 'LENGTH': '000008', 'TYPE': 'D', 'FIELDTEXT': 'End Date', 'KEYFIELD': 'X'}, 
                    {'FIELDNAME': 'RECORDMODE', 'OFFSET': '000027', 'LENGTH': '000001', 'TYPE': 'C', 'FIELDTEXT': 'BW Delta Process: Record Mode', 'KEYFIELD': ''}, 
                    {'FIELDNAME': 'DATEFROM', 'OFFSET': '000031', 'LENGTH': '000008', 'TYPE': 'D', 'FIELDTEXT': 'Start Date', 'KEYFIELD': ''}, 
                    {'FIELDNAME': 'JBEZ1', 'OFFSET': '000163', 'LENGTH': '000011', 'TYPE': 'P', 'FIELDTEXT': 'Course fees', 'KEYFIELD': ''}, 
                ], 
                'METADATA_TEXT': [], 
                'OPTIONS': [], 
                'OPTIONS_TEXT': [], 
                'RANGE': [], 
                'TAB': [{'WA': '00000111###51###99991231###N###00000000###  ###   ###00000000###  ###00000###00000###   0.00 ###     ### ###  ###  ######'}], 
                'TAB_TEXT': []
            }

            '''


            for col in col_lst :
                ## added check to remove columns with length 0 like .Node1 which is of type NODE
                if int(col['LENGTH']):
                    data = [[
                        '',
                        tbl_name, 
                        col['FIELDNAME'].strip(), 
                        col['TYPE'].strip(), 
                        int(col['LENGTH']), 
                        int(col['LENGTH']), 
                        False,  
                        int(col['LENGTH']), 
                        int(col['LENGTH']), 
                        0, ##int(col['DECIMALS']), 
                        -1, ##int(col['POSITION']),
                        "",
                        col['FIELDTEXT'].strip() 
                    ]]

                    if df is None :
                        df = pd.DataFrame(data, columns = col_name)
                    else :
                        df1 = pd.DataFrame(data, columns = col_name)
                        df_list = [df]
                        df_list.append(df1)
                        df = pd.concat(df_list, ignore_index=True)

            df.fillna(0, inplace = True)                   
        else :
            res = self.connection.call('DDIF_FIELDINFO_GET', TABNAME= tbl_name)
            col_lst = res['DFIES_TAB']

            '''
            Sample data from DDIF_FIELDINFO_GET key DFIES_TAB
            {   
                'TABNAME': 'TCURR', 'FIELDNAME': 'MANDT', 'LANGU': 'E', 'POSITION': '0001', 'OFFSET': '000000', 'DOMNAME': 'MANDT',
                'ROLLNAME': 'MANDT', 'CHECKTABLE': 'T000', 'LENG': '000003', 'INTLEN': '000006', 'OUTPUTLEN': '000003', 
                'DECIMALS': '000000', 'DATATYPE': 'CLNT', 'INTTYPE': 'C', 'REFTABLE': '', 'REFFIELD': '', 'PRECFIELD': 'TCURR', 'AUTHORID': '', 
                'MEMORYID': '', 'LOGFLAG': '', 'MASK': '', 'MASKLEN': '0000', 'CONVEXIT': '', 'HEADLEN': '03', 
                'SCRLEN1': '10', 'SCRLEN2': '15', 'SCRLEN3': '20', 'FIELDTEXT': 'Client', 'REPTEXT': 'Cl.',
                'SCRTEXT_S': 'Client', 'SCRTEXT_M': 'Client', 'SCRTEXT_L': 'Client', 'KEYFLAG': 'X', 
                'LOWERCASE': '', 'MAC': '', 'GENKEY': '', 'NOFORKEY': '', 'VALEXI': '', 
                'NOAUTHCH': '', 'SIGN': '', 'DYNPFLD': 'X', 'F4AVAILABL': 'X', 
                'COMPTYPE': 'E', 'LFIELDNAME': 'MANDT', 'LTRFLDDIS': '', 'BIDICTRLC': '',
                'OUTPUTSTYLE': '00', 'NOHISTORY': '', 'AMPMFORMAT': ''
            }        
            '''
            

            for col in col_lst :
                ## added check to remove columns with length 0 like .Node1 which is of type NODE
                if int(col['OUTPUTLEN']):
                    data = [[
                        '',
                        col['TABNAME'].strip(), 
                        col['FIELDNAME'].strip(), 
                        col['DATATYPE'].strip(), 
                        int(col['OUTPUTLEN']), 
                        int(col['OUTPUTLEN']), 
                        False,  
                        int(col['OUTPUTLEN']), 
                        int(col['OUTPUTLEN']), 
                        int(col['DECIMALS']), 
                        int(col['POSITION']),
                        col['CONVEXIT'].strip(),
                        col['FIELDTEXT'].strip() 
                    ]]

                    if df is None :
                        df = pd.DataFrame(data, columns = col_name)
                    else :
                        df1 = pd.DataFrame(data, columns = col_name)
                        df_list = [df]
                        df_list.append(df1)
                        df = pd.concat(df_list, ignore_index=True)

            df.fillna(0, inplace = True)       

        self.close()

        return df.to_dict(orient="records")  

    def generateQuery(
        self,
        tablename=None,
        columnnames=None,
        limit=None,
        orderby=None,
        filters=None,
        groupby=None,
        joins=None,
        joinCondition=None,
        distinct=0
    ):
        pass

    def create_engine(self):
       pass

    def get_params(self, params_dict):
        params = ''
        if isinstance(params_dict, dict):
            sep = ""
            for key in params_dict.keys() :
                params += "{} {} = '{}'".format(sep, key, params_dict[key])
                sep = ","

        return params        

    def readTable(self, tbl_name, limit = None, **others):
        src_type = others.get("src_type", SAPObjType.TABLE)
        column_name = others.get("column_name") 
        filter_ = others.get("filter")             
        params = others.get("params", {})
        start_date = others.get("start_date")
        end_date = others.get("end_date") 
        _range = others.get("range", []) 
        rowskips = others.get("rowskips", 0)

        bapi_name = others.get("bapi_name", "") 
        bapi_tbl_name = others.get("bapi_tbl_name", "") 

        if src_type == SAPObjType.BAPI :

            res = self.execute_bapi(bapi_name, params)
            df = pd.DataFrame(res[bapi_tbl_name])

            res = {}
            res["df"] = df
            res["df_text"] = [] 
            return res               


        ''' options = [{'TEXT': "FCURR = 'USD'"}] ##for TCURR
            options = [{'TEXT': "BELNR = '4900000115'"}] ## for BSEG
            options = [{'TEXT': "TABNAME LIKE 'BSEG%'"}] ## DD02T  SAP S4 Table
            options = [{'TEXT': "TABNAME LIKE 'I_SALESORDERITE%'"}] ## DD02V  SAP S4 CDS View
            options = [{'TEXT': "DATAEXTRACTIONVIEWNAME LIKE '%'"}] ## DD02V  SAP S4 Extractor
        '''

        if filter_ :
            options = [{'TEXT': filter_}]
        else :
            options = []

        if limit:
            limit = int(limit)
            ROWS_AT_A_TIME = limit
        else:
            ROWS_AT_A_TIME = 10000
        
        results = None
        if column_name:
            results = pd.DataFrame(columns=column_name)
        results_text = None



        ''' 
        Example :  Fields = ['BELNR', 'MANDT']
        '''

        params = self.get_params(params)
        # TODO: delimiter = chr(30)

        delimiter = SAPDelimiter.HASH2 ## '|'
        columns = column_name
        if type(columns) is str:
            columns = [columns]
        
        if columns:
            columns = [{'FIELDNAME': x} for x in columns]
        else :
            columns = []

        try : 
            self.connect()
            attempt_cnt = 0
            while True :
                try : 
                    if src_type in [SAPObjType.TRANS_TBL, SAPObjType.TABLE, SAPObjType.EXTRACTOR, SAPObjType.BAPI, SAPObjType.POOL]:
                        result = self.connection.call(
                            'Z_SCIKIQ_READ_TABLE',
                            QUERY_TABLE =   tbl_name,
                            OPTIONS     =   options,
                            ROWSKIPS    =   rowskips,
                            ROWCOUNT    =   ROWS_AT_A_TIME,
                            FIELDS      =   columns,
                            DELIMITER   =   delimiter
                        )
                    elif src_type in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT, SAPObjType.DSO, SAPObjType.ADSO]:
                        s_filter = filter_
                        if s_filter == [] or s_filter is None :
                            s_filter = ""
                        result = self.connection.call(
                            'Z_DM_SCIKIQ',
                            CATEGORY            =   src_type,
                            SEARCH_TECHNICAL    =   s_filter,
                            SEARCH_NAME         =   "",
                            NAME                =   tbl_name,
                            DELIMITER           =   delimiter,
                            NO_DATA             =   "",
                            OPTIONS             =   options,
                            ROWSKIPS            =   rowskips,
                            ROWCOUNT            =   ROWS_AT_A_TIME,
                            COUNT_ONLY          =   "",
                            DELTA               =   "",
                            DELTA_START_DATE    =   start_date,
                            DELTA_END_DATE      =   end_date,
                            RANGE               =   _range
                        ) 
                        '''                        
                        *"     VALUE(CATEGORY) TYPE  TEXT5
                        *"     VALUE(SEARCH_TECHNICAL) TYPE  TEXT50 OPTIONAL
                        *"     VALUE(SEARCH_NAME) TYPE  TEXT50 OPTIONAL
                        *"     VALUE(NAME) TYPE  STRING OPTIONAL
                        *"     VALUE(DELIMITER) TYPE  SO_TEXT003 OPTIONAL
                        *"     VALUE(NO_DATA) LIKE  SONV-FLAG OPTIONAL
                        *"     VALUE(ROWSKIPS) TYPE  INT4 OPTIONAL
                        *"     VALUE(ROWCOUNT) TYPE  INT4 OPTIONAL
                        *"     VALUE(DELIMITER_TEXT) TYPE  SO_TEXT003 OPTIONAL
                        *"     VALUE(NO_DATA_TEXT) LIKE  SONV-FLAG OPTIONAL
                        *"     VALUE(ROWSKIPS_TEXT) TYPE  INT4 OPTIONAL
                        *"     VALUE(ROWCOUNT_TEXT) TYPE  INT4 OPTIONAL
                        *"     VALUE(COUNT_ONLY) LIKE  SONV-FLAG OPTIONAL
                        *"     VALUE(DELTA) LIKE  SONV-FLAG OPTIONAL
                        *"     VALUE(DELTA_START_DATE) TYPE  DATS OPTIONAL
                        *"     VALUE(DELTA_END_DATE) TYPE  DATS OPTIONAL                                               
                        '''
                    else :
                        result = self.connection.call(
                            'Z_SCIKIQ_READ_CDSVIEW',
                            QUERY_TABLE =   tbl_name,
                            OPTIONS     =   options,
                            ROWSKIPS    =   rowskips,
                            ROWCOUNT    =   ROWS_AT_A_TIME,
                            DELIMITER   =   delimiter,
                            FLTR        =   params
                        )

                    # We split out fields and fields_name to hold the data and the column names
                    fields = []
                    fields_text = []
                    data_fields_text = []
                    data_names_text = []

                    if "DATA" in result :
                        data_fields = result["DATA"] # pull the data part of the result set
                    elif tbl_name : ## case IC, IO, DSO, ADSO
                        data_fields = result["TAB"] # pull the data part of the result set
                        if "TAB_TEXT" in result:
                            data_fields_text = result["TAB_TEXT"]

                    else : ## case when function is called to fetch list of objects
                        data_fields = result["LIST"] # pull the data part of the result set

                    if "FIELDS" in result :                        
                        data_names = result["FIELDS"] # pull the field name part of the result set
                    else : 
                        data_names = result["METADATA"] # pull the field name part of the result set
                        if "METADATA_TEXT" in result :
                            data_names_text = result["METADATA_TEXT"]

                    if tbl_name :
                        headers = [x['FIELDNAME'] for x in data_names] # headers extraction
                        long_fields = len(data_fields) # data extraction

                        ## below code is for handling info  cube and info object metadata
                        if src_type in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT] :
                            try :
                                headers_text = [x['FIELDNAME'] for x in data_names_text] # headers extraction
                                long_fields_text = len(data_fields_text) # data extraction       

                                # now parse the data fields into a list
                                for line in range(0, long_fields_text):
                                    fields_text.append(data_fields[line]["WA"].strip())

                                # for each line, split the list by the '|' separator
                                ## Delimiter change : fields = [x.strip().split('|') for x in fields ]
                                fields_text = [x.strip().split(delimiter) for x in fields_text ]

                                if results_text is None:
                                    results_text = pd.DataFrame(fields_text, columns=headers_text)
                                else:
                                    df_text = pd.DataFrame(fields_text, columns=headers_text)
                                    results_text = results_text.append(df_text)                                                     
                            except Exception as e :
                                print(e)
                                

                        ## End if src_type in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT]
                        # now parse the data fields into a list
                        for line in range(0, long_fields):
                            fields.append(data_fields[line]["WA"].strip())

                        # for each line, split the list by the '|' separator
                        ## Delimiter change : fields = [x.strip().split('|') for x in fields ]
                        fields = [x.strip().split(delimiter) for x in fields ]

                        if results is None:
                            results = pd.DataFrame(fields, columns=headers)
                        else:
                            df1 = pd.DataFrame(fields, columns=headers)
                            results = results.append(df1)

                        rowskips += ROWS_AT_A_TIME
                        attempt_cnt  = 0
                        if limit and rowskips >= limit:
                            break

                        if len(result['DATA']) < ROWS_AT_A_TIME:
                            break
                    ## case when function is called to fetch list of objects
                    else :
                        if results is None:
                            results = pd.DataFrame(result['LIST'])
                        else:
                            df1 = pd.DataFrame(result['LIST'])
                            results = results.append(df1)                        

                        ## commented as loop not  required.
                        ## if len(result['LIST']) < ROWS_AT_A_TIME:
                        break                        
                except Exception as e :
                    print(e)
                    ## exception to delimiter found in column data
                    ## try changing the delimiter
                    delimiter = SAPDelimiter.HASH
                    attempt_cnt += 1
                    if attempt_cnt > 1 :
                        break

            self.close()
        except Exception as e :
            self.close()
            print(e)
            raise   

        res = {}
        res["df"] = results
        res["df_text"] = results_text 
        return res        

    def truncateTable(self, table_name):
        pass

    def generateCreateTableScriptETL(self, tableDetails):
        pass

    def createTable(self, tableDetails, etl=False):
        pass

    def getColumnLOV(self, table_name, col_name):
        pass

    def getColumnsProfile(self, table_name, with_min_max=False, filter=None, type=SAPObjType.TABLE):
        df_col_dtls = self.getTableColumnsDetails(table_name, sort_on_position=True, type=type)

        '''
            COLUMN_NAME
            DATA_TYPE
            MAX_VAL
            MIN_VAL
            UNQ_VAL
            TOTAL_COUNT
            NULL_CNT
        '''

        options = SAPOptions.BLNK
        if filter and filter != '1=1' :
            options = [{'TEXT': filter}]        

        columns = ['COLUMN_NAME', 'DATA_TYPE', 'MAX_VAL', 'MIN_VAL', 'UNQ_VAL', 'TOTAL_COUNT', 'NULL_CNT']
        df = None
        self.connect()
 
        for row in df_col_dtls :
            ''' 
                No Response : {'WRITES': []}
            '''
            total_cnt = 0
            unq_val = 0
            null_cnt = 0      
            min_val = ""
            max_val = ""
            col_name = row["COLUMN_NAME"]                  
            try : 
                result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='CNT', P_TABLE=table_name, P_FIELD=col_name, OPTIONS = options)
                if len(result['WRITES']) > 0 :
                    total_cnt = int(result['WRITES'][0]['ZEILE'].strip())

                result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='CNTD', P_TABLE=table_name, P_FIELD=col_name, OPTIONS = options)
                if len(result['WRITES']) > 0 :
                    unq_val = int(result['WRITES'][0]['ZEILE'].strip())        

                result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='CNTN', P_TABLE=table_name, P_FIELD=col_name, OPTIONS = options)
                if len(result['WRITES']) > 0 :
                    null_cnt = int(result['WRITES'][0]['ZEILE'].strip())   

                if with_min_max :
                    result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='MINMAX', P_TABLE=table_name, P_FIELD=col_name, OPTIONS = options)
                    if len(result['WRITES']) > 0 :
                        min_max = result['WRITES'][0]['ZEILE'].strip().split('|')                                         
                        min_val = min_max[0].strip()
                        max_val = min_max[1].strip()
     
            except Exception as e :
                print(e)

            data = [[ col_name, row["DATA_TYPE"], max_val, min_val, unq_val, total_cnt, null_cnt]]
            if df is None :
                df = pd.DataFrame(data, columns=columns)
            else :
                df1 = pd.DataFrame(data, columns=columns)
                df_list = [df]
                df_list.append(df1)
                df = pd.concat(df_list, ignore_index=True)                  
       
        self.close()
        
        return df   
    
    def get_bapi_params(self, bapi_name):
        self.connect()

        function_interface = self.connection.call(
            'RFC_GET_FUNCTION_INTERFACE',
            FUNCNAME=bapi_name
        ) 
        import_params = [param for param in function_interface['PARAMS'] if param['PARAMCLASS'] == 'I']
        table_params = [param for param in function_interface['PARAMS'] if param['PARAMCLASS'] == 'T']
        export_params = [param for param in function_interface['PARAMS'] if param['PARAMCLASS'] == 'E']

        params = {}

        import_list = []
        for param in import_params:
            parameter = param['PARAMETER']
            paramtext = param['PARAMTEXT']
            paramtype = param['TABNAME']
            print(bapi_name, parameter, paramtext, paramtype)
            import_list.append([parameter, "", paramtext, paramtype])


        tab_list = {}
        for param in table_params:
            tab_list[param['PARAMETER']] = {
                "PARAMTEXT" : param['PARAMTEXT'],
                "TABNAME" : param['TABNAME']
            }

        export_list = []
        for param in export_params:
            parameter = param['PARAMETER']
            paramtext = param['PARAMTEXT']
            paramtype = param['TABNAME']
            print(bapi_name, parameter, paramtext, paramtype)
            export_list.append([parameter, "", paramtext, paramtype])

        params["imports"] = import_list
        params["tables"] = tab_list
        params["exports"] = export_list

        print(params)
        self.close()        

        return params

    def execute_bapi(self, bapi_name, params = {}):
        self.connect()

        v_params = {}

        ## convert '1' -> 1
        for key in params.keys() :
            ## remove params for which value is not provided
            if len(params[key]) == 0 :
                pass
            elif params[key].isnumeric() :
                v_params[key] = int(params[key])
            else :
                ## convert "'0000002502'" -> "0000002502" 
                v_params[key] = params[key].replace("'","")

        result = self.connection.call(bapi_name, **v_params)

        self.close()

        return result

    def getTableRowCount(self, table_name, filter, params = '', type = SAPObjType.TABLE):
        ## Ex : options = [{'TEXT': "FCURR = 'USD'"}]
        options = SAPOptions.BLNK
        if filter and filter != '1=1' :
            options = [{'TEXT': filter}]

        count = 0
        self.connect()

        if type in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT, SAPObjType.DSO, SAPObjType.ADSO] :
            result = self.connection.call(
                'Z_DM_SCIKIQ',
                CATEGORY            =   type,
                SEARCH_TECHNICAL    =   filter,
                SEARCH_NAME         =   "",
                NAME                =   table_name,
                DELIMITER           =   SAPDelimiter.PIPE,
                NO_DATA             =   "",
                OPTIONS             =   options,
                ROWSKIPS            =   0,
                ROWCOUNT            =   0,
                COUNT_ONLY          =   "1",
                DELTA               =   "",
                DELTA_START_DATE    =   None,
                DELTA_END_DATE      =   None                                                        
            ) 

            count = result["COUNT_DATA"]            
        else :
            result = self.connection.call(
                'Z_SCIKIQ_ROW_COUNT2',
                QUERY_TABLE=table_name,
                OPTIONS=options,
                PARAMS=params
            )
            count = result['COUNT']

        self.close()

        return count

    def getSAPObjDetails(self, table_name, type, df):        
        col_name = ['TABLE_SCHEMA', 'TABLE_NAME', 'NO_OF_COLS', 'SIZE_IN_MB', 'NO_OF_ROWS', 'LAST_UPDATED', 'TABLE_TYPE', 'COMMENT']

        row_count = self.getTableRowCount(table_name, filter="1=1", type=type)
        col_lst = self.getTableColumns(table_name, type=type)

        obj_lst = self.get_all_tables(search=table_name, type=type, limit = 100)
        comment = ""
        obj_type = type
        for tb in obj_lst :
            if tb['TABLE_NAME'] == table_name :
                comment = tb['DESCRIPTION']
                obj_type = tb['TABLE_TYPE']
                break

        ##TODO: calculate table size
        size = -1
        ##TODO: get last updated date
        last_updated = None

        data = [['', table_name, len(col_lst), size, row_count, last_updated, obj_type, comment]]
        if df is None :
            df = pd.DataFrame(data, columns=col_name)
        else :
            df1 = pd.DataFrame(data, columns=col_name)
            df_list = [df]
            df_list.append(df1)
            df = pd.concat(df_list, ignore_index=True)

        return df

    def getTableDetails(self, table_name, type = {}):

        col_name = ['TABLE_SCHEMA', 'TABLE_NAME', 'NO_OF_COLS', 'SIZE_IN_MB', 'NO_OF_ROWS', 'LAST_UPDATED', 'TABLE_TYPE', 'COMMENT']
        df = None

        if isinstance(table_name,str):
            table_name = [table_name]

        for tbl in table_name :
            ## {'tbl-type': 'BAPI', 'bapi-name': 'BAPI_USER_GETLIST', 'bapi-struct-type': 'BAPIUSNAME'}
            if isinstance(type[tbl], str) :
                type_ = type[tbl]
            else :
                type_ = type[tbl]["tbl-type"]
                if "bapi-name" in type[tbl] :
                    bapi_name = type[tbl]["bapi-name"]

                if "bapi-struct-type" in type[tbl] :                            
                    bapi_struct_type = type[tbl]["bapi-struct-type"]


            if type_ in [SAPObjType.INFOCUBE, SAPObjType.INFOOBJECT, SAPObjType.DSO, SAPObjType.ADSO] :
                df = self.getSAPObjDetails(tbl, type_, df)
            else :            

                try :
                    self.connect()
                    if type_ == "BAPI" :
                        res = self.connection.call('DDIF_FIELDINFO_GET', TABNAME= bapi_struct_type)
                    else :
                        res = self.connection.call('DDIF_FIELDINFO_GET', TABNAME= tbl)
                    col_lst = res['DFIES_TAB']
                    tbl_type = res['DDOBJTYPE']

                    ##TODO: EM_GET_NUMBER_OF_ENTRIES not give no of rows for CDS View and Extractor
                    if type_ == "BAPI" :
                        res = self.connection.call('EM_GET_NUMBER_OF_ENTRIES', IT_TABLES = [{'TABNAME': bapi_name}])
                    else :
                        res = self.connection.call('EM_GET_NUMBER_OF_ENTRIES', IT_TABLES = [{'TABNAME': tbl}])

                    ''' 
                    Example :
                        res = {'IT_TABLES': [{'TABNAME': '2LIS_11_VAITM', 'TABROWS': -1}]} 
                    '''
                    row_count = 0
                    if res and 'IT_TABLES' in res.keys() :
                        row_count = res['IT_TABLES'][0]['TABROWS']    
                                    
                    tbl_name = ''

                    if type_ in (SAPObjType.TABLE, SAPObjType.CDSVIEW, SAPObjType.TRANS_TBL, SAPObjType.POOL) :
                        tbl_name = 'DD02T'
                        options = "TABNAME = '{}' AND DDLANGUAGE = 'E'".format(tbl) ## DD02T  SAP S4 Table        
                        comment_col_name = 'DDTEXT'        
                    elif type_ == 'EXT' :
                        tbl_name = 'IXTRCTNENBLDVW'
                        options = "DATAEXTRACTIONVIEWNAME = '{}'".format(tbl) ## DD02T  SAP S4 Table                
                        comment_col_name = 'DATAEXTRACTIONVIEWDESCRIPTION'

                    ##TODO: calculate table size
                    size = 0
                    ##TODO: get last updated date
                    last_updated = None
                    if type_ == "BAPI" :
                        comment = ''
                    else : 
                        result = self.readTable(tbl_name, filter = options, limit=1)
                        result = result["df"]
                        comment = ''
                        if result.shape[0] > 0 :
                            comment = result[comment_col_name][0]

                    data = [['', tbl, len(col_lst), size, row_count, last_updated, tbl_type, comment]]
                    if df is None :
                        df = pd.DataFrame(data, columns=col_name)
                    else :
                        df1 = pd.DataFrame(data, columns=col_name)
                        df_list = [df]
                        df_list.append(df1)
                        df = pd.concat(df_list, ignore_index=True)
                except Exception :
                    print("Exception while fetching details of the table :" + tbl)

                self.close()

        return df

    def getTableRelationships(self, table_name, bi_directional = False):
        ## fetch bi directional relationship
        ## OP-5620 : changes to remove * from suggested table name.
        if bi_directional :
            filter_ = "TABNAME = '{}' AND CHECKTABLE <> '*' OR CHECKTABLE = '{}'".format(table_name, table_name)
        else :
            filter_ = "TABNAME = '{}' AND CHECKTABLE <> '*'".format(table_name)            
            
        res = self.readTable(tbl_name='DD08L', src_type = SAPObjType.TABLE, filter = filter_)

        df = res["df"]

        if isinstance(df, pd.DataFrame) :
            df.rename(columns={
                'TABNAME': 'ref_table_name',
                'FIELDNAME': 'col_name',
                'CHECKTABLE': 'table_name',
                'FRKART': 'ref_type'
            }, inplace=True)

            df = df[['table_name', 'col_name', 'ref_table_name', 'ref_type']]

            df['table_name'] = df['table_name'].apply(lambda x: x.strip())               
            df['col_name'] = df['col_name'].apply(lambda x: x.strip())
            df['ref_table_name'] = df['ref_table_name'].apply(lambda x: x.strip())
            df['ref_type'] = df['ref_type'].apply(lambda x: x.strip())
            df['ref_col_name'] = "" 

        return df

    def getDropTableQuery(self, table_name):
        pass

    def dropTable(self, table_name):
        pass

    def getTableIndexDetails(self, tablename):
        pass

    def get_incremental_columns(self, tablename, **others):
        try:
            type = others.get("type", SAPObjType.TABLE)
            tab_col_details = self.getTableColumnsDetails(tablename, type=type)  ## PASS
            col_data = convertDataType(tab_col_details, self.db_type)
            inc_columns = pd.DataFrame()

            for row in col_data:
                if row['DATA_TYPE'] in ('TMS', 'INT', 'DAT'):
                    inc_columns = inc_columns.append(
                        {
                            'COLUMN_NAME': row['COLUMN_NAME'],
                            'DATA_TYPE': row['DATA_TYPE']
                        },
                        ignore_index=True
                    )

        except Exception as e:
            self.close()
            print(e)
            raise
        return inc_columns

    def fetch_delta_columns(self, table_name, **others):
        type1 = others.get("type", SAPObjType.TABLE)
        inc_columns = self.get_incremental_columns(tablename=table_name, type=type1)
        '''
            COLUMN_NAME
            DATA_TYPE
            MAX_VAL
            MIN_VAL
            UNQ_VAL
            TOTAL_COUNT
            NULL_CNT
        '''

        options = SAPOptions.BLNK

        with_min_max = False
        columns = ['COLUMN_NAME', 'DATA_TYPE', 'MAX_VAL', 'MIN_VAL', 'UNQ_VAL', 'TOTAL_COUNT', 'NULL_CNT']
        df = None
        self.connect()

        index = 0
        for index, row in inc_columns.iterrows():
            ''' 
                No Response : {'WRITES': []}
            '''
            total_cnt = 0
            unq_val = 0
            null_cnt = 0
            min_val = ""
            max_val = ""
            col_name = row["COLUMN_NAME"]
            try:
                result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='CNT', P_TABLE=table_name, P_FIELD=col_name, OPTIONS=options)
                if len(result['WRITES']) > 0:
                    total_cnt = int(result['WRITES'][0]['ZEILE'].strip())

                result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='CNTD', P_TABLE=table_name, P_FIELD=col_name, OPTIONS=options)
                if len(result['WRITES']) > 0:
                    unq_val = int(result['WRITES'][0]['ZEILE'].strip())

                result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='CNTN', P_TABLE=table_name, P_FIELD=col_name, OPTIONS=options)
                if len(result['WRITES']) > 0:
                    null_cnt = int(result['WRITES'][0]['ZEILE'].strip())

                if with_min_max:
                    result = self.connection.call('Z_SCIKIQ_DATA_PROFILE', P_CODE='MINMAX', P_TABLE=table_name, P_FIELD=col_name, OPTIONS=options)
                    if len(result['WRITES']) > 0:
                        min_max = result['WRITES'][0]['ZEILE'].strip().split('|')
                        min_val = min_max[0].strip()
                        max_val = min_max[1].strip()

            except Exception as e:
                print(e)

            data = [[col_name, row["DATA_TYPE"], min_val, max_val, unq_val, total_cnt, null_cnt]]
            if df is None:
                df = pd.DataFrame(data, columns=columns)
            else:
                df1 = pd.DataFrame(data, columns=columns)
                
                df_list = [df]
                df_list.append(df1)
                df = pd.concat(df_list, ignore_index=True)


        self.close()
        if df is not None:
            df_date = df.loc[(df['DATA_TYPE'].str.upper().str.contains('TMS*|DAT*'))]
            if not df_date.empty:
                df_date = df_date[df_date['UNQ_VAL'] == df_date['UNQ_VAL'].max()]
            df_integer = df.loc[(df['DATA_TYPE'].str.upper().str.contains('INT*'))]
            if not df_integer.empty:
                df_integer = df_integer.loc[
                    df_integer['UNQ_VAL'] == df_integer['TOTAL_COUNT']]
            df = pd.concat([df_integer, df_date], axis=0)
            df = df[['COLUMN_NAME', 'DATA_TYPE']]
        else:
            df = pd.DataFrame(columns=['COLUMN_NAME', 'DATA_TYPE'])
        return df
    
    def find_row(self, tbl_name, row, on_condition, manage_connection):
        return False    

    def update_row(self, tbl_name, row, on_condition, matched_mapping, col_details, manage_connection):
        return False

    def insert_row(self, tbl_name, row, non_matched_mapping, col_details, manage_connection):

        '''
            INSERT INTO SCIKIQ_DEV.ORDERS
            (ID, CUSTOMER_ID, PRODUCT_ID, QUANTITY, PRICE, TOTAL_AMOUNT, STORE_ID, CREATED_DATE, CREATED_BY)
            VALUES(0, 0, 0, 0, 0, 0, 0, '', '');        
        '''
        
        return False
