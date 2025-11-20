import base64

def decodeData(iddata):
    mystr_encoded = base64.b64decode((iddata)).decode('utf-8')
    return mystr_encoded

def encodeData(iddata):
    mystr = iddata
    # Encode
    mystr_encoded = base64.b64encode(bytes(mystr, "utf-8"))
    return mystr_encoded

def remove_double_quotes(query=None,  lst_custom_column_names=[]):
    #Handling calculator column here.
    if query:
        for custom_column_name in lst_custom_column_names:
            first_index = query.find(custom_column_name)
            column_length = len(custom_column_name)
            #-1 and +1 using for eliminate the double quotes(") from the string
            query = str(query[:first_index-1]) + str(query[first_index:first_index+column_length])+ str(query[first_index+column_length+1:]) 

    return query


def generateCustomColumnExpression(action, column_value, expression,db_type):
    expr = ''
    
    if action in ('changeToLowerCase', 'changeToCapitalizeCase', 'calculateLength', 'changeToUpperCase'):
        expr = column_value.format(
            a=quote_column_name(expression['column_name_a'], db_type)
        )
    elif action in  ('aPlusB','aMinusB','aMultiplyB', 'aDivideB'):
        expr = column_value.format(
            a=quote_column_name(expression['column_name_a'], db_type), 
            b=quote_column_name(expression['column_name_b'], db_type)
        )
    elif action == 'aPlusBPlusC':
        expr = column_value.format(
            a=quote_column_name(expression['column_name_a'], db_type), 
            b=quote_column_name(expression['column_name_b'], db_type), 
            c=quote_column_name(expression['column_name_c'], db_type)
        )
    elif action == 'column1Column2':
        expr = column_value.format(
            a=quote_column_name(expression['column_name_a'], db_type),
            op1=expression['math_operator_a'], 
            b=quote_column_name(expression['column_name_b'], db_type)
        )
    elif action == 'column1Column2Column3':
        expr = column_value.format(
            a=quote_column_name(expression['column_name_a'], db_type),
            op1=expression['math_operator_a'],
            b=quote_column_name(expression['column_name_b'], db_type),
            op2=expression['math_operator_b'],
            c=quote_column_name(expression['column_name_c'], db_type)
        )
    elif action == 'customExpression':
        expr = column_value
    elif action == 'remainderOfADivideB':
        pass
    
    return expr


def quote_column_name(column_name, db_type):
    if isinstance(column_name, str):
        if db_type == 'MYSQL':
            return f"`{column_name}`"
        else:
            return f'"{column_name}"'
    return column_name