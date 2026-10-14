"""Bounded browser-file acquisition, independent of ETL and future connectors."""
import base64
import csv
import hashlib
import io
import re
import secrets
import time
import zipfile
from datetime import datetime,timedelta
from decimal import Decimal
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from copilot.auth import InputError
from copilot.security import AccessDenied
from copilot.canonical_transactions import suggest

MAX_FILE_BYTES=3_000_000;MAX_TOTAL_BYTES=10_000_000;MAX_FILES=10;MAX_ROWS=5000;MAX_COLUMNS=30
MAX_EXPANDED_BYTES=20_000_000;MAX_CELL=4096;MAX_PROCESSING_SECONDS=10
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
SENSITIVE=re.compile(r'card.?number|credit.?card|\bpan\b|cvv|cvc|password|secret|api.?key|access.?token|customer|client.?name|email|phone|ssn|passport',re.I)

def safe_path(value):
    if not isinstance(value,str) or not value or len(value)>240 or '\x00' in value:raise InputError('Invalid source filename/path')
    value=value.replace('\\','/')
    path=PurePosixPath(value)
    if path.is_absolute() or ':' in value or any(p in ('..','.') for p in value.split('/')):raise InputError('Absolute and parent-directory paths are not accepted')
    label=re.sub(r'[^\w ./-]','_',value)
    if re.search(r'\d{13,19}|[\w.+-]+@[\w-]+\.[\w.]+',label):raise InputError('Sensitive information in source filename is not accepted')
    return label,PurePosixPath(label).name

def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise InputError('XML declarations/entities are not accepted')
    try:return ET.fromstring(data)
    except ET.ParseError:raise InputError('Malformed XLSX XML') from None

def check_time(deadline):
    if time.monotonic()>deadline:raise InputError('File processing time limit exceeded')

def csv_table(content,deadline):
    if content.startswith((b'PK',b'\xd0\xcf')) or b'\x00' in content:raise InputError('File content is not a UTF-8 CSV')
    try:
        text=content.decode('utf-8-sig')
        result=[]
        for number,row in enumerate(csv.reader(io.StringIO(text),strict=True),1):
            check_time(deadline)
            if not any(c.strip() for c in row):continue
            if len(row)>MAX_COLUMNS or any(len(c)>MAX_CELL for c in row):raise InputError('CSV column or cell limit exceeded')
            result.append((number,row))
            if len(result)>MAX_ROWS+1:raise InputError('Maximum 5,000 rows per batch')
        return result
    except (UnicodeError,csv.Error):raise InputError('Malformed CSV or invalid UTF-8 encoding') from None

def xlsx_table(content,deadline):
    if not content.startswith(b'PK'):raise InputError('Encrypted or malformed XLSX is not supported')
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            info=archive.infolist();names=archive.namelist()
            if len(info)>200 or sum(i.file_size for i in info)>MAX_EXPANDED_BYTES:raise InputError('Workbook resource limit exceeded')
            for entry in info:
                if entry.flag_bits&1 or entry.file_size>MAX_EXPANDED_BYTES or entry.file_size>max(entry.compress_size,1)*200:
                    raise InputError('Encrypted or excessively compressed workbook rejected')
                if entry.filename.startswith('/') or '..' in PurePosixPath(entry.filename).parts:raise InputError('Unsafe workbook entry path')
            if any('vbaProject' in n or 'externalLinks/' in n for n in names):raise InputError('Macros and external workbook links are not accepted')
            for required in ('[Content_Types].xml','xl/workbook.xml','xl/_rels/workbook.xml.rels'):
                if required not in names:raise InputError('Not a valid XLSX workbook structure')
            content_types=archive.read('[Content_Types].xml')
            if b'macroEnabled' in content_types:raise InputError('Macro-enabled workbooks are not accepted')
            xml(content_types)
            for name in names:
                if name.endswith('.rels'):
                    root=xml(archive.read(name))
                    if any(e.get('TargetMode')=='External' for e in root):raise InputError('External workbook relationships are not accepted')
            workbook=xml(archive.read('xl/workbook.xml'))
            sheets=workbook.findall('s:sheets/s:sheet',NS)
            if len(sheets)!=1:raise InputError('Use one transaction worksheet per XLSX file')
            rel_id=sheets[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            relationships=xml(archive.read('xl/_rels/workbook.xml.rels'))
            target=next((e.get('Target') for e in relationships if e.get('Id')==rel_id),None)
            if not target:raise InputError('Worksheet relationship missing')
            sheet_path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            if sheet_path not in names or '..' in PurePosixPath(sheet_path).parts:raise InputError('Invalid worksheet relationship')
            strings=[]
            if 'xl/sharedStrings.xml' in names:
                strings=[''.join(x.itertext()) for x in xml(archive.read('xl/sharedStrings.xml')).findall('s:si',NS)]
                if len(strings)>MAX_ROWS*MAX_COLUMNS or any(len(s)>MAX_CELL for s in strings):raise InputError('Workbook string limit exceeded')
            date_styles=set()
            if 'xl/styles.xml' in names:
                styles=xml(archive.read('xl/styles.xml'));formats={e.get('numFmtId'):e.get('formatCode','') for e in styles.findall('s:numFmts/s:numFmt',NS)}
                for i,e in enumerate(styles.findall('s:cellXfs/s:xf',NS)):
                    identifier=int(e.get('numFmtId','0'));code=formats.get(str(identifier),'')
                    if identifier in range(14,23) or identifier in (45,46,47) or re.search(r'[dy]',re.sub(r'"[^"]*"','',code),re.I):date_styles.add(i)
            props=workbook.find('s:workbookPr',NS);epoch=datetime(1904,1,1) if props is not None and props.get('date1904') in ('1','true') else datetime(1899,12,30)
            result=[]
            for row in xml(archive.read(sheet_path)).findall('s:sheetData/s:row',NS):
                check_time(deadline);values=[];positions=set()
                for cell in row.findall('s:c',NS):
                    if cell.find('s:f',NS) is not None:raise InputError('Formula cells are rejected; paste values before uploading')
                    match=re.fullmatch(r'([A-Z]+)(\d+)',cell.get('r',''))
                    if not match:raise InputError('Invalid spreadsheet cell reference')
                    index=0
                    for char in match[1]:index=index*26+ord(char)-64
                    if not 1<=index<=MAX_COLUMNS or index in positions:raise InputError('Worksheet column limit or duplicate cell')
                    positions.add(index)
                    while len(values)<index:values.append('')
                    value=cell.findtext('s:v','',NS);kind=cell.get('t')
                    if kind=='s':value=strings[int(value)]
                    elif kind=='inlineStr':
                        inline=cell.find('s:is',NS);value=''.join(inline.itertext()) if inline is not None else ''
                    elif kind=='e':raise InputError('Worksheet contains error cells')
                    elif int(cell.get('s','0')) in date_styles and value:
                        value=(epoch+timedelta(days=float(Decimal(value)))).isoformat()
                    if len(value)>MAX_CELL:raise InputError('Worksheet cell limit exceeded')
                    values[index-1]=value
                if any(v.strip() for v in values):result.append((int(row.get('r',len(result)+1)),values))
                if len(result)>MAX_ROWS+1:raise InputError('Maximum 5,000 rows per batch')
            return result
    except (zipfile.BadZipFile,KeyError,IndexError,ValueError,OverflowError,RuntimeError) as error:
        if isinstance(error,InputError):raise
        raise InputError('Malformed or unsupported XLSX workbook') from None

def extract_files(files,merchant_id):
    if not isinstance(files,list) or not 1<=len(files)<=MAX_FILES:raise InputError('Choose between 1 and 10 files')
    result=[];total=0;row_count=0;deadline=time.monotonic()+MAX_PROCESSING_SECONDS
    for item in files:
        if not isinstance(item,dict) or set(item)-{'filename','content','relative_path'}:raise InputError('Invalid file descriptor')
        relative,name=safe_path(item.get('relative_path') or item.get('filename'))
        extension=PurePosixPath(name).suffix.lower()
        if extension not in ('.csv','.xlsx'):raise InputError('Only CSV and XLSX reports are supported')
        encoded=item.get('content')
        if not isinstance(encoded,str) or len(encoded)>4_000_000:raise InputError('Individual file exceeds 3 MB')
        try:content=base64.b64decode(encoded,validate=True)
        except ValueError:raise InputError('Invalid base64 file data') from None
        if not content or len(content)>MAX_FILE_BYTES:raise InputError('Individual file must be nonempty and at most 3 MB')
        total+=len(content)
        if total>MAX_TOTAL_BYTES:raise InputError('Maximum total upload size is 10 MB')
        table=csv_table(content,deadline) if extension=='.csv' else xlsx_table(content,deadline)
        if len(table)<2:raise InputError('Transaction report must contain a header and data rows')
        headers=[str(h).strip() for h in table[0][1]]
        if not all(headers) or len({h.casefold() for h in headers})!=len(headers):raise InputError('Source headers must be nonempty and unique')
        keep=[i for i,h in enumerate(headers) if not SENSITIVE.search(h) and not re.search(r'[\w.+-]+@[\w-]+\.[\w.]+|\b(?:\d[ -]?){13,19}\b',h)]
        rows=[]
        for number,values in table[1:]:
            if len(values)>len(headers):raise InputError('CSV/XLSX row has more values than its header')
            values+=['']*(len(headers)-len(values))
            data={headers[i]:values[i] for i in keep}
            for header,value in data.items():
                if header.casefold() in ('merchant_id','merchant id') and value and value!=merchant_id:raise AccessDenied('Source merchant does not match the authorized merchant')
                if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+',value) or re.search(r'\b(?:\d[ -]?){13,19}\b',value):
                    raise InputError('Unsupported personal/card information in transaction report')
                if re.search(r'(?i)\bbearer\s+|\bgh[pousr]_|\bsk-[a-z0-9]',value):raise InputError('Authentication credentials are not accepted in POS reports')
                if value.strip().startswith(('=','@','+','-')) and not re.fullmatch(r'[+-]?\d[\d,.]*',value.strip()):
                    raise InputError('Formula-like source values are rejected')
            rows.append({'row':number,'values':data})
        row_count+=len(rows)
        if row_count>MAX_ROWS:raise InputError('Maximum 5,000 parsed rows per batch')
        kept=[headers[i] for i in keep]
        summary=any(re.search(r'daily total|monthly total|total sales|sales count|transaction count',h,re.I) for h in kept)
        result.append({'file_id':secrets.token_hex(12),'filename':name,'relative_path':relative,'format':extension[1:],'size':len(content),
            'sha256':hashlib.sha256(content).hexdigest(),'headers':kept,'excluded_sensitive_columns':len(headers)-len(keep),
            'summary_detected':summary,'suggestions':suggest(kept),'rows':rows})
    return result
