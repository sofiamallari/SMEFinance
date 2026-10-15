"""Validated, persistent transaction management and server-bound upload previews."""
import base64
import csv
import io
import json
import os
import secrets
import threading
import time
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET
from copilot.security import AccessDenied
from copilot.authorization import require

COLUMNS = ['date', 'type', 'amount', 'channel', 'category', 'reference', 'description']
CHANNELS = {'cash', 'qr_pay', 'tap_pay', 'pay_link', 'external_wallet', 'external_card'}

def validate_entry(row, as_of):
    if not isinstance(row, dict):
        raise ValueError('Each row must be an object')
    d = date.fromisoformat(str(row.get('date', '')))
    if not date(2000, 1, 1) <= d <= as_of:
        raise ValueError('Date must be between 2000-01-01 and the demo as-of date')
    kind = str(row.get('type', '')).strip().lower()
    if kind not in ('income', 'expense'):
        raise ValueError('Type must be income or expense')
    try:
        amount = Decimal(str(row.get('amount', '')))
    except InvalidOperation:
        raise ValueError('Invalid amount')
    if not amount.is_finite() or not 0 < amount <= Decimal('1e12') or amount != amount.quantize(Decimal('.01')):
        raise ValueError('Amount must be positive, finite, at most 1 trillion, with at most two decimal places')
    channel = str(row.get('payment_method', row.get('channel', 'cash')) or 'cash').strip().lower()
    if channel not in CHANNELS:
        raise ValueError('Invalid payment method')
    result = dict(date=d.isoformat(), type=kind, amount=float(amount), channel=channel)
    for key, limit in [('category',80), ('reference',100), ('description',250)]:
        value = str(row.get(key, '') or '').strip()
        if len(value) > limit:
            raise ValueError(f'{key} exceeds {limit} characters')
        result[key] = value or ('other' if key == 'category' else '')
    return result

def parse_upload(filename, content):
    if len(content) > 3_000_000:
        raise ValueError('File exceeds 3 MB')
    if filename.lower().endswith('.csv'):
        table = list(csv.reader(io.StringIO(content.decode('utf-8-sig')), strict=True))
    elif filename.lower().endswith('.xlsx'):
        # Read OOXML directly: no macros, formulas, external links or dependency required.
        ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if sum(i.file_size for i in z.infolist()) > 20_000_000:
                    raise ValueError('Expanded workbook exceeds 20 MB')
                strings = []
                if 'xl/sharedStrings.xml' in z.namelist():
                    strings = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', ns)]
                sheets = sorted(n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'))
                if len(sheets) != 1:
                    raise ValueError('Upload a workbook with exactly one worksheet')
                table = []
                for row in ET.fromstring(z.read(sheets[0])).findall('.//s:sheetData/s:row', ns):
                    values = []
                    for cell in row.findall('s:c', ns):
                        if cell.find('s:f', ns) is not None:
                            raise ValueError('Formula cells are not supported; paste values first')
                        index = 0
                        for ch in cell.get('r', ''):
                            if ch.isalpha(): index = index * 26 + ord(ch.upper()) - 64
                        if not index or index > 20:
                            raise ValueError('Invalid worksheet columns')
                        while len(values) < index: values.append('')
                        value = cell.findtext('s:v', '', ns)
                        if cell.get('t') == 's': value = strings[int(value)]
                        if cell.get('t') == 'inlineStr': value = ''.join(cell.find('s:is', ns).itertext())
                        values[index-1] = value
                    table.append(values)
        except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError) as e:
            raise ValueError('Invalid XLSX workbook') from e
    else:
        raise ValueError('Use CSV or .xlsx')
    table = [r for r in table if any(str(v).strip() for v in r)]
    if not table: raise ValueError('Empty file')
    headers = [str(v).strip().lower() for v in table.pop(0)]
    headers = [{'payment_method':'channel', 'reference_number':'reference'}.get(h,h) for h in headers]
    if len(set(headers)) != len(headers) or set(headers) - set(COLUMNS) or not {'date','type','amount'} <= set(headers):
        raise ValueError('Headers must be unique known columns and include date,type,amount')
    rows = []
    for i, r in enumerate(table, 2):
        if len(r) > len(headers): raise ValueError(f'Column count mismatch at row {i}')
        r += [''] * (len(headers)-len(r))
        rows.append(dict(zip(headers, r)))
    return rows

class TransactionStore:
    def __init__(self, copilot, path):
        self.copilot, self.path = copilot, path
        if getattr(copilot,"identity_store",None):
            from copilot.merchant_management import restore_profiles
            restore_profiles(copilot,copilot.identity_store)
            from copilot.transaction_settings import restore_currency_configuration
            restore_currency_configuration(copilot,copilot.identity_store)
        self.lock, self.previews, self.entries = threading.RLock(), {}, {}
        from copilot.transaction_journal import TransactionJournal
        self.journal=TransactionJournal(self)
        self.copilot.financial_data.attach(self.journal)
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                for line_number,line in enumerate(f,1):
                    event = json.loads(line)
                    if event.get('action')=='canonical_batch':continue
                    mid = event['merchant']
                    if mid not in copilot.merchants: continue
                    if event.get('action') == 'batch':
                        for item in event['entries']:
                            self.entries[item['id']] = (mid, validate_entry(item['entry'], copilot.as_of))
                        continue
                    from copilot.transaction_journal import checksum
                    tid = event.get('id') or 'LEGACY-'+checksum({'line':line_number,'event':event})[:24]
                    if event.get('action') == 'delete': self.entries.pop(tid, None)
                    else: self.entries[tid] = (mid, validate_entry(event['entry'], copilot.as_of))
            for tid, (mid, entry) in self.entries.items(): self.apply(mid, tid, entry)

    def authorize(self, p, mid, owner=False, action=None):
        require(p, action or ("manage_transactions" if owner else "create_transactions"), mid)
        if mid not in p.merchant_ids or p.role not in (('owner',) if owner else ('owner','staff')):
            raise AccessDenied('Only authorized owners and staff can access transactions; management requires owner')

    def apply(self, mid, tid, entry):
        m = self.copilot.merchants[mid]
        target = m.transactions if entry['type'] == 'income' else m.expenses
        target.append({**entry, 'id':tid, 'source':'manual', 'count':1})

    def checked(self, mid, rows, exclude=None):
        if not isinstance(rows,list) or not 1 <= len(rows) <= 1000: raise ValueError('Provide 1–1000 rows')
        seen, refs = set(), set()
        for tid,(merchant,e) in self.entries.items():
            if merchant == mid and tid != exclude:
                seen.add(json.dumps(e,sort_keys=True));
                if e['reference']: refs.add(e['reference'].casefold())
        records,_=self.journal.read()
        for tid,e in records.items():
            if e['merchant_id']==mid and tid!=exclude and e.get('external_reference'):refs.add(e['external_reference'].casefold())
        checked, errors = [], []
        for i,row in enumerate(rows,1):
            try:
                e = validate_entry(row,self.copilot.as_of)
                key = json.dumps(e,sort_keys=True)
                ref = e['reference'].casefold()
                if key in seen or (ref and ref in refs): raise ValueError('Duplicate transaction or reference')
                seen.add(key)
                if ref: refs.add(ref)
                checked.append(e)
            except (ValueError,TypeError,InvalidOperation) as exc: errors.append({'row':i,'error':str(exc)})
        return checked, errors

    def preview(self,p,mid,body):
        self.authorize(p,mid,action="bulk_import")
        rows = body.get('rows')
        if 'content' in body:
            try: content = base64.b64decode(body['content'],validate=True)
            except (ValueError,TypeError): raise ValueError('Invalid base64 file')
            rows = parse_upload(str(body.get('filename','')),content)
        with self.lock:
            checked,errors = self.checked(mid,rows)
            token = None
            now = time.time()
            self.previews = {k:v for k,v in self.previews.items() if v[3] > now}
            if not errors:
                token = secrets.token_urlsafe(32)
                self.previews[token] = (p.user_id,mid,checked,now+600,p.role)
            return {'rows':checked,'errors':errors,'valid':not errors,'preview_token':token,'total':len(rows)}

    def confirm(self,p,mid,token,confirmed):
        self.authorize(p,mid,action="bulk_import")
        with self.lock:
            preview = self.previews.get(token)
            if confirmed is not True or not preview or preview[0:2] != (p.user_id,mid) or preview[3] < time.time() or preview[4] != p.role:
                raise ValueError('Explicit confirmation of a current preview is required')
            result = self.save(p,mid,preview[2])
            if result['valid']:
                self.previews.pop(token)
                if p.authenticated:self.copilot.identity_store.audit('transactions_imported',p,mid,target=str(result['imported']))
            return result

    def persist(self,event):
        self.journal.append(event)

    def save(self,p,mid,rows):
        self.authorize(p,mid)
        with self.journal.writer():
            checked, errors = self.checked(mid,rows)
            if errors: return {'valid':False,'imported':0,'errors':errors}
            # One durable event per batch; replay preserves complete batches.
            ids = [secrets.token_hex(12) for _ in checked]
            events = [{'merchant':mid,'actor':p.user_id,'id':tid,'entry':e} for tid,e in zip(ids,checked)]
            self.persist({'merchant':mid,'action':'batch','entries':events})
            for event in events:
                self.entries[event['id']] = (mid,event['entry']); self.apply(mid,event['id'],event['entry'])
            if getattr(self.copilot,'identity_store',None) and p.authenticated:
                self.copilot.identity_store.audit('transactions_created',p,mid,target=str(len(checked)))
            return {'valid':True,'imported':len(checked),'errors':[]}

    def list_entries(self,p,mid):
        self.authorize(p,mid,action="view_transactions")
        return {'transactions':[{'id':tid,**e} for tid,(m,e) in self.entries.items() if m == mid]}

    def manage(self,p,mid,body):
        self.authorize(p,mid,owner=True)
        with self.journal.writer():
            tid = body.get('id'); action = body.get('action')
            if tid not in self.entries or self.entries[tid][0] != mid: raise ValueError('Unknown transaction')
            if action not in ('update','delete'): raise ValueError('Use update or delete')
            event = {'merchant':mid,'actor':p.user_id,'id':tid,'action':action}
            if action == 'update':
                checked,errors = self.checked(mid,[body.get('entry')],exclude=tid)
                if errors: return {'valid':False,'errors':errors}
                event['entry'] = checked[0]
            self.persist(event)
            m = self.copilot.merchants[mid]
            m.transactions[:] = [e for e in m.transactions if e.get('id') != tid]
            m.expenses[:] = [e for e in m.expenses if e.get('id') != tid]
            self.entries.pop(tid)
            if action == 'update':
                self.entries[tid] = (mid,event['entry']); self.apply(mid,tid,event['entry'])
            if p.authenticated:self.copilot.identity_store.audit('transaction_'+action,p,mid,tid)
            return {'valid':True}
