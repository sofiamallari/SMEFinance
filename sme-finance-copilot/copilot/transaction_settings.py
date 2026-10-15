"""Merchant settings reuse live membership/grant checks and the existing audit chain."""
import copy,hashlib,json,secrets
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from copilot.auth import InputError
from copilot.security import AccessDenied,Principal
from copilot.canonical_transactions import IMPORT_CURRENCIES,METHODS,safe_text
from copilot.currency_catalog import search,timezones

COUNTRY_ZONES={'ID':'Asia/Jakarta','CN':'Asia/Shanghai','PH':'Asia/Manila','MY':'Asia/Kuala_Lumpur','SG':'Asia/Singapore','TH':'Asia/Bangkok','VN':'Asia/Ho_Chi_Minh'}
DISPLAY_FORMATS=('YYYY-MM-DD','DD/MM/YYYY','MM/DD/YYYY')
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'))

def restore_currency_configuration(copilot,auth):
    # Saved configuration is applied before journal projection, never to record values.
    with auth.db() as db:rows=db.execute('SELECT merchant_id,config_json FROM merchant_transaction_settings').fetchall()
    for row in rows:
        mid=row['merchant_id'];currency=json.loads(row['config_json'])['base_currency']
        if mid in copilot.merchants:
            base=copilot.financial_data.base[mid]
            if base.currency!=currency and any(bool(getattr(base,k,None)) for k in ('transactions','expenses','receivables','payables','wallet_balance','monthly_debt_service','confirmed_orders_value','prior_loans')):
                raise InputError('Saved currency conflicts with existing configured financial data; operator review is required',409)
            copilot.merchants[mid].currency=currency
            copilot.financial_data.base[mid].currency=currency

class TransactionSettings:
    def __init__(self,pos):self.pos=pos;self.auth=pos.auth;self.c=pos.store.copilot

    def guard(self,db,token,mid,edit=False):
        session=self.auth._session(db,token,touch=False)
        if session['role'] not in (('owner',) if edit else ('owner','staff')):raise AccessDenied('Business transaction settings are not available to this role')
        if edit:self.auth._authorize(db,token,'manage_transactions',mid)
        else:
            for action in ('create_transactions','bulk_import','view_transactions'):
                try:self.auth._authorize(db,token,action,mid);break
                except AccessDenied:pass
            else:raise AccessDenied('An authorized merchant transaction operation is required')
        return Principal(session['user_id'],session['role'])

    def current(self,db,mid):
        if mid not in self.c.merchants:raise AccessDenied('Merchant access denied')
        row=db.execute('SELECT * FROM merchant_transaction_settings WHERE merchant_id=?',(mid,)).fetchone()
        if row:return {**json.loads(row['config_json']),'version':row['version'],'merchant_id':mid}
        m=self.c.merchants[mid]
        if m.currency not in IMPORT_CURRENCIES or m.country not in COUNTRY_ZONES:raise InputError('Merchant configuration requires explicit initialization by the application operator',409)
        return {'merchant_id':mid,'base_currency':m.currency,'timezone':COUNTRY_ZONES[m.country],
                'display_date_format':'YYYY-MM-DD','default_status':'completed','payment_method_values':{},'version':0}

    def currency_locked(self,db,mid):
        m=self.c.financial_data.base[mid]
        financial_fields=('transactions','expenses','receivables','payables','loans','wallet_balance','monthly_debt_service','confirmed_orders_value','prior_loans')
        return (any(bool(getattr(m,k,None)) for k in financial_fields) or
                any(r['merchant_id']==mid for r in self.pos.journal.read()[0].values()) or
                any(p.merchant_id==mid for p in self.c.payments.payments.values()) or
                bool(self.c.payments.wallets.get(mid,0)) or
                bool(db.execute('SELECT 1 FROM pos_import_runs WHERE merchant_id=? LIMIT 1',(mid,)).fetchone()) or
                bool(db.execute('SELECT 1 FROM applications WHERE merchant_id=? LIMIT 1',(mid,)).fetchone()))

    def get(self,token,mid,include_catalog=False):
        with self.auth.db() as db:
            actor=self.guard(db,token,mid);value=self.current(db,mid)
            value.update(migration_required=value['base_currency']!='CNY',can_edit=actor.role=='owner',currency_locked=self.currency_locked(db,mid),
                         eligible_currencies=sorted(IMPORT_CURRENCIES),transaction_types=['sale','expense','refund','reversal'],
                         statuses=['completed','pending','failed','voided'],payment_methods=sorted(set(METHODS.values())),payment_method_aliases=dict(METHODS))
            if include_catalog:
                from copilot.demo_environment import selected
                value.update(currencies=[c for c in search() if not selected() or c['code']=='CNY'],timezones=timezones())
            return value

    def save(self,token,mid,body):
        with self.pos.journal.writer():return self._save(token,mid,body)

    def _save(self,token,mid,body):
        allowed={'base_currency','timezone','display_date_format','default_status','payment_method_values','expected_version','confirmed'}
        if not isinstance(body,dict) or set(body)-allowed or body.get('confirmed') is not True:raise InputError('Confirm the merchant settings update')
        with self.pos.journal.writer(),self.auth.db() as db:
            db.execute('BEGIN IMMEDIATE');actor=self.guard(db,token,mid,True);old=self.current(db,mid)
            if type(body.get('expected_version')) is not int or body['expected_version']!=old['version']:raise InputError('Settings changed; reload before saving',409)
            config={k:body.get(k,old[k]) for k in ('base_currency','timezone','display_date_format','default_status','payment_method_values')}
            if not isinstance(config['base_currency'],str) or (config['base_currency']!='CNY' and config['base_currency']!=old['base_currency']):raise InputError('Catalog currency is not enabled for transaction processing; no FX or simulator tax assumptions are supplied')
            if config['base_currency']!=old['base_currency'] and self.currency_locked(db,mid):raise InputError('Base currency is locked by existing financial data, balances or import runs; historical currency migration is not supported',409)
            if not isinstance(config['timezone'],str) or config['timezone'] not in timezones():raise InputError('Select a valid IANA timezone')
            if config['display_date_format'] not in DISPLAY_FORMATS:raise InputError('Invalid display date format')
            if config['default_status'] not in ('completed','pending','failed','voided'):raise InputError('Unsupported default status')
            translations=config['payment_method_values']
            if not isinstance(translations,dict) or len(translations)>30:raise InputError('At most 30 confirmed payment translations are supported')
            for label,target in translations.items():
                if not isinstance(label,str) or not label.strip() or len(label)>100 or target not in set(METHODS.values()):raise InputError('Invalid payment translation')
                safe_text(label,'payment label',100)
            version=old['version']+1
            db.execute('INSERT INTO merchant_transaction_settings VALUES(?,?,?,?,?) ON CONFLICT(merchant_id) DO UPDATE SET config_json=excluded.config_json,version=excluded.version,updated_by=excluded.updated_by,updated_at=excluded.updated_at',
                       (mid,encoded(config),version,actor.user_id,self.auth.clock()))
            self.auth.audit('transaction_settings_updated',actor,mid,str(version),db=db,metadata={'schema_version':1,'configuration_digest':hashlib.sha256(encoded(config).encode()).hexdigest()})
        self.c.merchants[mid].currency=config['base_currency'];self.c.financial_data.base[mid].currency=config['base_currency']
        return self.get(token,mid)

    def templates(self,token,mid):
        with self.auth.db() as db:
            self.guard(db,token,mid)
            return [dict(r,headers=json.loads(r['headers_json']),mapping=json.loads(r['mapping_json'])) for r in db.execute('SELECT t.* FROM merchant_mapping_templates t WHERE merchant_id=? AND version=(SELECT MAX(version) FROM merchant_mapping_templates x WHERE x.merchant_id=t.merchant_id AND x.template_id=t.template_id) ORDER BY name,template_id',(mid,))]

    def save_template(self,token,mid,body):
        if not isinstance(body,dict) or set(body)-{'name','batch_id','file_id','expected_version','template_id','confirmed'} or body.get('confirmed') is not True:raise InputError('Explicitly confirm saving a validated mapping')
        name=safe_text(body.get('name'),'template name',80)
        if not name:raise InputError('A template name is required')
        with self.auth.db() as db:
            db.execute('BEGIN IMMEDIATE');actor=self.guard(db,token,mid,True)
            _,run=self.pos._private(db,token,mid,body.get('batch_id'))
            if run['state']!='validated':raise InputError('Only a successfully validated, uncommitted batch can supply a template')
            source=next((f for f in json.loads(run['source_json']) if f['file_id']==body.get('file_id')),None)
            if not source:raise InputError('Source not found')
            mapping=json.loads(run['mappings_json'])[source['file_id']]
            # Independent control totals must never be reused as template defaults.
            mapping=copy.deepcopy(mapping);mapping.pop('control_totals',None)
            tid=body.get('template_id') or secrets.token_hex(12)
            if not isinstance(tid,str) or not 1<=len(tid)<=80:raise InputError('Invalid template identity')
            previous=db.execute('SELECT MAX(version) FROM merchant_mapping_templates WHERE merchant_id=? AND template_id=?',(mid,tid)).fetchone()[0] or 0
            if type(body.get('expected_version',0)) is not int or body.get('expected_version',0)!=previous:raise InputError('Template changed; reload before saving',409)
            if not previous and db.execute('SELECT COUNT(DISTINCT template_id) FROM merchant_mapping_templates WHERE merchant_id=?',(mid,)).fetchone()[0]>=50:raise InputError('Merchant template limit reached')
            db.execute('INSERT INTO merchant_mapping_templates VALUES(?,?,?,?,?,?,?,?)',(mid,tid,previous+1,name,encoded(source['headers']),encoded(mapping),actor.user_id,self.auth.clock()))
            self.auth.audit('transaction_mapping_template_saved',actor,mid,tid+':'+str(previous+1),db=db)
            return {'ok':True,'template_id':tid,'version':previous+1}
