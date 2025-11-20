import cx_Oracle

cx_Oracle.init_oracle_client(lib_dir = "C:\OracleInstaClient\instantclient_21_9")


# Define EBS database connection details
ebs_user = 'ebs_user'
ebs_password = 'ebs_password'
ebs_host = 'ebs_host'
ebs_port = 'ebs_port'
ebs_service_name = 'ebs_service_name'

# Define Fusion database connection details
fusion_user = 'fusion_user'
fusion_password = 'fusion_password'
fusion_host = 'fusion_host'
fusion_port = 'fusion_port'
fusion_service_name = 'fusion_service_name'


# Define SQL query to extract CoA data from EBS
ebs_query = 'SELECT SEGMENT1, SEGMENT2, SEGMENT3, SEGMENT4, SEGMENT5, SEGMENT6, SEGMENT7, SEGMENT8, SEGMENT9, SEGMENT10 \
            FROM GL_CODE_COMBINATIONS'

# Define the mapping from the old EBS CoA structure to the new Fusion CoA structure
# The keys represent the old EBS segment values, and the values represent the corresponding new Fusion segment values
mapping = {
    '01': '100',
    '02': '200',
    '03': '300',
    '04': '400',
    '05': '500',
    '06': '600',
    '07': '700',
    '08': '800',
    '09': '900',
    '10': '1000'
}

# Connect to EBS database and extract CoA data
ebs_conn = cx_Oracle.connect(ebs_user, ebs_password, f'{ebs_host}:{ebs_port}/{ebs_service_name}')
ebs_cursor = ebs_conn.cursor()
ebs_cursor.execute(ebs_query)

# Connect to Fusion database and load CoA data
# fusion_conn = cx_Oracle.connect(fusion_user, fusion_password, f'{fusion_host}:{fusion_port}/{fusion_service_name}')
# fusion_cursor = fusion_conn.cursor()

for row in ebs_cursor:
    # Map the old EBS segment values to the new Fusion segment values
    print(row)
    new_segments = []
    for segment in row:
        new_segment = mapping.get(segment, '')
        new_segments.append(new_segment)

    fusion_code = '.'.join(new_segments)

    print("Fusion Code :", fusion_code)
    # # Load the CoA data into the Fusion database
    # insert_query = f"INSERT INTO FND_FLEX_VALUES (FLEX_VALUE_SET_ID, FLEX_VALUE, ENABLED_FLAG) \
    #                  VALUES (10, '{fusion_code}', 'Y')"

    # fusion_cursor.execute(insert_query)

# Commit the changes and close the connections

# fusion_conn.commit()
ebs_cursor.close()
ebs_conn.close()
# fusion_cursor.close()
# fusion_conn.close()


print('CoA data loaded successfully.')

