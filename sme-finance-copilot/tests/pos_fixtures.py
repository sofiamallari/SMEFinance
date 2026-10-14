import base64,csv,io,zipfile
from xml.sax.saxutils import escape
from datetime import datetime

def csv_file(rows=None,name='sales.csv',headers=None):
    headers=headers or ['date','net_amount','currency','type','channel','status','reference']
    rows=rows if rows is not None else [['2026-10-01T10:00:00+07:00','100.00','IDR','sale','cash','completed','POS-1'],['2026-10-01T11:00:00+07:00','50.00','IDR','sale','card','paid','POS-2']]
    text=io.StringIO();writer=csv.writer(text);writer.writerow(headers);writer.writerows(rows)
    return {'filename':name,'content':base64.b64encode(text.getvalue().encode()).decode()}

def xlsx_bytes(rows=None,formula=False,external=False,native_date=False):
    rows=rows or [['date','net_amount','currency','type','channel','status','reference'],['2026-10-01T10:00:00+07:00','100.00','IDR','sale','cash','completed','XLSX-1']]
    sheet=[]
    for i,row in enumerate(rows,1):
        cells=[]
        for j,value in enumerate(row):
            ref=chr(65+j)+str(i)
            if i==2 and j==0 and native_date:
                serial=(datetime(2026,10,1)-datetime(1899,12,30)).days
                cells.append(f'<c r="{ref}" s="1"><v>{serial}</v></c>')
            elif formula and i==2 and j==1:cells.append(f'<c r="{ref}"><f>1+1</f><v>2</v></c>')
            else:cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        sheet.append(f'<row r="{i}">{"".join(cells)}</row>')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="POS Sales" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/styles.xml','<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(sheet)+'</sheetData></worksheet>')
        if external:z.writestr('xl/externalLinks/externalLink1.xml','<externalLink/>')
    return out.getvalue()

def mapping(session,controls=None):
    result={}
    for file in session['files']:
        columns={k:v for k,v in file['suggestions'].items()}
        result[file['file_id']]={'columns':columns,'defaults':{'currency':'IDR','transaction_type':'sale','status':'completed'},'timezone':'+07:00','date_format':'iso','report_kind':'transactions','control_totals':controls or {}}
    return result
