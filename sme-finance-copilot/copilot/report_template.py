"""Downloadable standard Revenue / Expense report template for Bulk POS Import.

Built in code (no spreadsheet library): instructions plus the Revenue and Expense report sheets with the
standard columns, empty data rows, and dropdown lists for the classification and payment columns.
Headers name the merchant currency (e.g. "Net Amount (CNY)") so the import never has to guess it.
"""
import io
import zipfile
from xml.sax.saxutils import escape

ROWS = 10_000  # matches the import limit of 10,000 rows per batch
REVENUE_CLASSES = ['Sales Revenue', 'Other Business Income', 'Customer Refund / Sales Return', 'Loan Proceeds', 'Owner Contribution', 'Sales Tax / VAT Collected', 'Unknown / Needs Review']
EXPENSE_CLASSES = ['Operating Expense', 'Tax / Permit / Government Fee', 'Loan Interest / Financing Fee', 'Loan Principal Repayment', 'Equipment / Capital Purchase', 'Income Tax / Business Tax Payment', 'Unknown / Needs Review']
PAYMENT_METHODS = ['Cash', 'QR', 'Tap-to-Pay', 'Credit Card', 'Debit Card', 'E-Wallet', 'Pay Link', 'Bank Transfer']
EXPENSE_CATEGORIES = ['COGS / Inventory', 'Payroll & Wages', 'Store Rent & Utilities', 'Marketing & Ads', 'Software & Subscriptions', 'Payment & Gateway Fees', 'Other Overhead']


def _col(index):
    name = ''
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def _sheet(rows, widths, validations=(), header_row=None, freeze=None):
    """rows: list of (row_number, [cell text...], style_id)."""
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    if freeze:
        out.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="%d" topLeftCell="A%d" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>' % (freeze, freeze + 1))
    out.append('<cols>' + ''.join('<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i, i, w) for i, w in enumerate(widths, 1)) + '</cols><sheetData>')
    for number, cells, style in rows:
        out.append('<row r="%d">' % number + ''.join(
            '<c r="%s%d" t="inlineStr" s="%d"><is><t xml:space="preserve">%s</t></is></c>' % (_col(i), number, style, escape(str(text)))
            for i, text in enumerate(cells, 1) if text not in (None, '')) + '</row>')
    out.append('</sheetData>')
    if validations:
        out.append('<dataValidations count="%d">' % len(validations))
        for column, options, prompt in validations:
            ref = '%s%d:%s%d' % (column, header_row + 1, column, header_row + ROWS)
            out.append('<dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" errorStyle="warning" promptTitle="Choose a value" prompt="%s" sqref="%s"><formula1>"%s"</formula1></dataValidation>'
                       % (escape(prompt, {'"': '&quot;'}), ref, escape(','.join(options))))
        out.append('</dataValidations>')
    out.append('</worksheet>')
    return ''.join(out)


def build(merchant_name, currency):
    """Return (filename, xlsx bytes) for one merchant's blank standard template."""
    c = currency
    revenue_headers = ['Transaction ID', 'Transaction Date', 'Payment Method', 'Gross Amount (%s)' % c, 'Processing Fee (%s)' % c, 'Net Amount (%s)' % c, 'Revenue / Cash-In Classification']
    expense_headers = ['Expense ID', 'Expense Date', 'Category', 'Sub-Category', 'Description / Vendor', 'Amount (%s)' % c, 'Cash-Flow / Accounting Type', 'Indicative Tax Treatment', 'Financing / Tax Note']
    sheets = [
        ('Instructions', _sheet([
            (1, ['How to use this template'], 1),
            (3, ['1. Fill one row per transaction in "Revenue Report" (customer payments) and one row per cost in "Expense Report". Start at row 6; keep the headers in row 5 unchanged.'], 0),
            (4, ['2. Dates: use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (for example 2026-10-02 or 2026-10-02 09:15:00). Amounts: numbers only, in %s, without currency symbols.' % c], 0),
            (5, ['3. Revenue Report: Gross Amount minus Processing Fee must equal Net Amount on every row. Payment Method is required.'], 0),
            (6, ['4. Expense Report: Payment Method is not needed. Use the dropdowns for Category and Cash-Flow / Accounting Type.'], 0),
            (7, ['5. Classification decides how the app counts each row: loan proceeds, owner contributions and VAT collected are not revenue; loan principal is not an expense.'], 0),
            (8, ['6. Save the file and upload it in Merchant Transactions → Bulk POS Import. Select both report sheets, review the detected columns, validate, preview and import.'], 0),
            (10, ['Business: ' + merchant_name], 0), (11, ['Currency: ' + c], 0),
        ], [140])),
        ('Revenue Report', _sheet([
            (2, ['Revenue Transaction Log (%s)' % c], 1),
            (3, ['All customer payment transactions. One row per transaction; start at row 6.'], 0),
            (5, revenue_headers, 2),
        ], [18, 22, 16, 18, 18, 18, 32], [('C', PAYMENT_METHODS, 'How the customer paid.'), ('G', REVENUE_CLASSES, 'How the app counts this row.')], 5, 5)),
        ('Expense Report', _sheet([
            (2, ['Merchant Operational Expense Log (%s)' % c], 1),
            (3, ['Store operations, COGS, payroll, marketing and fees. One row per cost; start at row 6.'], 0),
            (5, expense_headers, 2),
        ], [16, 16, 26, 28, 30, 16, 32, 32, 40], [('C', EXPENSE_CATEGORIES, 'Expense category.'), ('G', EXPENSE_CLASSES, 'How the app counts this row.')], 5, 5)),
    ]
    return 'Revenue-and-Expense-Report-Template.xlsx', _workbook(sheets)


def _workbook(sheets):
    """Zip (sheet name, sheet XML) pairs into an .xlsx with the shared styles."""
    files = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + ''.join('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i for i in range(1, len(sheets) + 1)) + '</Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView activeTab="1"/></bookViews><sheets>'
            + ''.join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i) for i, (name, _) in enumerate(sheets, 1)) + '</sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i) for i in range(1, len(sheets) + 1))
            + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>' % (len(sheets) + 1),
        # Styles: 0 normal (wrapped), 1 bold title, 2 bold white header on brand green.
        'xl/styles.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="14"/><color rgb="FF08663D"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>'
            '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF08663D"/><bgColor indexed="64"/></patternFill></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
    }
    for i, (_, xml) in enumerate(sheets, 1):
        files['xl/worksheets/sheet%d.xml' % i] = xml
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, text in files.items():
            archive.writestr(path, text.encode('utf-8'))
    return buffer.getvalue()


def cashflow_workbook(merchant_name, currency):
    """Blank Cash Flow workbook: cash on hand, AR and AP ledgers, monthly cash inflow and outflow logs."""
    c = currency
    status = [('E', ['Open', 'Paid'], 'Open = still to collect or pay; Paid = settled.')]
    sheets = [
        ('Instructions', _sheet([
            (1, ['How to use this Cash Flow workbook'], 1),
            (3, ['1. "Dashboard Source & Summary": enter your current cash on hand (bank balance plus petty cash) in cell B6.'], 0),
            (4, ['2. "Accounts Receivable (AR)": one row per customer invoice. "Accounts Payable (AP)": one row per supplier bill. Start at row 6; keep the headers in row 5.'], 0),
            (5, ['3. Dates as YYYY-MM-DD. Payment Status is Open or Paid. The app works out the outstanding balance as amount minus collected/paid.'], 0),
            (6, ['4. "Monthly Cash Inflow Log" and "Monthly Cash Outflow Log": one row per category per month, with the month as Oct 2025 or 2025-10.'], 0),
            (7, ['5. Upload the saved file on Dashboard → Cash Flow. Uploading again replaces the earlier data.'], 0),
            (9, ['Business: ' + merchant_name], 0), (10, ['Currency: ' + c], 0),
        ], [140])),
        ('Dashboard Source & Summary', _sheet([
            (2, ['Cash Flow Source Data (%s)' % c], 1),
            (5, ['KPI Metric Name', 'Value (%s)' % c], 2),
            (6, ['Current Cash on Hand', ''], 0),
        ], [36, 20])),
        ('Accounts Receivable (AR)', _sheet([
            (2, ['Accounts Receivable (AR) Ledger (%s)' % c], 1), (3, ['Customer invoices. One row per invoice; start at row 6.'], 0),
            (5, ['Invoice ID', 'Customer Name', 'Invoice Date', 'Due Date', 'Payment Status', 'Invoice Amount (%s)' % c, 'Amount Collected (%s)' % c], 2),
        ], [18, 30, 14, 14, 16, 20, 22], status, 5, 5)),
        ('Accounts Payable (AP)', _sheet([
            (2, ['Accounts Payable (AP) Ledger (%s)' % c], 1), (3, ['Supplier bills. One row per bill; start at row 6.'], 0),
            (5, ['Bill ID', 'Supplier Vendor', 'Bill Date', 'Due Date', 'Payment Status', 'Bill Amount (%s)' % c, 'Amount Paid (%s)' % c], 2),
        ], [18, 30, 14, 14, 16, 20, 20], status, 5, 5)),
        ('Monthly Cash Inflow Log', _sheet([
            (2, ['Monthly Cash Inflow Log (%s)' % c], 1), (3, ['Cash received per month by category.'], 0),
            (5, ['Log ID', 'Month', 'Revenue Channel / Category', 'Payment Method', 'Gross Inflow (%s)' % c, 'Notes / Source'], 2),
        ], [12, 12, 34, 18, 18, 30])),
        ('Monthly Cash Outflow Log', _sheet([
            (2, ['Monthly Cash Outflow Log (%s)' % c], 1), (3, ['Cash paid out per month by category.'], 0),
            (5, ['Log ID', 'Month', 'Expense Category', 'Payment Method', 'Gross Outflow (%s)' % c, 'Notes / Vendor'], 2),
        ], [12, 12, 34, 18, 18, 30])),
    ]
    return 'Cash-Flow-Workbook-Template.xlsx', _workbook(sheets)
