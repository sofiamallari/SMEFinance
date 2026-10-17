"""One JSONL source of truth, batch checksums, and inter-process append locking."""
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import json
import os
import threading
import time
from copilot.auth import InputError
from copilot.canonical_transactions import normalize,OFFSETS
from copilot.security import mask_pii

def checksum(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()

class LedgerError(InputError):
    def __init__(self):super().__init__('Transaction ledger integrity failure; restore a verified backup',500)

class TransactionJournal:
    def __init__(self,store):
        self.store=store;self.path=store.path;self.lock=store.lock;self.local=threading.local()

    @contextmanager
    def writer(self):
        with self.lock:
            depth=getattr(self.local,'depth',0)
            if depth:
                self.local.depth+=1
                try:yield self
                finally:self.local.depth-=1
                return
            os.makedirs(os.path.dirname(self.path) or '.',exist_ok=True)
            handle=open(self.path+'.lock','a+b')
            try:
                if os.name=='nt':
                    import msvcrt
                    handle.seek(0,2)
                    if handle.tell()==0:handle.write(b'0');handle.flush()
                    handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
                self.local.depth=1
                yield self
            finally:
                self.local.depth=0
                if os.name=='nt':
                    import msvcrt
                    handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
                handle.close()

    # Parsed ledger cache, shared by every reader of the same file. The key changes whenever the file is appended to or
    # replaced, so a cached copy is never served after new transactions or a replacing import are written.
    _cache={};_cache_lock=threading.Lock()

    def _version(self):
        try:info=os.stat(self.path)
        except FileNotFoundError:return None
        return (info.st_size,info.st_mtime_ns,info.st_ino)

    def read(self):
        version=self._version()
        if version is None:return {},{}
        key=os.path.abspath(self.path)
        with self._cache_lock:hit=self._cache.get(key)
        if not hit or hit[0]!=version:
            records,batches=self._parse()
            # Only keep the result if the file did not change while it was being parsed.
            if self._version()==version:
                with self._cache_lock:self._cache[key]=(version,records,batches)
            hit=(version,records,batches)
        # Callers get their own dicts so changes they make never leak into the cache.
        return {t:dict(r) for t,r in hit[1].items()},dict(hit[2])

    def _parse(self):
        records={};batches={}
        if not os.path.exists(self.path):return records,batches
        try:
            with open(self.path,encoding='utf-8') as stream:
                for line_number,line in enumerate(stream,1):
                    if not line.strip():continue
                    event=json.loads(line);mid=event['merchant']
                    if mid not in self.store.copilot.merchants:raise LedgerError()
                    if event.get('action')=='canonical_batch':
                        body={k:v for k,v in event.items() if k!='checksum'}
                        if event.get('checksum')!=checksum(body):raise LedgerError()
                        bid=event['batch_id']
                        if bid in batches and batches[bid]['checksum']!=event['checksum']:raise LedgerError()
                        # A Bulk POS Import replaces earlier imports: their rows stay in the file (append-only) but are no longer current.
                        for old in event.get('supersedes') or []:
                            if old not in batches or batches[old]['merchant']!=mid:raise LedgerError()
                            for tid in [t for t,r in records.items() if r.get('import_batch_id')==old and r.get('merchant_id')==mid]:records.pop(tid)
                        for row in event['transactions']:
                            if row.get('merchant_id')!=mid or not isinstance(row.get('transaction_id'),str) or not isinstance(row.get('amount'),str) or not Decimal(row['amount']).is_finite():raise LedgerError()
                            tid=row['transaction_id']
                            if tid in records and records[tid]!=row:raise LedgerError()
                            records[tid]=row
                        batches[bid]=event
                    else:
                        items=event.get('entries') if event.get('action')=='batch' else [event]
                        if not isinstance(items,list):raise LedgerError()
                        for item in items:
                            tid=item.get('id') or 'LEGACY-'+checksum({'line':line_number,'event':item})[:24]
                            if item.get('action')=='delete':records.pop(tid,None);continue
                            entry=item['entry'];merchant=self.store.copilot.merchants[mid]
                            values={'transaction_date':entry['date'],'net_amount':str(entry['amount']),'currency':merchant.currency,
                                'transaction_type':'sale' if entry['type']=='income' else 'expense',
                                'payment_method':entry.get('channel') or 'cash','status':'completed','external_reference':'',
                                'description':'','category':'other'}
                            row=normalize(values,merchant,{'timezone':OFFSETS.get(merchant.country,'+00:00')},time.time(),strict=True)
                            row['external_reference']=mask_pii(entry.get('reference',''));row['description']=mask_pii(entry.get('description',''))
                            row['category']=mask_pii(entry.get('category','other'))
                            records[tid]={**row,'transaction_id':tid,'merchant_id':mid,'source':'legacy_manual','import_batch_id':None,
                                'created_by':item.get('actor',event.get('actor','legacy')),'created_at':None,'source_filename':None}
            return records,batches
        except (ValueError,KeyError,TypeError,ArithmeticError):raise LedgerError() from None

    def append(self,event):
        encoded=(json.dumps(event,ensure_ascii=True,separators=(',',':'))+'\n').encode()
        with self.writer():
            self.read()  # Never append beyond corruption.
            with open(self.path,'a+b') as stream:
                stream.seek(0,2);offset=stream.tell()
                try:
                    stream.write(encoded);stream.flush();os.fsync(stream.fileno())
                except BaseException:
                    # Handles caught I/O failures; a power-loss torn tail is detected on read.
                    stream.seek(offset);stream.truncate();stream.flush();os.fsync(stream.fileno())
                    raise

    def append_batch(self,batch_id,merchant,rows,supersedes=None):
        with self.writer():
            records,batches=self.read()
            if batch_id in batches:
                if batches[batch_id]['transactions']!=rows:raise LedgerError()
                return False
            body={'action':'canonical_batch','schema_version':2,'batch_id':batch_id,'merchant':merchant,'transactions':rows,**({'supersedes':sorted(supersedes)} if supersedes else {})}
            self.append({**body,'checksum':checksum(body)})
            return True
