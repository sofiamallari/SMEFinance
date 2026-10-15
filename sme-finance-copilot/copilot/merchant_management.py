"""Administrative business metadata; never grants financial access or creates ledger rows."""
import copy,secrets,json,hashlib
from dataclasses import fields,MISSING
from copilot.auth import InputError
from copilot.currency_policy import CODE
from copilot.security import AccessDenied
from copilot.data.synthetic import Merchant,PERSONAS
from copilot.transaction_settings import TransactionSettings,COUNTRY_ZONES,DISPLAY_FORMATS,encoded
from copilot.canonical_transactions import IMPORT_CURRENCIES,safe_text
from copilot.currency_catalog import timezones

def empty_merchant(mid,profile,currency):
    # Neutral model inputs only; no accounts, balances, ledger rows or synthetic history.
    values={f.name:False if f.type=='bool' or f.type is bool else 0 for f in fields(Merchant) if f.default is MISSING and f.default_factory is MISSING}
    values.update(merchant_id=mid,name=profile['name'],country=profile['country'],sector=profile['sector'],currency=currency,bookkeeping='none')
    return Merchant(**values)

def restore_profiles(c,auth):
    with auth.db() as db:
        for mid,m in c.merchants.items():
            db.execute('INSERT OR IGNORE INTO merchant_profiles VALUES (?,?,?,?,?,1,NULL,?)',(mid,m.name,m.country,m.sector,'active',auth.clock()))
        for row in db.execute('SELECT * FROM merchant_profiles'):
            mid=row['merchant_id']
            if mid not in c.merchants:
                conf=db.execute('SELECT config_json FROM merchant_transaction_settings WHERE merchant_id=?',(mid,)).fetchone()
                if not conf:raise InputError('Saved merchant configuration is missing; operator review required',409)
                c.merchants[mid]=empty_merchant(mid,row,json.loads(conf[0])['base_currency'])
                c.financial_data.base[mid]=copy.deepcopy(c.merchants[mid])
            for m in (c.merchants[mid],c.financial_data.base[mid]):
                for key in ('name','country','sector'):setattr(m,key,row[key])
            auth.merchants.add(mid)

class MerchantManagement:
    def __init__(self,pos):self.pos=pos;self.auth=pos.auth;self.c=pos.store.copilot;self.settings=TransactionSettings(pos)
    def guard(self,token):
        actor=self.auth.principal(token)
        if actor.role!='security_admin':raise AccessDenied('System Admin only')
        self.auth.authorize(token,'manage_users')
        return actor
    def listing(self,token):
        self.guard(token)
        with self.auth.db() as db:
            rows=[]
            for row in db.execute('SELECT * FROM merchant_profiles ORDER BY name COLLATE NOCASE,merchant_id'):
                conf=self.settings.current(db,row['merchant_id'])
                rows.append({**dict(row),**{k:conf[k] for k in ('base_currency','timezone','display_date_format')},'migration_required':conf['base_currency']!=CODE,'settings_version':conf['version'],'currency_locked':self.settings.currency_locked(db,row['merchant_id'])})
        return {'merchants':rows,'countries':sorted(COUNTRY_ZONES),'currencies':[CODE],'categories':sorted({p['sector'] for p in PERSONAS}),'timezones':timezones(),'date_formats':list(DISPLAY_FORMATS)}
    def save(self,token,body,mid=None):
        self.guard(token)
        self.auth.authorize(token,'manage_users',reauth=True)
        with self.pos.journal.writer():return self._save(token,body,mid)
    def _save(self,token,body,mid=None):
        actor=self.guard(token)
        if not isinstance(body,dict) or set(body)-{'name','country','sector','base_currency','timezone','display_date_format','status','expected_version','expected_settings_version'}:raise InputError('Unsupported merchant fields')
        attempted=False
        try:
            with self.pos.journal.writer(),self.auth.db() as db:
                db.execute('BEGIN IMMEDIATE')
                old=db.execute('SELECT * FROM merchant_profiles WHERE merchant_id=?',(mid,)).fetchone() if mid else None
                if mid and not old:raise InputError('Merchant not found',404)
                previous=self.settings.current(db,mid) if old else {}
                attempted=bool(old and body.get('base_currency',previous['base_currency'])!=previous['base_currency'])
                if old and (type(body.get('expected_version')) is not int or body['expected_version']!=old['version']):raise InputError('Merchant changed; refresh before saving',409)
                if old and 'expected_settings_version' in body and body['expected_settings_version']!=previous['version']:raise InputError('Transaction settings changed; refresh before saving',409)
                val={key:body.get(key,old[key] if old and key in old.keys() else previous.get(key,CODE if key=='base_currency' else None)) for key in ('name','country','sector','status','base_currency','timezone','display_date_format')}
                val['name']=safe_text(val['name'],'merchant name',150)
                if not val['name']:raise InputError('Merchant name is required')
                if val['country'] not in COUNTRY_ZONES:raise InputError('Unsupported country')
                if val['sector'] not in {p['sector'] for p in PERSONAS}:raise InputError('Select a supported business category')
                if val['status'] not in ('active','inactive'):raise InputError('Invalid merchant status')
                attempted=bool(old and val['base_currency']!=previous['base_currency'])
                if val['base_currency']!=CODE and not (old and val['base_currency']==previous['base_currency']):raise InputError('Currency is not enabled for import; no FX conversion is available')
                if not isinstance(val['timezone'],str) or val['timezone'] not in timezones():raise InputError('Select a supported IANA timezone')
                if val['display_date_format'] not in DISPLAY_FORMATS:raise InputError('Invalid date display format')
                if old and self.settings.currency_locked(db,mid) and (attempted or val['country']!=old['country']):raise InputError('Base currency and country are locked by existing financial records, balances or import runs. Historical migration is not supported.',409)
                new_id=mid or 'M'+secrets.token_hex(5).upper()
                while not mid and (new_id in self.auth.merchants or db.execute('SELECT 1 FROM merchant_profiles WHERE merchant_id=?',(new_id,)).fetchone() or db.execute('SELECT 1 FROM merchant_transaction_settings WHERE merchant_id=?',(new_id,)).fetchone()):new_id='M'+secrets.token_hex(5).upper()
                config={**previous,**{k:val[k] for k in ('base_currency','timezone','display_date_format')}}
                config={k:config.get(k,default) for k,default in {'base_currency':None,'timezone':None,'display_date_format':None,'default_status':'completed','payment_method_values':{}}.items()}
                cv=previous.get('version',0)+1
                db.execute('INSERT INTO merchant_transaction_settings VALUES(?,?,?,?,?) ON CONFLICT(merchant_id) DO UPDATE SET config_json=excluded.config_json,version=excluded.version,updated_by=excluded.updated_by,updated_at=excluded.updated_at',(new_id,encoded(config),cv,actor.user_id,self.auth.clock()))
                version=old['version']+1 if old else 1
                db.execute('INSERT INTO merchant_profiles VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(merchant_id) DO UPDATE SET name=excluded.name,country=excluded.country,sector=excluded.sector,status=excluded.status,version=excluded.version,updated_by=excluded.updated_by,updated_at=excluded.updated_at',(new_id,val['name'],val['country'],val['sector'],val['status'],version,actor.user_id,self.auth.clock()))
                self.auth.audit('merchant_profile_updated' if old else 'merchant_created',actor,new_id,new_id,db=db,metadata={'schema_version':1,'change_count':len(body),'configuration_digest':hashlib.sha256(encoded(val).encode()).hexdigest()})
                if old and val['status']!=old['status']:self.auth.audit('merchant_status_changed',actor,new_id,new_id,db=db,reason=val['status'])
                if attempted:self.auth.audit('merchant_currency_change_attempt',actor,new_id,new_id,db=db,reason='from_'+previous['base_currency']+'_to_'+val['base_currency'])
            if not old:
                self.c.merchants[new_id]=empty_merchant(new_id,val,val['base_currency']);self.c.financial_data.base[new_id]=copy.deepcopy(self.c.merchants[new_id]);self.auth.merchants.add(new_id)
            for m in (self.c.merchants[new_id],self.c.financial_data.base[new_id]):
                for key in ('name','country','sector'):setattr(m,key,val[key])
                m.currency=val['base_currency']
            return {'merchant_id':new_id,'version':version}
        except (InputError,ValueError):
            if attempted:self.auth.audit('merchant_currency_change_attempt',actor,mid,mid,result='denied',reason='financial_protection_or_validation')
            raise
