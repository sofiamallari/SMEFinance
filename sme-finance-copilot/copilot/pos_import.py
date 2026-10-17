"""Secure synchronous POS ETL, journal commits, persisted monitoring and alerts."""
import hashlib
import hmac
import json
import secrets
import re
import threading
from datetime import datetime,timezone,date
from decimal import Decimal
from statistics import median
from copilot.auth import AuthError,InputError,digest
from copilot.security import Principal,AccessDenied
from copilot.canonical_transactions import FIELDS,REQUIRED,normalize,fingerprint,money,zone,safe_text,ALIASES,RowError
from copilot.pos_extract import extract_files,MAX_ROWS
from copilot.transaction_journal import TransactionJournal,LedgerError,checksum

TTL=1800;MAX_PENDING=64;MAX_STAGING_BYTES=32_000_000
RULES=['required_fields','uniqueness','monetary_precision','date_validity','currency_validity','status_validity','payment_method_validity',
       'count_reconciliation','financial_reconciliation','merchant_authorization','import_integrity']

# Live validation progress per batch (counts only, no row data), read by the progress endpoint while validate() runs.
PROGRESS={};PROGRESS_LOCK=threading.Lock()
def _progress(bid,**values):
    with PROGRESS_LOCK:PROGRESS.setdefault(bid,{}).update(values)

def validation_progress(token,mid,bid):
    """Counts for a running validation. Validation holds the identity database for its whole run, so this does not
    query it: only the same session that started the validation (matched by token hash) and the same business get counts."""
    with PROGRESS_LOCK:value=dict(PROGRESS.get(bid) or {})
    if not token or value.get('merchant')!=mid or not hmac.compare_digest(value.get('session','') or '',digest(token)):return {'batch_id':bid,'phase':'idle'}
    return {'batch_id':bid,**{k:v for k,v in value.items() if k in ('phase','done','total','file')}}

def dump(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def utc(value):return datetime.fromtimestamp(value,timezone.utc).isoformat().replace('+00:00','Z')

class POSImportService:
    def __init__(self,auth,store):
        self.auth,self.store=auth,store;self.journal=TransactionJournal(store)
        with auth.db() as db:
            db.execute('INSERT OR IGNORE INTO pos_integrity_key VALUES (1,?)',(secrets.token_hex(32),))
            self.key=bytes.fromhex(db.execute('SELECT secret FROM pos_integrity_key WHERE singleton=1').fetchone()[0])
        self.recover()
        from copilot.transaction_settings import TransactionSettings
        self.settings=TransactionSettings(self)

    def sign(self,batch_id,mid,actor,payload,session_hash=''):
        return hmac.new(self.key,dump([batch_id,mid,actor,session_hash,payload]).encode(),hashlib.sha256).hexdigest()

    def _dataset_sign(self,bid,mid,actor,rows,mappings,version,session_hash):
        return self.sign(bid,mid,actor,{'rows':rows,'mappings':mappings,'version':version},session_hash)

    def authorize(self,token,action,mid):
        try:
            with self.auth.db() as db:return self._guard(db,token,action,mid)
        except AccessDenied:
            self.auth.audit('pos_access_denied',merchant=mid,result='denied',reason='merchant_scope_or_permission')
            raise

    def read_ledger(self,mid):
        try:return self.journal.read()
        except LedgerError:
            self._storage_failure(mid,'storage','critical','Confirmed transaction journal integrity failure; affected access and writes are blocked.')
            raise

    def _guard(self,db,token,action,mid):
        self.auth._authorize(db,token,action,mid)
        row=self.auth._session(db,token,touch=False)
        if row['role'] not in ('owner','staff'):raise AccessDenied('Merchant transaction access requires an authorized business account')
        return Principal(row['user_id'],row['role'])

    def _alert(self,db,mid,bid,rule,severity,description,rows,recommendation):
        now=self.auth.clock();existing=db.execute('SELECT alert_id FROM quality_alerts WHERE merchant_id=? AND batch_id IS ? AND rule=?',(mid,bid,rule)).fetchone()
        if existing:return existing[0]
        aid=secrets.token_hex(12)
        db.execute('INSERT INTO quality_alerts VALUES (?,?,?,?,?,?,?,?,?,?,?)',(aid,mid,bid,rule,severity,description,rows,recommendation,'open',now,now))
        return aid

    def _cleanup(self,db):
        now=self.auth.clock()
        rows=db.execute("SELECT * FROM pos_import_runs WHERE state IN ('staged','validated','validation_failed','failed') AND expires_at<=?",(now,)).fetchall()
        for row in rows:
            db.execute("UPDATE pos_import_runs SET state='expired',source_json=NULL,dataset_json=NULL,preview_hash=NULL WHERE batch_id=?",(row['batch_id'],))
            self._alert(db,row['merchant_id'],row['batch_id'],'session_expired','informational','The abandoned import session expired; no transactions were committed.',0,'Select the original files and validate a new batch.')
            self.auth.audit('pos_import_expired',merchant=row['merchant_id'],target=row['batch_id'],db=db)
        db.execute("UPDATE pos_import_runs SET source_json=NULL,dataset_json=NULL WHERE state IN ('cancelled','expired','committed')")
        # Failed/abandoned run metadata has a documented 90-day retention; committed lineage stays.
        old=db.execute("SELECT batch_id FROM pos_import_runs WHERE state IN ('failed','cancelled','expired') AND created_at<?",(now-90*86400,)).fetchall()
        for row in old:
            db.execute("DELETE FROM pos_import_runs WHERE batch_id=?",(row[0],))

    def _private(self,db,token,mid,bid,action='bulk_import'):
        actor=self._guard(db,token,action,mid)
        row=db.execute('SELECT * FROM pos_import_runs WHERE batch_id=? AND merchant_id=? AND actor_id=? AND session_hash=?',(bid,mid,actor.user_id,digest(token))).fetchone()
        if not row:raise AuthError('Import session is not available to this user, session and merchant',403)
        if row['state']=='expired' or (row['expires_at']<=self.auth.clock() and row['state']!='committed'):raise InputError('Import session expired',409)
        return actor,row

    def _run_public(self,row):
        source=json.loads(row['source_json']) if row['source_json'] else None
        metrics=json.loads(row['metrics_json']);result=json.loads(row['result_json']) if row['result_json'] else None
        return {'batch_id':row['batch_id'],'merchant_id':row['merchant_id'],'actor':row['actor_id'],'kind':row['kind'],
                'state':row['state'],'created_at':utc(row['created_at']),'expires_at':utc(row['expires_at']),
                'validation_version':row['validation_version'],'metrics':metrics,'findings':json.loads(row['findings_json']),
                'result':result,'audit_reference':row['audit_reference'],
                'files':[{k:v for k,v in f.items() if k!='rows'} for f in source] if source else metrics.get('files',[])}

    def inspect_files(self,token,mid,files):
        actor=self.authorize(token,'bulk_import',mid)
        result=extract_files(files,mid,discover=True)
        self.authorize(token,'bulk_import',mid)
        self.auth.audit('pos_sources_inspected',actor,mid)
        return {'files':result}

    def stage(self,token,mid,files):
        bid=secrets.token_hex(16)
        with self.auth.db() as db:
            actor=self._guard(db,token,'bulk_import',mid);self._cleanup(db)
            # A new upload replaces all imported data, so this user's unfinished uploads for the same business are
            # abandoned: cancel them to free their temporary storage instead of hitting the storage limit.
            for (old,) in db.execute("SELECT batch_id FROM pos_import_runs WHERE merchant_id=? AND actor_id=? AND state IN ('staged','validated','validation_failed')",(mid,actor.user_id)).fetchall():
                db.execute("UPDATE pos_import_runs SET state='cancelled',source_json=NULL,dataset_json=NULL,preview_hash=NULL WHERE batch_id=?",(old,))
                self.auth.audit('pos_import_cancelled',actor,mid,old,reason='replaced_by_new_upload',db=db)
            active=db.execute("SELECT COUNT(*) FROM pos_import_runs WHERE state IN ('staged','validated','validation_failed','committing')").fetchone()[0]
            size=db.execute("SELECT COALESCE(SUM(LENGTH(CAST(source_json AS BLOB))+COALESCE(LENGTH(CAST(dataset_json AS BLOB)),0)),0) FROM pos_import_runs").fetchone()[0]
            owned=db.execute("SELECT COUNT(*) FROM pos_import_runs WHERE actor_id=? AND state IN ('staged','validated','validation_failed')",(actor.user_id,)).fetchone()[0]
            if active>=MAX_PENDING or owned>=5 or size>=MAX_STAGING_BYTES:raise InputError('Temporary import capacity reached; cancel or wait for sessions to expire',429)
        try:source=extract_files(files,mid)
        except (InputError,AccessDenied) as error:
            with self.auth.db() as db:
                self._guard(db,token,'bulk_import',mid)
                now=self.auth.clock()
                metrics={'file_count':len(files) if isinstance(files,list) else 0,'parsed_rows':0,'eligible_rows':0,'duplicate_rows':0,'invalid_rows':0,'quality_status':'fail'}
                db.execute('INSERT INTO pos_import_runs(batch_id,merchant_id,actor_id,session_hash,kind,state,created_at,expires_at,metrics_json,findings_json) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (bid,mid,actor.user_id,digest(token),'pos','failed',now,now+TTL,dump(metrics),dump([{'field':'file','error':str(error),'correction':'Upload a bounded transaction-level CSV/XLSX with values only.'}])))
                scoped=isinstance(error,AccessDenied)
                self._alert(db,mid,bid,'source_merchant_mismatch' if scoped else 'extraction_failed','critical' if scoped else 'high','A source file could not be safely extracted or failed merchant integrity. No transactions were saved.',0,'Correct the file format/merchant ownership and start a new import.')
                self.auth.audit('pos_extract_failed',actor,mid,bid,result='denied' if scoped else 'failed',reason='source_scope_mismatch' if scoped else 'file_rejected',db=db)
            error.batch_id=bid;raise
        encoded=dump(source)
        with self.auth.db() as db:
            db.execute('BEGIN IMMEDIATE');self._guard(db,token,'bulk_import',mid);self._cleanup(db)
            used=db.execute('SELECT COALESCE(SUM(LENGTH(CAST(source_json AS BLOB))+COALESCE(LENGTH(CAST(dataset_json AS BLOB)),0)),0) FROM pos_import_runs').fetchone()[0]
            active=db.execute("SELECT COUNT(*) FROM pos_import_runs WHERE state IN ('staged','validated','validation_failed','committing')").fetchone()[0]
            owned=db.execute("SELECT COUNT(*) FROM pos_import_runs WHERE actor_id=? AND state IN ('staged','validated','validation_failed')",(actor.user_id,)).fetchone()[0]
            if active>=MAX_PENDING or owned>=5:raise InputError('Temporary import capacity reached',429)
            if used+len(encoded.encode())>MAX_STAGING_BYTES:raise InputError('Temporary storage limit reached',429)
            now=self.auth.clock()
            metrics={'file_count':len({f.get('upload_index',f['relative_path']) for f in source}),'worksheet_count':sum(bool(f.get('worksheet')) for f in source),'parsed_rows':sum(len(f['rows']) for f in source),'eligible_rows':0,'duplicate_rows':0,'invalid_rows':0,
                     'files':[{k:v for k,v in f.items() if k not in ('rows','suggestions','headers')} for f in source],'quality_status':'not_validated','actor_role':actor.role}
            db.execute('INSERT INTO pos_import_runs(batch_id,merchant_id,actor_id,session_hash,kind,state,created_at,expires_at,source_json,source_signature,metrics_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (bid,mid,actor.user_id,digest(token),'pos','staged',now,now+TTL,encoded,self.sign(bid,mid,actor.user_id,source,digest(token)),dump(metrics)))
            audit=self.auth.audit('pos_import_staged',actor,mid,bid,db=db)
            db.execute('UPDATE pos_import_runs SET audit_reference=? WHERE batch_id=?',(audit['seq'],bid))
        return self.get_session(token,mid,bid)

    def get_session(self,token,mid,bid):
        with self.auth.db() as db:
            self._cleanup(db);actor,row=self._private(db,token,mid,bid)
            result=self._run_public(row)
            if row['source_json']:
                source=json.loads(row['source_json']);result['files']=[{**{k:v for k,v in f.items() if k!='rows'},'sample':f['rows'][:3]} for f in source]
            result['mappings']=json.loads(row['mappings_json']) if row['mappings_json'] else {}
            return result

    def _mapping(self,file,mapping):
        if not isinstance(mapping,dict) or set(mapping)-{'columns','defaults','timezone','date_format','control_totals','report_kind','payment_method_values','review','template','profile'}:raise InputError('Unsupported mapping fields')
        columns=mapping.get('columns',{});defaults=mapping.get('defaults',{})
        if not isinstance(columns,dict) or not isinstance(defaults,dict):raise InputError('Columns and defaults must be mapping objects')
        review=mapping.get('review',{})
        if not isinstance(review,dict) or set(review)-{'type_confirmed','amount_confirmed','currency_confirmed','payment_method_confirmed'} or any(type(v) is not bool for v in review.values()):raise InputError('Invalid mapping review confirmations')
        profile=mapping.get('profile')
        if profile is not None:
            if not isinstance(profile,dict) or set(profile)!={'kind','confirmed'} or profile.get('kind') not in ('revenue','expense') or profile.get('confirmed') is not True:raise InputError('Choose and explicitly confirm the report profile')
            if 'transaction_type' not in columns:
                permitted=('sale','refund','reversal') if profile['kind']=='revenue' else ('expense',)
                if defaults.get('transaction_type') not in permitted:raise InputError('Worksheet default transaction type conflicts with the selected report profile')
            if profile['kind']=='revenue' and 'payment_method' not in columns and review.get('payment_method_confirmed') is not True:raise InputError('Missing source payment method: explicitly verify a worksheet payment method from trustworthy records')
        if 'transaction_type' not in columns and review.get('type_confirmed') is not True:raise InputError('Explicitly confirm the worksheet transaction type default')
        ambiguous=any(re.sub(r'\s*\([^)]*\)\s*$','',str(columns.get(k,'')).strip().casefold())=='amount' for k in ('net_amount','gross_amount'))
        if ambiguous and review.get('amount_confirmed') is not True:raise InputError('Confirm whether Amount represents net or gross before validation')
        if file.get('ambiguous_currency_symbols') and not file.get('currency_hints') and review.get('currency_confirmed') is not True:raise InputError('Ambiguous currency symbol: explicitly confirm the source currency')
        translations=mapping.get('payment_method_values',{})
        if not isinstance(translations,dict) or len(translations)>30 or any(not isinstance(k,str) or len(k)>100 or v not in ('cash','qr_pay','tap_pay','pay_link','external_card','external_wallet','bank_transfer','not_recorded') for k,v in translations.items()):raise InputError('Invalid explicit payment-method translations')
        if not isinstance(columns,dict) or set(columns)-FIELDS or any(not isinstance(v,str) or v not in file['headers'] for v in columns.values()) or len(set(columns.values()))!=len(columns):raise InputError('Column mapping contains unknown, protected or conflicting fields')
        if not isinstance(defaults,dict) or set(defaults)-{'currency','transaction_type','status','payment_method','category'}:raise InputError('Unsupported mapping defaults')
        required=REQUIRED-{'payment_method'} if (profile or {}).get('kind')=='expense' else REQUIRED # expense reports may not record how a cost was paid
        if not required<=set(columns)|set(defaults) or 'transaction_date' not in columns or not {'net_amount','gross_amount'}&set(columns):raise InputError('Map date and net/gross amount; explicitly map or default all required fields')
        if any(columns.get(k,'').strip().lower() in ALIASES['settlement_amount'] for k in ('net_amount','gross_amount')):raise InputError('Settlement columns cannot be mapped as sales net/gross amounts')
        if mapping.get('date_format','iso') not in ('iso','day_first','month_first'):raise InputError('Invalid date format')
        zone(mapping.get('timezone','+00:00'))
        if file['summary_detected'] or mapping.get('report_kind','transactions')!='transactions':raise InputError('Aggregate summaries are unsupported; supply one row per transaction, not daily/monthly totals')
        control=mapping.get('control_totals',{})
        if not isinstance(control,dict) or set(control)-{'count','net_total','gross_total','basis'} or control.get('basis','completed_net') not in ('completed_net','nominal_net'):raise InputError('Unsupported control totals or monetary basis')
        if control.get('count') is not None and (type(control['count']) is not int or not 0<=control['count']<=MAX_ROWS):raise InputError('Control count must be an integer from 0 to 10,000')
        for field in ('net_total','gross_total'):
            if control.get(field) not in (None,''):money(control[field],field)
        return columns,defaults,control

    @staticmethod
    def _imported(existing,mid):
        """Current Bulk POS Import batches for a merchant; a new import replaces all of them (manual entries stay)."""
        return sorted({r['import_batch_id'] for r in existing.values() if r.get('merchant_id')==mid and str(r.get('source','')).startswith('pos_') and r.get('import_batch_id')})

    @staticmethod
    def _kept(existing,mid):
        """Records that survive a replacing import, used for duplicate checks."""
        return {t:r for t,r in existing.items() if not (r.get('merchant_id')==mid and str(r.get('source','')).startswith('pos_'))}

    def _duplicates(self,existing,seen,row):
        ref=row['external_reference'].casefold();fp=fingerprint(row)
        candidates=[r for r in existing.values() if r['merchant_id']==row['merchant_id'] and
            ((ref and r.get('external_reference','').casefold()==ref) or (not ref and fingerprint(r)==fp))]+seen
        for other in candidates:
            other_ref=other.get('external_reference','').casefold()
            if ref and other_ref!=ref:continue
            if not ref and fingerprint(other)!=fp:continue
            exact=fingerprint(other)==fp
            same_source=other.get('source_file_hash')==row.get('source_file_hash') and other.get('source_row_number')==row.get('source_row_number')
            if exact and (bool(ref) or same_source):return 'exact'
            return 'ambiguous'
        return None

    class DuplicateIndex:
        """Same rules as _duplicates, but rows are looked up by reference or fingerprint instead of scanning every
        committed transaction for each new row (that scan made large imports take minutes to validate)."""
        def __init__(self,existing,mid):
            self.by_ref={};self.by_fp={}
            for r in existing.values():
                if r['merchant_id']==mid:self.add(r)

        def add(self,row):
            fp=fingerprint(row);ref=(row.get('external_reference') or '').casefold()
            self.by_fp.setdefault(fp,[]).append((row,fp))
            if ref:self.by_ref.setdefault(ref,[]).append((row,fp))

        def check(self,row):
            ref=row['external_reference'].casefold();fp=fingerprint(row)
            for other,other_fp in (self.by_ref.get(ref,[]) if ref else self.by_fp.get(fp,[])):
                exact=other_fp==fp
                same_source=other.get('source_file_hash')==row.get('source_file_hash') and other.get('source_row_number')==row.get('source_row_number')
                if exact and (bool(ref) or same_source):return 'exact'
                return 'ambiguous'
            return None

    def validate(self,token,mid,bid,mappings):
        self.authorize(token,'bulk_import',mid)
        _progress(bid,merchant=mid,session=digest(token),phase='reading',done=0,total=None,file=None)
        try:return self._validate(token,mid,bid,mappings)
        finally:
            with PROGRESS_LOCK:PROGRESS.pop(bid,None)

    def _validate(self,token,mid,bid,mappings):
        with self.journal.writer():
            existing,_=self.read_ledger(mid);previous=set(self._imported(existing,mid));replaced=[r for r in existing.values() if r.get('import_batch_id') in previous];existing=self._kept(existing,mid)
            with self.auth.db() as db:
                db.execute('BEGIN IMMEDIATE');self._cleanup(db);actor,run=self._private(db,token,mid,bid)
                if run['state'] in ('committed','committing','cancelled'):raise InputError('This batch cannot be revalidated',409)
                source=json.loads(run['source_json']) if run['source_json'] else None
                if source is None or not hmac.compare_digest(run['source_signature'],self.sign(bid,mid,actor.user_id,source,run['session_hash'])):
                    return self._integrity_failure(db,actor,mid,bid)
                eligible=[];seen=[];findings=[];reconciliation=[];duplicates=0;invalid=0;all_valid=[];ambiguous=0;index=self.DuplicateIndex(existing,mid)
                _progress(bid,phase='validating',done=0,total=sum(len(f['rows']) for f in source))
                version=run['validation_version']+1;ordinal=0;now=self.auth.clock()
                merchant_settings=self.settings.current(db,mid)
                if not isinstance(mappings,dict) or set(mappings)!={f['file_id'] for f in source}:raise InputError('Provide one mapping for every source file')
                for file in source:
                    mapping=mappings[file['file_id']];file_valid=[];file_errors=0
                    if isinstance(mapping,dict):mapping={**mapping,'timezone':mapping.get('timezone',merchant_settings['timezone'])}
                    try:
                        if file.get('currency_hints') and file['currency_hints']!=[self.store.copilot.merchants[mid].currency]:raise InputError('Workbook currency declaration does not match this merchant; no FX conversion is supported')
                        columns,defaults,controls=self._mapping(file,mapping)
                        if mapping.get('template'):
                            template=mapping['template']
                            if not isinstance(template,dict) or set(template)!={'id','version'} or not isinstance(template.get('id'),str) or type(template.get('version')) is not int:raise InputError('Invalid template selection')
                            saved=db.execute('SELECT * FROM merchant_mapping_templates WHERE merchant_id=? AND template_id=? AND version=?',(mid,template['id'],template['version'])).fetchone()
                            if not saved or json.loads(saved['headers_json'])!=file['headers']:raise InputError('Template does not match this merchant and exact source columns')
                            original=json.loads(saved['mapping_json'])
                            if original.get('columns',{}).get('transaction_type')!=columns.get('transaction_type') or original.get('defaults',{}).get('transaction_type')!=defaults.get('transaction_type'):raise InputError('Template transaction meaning changed; review a new independent mapping')
                    except InputError as error:
                        invalid+=len(file['rows']);findings.append({'filename':file.get('source_label',file['filename']),'file_id':file['file_id'],'worksheet':file.get('worksheet'),'row':file.get('header_row',1),'field':'mapping','error':str(error),'correction':'Correct the mapping or supply a transaction-level report.'});continue
                    label=file.get('source_label',file['filename'])
                    for raw in file['rows']:
                        ordinal+=1
                        if ordinal%25==0:_progress(bid,done=ordinal,file=label)
                        try:
                            values={field:raw['values'][header] for field,header in columns.items()};values={**defaults,**values}
                            if values.get('payment_method') in mapping.get('payment_method_values',{}):values['payment_method']=mapping['payment_method_values'][values['payment_method']]
                            row=normalize(values,self.store.copilot.merchants[mid],{**mapping,'merchant_timezone':merchant_settings['timezone'],'source_currency_hints':file.get('currency_hints',[])},now)
                            if mapping.get('profile') and ((mapping['profile']['kind']=='expense' and row['transaction_type'] not in ('expense','cash_out')) or (mapping['profile']['kind']=='revenue' and row['transaction_type'] in ('expense','cash_out'))):raise RowError('transaction_type','Source transaction type conflicts with the selected report profile; correct the profile or split mixed revenue/expense sources')
                            row.update(transaction_id='TX-'+bid+'-'+str(ordinal),merchant_id=mid,source='pos_'+file['format'],
                                import_batch_id=bid,source_filename=file['filename'],source_file_hash=file['sha256'],source_row_number=raw['row'],source_file_id=file['file_id'],source_worksheet=file.get('worksheet'),source_workbook_hash=file.get('workbook_hash'),source_values=raw['values'],
                                mapping_version=version,created_by=actor.user_id,created_at=utc(now))
                            result=index.check(row)
                            if result=='ambiguous':
                                ambiguous+=1;raise InputError('Ambiguous duplicate reference/fingerprint; correct or use stable unique POS identifiers')
                            file_valid.append(row);all_valid.append(row)
                            if result=='exact':
                                duplicates+=1
                                findings.append({'filename':file.get('source_label',file['filename']),'file_id':file['file_id'],'worksheet':file.get('worksheet'),'row':raw['row'],'field':'uniqueness','error':'Exact duplicate excluded','correction':'Verify the visible exclusion; no additional financial entry is created.','validation_result':'excluded'})
                            else:eligible.append(row);seen.append(row);index.add(row)
                        except InputError as error:
                            invalid+=1;file_errors+=1
                            findings.append({'filename':file.get('source_label',file['filename']),'file_id':file['file_id'],'worksheet':file.get('worksheet'),'row':raw['row'],'field':getattr(error,'field','uniqueness'),
                                'error':str(error),'correction':getattr(error,'correction','Correct conflicting records or add unique external references.')})
                    completed=sum((Decimal(r['effective_amount']) for r in file_valid),Decimal(0));nominal=sum((Decimal(r['amount']) for r in file_valid),Decimal(0))
                    gross=sum((Decimal(r['gross_amount']) for r in file_valid if r['gross_amount'] is not None),Decimal(0))
                    observed=completed if controls.get('basis','completed_net')=='completed_net' else nominal
                    mismatches=[]
                    if controls.get('count') is not None and controls['count']!=len(file['rows']):mismatches.append('Reported row count does not match parsed transaction rows')
                    if controls.get('net_total') not in (None,'') and (file_errors or money(controls['net_total'],'net_total')!=observed):mismatches.append('Reported net control does not reconcile on the selected basis')
                    if controls.get('gross_total') not in (None,'') and (file_errors or any(r['gross_amount'] is None for r in file_valid) or money(controls['gross_total'],'gross_total')!=gross):mismatches.append('Reported gross control requires mapped gross values and matching gross totals')
                    provided=any(controls.get(k) not in (None,'') for k in ('count','net_total','gross_total'))
                    reconciliation.append({'filename':file.get('source_label',file['filename']),'file_id':file['file_id'],'worksheet':file.get('worksheet'),'parsed_rows':len(file['rows']),'controls':controls,
                        'nominal_net_total':format(nominal,'.2f'),'completed_net_total':format(completed,'.2f'),'mapped_gross_total':format(gross,'.2f') if any(r['gross_amount'] is not None for r in file_valid) else None,
                        'status':'fail' if mismatches else 'pass' if provided else 'not_available','issues':mismatches,
                        'explanation':'Totals include all valid source rows before visible duplicate exclusions. Failed/pending/voided rows contribute zero completed revenue. Settlement is separate; no FX conversion.'})
                _progress(bid,phase='saving',done=ordinal)
                parsed=sum(len(f['rows']) for f in source);blocked=bool(invalid or ambiguous or any(r['status']=='fail' for r in reconciliation))
                if parsed!=len(eligible)+duplicates+invalid:raise InputError('Count reconciliation integrity failure',500)
                source_counts=[{'file_id':f['file_id'],'filename':f.get('source_label',f['filename']),'parsed_rows':len(f['rows']),
                    'eligible_rows':sum(r.get('source_file_id')==f['file_id'] for r in eligible),
                    'duplicate_rows':sum(x.get('file_id')==f['file_id'] and x.get('validation_result')=='excluded' for x in findings),
                    'invalid_rows':len(f['rows'])-sum(r.get('source_file_id')==f['file_id'] for r in eligible)-sum(x.get('file_id')==f['file_id'] and x.get('validation_result')=='excluded' for x in findings)} for f in source]
                metrics={'file_count':len({f.get('upload_index',f['relative_path']) for f in source}),'worksheet_count':sum(bool(f.get('worksheet')) for f in source),'parsed_rows':parsed,'valid_rows':len(eligible)+duplicates,'eligible_rows':len(eligible),
                    'duplicate_rows':duplicates,'invalid_rows':invalid,'ambiguous_duplicates':ambiguous,
                    'eligible_total':format(sum((Decimal(r['effective_amount']) for r in eligible),Decimal(0)),'.2f'),
                    'eligible_nominal_total':format(sum((Decimal(r['amount']) for r in eligible),Decimal(0)),'.2f'),
                    'currency':self.store.copilot.merchants[mid].currency,'source_counts':source_counts,'reconciliation':reconciliation,
                    'reconciliation_failures':sum(r['status']=='fail' for r in reconciliation),'count_reconciled':True,
                    'files':[{k:v for k,v in f.items() if k not in ('rows','suggestions','headers')} for f in source],
                    'quality_status':'fail' if blocked else 'warning' if duplicates or any(r['status']=='not_available' for r in reconciliation) else 'pass','actor_role':actor.role}
                errors=[f for f in findings if f.get('validation_result')!='excluded']
                metrics['rules']={rule:'pass' for rule in RULES}
                metrics['rules'].update(required_fields='fail' if any('required' in f['error'].lower() or f['field']=='mapping' for f in errors) else 'pass',
                    uniqueness='fail' if ambiguous else 'warning' if duplicates else 'pass',
                    monetary_precision='fail' if any(f['field'] in ('amount','net_amount','gross_amount','tax','discount','refund_amount','settlement_amount') for f in errors) else 'pass',
                    date_validity='fail' if any(f['field']=='transaction_date' for f in errors) else 'pass',
                    currency_validity='fail' if any(f['field']=='currency' for f in errors) else 'pass',
                    status_validity='fail' if any(f['field'] in ('status','transaction_type') for f in errors) else 'pass',
                    payment_method_validity='fail' if any(f['field']=='payment_method' for f in errors) else 'pass',
                    financial_reconciliation='fail' if metrics['reconciliation_failures'] else 'warning' if any(r['status']=='not_available' for r in reconciliation) else 'pass')
                if any(f['field']=='mapping' for f in errors):
                    for rule in ('monetary_precision','date_validity','currency_validity','status_validity','payment_method_validity','financial_reconciliation'):
                        if metrics['rules'][rule]=='pass':metrics['rules'][rule]='warning'
                metrics.update(replaced_rows=len(replaced),replaced_imports=len({r['import_batch_id'] for r in replaced}))
                preview=secrets.token_urlsafe(32) if not blocked else None
                db.execute('UPDATE pos_import_runs SET state=?,mappings_json=?,dataset_json=?,dataset_signature=?,preview_hash=?,validation_version=?,metrics_json=?,findings_json=? WHERE batch_id=?',
                    ('validation_failed' if blocked else 'validated',dump(mappings),dump(eligible),self._dataset_sign(bid,mid,actor.user_id,eligible,mappings,version,run['session_hash']),digest(preview) if preview else None,version,dump(metrics),dump(findings),bid))
                self._quality_checks(db,mid,bid,metrics,eligible,existing)
                audit=self.auth.audit('pos_import_validated',actor,mid,bid,result='failed' if blocked else 'success',reason='blocking_findings' if blocked else 'validated',db=db)
                db.execute('UPDATE pos_import_runs SET audit_reference=? WHERE batch_id=?',(audit['seq'],bid))
                return {'batch_id':bid,'valid':not blocked,'metrics':metrics,'findings':findings,'preview_token':preview,'validation_version':version}

    def _integrity_failure(self,db,actor,mid,bid):
        run=db.execute('SELECT metrics_json FROM pos_import_runs WHERE batch_id=?',(bid,)).fetchone()
        metrics=json.loads(run[0]);metrics['quality_status']='fail';metrics.setdefault('rules',{})['import_integrity']='fail'
        db.execute('UPDATE pos_import_runs SET metrics_json=? WHERE batch_id=?',(dump(metrics),bid))
        db.execute("UPDATE pos_import_runs SET state='integrity_failed',source_json=NULL,dataset_json=NULL,preview_hash=NULL WHERE batch_id=?",(bid,))
        self._alert(db,mid,bid,'import_integrity','critical','Staged import integrity verification failed. Commit is blocked.',0,'Cancel this batch and start from verified original files.')
        self.auth.audit('pos_integrity_failure',actor,mid,bid,result='denied',reason='integrity_failure',db=db)
        return {'valid':False,'batch_id':bid,'blocking_error':'Staged data integrity failure; no transactions saved'}

    def _quality_checks(self,db,mid,bid,metrics,rows,existing):
        parsed=metrics.get('parsed_rows',0);invalid=metrics.get('invalid_rows',0);duplicates=metrics.get('duplicate_rows',0)
        if invalid:self._alert(db,mid,bid,'invalid_records','high','Invalid transaction records block this batch.',invalid,'Review field-level errors, correct the mapping/source and validate again.')
        if metrics.get('ambiguous_duplicates'):self._alert(db,mid,bid,'ambiguous_duplicates','high','Conflicting identifiers or ambiguous fingerprints block this batch.',metrics['ambiguous_duplicates'],'Use unique POS transaction references and correct conflicting amounts.')
        if metrics.get('reconciliation_failures'):self._alert(db,mid,bid,'reconciliation_mismatch','high','Reported POS control totals do not reconcile.',parsed,'Verify gross/net meaning, counts, taxes, discounts, refunds and control basis.')
        if parsed>=2 and duplicates/parsed>=.2:self._alert(db,mid,bid,'duplicate_rate','medium','Exact duplicate rate is at least 20%.',duplicates,'Review repeated files and source identifiers; exclusions are visible in preview.')
        if parsed>=2 and invalid/parsed>=.1:self._alert(db,mid,bid,'invalid_rate','medium','Invalid row rate is at least 10%.',invalid,'Correct source data and mapping. This is a data-quality signal, not a fraud determination.')
        if duplicates:self._alert(db,mid,bid,'duplicates_excluded','informational','Known exact duplicates were excluded from eligible rows.',duplicates,'Verify duplicate exclusions before confirming import.')
        history=[abs(Decimal(r['effective_amount'])) for r in existing.values() if r['merchant_id']==mid and r['status']=='completed' and Decimal(r['effective_amount'])]
        if len(history)>=5:
            threshold=max(Decimal(1000),median(history)*10);unusual=sum(abs(Decimal(r['amount']))>threshold for r in rows)
            if unusual:self._alert(db,mid,bid,'unusual_amount','medium','Amounts exceed ten times the available-history median (and at least 1,000).',unusual,'Verify high-value receipts; this does not establish fraud.')
        dates=sorted({r['business_date'] for r in rows})
        if any((datetime.fromisoformat(b)-datetime.fromisoformat(a)).days>7 for a,b in zip(dates,dates[1:])):
            self._alert(db,mid,bid,'date_gap','medium','Validated transactions have a gap exceeding seven days.',len(rows),'Check report coverage; a gap may legitimately reflect no trading.')

    def preview(self,token,mid,bid,offset=0,limit=50):
        if type(offset) is not int or type(limit) is not int or offset<0 or not 1<=limit<=100:raise InputError('Invalid preview pagination')
        with self.auth.db() as db:
            self._cleanup(db);actor,run=self._private(db,token,mid,bid)
            if run['state'] not in ('validated','validation_failed'):raise InputError('Validate this batch before previewing',409)
            rows=json.loads(run['dataset_json'] or '[]')
            if not hmac.compare_digest(run['dataset_signature'] or '',self._dataset_sign(bid,mid,actor.user_id,rows,json.loads(run['mappings_json'] or '{}'),run['validation_version'],run['session_hash'])):return self._integrity_failure(db,actor,mid,bid)
            return {'batch_id':bid,'valid':run['state']=='validated','rows':rows[offset:offset+limit],'offset':offset,'total':len(rows),
                    'metrics':json.loads(run['metrics_json']),'findings':json.loads(run['findings_json']),'validation_version':run['validation_version']}

    def commit(self,token,mid,bid,preview_token,confirmed):
        self.authorize(token,'bulk_import',mid)
        if confirmed is not True or not isinstance(preview_token,str):raise InputError('Explicit confirmation of the validated preview is required')
        with self.journal.writer():
            existing,batches=self.read_ledger(mid);supersedes=self._imported(existing,mid);existing=self._kept(existing,mid)
            with self.auth.db() as db:
                db.execute('BEGIN IMMEDIATE');actor,run=self._private(db,token,mid,bid)
                if run['state']=='committed':raise InputError('Batch already committed. Fetch its confirmed outcome; replay is denied.',409)
                if run['state']!='validated' or run['preview_hash']!=digest(preview_token):raise InputError('Validated preview is unavailable or changed',409)
                rows=json.loads(run['dataset_json'] or '[]')
                if not hmac.compare_digest(run['dataset_signature'] or '',self._dataset_sign(bid,mid,actor.user_id,rows,json.loads(run['mappings_json'] or '{}'),run['validation_version'],run['session_hash'])):return self._integrity_failure(db,actor,mid,bid)
                index=self.DuplicateIndex(existing,mid)
                for row in rows:
                    if index.check(row):
                        self._alert(db,mid,bid,'concurrent_duplicate','high','Committed transactions changed after validation; commit is blocked.',1,'Validate again to reconcile the current duplicate exclusions.')
                        db.execute("UPDATE pos_import_runs SET state='validation_failed',preview_hash=NULL WHERE batch_id=?",(bid,))
                        return {'ok':False,'error':'Transactions changed since preview; validate again','batch_id':bid}
                    index.add(row)
                metrics=json.loads(run['metrics_json']);now=self.auth.clock()
                result={'ok':True,'batch_id':bid,'files_processed':metrics.get('file_count',0),'worksheets_processed':metrics.get('worksheet_count',0),'imported_rows':len(rows),
                        'duplicates_excluded':metrics.get('duplicate_rows',0),'rejected_rows':metrics.get('invalid_rows',0),
                        'imported_total':metrics.get('eligible_total','0.00'),'currency':self.store.copilot.merchants[mid].currency,
                        'completed_at':utc(now),'status':'committed','replaced_imports':len(supersedes)}
                db.execute("UPDATE pos_import_runs SET state='committing',result_json=?,completed_at=? WHERE batch_id=?",(dump(result),now,bid))
                self.auth.audit('pos_commit_intent',actor,mid,bid,db=db)
            try:
                self.journal.append_batch(bid,mid,rows,supersedes)
                self._finalize(bid)
            except LedgerError:
                self._storage_failure(mid,bid,'critical','Ledger integrity verification failed; writes are blocked.')
                raise
            except Exception:
                self._storage_failure(mid,bid,'high','Commit was interrupted. The durable journal marker will be checked before retry/recovery.')
                raise InputError('Commit could not be finalized. Check the batch outcome before reimporting.',500) from None
            return result

    def _storage_failure(self,mid,bid,severity,message):
        with self.auth.db() as db:
            self._alert(db,mid,bid,'commit_failed',severity,message,0,'Review run details and restore verified storage if necessary; acknowledgment never bypasses blocking checks.')
            self.auth.audit('pos_commit_failed',merchant=mid,target=bid,result='failed',reason='storage_failure',db=db)

    def _finalize(self,bid):
        with self.auth.db() as db:
            db.execute('BEGIN IMMEDIATE');run=db.execute('SELECT * FROM pos_import_runs WHERE batch_id=?',(bid,)).fetchone()
            if not run or run['state']=='committed':return
            actor=Principal(run['actor_id'],json.loads(run['metrics_json']).get('actor_role','owner' if run['kind']=='manual' else 'staff'))
            audit=self.auth.audit('transaction_created' if run['kind']=='manual' else 'pos_import_committed',actor,run['merchant_id'],bid,db=db)
            db.execute("UPDATE pos_import_runs SET state='committed',source_json=NULL,dataset_json=NULL,preview_hash=NULL,audit_reference=? WHERE batch_id=?",(audit['seq'],bid))

    def recover(self):
        with self.journal.writer():
            try:records,batches=self.journal.read()
            except LedgerError:return  # Authorized foreground calls report corruption, never append blindly.
            with self.auth.db() as db:runs=[dict(r) for r in db.execute("SELECT * FROM pos_import_runs WHERE state='committing'")]
            for run in runs:
                bid=run['batch_id']
                if bid in batches:
                    rows=json.loads(run['dataset_json'] or '[]')
                    if rows!=batches[bid]['transactions'] or not hmac.compare_digest(run['dataset_signature'] or '',self._dataset_sign(bid,run['merchant_id'],run['actor_id'],rows,json.loads(run['mappings_json'] or '{}'),run['validation_version'],run['session_hash'])):
                        self._storage_failure(run['merchant_id'],bid,'critical','Commit-intent and durable journal contents disagree; operation remains blocked.')
                        continue
                    self._finalize(bid)
                else:
                    with self.auth.db() as db:
                        db.execute("UPDATE pos_import_runs SET state='failed',preview_hash=NULL WHERE batch_id=?",(bid,))
                        self._alert(db,run['merchant_id'],bid,'interrupted_no_commit','high','An interrupted commit has no durable journal batch; no financial records were imported.',0,'Revalidate or start a new authorized batch. Recovery never creates financial entries without current authorization.')

    def cancel(self,token,mid,bid):
        with self.auth.db() as db:
            actor,run=self._private(db,token,mid,bid)
            if run['state'] in ('committed','committing'):raise InputError('A committed/in-progress batch cannot be cancelled',409)
            db.execute("UPDATE pos_import_runs SET state='cancelled',source_json=NULL,dataset_json=NULL,preview_hash=NULL WHERE batch_id=?",(bid,))
            self.auth.audit('pos_import_cancelled',actor,mid,bid,db=db)
            return {'ok':True,'batch_id':bid,'state':'cancelled'}

    def single(self,token,mid,values,key):
        self.authorize(token,'create_transactions',mid)
        if not isinstance(key,str) or not 8<=len(key)<=100:raise InputError('A stable 8–100 character submission key is required')
        if not isinstance(values,dict) or not isinstance(values.get('external_reference'),str) or not values['external_reference'].strip():raise InputError('External reference is required for manual encoding')
        with self.journal.writer():
            existing,batches=self.read_ledger(mid)
            with self.auth.db() as db:
                db.execute('BEGIN IMMEDIATE');actor=self._guard(db,token,'create_transactions',mid)
                config=self.settings.current(db,mid)
                row=normalize(values,self.store.copilot.merchants[mid],{'timezone':config['timezone'],'merchant_timezone':config['timezone']},self.auth.clock())
                request_hash=checksum(row)
                old=db.execute("SELECT * FROM pos_import_runs WHERE actor_id=? AND merchant_id=? AND kind='manual' AND idempotency_key=?",(actor.user_id,mid,key)).fetchone()
                if old:
                    if old['source_signature']!=request_hash:raise InputError('Submission key belongs to a different transaction',409)
                    if old['state']=='committed':return json.loads(old['result_json'])
                    raise InputError('Submission is being recovered; check Transaction History before retrying',409)
                bid=secrets.token_hex(16);now=self.auth.clock()
                row.update(transaction_id='TX-'+bid+'-1',merchant_id=mid,source='manual',import_batch_id=None,source_filename=None,
                           source_file_hash=None,source_row_number=None,mapping_version=1,created_by=actor.user_id,created_at=utc(now))
                if self._duplicates(existing,[],row):raise InputError('Duplicate or ambiguous transaction; use a distinct external reference',409)
                result={'ok':True,'transaction_id':row['transaction_id'],'reference':row['external_reference'],'status':'committed','batch_id':bid,
                        'imported_rows':1,'imported_total':row['effective_amount'],'currency':row['currency'],'completed_at':utc(now)}
                metrics={'file_count':0,'parsed_rows':1,'valid_rows':1,'eligible_rows':1,'invalid_rows':0,'duplicate_rows':0,'eligible_total':row['effective_amount'],'quality_status':'pass','actor_role':actor.role}
                db.execute('INSERT INTO pos_import_runs(batch_id,merchant_id,actor_id,session_hash,kind,state,created_at,expires_at,source_signature,dataset_json,dataset_signature,metrics_json,result_json,completed_at,idempotency_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (bid,mid,actor.user_id,digest(token),'manual','committing',now,now+TTL,request_hash,dump([row]),self._dataset_sign(bid,mid,actor.user_id,[row],{},0,digest(token)),dump(metrics),dump(result),now,key))
            try:self.journal.append_batch(bid,mid,[row]);self._finalize(bid)
            except Exception:
                self._storage_failure(mid,bid,'high','Manual transaction commit was interrupted; inspect its durable outcome before resubmitting.')
                raise InputError('Transaction persistence could not be finalized; check history before retrying',500) from None
            return result

    def template(self,token,mid):
        """Blank standard Revenue/Expense report template for this merchant (Bulk Import permission)."""
        actor=self.authorize(token,'bulk_import',mid)
        from copilot.report_template import build
        merchant=self.store.copilot.merchants[mid];name,content=build(merchant.name,merchant.currency)
        self.auth.audit('pos_template_downloaded',actor,mid,result='success')
        return name,content

    def import_summary(self,token,mid):
        """What the chat needs to answer "did my upload go through" and "how many records": the latest completed
        Bulk POS Import, what is in the records now (imports replace each other; manual entries are kept) and unfinished uploads."""
        with self.auth.db() as db:
            self._guard(db,token,'view_transactions',mid)
            runs=db.execute("SELECT batch_id,kind,state,created_at,completed_at,metrics_json,result_json FROM pos_import_runs WHERE merchant_id=? AND kind='pos' ORDER BY created_at DESC",(mid,)).fetchall()
        records,_=self.read_ledger(mid)
        mine=[r for r in records.values() if r.get('merchant_id')==mid]
        imported=[r for r in mine if str(r.get('source','')).startswith('pos_')];manual=[r for r in mine if not str(r.get('source','')).startswith('pos_')]
        def span(rows):
            dates=[r['business_date'] for r in rows if r.get('business_date')]
            return {'start':min(dates),'end':max(dates)} if dates else None
        expense=lambda r:r.get('transaction_type') in ('expense','cash_out')
        latest=None;done=[r for r in runs if r['state']=='committed']
        if done:
            run=done[0];result=json.loads(run['result_json'] or '{}');metrics=json.loads(run['metrics_json'] or '{}')
            latest={'imported_at':utc(run['completed_at'] or run['created_at']),
                'files':[str(f.get('source_label') or f.get('filename') or '')[:120] for f in metrics.get('files',[])][:6],
                'file_count':int(result.get('files_processed') or metrics.get('file_count') or 0),'worksheet_count':int(result.get('worksheets_processed') or metrics.get('worksheet_count') or 0),
                'imported_rows':int(result.get('imported_rows') or 0),'duplicates_excluded':int(result.get('duplicates_excluded') or 0),'rejected_rows':int(result.get('rejected_rows') or 0),
                'imported_total':str(result.get('imported_total') or '0.00'),'replaced_imports':int(result.get('replaced_imports') or 0),
                'is_current':any(r.get('import_batch_id')==run['batch_id'] for r in imported)}
        last_manual=max((r for r in manual if r.get('business_date')),key=lambda r:r['business_date'],default=None)
        return {'currency':self.store.copilot.merchants[mid].currency,'latest_import':latest,
            'imported_rows_current':len(imported),'imported_revenue_rows':sum(not expense(r) for r in imported),'imported_expense_rows':sum(expense(r) for r in imported),'imported_dates':span(imported),
            'manual_entries':len(manual),'manual_dates':span(manual),'latest_manual_entry_date':last_manual['business_date'] if last_manual else None,
            'completed_imports':len(done),'unfinished_uploads':sum(r['state'] in ('staged','validated','validation_failed') for r in runs),
            'failed_uploads':sum(r['state'] in ('failed','integrity_failed') for r in runs),'upload_attempts':len(runs)}

    def history(self,token,mid,filters=None):
        filters=filters or {}
        with self.auth.db() as db:self._guard(db,token,'view_transactions',mid)
        for key in ('start','end'):
            if filters.get(key):
                try:date.fromisoformat(filters[key])
                except ValueError:raise InputError('History dates must use YYYY-MM-DD')
        if filters.get('start') and filters.get('end') and filters['start']>filters['end']:raise InputError('Start date must not exceed end date')
        with self.journal.writer():
            try:records,batches=self.journal.read()
            except LedgerError:
                self._storage_failure(mid,'storage','critical','Confirmed ledger integrity failure. Transaction access/writes are blocked.');raise
        rows=[r for r in records.values() if r['merchant_id']==mid]
        for field in ('status','source','payment_method'):
            if filters.get(field):rows=[r for r in rows if r.get(field)==filters[field]]
        # Report type follows the transaction's financial meaning, so manual entries are grouped the same way as imports.
        report=filters.get('report')
        if report not in (None,'','revenue','expense'):raise InputError('Report type must be revenue or expense')
        if report:rows=[r for r in rows if (r.get('transaction_type') in ('expense','cash_out'))==(report=='expense')]
        search=str(filters.get('search') or '').strip().casefold()
        if len(search)>80:raise InputError('Search text must be at most 80 characters')
        if search:
            fields=('transaction_id','external_reference','description','category','sub_category','classification','source_filename','source_worksheet','payment_method','transaction_type')
            # The original file values ("Credit Card", sub-category text) are searchable too.
            text=lambda r:' '.join([*(str(r.get(f) or '') for f in fields),*(str(v) for v in (r.get('source_values') or {}).values())]).casefold()
            rows=[r for r in rows if all(term in text(r) for term in search.split())]
        if filters.get('start'):rows=[r for r in rows if r['business_date']>=filters['start']]
        if filters.get('end'):rows=[r for r in rows if r['business_date']<=filters['end']]
        offset=int(filters.get('offset',0));limit=int(filters.get('limit',50))
        if offset<0 or not 1<=limit<=100:raise InputError('Invalid history pagination')
        rows.sort(key=lambda r:(r['transaction_date'],r['transaction_id']),reverse=True)
        return {'transactions':rows[offset:offset+limit],'total':len(rows),'offset':offset,'limit':limit}

    def monitoring(self,token,mid,filters=None):
        self.authorize(token,'view_quality_monitoring',mid)
        filters=filters or {};self.recover()
        with self.journal.writer():
            try:self.read_ledger(mid)
            except LedgerError:pass  # Monitoring still displays the persisted critical finding.
        with self.auth.db() as db:
            self._guard(db,token,'view_quality_monitoring',mid);self._cleanup(db)
            all_runs=db.execute("SELECT * FROM pos_import_runs WHERE merchant_id=? AND kind='pos' ORDER BY created_at DESC",(mid,)).fetchall()
            measured=[json.loads(r['metrics_json']) for r in all_runs if r['validation_version']>0]
            parsed=sum(m.get('parsed_rows',0) for m in measured);valid=sum(m.get('valid_rows',0) for m in measured)
            invalid=sum(m.get('invalid_rows',0) for m in measured);duplicates=sum(m.get('duplicate_rows',0) for m in measured)
            alerts=[dict(r) for r in db.execute('SELECT * FROM quality_alerts WHERE merchant_id=? ORDER BY detected_at DESC',(mid,))]
            open_count=sum(a['state']!='resolved' for a in alerts)
            attention=[a for a in alerts if a['state']!='resolved'][:5]
            for field in ('severity','state'):
                if filters.get(field):alerts=[a for a in alerts if a[field]==filters[field]]
            for key in ('start','end'):
                if filters.get(key):
                    bound=datetime.fromisoformat(filters[key]).replace(tzinfo=timezone.utc).timestamp()+(86400-1 if key=='end' else 0)
                    alerts=[a for a in alerts if a['detected_at']>=bound] if key=='start' else [a for a in alerts if a['detected_at']<=bound]
            successes=[r for r in all_runs if r['state']=='committed']
            runs=[r for r in all_runs if not filters.get('run_state') or r['state']==filters['run_state']]
            summary={'total_import_runs':len(all_runs),'successful_imports':len(successes),
                'failed_imports':sum(r['state'] in ('failed','validation_failed','integrity_failed') for r in all_runs),'parsed_rows':parsed,
                'valid_row_rate':valid/parsed if parsed else None,'invalid_row_rate':invalid/parsed if parsed else None,
                'duplicate_rate':duplicates/parsed if parsed else None,'reconciliation_failures':sum(m.get('reconciliation_failures',0) for m in measured),
                'open_alerts':open_count,'last_successful_import':utc(successes[0]['completed_at']) if successes else None,
                'formula':'Rates use latest validation of each retained POS run; valid=eligible+exact duplicates; parsed=eligible+duplicates+invalid. Unresolved=open+acknowledged.'}
            run_offset=int(filters.get('run_offset',0));run_limit=int(filters.get('run_limit',100))
            alert_offset=int(filters.get('alert_offset',0));alert_limit=int(filters.get('alert_limit',100))
            if min(run_offset,alert_offset)<0 or not 1<=run_limit<=100 or not 1<=alert_limit<=100:raise InputError('Invalid monitoring pagination')
            run_offset=min(run_offset,max(0,(len(runs)-1)//run_limit)*run_limit)
            alert_offset=min(alert_offset,max(0,(len(alerts)-1)//alert_limit)*alert_limit)
            return {'summary':summary,'runs':[self._run_public(r) for r in runs[run_offset:run_offset+run_limit]],'alerts':alerts[alert_offset:alert_offset+alert_limit],
                    'run_total':len(runs),'alert_total':len(alerts),'run_offset':run_offset,'alert_offset':alert_offset,'attention':attention,'rules':RULES,'evaluated_at':utc(self.auth.clock())}

    def run_details(self,token,mid,bid):
        with self.auth.db() as db:
            self._guard(db,token,'view_quality_monitoring',mid)
            row=db.execute('SELECT * FROM pos_import_runs WHERE batch_id=? AND merchant_id=?',(bid,mid)).fetchone()
            if not row:raise InputError('Import run not found',404)
            result=self._run_public(row)
            result['alerts']=[dict(a) for a in db.execute('SELECT * FROM quality_alerts WHERE merchant_id=? AND batch_id=?',(mid,bid))]
            result['alert_events']=[dict(e) for e in db.execute('SELECT e.* FROM quality_alert_events e JOIN quality_alerts a ON a.alert_id=e.alert_id WHERE a.merchant_id=? AND a.batch_id=? ORDER BY e.created_at',(mid,bid))]
            return result

    def alert_action(self,token,mid,aid,state,reason):
        action='acknowledge_quality_alerts' if state=='acknowledged' else 'resolve_quality_alerts'
        if state not in ('acknowledged','resolved') or not isinstance(reason,str) or not 8<=len(reason.strip())<=500:raise InputError('Choose an alert transition and provide 8–500 characters of reason/evidence')
        reason=safe_text(reason,'reason',500)
        with self.auth.db() as db:
            db.execute('BEGIN IMMEDIATE');actor=self._guard(db,token,action,mid)
            alert=db.execute('SELECT * FROM quality_alerts WHERE alert_id=? AND merchant_id=?',(aid,mid)).fetchone()
            if not alert:raise InputError('Alert not found',404)
            if (alert['state'],state) not in (('open','acknowledged'),('acknowledged','resolved')):raise InputError('Alert lifecycle is Open → Acknowledged → Resolved',409)
            now=self.auth.clock()
            db.execute('UPDATE quality_alerts SET state=?,updated_at=? WHERE alert_id=?',(state,now,aid))
            db.execute('INSERT INTO quality_alert_events VALUES (?,?,?,?,?,?,?)',(secrets.token_hex(12),aid,actor.user_id,alert['state'],state,reason.strip(),now))
            self.auth.audit('quality_alert_'+state,actor,mid,aid,db=db)
            return {'ok':True,'state':state,'warning':'Alert status never bypasses import validation or changes financial records'}
