import configparser
import pyrfc

# Load configuration from file
# config = configparser.ConfigParser()
# config.read('config.ini')

# Connect to SAP system using PyRFC
conn = pyrfc.Connection(
    ashost='host',
    sysnr='00',
    client='800',
    user='user',
    passwd='password'
)

params = {
    'MAX_ROWS': 10
}

# Query open invoices from SAP
result = conn.call('BAPI_USER_GETLIST', WITH_USERNAME = '1')

# Loop through open invoices and generate FBDI file
# for invoice in result['OPEN_ITEMS']:
#     fbdi = fbdi_format.format(
#         invoice_number=invoice['INVOICE_NUMBER'],
#         invoice_date=invoice['INVOICE_DATE'],
#         invoice_amount=invoice['INVOICE_AMOUNT']
#     )
#     # Write FBDI file to disk
#     filename = f"{invoice['INVOICE_NUMBER']}.xml"
#     with open(filename, 'w') as f:
#         f.write(fbdi)

print(result)

print(f"Exported {len(result['OPEN_ITEMS'])} open invoices to FBDI format.")

# Disconnect from SAP system
conn.close()
