import pandas as pd

sap_fn_map = {}

sap_fn_map["INVDT"] = "conversion_exit_invdt_output"
sap_fn_map["EXCRT"] = "conversion_exit_excrt_input"
sap_fn_map['AU132'] = "conversion_exit_au132_input"
sap_fn_map['AC132'] = "conversion_exit_ac132_input"

'''
TODO : below mapping need to be implemented

sap_fn_map['ALPHA'] = "conversion_exit_alpha_input"
sap_fn_map['GJAHR'] = "conversion_exit_gjahr_input"
sap_fn_map['MATN1'] = "conversion_exit_matn1_range_o"
sap_fn_map['CUNIT'] = "CONVERSION_EXIT_CUNIT_OUTPUT"
sap_fn_map['IMKEY'] = "CONVERSION_EXIT_IMKEY_OUTPUT"
sap_fn_map['FMCIS'] = "CONVERSION_EXIT_FIPOS_OUTPUT"
sap_fn_map['ABPSP'] = "conversion_exit_konpr_output"

'''


def conversion_exit_invdt_output(df, col_name):
    try :
        if df[col_name].dtype == 'object':
            df[col_name] = df[col_name].apply(lambda x: int(x))

        df[col_name] = 99999999 - df[col_name]

        ## Below   dt.strftime('%d/%m/%Y')  will give output in SAP format
        ##TODO: df[col_name] = df[col_name].apply(lambda x: pd.to_datetime(str(x), format='%Y%m%d')).dt.strftime('%d/%m/%Y')

        df[col_name] = df[col_name].apply(lambda x: pd.to_datetime(str(x), format='%Y%m%d'))

    except Exception :
        pass

    return df


def conversion_exit_excrt_input(df, col_name):    
    try :
        ## move negative sign from last to the  front
        df[col_name] = df[col_name].apply(lambda x: '0' if len(x.strip())== 0  else x)   
        df[col_name] = df[col_name].apply(lambda x: x.replace('*', ''))                    
        df[col_name] = df[col_name].apply(lambda x: float('-' + x[0:len(x)-1].strip()) if x[-1] == '-' else float(x.strip()))
    except Exception :
        pass

    return df

def conversion_exit_au132_input(df, col_name):  
    try :
        ## move negative sign from last to the  front
        df[col_name] = df[col_name].apply(lambda x: '0' if len(x.strip())== 0  else x)  
        df[col_name] = df[col_name].apply(lambda x: x.replace('*', ''))                     
        df[col_name] = df[col_name].apply(lambda x: float('-' + x[0:len(x)-1].strip()) if x[-1] == '-' else float(x.strip()))
    except Exception :
        pass

    return df
def conversion_exit_ac132_input(df, col_name):    
    try :
        ## move negative sign from last to the  front
        df[col_name] = df[col_name].apply(lambda x: '0' if len(x.strip())== 0  else x)    
        df[col_name] = df[col_name].apply(lambda x: x.replace('*', ''))                   
        df[col_name] = df[col_name].apply(lambda x: float('-' + x[0:len(x)-1].strip()) if x[-1] == '-' else float(x.strip()))
    except Exception :
        pass

    return df

def conversion_int(df, col_name):    
    try :
        ## move negative sign from last to the  front
        df[col_name] = df[col_name].apply(lambda x: '0' if len(x.strip())== 0  else x)  
        df[col_name] = df[col_name].apply(lambda x: x.replace('*', ''))                     
        df[col_name] = df[col_name].apply(lambda x: int(float('-' + x[0:len(x)-1].strip())) if x[-1] == '-' else int(float(x.strip())))
    except Exception :
        pass

    return df

def conversion_date(df, col_name):    
    try :
        ## move negative sign from last to the  front
        df[col_name] = df[col_name].apply(lambda x: '19700101' if x.strip() in ('00000000','')  else x.strip())            
        df[col_name] = df[col_name].apply(lambda x: '19700101' if int(float(x.strip())) == 0  else x.strip())
        ## 99991231 is not supported by pandas as max date supported is 22620411
        # In [54]: pd.Timestamp.min
        # Out[54]: Timestamp('1677-09-22 00:12:43.145225')

        # In [55]: pd.Timestamp.max
        # Out[55]: Timestamp('2262-04-11 23:47:16.854775807')        
        df[col_name] = df[col_name].apply(lambda x: '22620411' if x.strip() == '99991231'  else x.strip())           
        df[col_name] = df[col_name].apply(lambda x: pd.to_datetime(str(x), format='%Y%m%d'))        
        df[col_name] = df[col_name].apply(lambda x: pd.to_datetime(str(x), format='%Y%m%d'))
  
    except Exception :
        pass

    return df        