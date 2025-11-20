import configparser
import pyrfc

# Load configuration from file
# config = configparser.ConfigParser()
# config.read('config.ini')

# Connect to SAP system using PyRFC
conn = pyrfc.Connection(
    ashost='host',
    sysnr='00',
    client='',
    user='username',
    passwd='password',
)

# Define the function to export open invoices in FBDI format
def export_open_invoices():
    # Define the FBDI format for open invoices
    fbdi_format = """
        <?xml version="1.0"?>
        <InvoiceUpload xmlns="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/"
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xsi:schemaLocation="http://xmlns.oracle.com/apps/financials/commonModules/shared/model/erpIntegrationService/ ../model/erpIntegrationService.xsd">
            <InvoiceLine>
                <TransactionType>CREATE</TransactionType>
                <TransactionSourceSystem>System1</TransactionSourceSystem>
                <InvoiceHeader>
                    <InvoiceNumber>{invoice_number}</InvoiceNumber>
                    <InvoiceDate>{invoice_date}</InvoiceDate>
                    <InvoiceAmount>{invoice_amount}</InvoiceAmount>
                </InvoiceHeader>
            </InvoiceLine>
        </InvoiceUpload>
    """

    # Query open invoices from SAP
    result = conn.call('BAPI_FTR_RDFOROPENITEMS', MaxRows=100)

    # Loop through open invoices and generate FBDI file
    for invoice in result['OPEN_ITEMS']:
        fbdi = fbdi_format.format(
            invoice_number=invoice['INVOICE_NUMBER'],
            invoice_date=invoice['INVOICE_DATE'],
            invoice_amount=invoice['INVOICE_AMOUNT']
        )
        # Write FBDI file to disk
        filename = f"{invoice['INVOICE_NUMBER']}.xml"
        with open(filename, 'w') as f:
            f.write(fbdi)

    print(f"Exported {len(result['OPEN_ITEMS'])} open invoices to FBDI format.")

# Call the function to export open invoices
export_open_invoices()

# Disconnect from SAP system
conn.close()
