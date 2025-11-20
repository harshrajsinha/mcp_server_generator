import cx_Oracle
import pandas as pd

cx_Oracle.init_oracle_client(lib_dir = "C:\OracleInstaClient\instantclient_21_9")


# Define EBS database connection details
ebs_user = 'apps'
ebs_password = 'ebs_password'
ebs_host = 'ebs_host'
ebs_port = 'ebs_port'
ebs_service_name = 'ebs_service_name'

# Define the CoA hierarchy mapping
hierarchy_mapping = {
'01': ('100', '01'),
'02': ('100', '02'),
'03': ('200', '03'),
'04': ('300', '04'),
'05': ('400', '05'),
'06': ('500', '06'),
'07': ('500', '07'),
'08': ('600', '08'),
'09': ('700', '09'),
'10': ('800', '10')
}

# Define the hierarchy levels for the new Fusion CoA
hierarchy_levels = {
'100': ['100', '101'],
'200': ['200', '201'],
'300': ['300', '301'],
'400': ['400', '401', '402'],
'500': ['500', '501', '502', '503'],
'600': ['600', '601'],
'700': ['700', '701'],
'800': ['800', '801', '802']
}

# Define the formatting rules for the new Fusion CoA structure
formatting = {
'100': '{:<3}',
'101': '{:<3}',
'200': '{:<4}',
'201': '{:<4}',
'300': '{:<5}',
'301': '{:<5}',
'400': '{:<6}',
'401': '{:<6}',
'402': '{:<6}',
'500': '{:<7}',
'501': '{:<7}',
'502': '{:<7}',
'503': '{:<7}',
'600': '{:<6}',
'601': '{:<6}',
'700': '{:<6}',
'701': '{:<6}',
'800': '{:<6}',
'801': '{:<6}',
'802': '{:<6}'
}

# Define the cost center mapping
cost_center_mapping = {
'01': '10000',
'02': '20000',
'03': '30000',
'04': '40000',
'05': '50000',
'06': '60000',
'07': '70000',
'08': '80000',
'09': '90000',
'10': '100000'
}


ebs_conn = cx_Oracle.connect(ebs_user, ebs_password, f'{ebs_host}:{ebs_port}/{ebs_service_name}')


ebs_query = 'SELECT SEGMENT1, SEGMENT2, SEGMENT3, SEGMENT4, SEGMENT5, SEGMENT6, SEGMENT7, SEGMENT8, SEGMENT9, SEGMENT10 FROM GL_CODE_COMBINATIONS'

# Extract the CoA data from the EBS database
ebs_coa = pd.read_sql(ebs_query, ebs_conn)

# Apply the CoA hierarchy mapping to the EBS CoA
ebs_coa[['SEGMENT1', 'SEGMENT2']] = ebs_coa[['SEGMENT1', 'SEGMENT2']].applymap(lambda x: hierarchy_mapping.get(x, ('', '')))
ebs_coa = ebs_coa.groupby(['SEGMENT1', 'SEGMENT2', 'SEGMENT3', 'SEGMENT4', 'SEGMENT5', 'SEGMENT6', 'SEGMENT7', 'SEGMENT8', 'SEGMENT9']).size().reset_index().rename(columns={0: 'COUNT'})

# Create a new DataFrame to hold the converted CoA data
fusion_coa = pd.DataFrame(columns=['SEGMENT1', 'SEGMENT2', 'SEGMENT3', 'SEGMENT4', 'SEGMENT5', 'SEGMENT6', 'SEGMENT7', 'SEGMENT8', 'SEGMENT9', 'SEGMENT10', 'COST_CENTER'])

# Iterate over the rows of the EBS CoA and map the values to the new Fusion CoA format
for index, row in ebs_coa.iterrows():
    segment1 = formatting['100'].format(row['SEGMENT1'])
    segment2 = formatting['101'].format(row['SEGMENT2'])
    segment3 = formatting['200'].format(row['SEGMENT3'])
    segment4 = formatting['201'].format(row['SEGMENT4'])
    segment5 = formatting['300'].format(row['SEGMENT5'])
    segment6 = formatting['301'].format(row['SEGMENT6'])
    segment7 = formatting['400'].format(row['SEGMENT7'])
    segment8 = formatting['401'].format(row['SEGMENT8'])
    segment9 = formatting['402'].format(row['SEGMENT9'])
    count = row['COUNT']
    cost_center = cost_center_mapping.get(row['SEGMENT2'], '')

    new_row = {'SEGMENT1': segment1, 'SEGMENT2': segment2, 'SEGMENT3': segment3, 'SEGMENT4': segment4, 'SEGMENT5': segment5, 'SEGMENT6': segment6, 'SEGMENT7': segment7, 'SEGMENT8': segment8, 'SEGMENT9': segment9, 'SEGMENT10': '', 'COST_CENTER': cost_center}

    for level, values in hierarchy_levels.items():
        if level in new_row.values():
            continue
        else:
            for value in values:
                new_row[f'SEGMENT{len(level)+1}'] = value
                if level == '800':
                    fusion_coa = fusion_coa.append(new_row, ignore_index=True)

print(fusion_coa)
# Connect to the Fusion database and insert the converted CoA data
# fusion_conn = cx_Oracle.connect(f'{fusion_connection["user"]}/{fusion_connection["password"]}@{fusion_connection["host"]}:{fusion_connection["port"]}/{fusion_connection["service_name"]}')
# cursor = fusion_conn.cursor()
# for index, row in fusion_coa.iterrows():
#     cursor.execute(f"INSERT INTO GL_CODE_COMBINATIONS (CODE_COMBINATION_ID, CHART_OF_ACCOUNTS_ID, CHART_OF_ACCOUNTS