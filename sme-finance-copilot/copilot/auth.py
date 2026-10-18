"""SQLite identity, sessions and bounded security administration. No external services."""
import argparse
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from contextvars import ContextVar
REQUEST_ID = ContextVar("request_id", default=None)
from contextlib import contextmanager
from pathlib import Path
from copilot.security import AccessDenied, AuditLog, Principal, ROLE_MAX_TIER
from copilot.authorization import BOUNDARIES, DEFAULTS, ROLE_LABELS, CATEGORIES, resolve_role, AUTHORITATIVE_ROLES, STAFF_ACTIONS

class AuthError(AccessDenied):
    def __init__(self, message='Authentication required', status=401):
        super().__init__(message)
        self.status = status

class InputError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def demo_mode():
    # Client-selected identities are never an application authentication mechanism.
    return False

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password_hash(password):
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=128*1024*1024)
    return f'scrypt$32768$8$1${salt.hex()}${value.hex()}'

def verify_password(password, encoded):
    try:
        algorithm, n, r, p, salt, expected = encoded.split('$')
        if algorithm != 'scrypt' or (n,r,p) != ('32768','8','1'): return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), maxmem=128*1024*1024)
        return hmac.compare_digest(actual,bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False

POLICIES = {'idle_timeout':1800, 'max_session_lifetime':28800, 'failure_threshold':5,
            'lockout_duration':900, 'password_min_length':12, 'password_require_mixed':True,
            'reset_expiration':1800, 'admin_reauth_window':300}
RANGES = {'idle_timeout':(300,3600),'max_session_lifetime':(900,86400),
          'failure_threshold':(3,10),'lockout_duration':(60,3600),'password_min_length':(12,128),
          'reset_expiration':(300,3600),'admin_reauth_window':(60,600)}
ACCOUNT_EVENTS = {'account_created','account_updated','account_suspended','sessions_revoked',
                  'password_reset_issued','password_reset','password_changed','role_changed','staff_access_requested',
                  'merchant_assignment_changed','permission_changed'}

# Banks record reviews only; the app never simulates underwriting (no approval or rejection).
REVIEW_OUTCOMES = ('reviewed','more_information_needed','ready_for_further_assessment')
# Applications or reviews saved by an older version as approved or rejected are shown as a closed review.
LEGACY_DECISION_FIELDS = ('decision_at','decision_by','decision_note','simulated_decision')

def neutral_status(status):
    return 'REVIEW_CLOSED' if status in ('APPROVED','REJECTED') else status

def neutral_outcome(outcome):
    return 'review_closed' if outcome in ('approved','rejected') else outcome

class AuthStore:
    def __init__(self, path, merchants, clock=time.time):
        self.path, self.merchants, self.clock = str(path), set(merchants), clock
        self.lock = threading.RLock()
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        self.dummy_hash = password_hash(secrets.token_urlsafe(24))
        self.migrate()
        with self.db() as db:self.merchants.update(row[0] for row in db.execute("SELECT merchant_id FROM merchant_profiles"))
        from copilot.security_configuration import SecurityConfiguration
        self.security_config = SecurityConfiguration(self)

    @contextmanager
    def db(self):
        with self.lock:
            connection = sqlite3.connect(self.path,timeout=30)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA foreign_keys=ON')
            try:
                with connection:
                    yield connection
            finally:
                connection.close()

    def migrate(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at REAL)')
            for path in sorted((Path(__file__).parent/'migrations').glob('*.sql')):
                if db.execute('SELECT 1 FROM schema_migrations WHERE version=?',(path.name,)).fetchone(): continue
                # Scripts contain only trusted CREATE statements; execute in one transaction.
                for sql in path.read_text(encoding='utf-8').split(';'):
                    if sql.strip(): db.execute(sql)
                db.execute('INSERT INTO schema_migrations VALUES (?,?)',(path.name,self.clock()))
            empty_roles=not db.execute('SELECT 1 FROM role_permissions LIMIT 1').fetchone()
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version='four_role_permissions_v1'").fetchone():
                additions={'owner':{'manage_merchant_staff','view_merchant_audit','create_financing_draft','edit_financing_draft'},'staff':STAFF_ACTIONS-{'create_transactions','bulk_import','acknowledge_quality_alerts','resolve_quality_alerts'},'lender_analyst':{'view_bank_review','export_bank_review','view_bank_audit'}}
                for role,actions in additions.items():db.executemany('INSERT OR IGNORE INTO role_permissions VALUES (?,?)',[(role,a) for a in actions])
                db.execute("DELETE FROM role_permissions WHERE role='lender_analyst' AND permission='review_application'")
                db.execute('INSERT INTO schema_migrations VALUES (?,?)',('four_role_permissions_v1',self.clock()))
            for key,value in POLICIES.items():
                db.execute('INSERT OR IGNORE INTO security_policies VALUES (?,?)',(key,json.dumps(value)))
            if empty_roles or not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                db.execute('DELETE FROM role_permissions')
                for role,actions in DEFAULTS.items():
                    db.executemany('INSERT INTO role_permissions VALUES (?,?)',[(role,a) for a in actions])

    def policies(self, db):
        return {r['policy_key']:json.loads(r['value']) for r in db.execute('SELECT * FROM security_policies')}

    def audit(self, action, actor=None, merchant=None, target=None, result='success', reason=None, request_id=None, db=None, metadata=None):
        if db is None:
            with self.db() as connection:
                return self.audit(action,actor,merchant,target,result,reason,request_id,connection,metadata)
        last = db.execute('SELECT seq,hash FROM audit_events ORDER BY seq DESC LIMIT 1').fetchone()
        logger = AuditLog(clock=self.clock)
        logger.prev = last['hash'] if last else 'GENESIS'
        safe_metadata={k:v for k,v in (metadata or {}).items() if k in {'schema_version','configuration_digest','change_count','tool','policy_version','approval_reference','failure_stage','failure_category','provider_status','rejected_claim','required_qualification','retry_count','response_path','validation_code','provider_http_status'}}
        record = logger.write(**safe_metadata,seq=last['seq']+1 if last else 1, action=action,
            actor=actor.user_id if isinstance(actor,Principal) else actor,
            role=actor.role if isinstance(actor,Principal) else None, merchant_id=merchant,
            target=target, result=result, reason_code=reason, request_id=request_id or REQUEST_ID.get() or secrets.token_hex(8))
        # A generated SHA-256 digest is metadata, not a phone number. Keep it exact
        # while preserving the existing hash-chain serialization and PII masking.
        generated_digest=safe_metadata.get('configuration_digest')
        if isinstance(generated_digest,str) and re.fullmatch(r'[0-9a-f]{64}',generated_digest):
            record['configuration_digest']=generated_digest
            record['hash']=hashlib.sha256(json.dumps({k:v for k,v in record.items() if k!='hash'},sort_keys=True,default=str).encode()).hexdigest()
        db.execute('INSERT INTO audit_events VALUES (?,?,?)',(record['seq'],json.dumps(record),record['hash']))
        return record

    def financial_audit(self, event):
        self.audit('ai_tool_execution', actor=Principal(event.get('actor'),event.get('role')),
                   merchant=event.get('merchant_id'),target=event.get('tool'),
                   result='denied' if event.get('decision')=='denied' else 'failed' if event.get('outcome')=='error' else 'success',
                   reason=event.get('decision'))

    def check_password(self,password,policies):
        if not isinstance(password,str) or not policies['password_min_length'] <= len(password) <= 256:
            raise InputError(f"Password length must be {policies['password_min_length']}–256 characters")
        if policies['password_require_mixed'] and not (any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password)):
            raise InputError('Password must include lowercase, uppercase and a number')

    def _public_user(self,db,row):
        row=dict(row);row['role']=resolve_role(row['role'])
        keys = ['user_id','username','email','display_name','role','account_status','must_change_password',
                'created_at','updated_at','last_login_at','created_by','organization','locked_until']
        return {'effective_role':AUTHORITATIVE_ROLES.get(row['role'],'UNMAPPED'),**{k:row[k] for k in keys},
                'merchants':[r[0] for r in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(row['user_id'],))],
                'optional_permissions':[r[0] for r in db.execute('SELECT permission FROM optional_permissions WHERE user_id=?',(row['user_id'],))],
                'transaction_grants':{m:[r[0] for r in db.execute('SELECT permission FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=?',(row['user_id'],m))] for m in [r[0] for r in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(row['user_id'],))]} if row['role']=='staff' else {}}

    def _validate_user(self,body,actor=None):
        role=body.get('role')
        if role not in BOUNDARIES: raise InputError('Invalid role')
        if role=='coach' and os.environ.get('COPILOT_ALLOW_COACH_ASSIGNMENT')!='yes':
            raise InputError('New coach assignments are disabled')
        if actor and actor.role=='user_admin' and role not in ('owner','staff','lender_analyst'):
            raise AccessDenied('User Administrators can assign only business-facing roles')
        ids=body.get('merchants',[])
        if not isinstance(ids,list) or any(not isinstance(x,str) for x in ids) or not set(ids)<=self.merchants:
            raise InputError('Invalid merchant memberships')
        if role in ('user_admin','security_admin') and ids: raise InputError('Administrators cannot hold merchant memberships')
        if role not in ('user_admin','security_admin') and not ids: raise InputError('Business accounts require merchant memberships')
        if role=='lender_analyst' and not str(body.get('organization','')).strip(): raise InputError('Financing Agents require an organization or explicit demo scope name')
        optional=body.get('optional_permissions',[])
        if not isinstance(optional,list) or any(x!='bulk_import' for x in optional) or (optional and role!='staff'):
            raise InputError('Only the staff bulk_import optional permission is supported')
        grants=body.get('transaction_grants',{})
        if not isinstance(grants,dict) or (grants and role!='staff') or not set(grants)<=set(ids) or any(not isinstance(v,list) or any(a not in STAFF_ACTIONS for a in v) for v in grants.values()):raise InputError('Invalid merchant-level staff transaction grants')
        for key in ('username','email','display_name'):
            if not isinstance(body.get(key),str) or not 1<=len(body[key].strip())<=150:
                raise InputError(f'Invalid {key}')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',body['username'].strip()):raise InputError('Username must use letters, numbers, dots, underscores or hyphens (max 64)')
        if '@' not in body['email']: raise InputError('Valid email required')
        if body.get('account_status','active') not in ('active','inactive','suspended','locked'): raise InputError('Invalid account status')

    def bootstrap(self,username,email,password):
        with self.db() as db:
            if db.execute('SELECT 1 FROM users LIMIT 1').fetchone(): raise InputError('Bootstrap is available only before the first user exists',409)
            body=dict(username=username,email=email,display_name='Security Administrator',role='security_admin',merchants=[])
            return self._create(db,None,body,password,False)

    def _create(self,db,actor,body,password,must_change=True):
        body={**body,'role':resolve_role(body.get('role'))}
        self._validate_user(body,actor)
        self.check_password(password,self.policies(db))
        uid=secrets.token_hex(12); now=self.clock()
        try:
            db.execute('INSERT INTO users (user_id,username,email,display_name,role,account_status,password_hash,must_change_password,created_at,updated_at,created_by,organization) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (uid,body['username'].strip(),body['email'].strip(),body['display_name'].strip(),AUTHORITATIVE_ROLES[body['role']],body.get('account_status','active'),password_hash(password),int(must_change),now,now,actor.user_id if actor else 'bootstrap',str(body.get('organization','')).strip()[:150]))
        except sqlite3.IntegrityError: raise InputError('Username or email is already registered',409)
        db.executemany('INSERT INTO memberships VALUES (?,?)',[(uid,m) for m in set(body.get('merchants',[]))])
        db.executemany('INSERT INTO optional_permissions VALUES (?,?)',[(uid,a) for a in set(body.get('optional_permissions',[]))])
        self._save_transaction_grants(db,uid,body,actor.user_id if actor else 'bootstrap')
        self.audit('account_created',actor,target=uid,db=db)
        return self._public_user(db,db.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone())

    def _save_transaction_grants(self,db,uid,body,actor):
        db.execute('DELETE FROM merchant_transaction_grants WHERE user_id=?',(uid,))
        if body['role']!='staff':return
        grants={m:set(actions) for m,actions in body.get('transaction_grants',{}).items()}
        if 'transaction_grants' not in body and 'bulk_import' in body.get('optional_permissions',[]):
            for mid in body['merchants']:grants.setdefault(mid,set()).add('bulk_import')
        for mid,actions in grants.items():
            db.executemany('INSERT INTO merchant_transaction_grants VALUES (?,?,?,?,?)',[(uid,mid,a,actor,self.clock()) for a in actions])
        if any('bulk_import' in actions for actions in grants.values()):
            db.execute('INSERT OR IGNORE INTO optional_permissions VALUES (?,?)',(uid,'bulk_import'))
        else:db.execute('DELETE FROM optional_permissions WHERE user_id=? AND permission=?',(uid,'bulk_import'))

    def login(self,identity,password,address='local'):
        if not isinstance(identity,str) or not isinstance(password,str) or len(identity)>150 or len(password)>256:
            raise AuthError('Invalid credentials')
        now=self.clock(); identity=identity.strip().lower()
        key,ip=digest(identity),digest(address)
        with self.db() as db:
            policy=self.policies(db)
            db.execute('DELETE FROM login_attempts WHERE created_at<?',(now-3600,))
            failures=db.execute('SELECT COUNT(*) FROM login_attempts WHERE (identity_hash=? OR address_hash=?) AND created_at>?',(key,ip,now-policy['lockout_duration'])).fetchone()[0]
            if failures>=30 or db.execute('SELECT COUNT(*) FROM login_attempts WHERE identity_hash=? AND created_at>?',(key,now-policy['lockout_duration'])).fetchone()[0]>=policy['failure_threshold']:
                self.audit('login_failed',result='denied',reason='rate_limited',db=db)
                error=AuthError('Unable to sign in. Try again later.',429)
                result=None
            else:
                row=db.execute('SELECT * FROM users WHERE username=? OR email=?',(identity,identity)).fetchone()
                valid=verify_password(password,row['password_hash'] if row else self.dummy_hash)
                if not row or not valid or row['account_status']!='active' or row['locked_until']>now:
                    db.execute('INSERT INTO login_attempts VALUES (?,?,?)',(key,ip,now))
                    if row:
                        count=row['failed_attempts']+1
                        db.execute('UPDATE users SET failed_attempts=?, locked_until=? WHERE user_id=?',(count,now+policy['lockout_duration'] if count>=policy['failure_threshold'] else row['locked_until'],row['user_id']))
                    self.audit('login_failed',target=row['user_id'] if row else None,result='denied',reason='invalid_credentials',db=db)
                    error=AuthError('Invalid credentials');result=None
                else:
                    db.execute('UPDATE users SET failed_attempts=0,locked_until=0,last_login_at=? WHERE user_id=?',(now,row['user_id']))
                    db.execute('DELETE FROM login_attempts WHERE identity_hash=?',(key,))
                    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
                    db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,0)',(digest(token),row['user_id'],csrf,now,now,now))
                    self.audit('login_success',Principal(row['user_id'],row['role']),db=db)
                    result=(token,csrf,bool(row['must_change_password']));error=None
        # Raise after transaction commits so failed login counters/audit survive.
        if error: raise error
        return result

    def _session(self,db,token,touch=True):
        if not isinstance(token,str) or not token: raise AuthError()
        row=db.execute('SELECT u.*,s.token_hash,s.csrf_token,s.created_at AS session_created_at,s.last_seen,s.reauthenticated_at,s.revoked FROM sessions s JOIN users u ON u.user_id=s.user_id WHERE s.token_hash=?',(digest(token),)).fetchone()
        p=self.policies(db);now=self.clock()
        if not row or row['revoked'] or row['account_status']!='active' or row['locked_until']>now or now-row['last_seen']>p['idle_timeout'] or now-row['session_created_at']>p['max_session_lifetime']:
            raise AuthError('Session expired or unavailable')
        if touch: db.execute('UPDATE sessions SET last_seen=? WHERE token_hash=?',(now,digest(token)))
        row=dict(row);row['role']=resolve_role(row['role'])
        if row['role'] not in BOUNDARIES:raise AuthError('Legacy account needs an administrator role mapping',403)
        return row

    def principal(self,token):
        with self.db() as db:
            row=self._session(db,token)
            permissions={r[0] for r in db.execute('SELECT permission FROM role_permissions WHERE role=?',(row['role'],))}
            optional={r[0] for r in db.execute('SELECT permission FROM optional_permissions WHERE user_id=?',(row['user_id'],))}
            permissions=permissions&BOUNDARIES.get(row['role'],set())
            if row['role']=='staff' and 'bulk_import' not in optional: permissions.discard('bulk_import')
            policy=self.policies(db)
            ids={r[0] for r in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(row['user_id'],))}
            return Principal(row['user_id'],row['role'],ids,set(),True,permissions,
                             lambda action,mid:self.authorize(token,action,mid),
                             policy.get('ai_tiers',{}).get(row['role'],int(ROLE_MAX_TIER[row['role']])),
                             hashlib.sha256(token.encode()).hexdigest())

    def authorize(self,token,action,merchant=None,reauth=False):
        with self.db() as db:
            return self._authorize(db,token,action,merchant,reauth)

    def _authorize(self,db,token,action,merchant=None,reauth=False,touch=True):
        row=self._session(db,token,touch=touch)
        role=row['role']
        if row['must_change_password']: raise AccessDenied('Change your temporary password first')
        enabled={r[0] for r in db.execute('SELECT permission FROM role_permissions WHERE role=?',(role,))}
        if role=='staff' and action=='bulk_import' and not db.execute('SELECT 1 FROM optional_permissions WHERE user_id=? AND permission=?',(row['user_id'],'bulk_import')).fetchone(): raise AccessDenied('Staff upload permission has not been granted')
        if role=='staff' and merchant is not None and action in STAFF_ACTIONS and not db.execute('SELECT 1 FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=? AND permission=?',(row['user_id'],merchant,action)).fetchone():raise AccessDenied('An explicit merchant-level staff grant is required')
        if action not in enabled or action not in BOUNDARIES.get(role,set()): raise AccessDenied('Action is not permitted for this account')
        if merchant is not None and role=='lender_analyst' and 'view_financing_data' not in enabled:
            raise AccessDenied('Consent-authorized financing data permission is disabled')
        if reauth and self.clock()-row['reauthenticated_at']>self.policies(db)['admin_reauth_window']:
            raise AccessDenied('Administrator reauthentication required')
        if merchant is not None:
            inactive=db.execute("SELECT 1 FROM merchant_profiles WHERE merchant_id=? AND status='inactive'",(merchant,)).fetchone()
            if inactive:raise AccessDenied('Merchant is inactive')
            if merchant not in self.merchants or not db.execute('SELECT 1 FROM memberships WHERE user_id=? AND merchant_id=?',(row['user_id'],merchant)).fetchone():
                raise AccessDenied('Merchant access denied')
            if role in ('lender_analyst','coach'):
                category=CATEGORIES.get(action)
                consent=self._consent(db,merchant,row['user_id'],category,download=action=='export_bank_review')
                if not consent: raise AccessDenied('Active merchant consent for this data category is required')
            if action=='submit_application' and not self._owner_consent(db,merchant,row['user_id']):
                raise AccessDenied('Active financing consent including applications is required before submission')
        return self.policies(db).get('ai_tiers',{}).get(role,int(ROLE_MAX_TIER[role]))

    def _consent(self,db,mid,recipient,category=None,download=False):
        if not db.execute("SELECT 1 FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE u.user_id=? AND m.merchant_id=? AND u.role='BANK' AND u.account_status='active'",(recipient,mid)).fetchone():return None
        for row in db.execute('SELECT c.* FROM consents c JOIN users o ON o.user_id=c.owner_id WHERE c.merchant_id=? AND c.recipient_id=? AND c.revoked_at IS NULL AND c.expires_at>? AND o.account_status=\'active\' AND o.role=\'SME_OWNER\' AND EXISTS (SELECT 1 FROM memberships m WHERE m.user_id=o.user_id AND m.merchant_id=c.merchant_id)',(mid,recipient,self.clock())):
            if download and not db.execute('SELECT 1 FROM consent_downloads WHERE consent_id=? AND allow_csv=1',(row['consent_id'],)).fetchone():continue
            if category is None or category in json.loads(row['categories']): return row
        return None

    def _owner_consent(self,db,mid,owner):
        for row in db.execute('SELECT c.* FROM consents c JOIN users u ON u.user_id=c.recipient_id WHERE c.merchant_id=? AND c.owner_id=? AND c.revoked_at IS NULL AND c.expires_at>? AND u.account_status=\'active\' AND u.role=\'BANK\' AND EXISTS(SELECT 1 FROM memberships m WHERE m.user_id=u.user_id AND m.merchant_id=c.merchant_id)',(mid,owner,self.clock())):
            if 'applications' in json.loads(row['categories']): return row
        return None

    def me(self,token):
        principal=self.principal(token)
        with self.db() as db:
            row=self._session(db,token)
            return {'user':self._public_user(db,row),'permissions':sorted(principal.permissions),
                    'csrf_token':row['csrf_token'],'demo':False}

    def csrf(self,token,given):
        with self.db() as db:
            row=self._session(db,token)
            if not isinstance(given,str) or not hmac.compare_digest(row['csrf_token'],given): raise AccessDenied('Invalid CSRF token')

    def logout(self,token):
        with self.db() as db:
            row=self._session(db,token)
            db.execute('UPDATE sessions SET revoked=1 WHERE token_hash=?',(digest(token),))
            self.audit('logout',Principal(row['user_id'],row['role']),db=db)

    def reauthenticate(self,token,password):
        error=None
        with self.db() as db:
            row=self._session(db,token)
            actor=Principal(row['user_id'],row['role'])
            if not isinstance(password,str) or len(password)>256 or not verify_password(password,row['password_hash']):
                attempts=row['failed_attempts']+1
                until=self.clock()+self.policies(db)['lockout_duration'] if attempts>=self.policies(db)['failure_threshold'] else 0
                db.execute('UPDATE users SET failed_attempts=?,locked_until=? WHERE user_id=?',(attempts,until,row['user_id']))
                self.audit('reauthentication_failed',actor,result='denied',reason='invalid_credentials',db=db)
                error=AuthError('Invalid credentials')
            else:
                db.execute('UPDATE sessions SET reauthenticated_at=? WHERE token_hash=?',(self.clock(),digest(token)))
                db.execute('UPDATE users SET failed_attempts=0 WHERE user_id=?',(row['user_id'],))
                self.audit('reauthenticated',actor,db=db)
        if error:raise error

    def change_password(self,token,current,new):
        with self.db() as db:
            row=self._session(db,token)
            if not isinstance(current,str) or len(current)>256 or not verify_password(current,row['password_hash']): raise AuthError('Invalid credentials')
            self.check_password(new,self.policies(db))
            if verify_password(new,row['password_hash']): raise InputError('Choose a different password')
            db.execute('UPDATE users SET password_hash=?,must_change_password=0,updated_at=? WHERE user_id=?',(password_hash(new),self.clock(),row['user_id']))
            db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(row['user_id'],))
            db.execute('UPDATE reset_tokens SET used=1 WHERE user_id=?',(row['user_id'],))
            self.audit('password_changed',Principal(row['user_id'],row['role']),db=db)

    def reset_password(self,token,new):
        with self.db() as db:
            row=db.execute('SELECT * FROM reset_tokens WHERE token_hash=?',(digest(str(token)),)).fetchone()
            if not row or row['used'] or row['expires_at']<=self.clock(): raise InputError('Reset token is invalid or expired')
            self.check_password(new,self.policies(db))
            db.execute('UPDATE users SET password_hash=?,must_change_password=0,updated_at=? WHERE user_id=?',(password_hash(new),self.clock(),row['user_id']))
            db.execute('UPDATE reset_tokens SET used=1 WHERE user_id=?',(row['user_id'],))
            db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(row['user_id'],))
            self.audit('password_reset',target=row['user_id'],db=db)

    def users(self,token,query='',status='',role=''):
        self.authorize(token,'manage_users')
        with self.db() as db:
            return [self._public_user(db,r) for r in db.execute('SELECT * FROM users ORDER BY username')
                    if query.casefold() in (r['username']+' '+r['email']+' '+r['display_name']).casefold()
                    and (not status or r['account_status']==status) and (not role or resolve_role(r['role'])==resolve_role(role))]

    def create_user(self,token,body):
        self.authorize(token,'manage_users',reauth=True)
        if body.get('role')=='staff':self.authorize(token,'manage_staff_accounts',reauth=True)
        actor=self.principal(token)
        with self.db() as db:return self._create(db,actor,body,body.get('password'))

    def update_user(self,token,uid,body):
        self.authorize(token,'manage_users',reauth=True)
        actor=self.principal(token)
        allowed={'username','email','display_name','role','account_status','merchants','optional_permissions','organization','transaction_grants'}
        if not isinstance(body,dict) or set(body)-allowed: raise InputError('Unsupported account fields')
        with self.db() as db:
            row=db.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone()
            if not row: raise InputError('User not found',404)
            row=dict(row);row['role']=resolve_role(row['role'])
            body={**body,**({'role':resolve_role(body['role'])} if 'role' in body else {})}
            if row['role']=='staff' or body.get('role')=='staff':self.authorize(token,'manage_staff_accounts',reauth=True)
            if actor.role=='user_admin' and row['role'] in ('user_admin','security_admin'): raise AccessDenied('User Administrators cannot modify administrator accounts')
            merged={**self._public_user(db,row),**body}
            if merged['role']!='staff' and 'transaction_grants' not in body:merged['transaction_grants']={}
            if 'transaction_grants' not in body:merged['transaction_grants']={m:a for m,a in merged['transaction_grants'].items() if m in merged['merchants']}
            if merged['role']=='staff' and 'optional_permissions' in body and 'transaction_grants' not in body:
                for mid in merged['merchants']:
                    actions=set(merged['transaction_grants'].get(mid,[]))
                    if 'bulk_import' in body['optional_permissions']:actions.add('bulk_import')
                    else:actions.discard('bulk_import')
                    merged['transaction_grants'][mid]=sorted(actions)
            # Existing coaches can be maintained without enabling new assignments.
            if row['role']=='coach' and 'role' not in body:
                validation={**merged,'role':'owner'}
            else:validation=merged
            self._validate_user(validation,actor)
            if uid==actor.user_id and any(k in body for k in ('role','merchants','optional_permissions','account_status')):
                raise AccessDenied('Administrators cannot change their own authority or status')
            if row['role']=='security_admin' and row['account_status']=='active' and (merged['role']!='security_admin' or merged['account_status']!='active'):
                count=db.execute("SELECT COUNT(*) FROM users WHERE role='SYSTEM_ADMIN' AND account_status='active'").fetchone()[0]
                if count<=1: raise InputError('Cannot remove the last active Security Administrator',409)
            try:
                db.execute('UPDATE users SET username=?,email=?,display_name=?,role=?,account_status=?,organization=?,updated_at=?,locked_until=0,failed_attempts=0 WHERE user_id=?',
                    (merged['username'].strip(),merged['email'].strip(),merged['display_name'].strip(),AUTHORITATIVE_ROLES[merged['role']],merged['account_status'],str(merged.get('organization',''))[:150],self.clock(),uid))
            except sqlite3.IntegrityError: raise InputError('Username or email is already registered',409)
            db.execute('DELETE FROM memberships WHERE user_id=?',(uid,));db.execute('DELETE FROM optional_permissions WHERE user_id=?',(uid,))
            db.executemany('INSERT INTO memberships VALUES (?,?)',[(uid,m) for m in set(merged['merchants'])])
            db.executemany('INSERT INTO optional_permissions VALUES (?,?)',[(uid,a) for a in set(merged['optional_permissions'])])
            self._save_transaction_grants(db,uid,merged,actor.user_id)
            db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(uid,))
            if 'transaction_grants' in body:self.audit('permission_changed',actor,target=uid,db=db)
            if body.get('account_status')=='active':
                identities={digest(row['username'].lower()),digest(row['email'].lower()),digest(merged['username'].lower()),digest(merged['email'].lower())}
                for key in identities:db.execute('DELETE FROM login_attempts WHERE identity_hash=?',(key,))
            if merged['role']!=row['role']: self.audit('role_changed',actor,target=uid,db=db)
            if 'merchants' in body:self.audit('merchant_assignment_changed',actor,target=uid,db=db)
            if 'optional_permissions' in body:self.audit('permission_changed',actor,target=uid,db=db)
            if merged['account_status']=='suspended':self.audit('account_suspended',actor,target=uid,db=db)
            self.audit('account_updated',actor,target=uid,db=db)
            return self._public_user(db,db.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone())

    def account_action(self,token,uid,action):
        self.authorize(token,'manage_users',reauth=True);actor=self.principal(token)
        with self.db() as db:
            row=db.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone()
            if not row:raise InputError('User not found',404)
            if row['role']=='staff':self.authorize(token,'manage_staff_accounts',reauth=True)
            if actor.role=='user_admin' and row['role'] in ('user_admin','security_admin'):raise AccessDenied('Administrator target is not permitted')
            if action=='revoke-sessions':
                db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(uid,))
                self.audit('sessions_revoked',actor,target=uid,db=db);return {'ok':True}
            if action=='reset-password':
                reset=secrets.token_urlsafe(32)
                db.execute('UPDATE reset_tokens SET used=1 WHERE user_id=?',(uid,))
                db.execute('INSERT INTO reset_tokens VALUES (?,?,?,0)',(digest(reset),uid,self.clock()+self.policies(db)['reset_expiration']))
                db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(uid,))
                self.audit('password_reset_issued',actor,target=uid,db=db)
                return {'reset_token':reset,'expires_in':self.policies(db)['reset_expiration']}
            raise InputError('Unsupported account action')

    def security_policies(self,token):
        self.authorize(token,'manage_security')
        with self.db() as db:
            return {'settings':self.policies(db),'roles':ROLE_LABELS,
                    'permissions':{role:[r[0] for r in db.execute('SELECT permission FROM role_permissions WHERE role=?',(role,))] for role in BOUNDARIES},
                    'boundaries':{role:sorted(actions) for role,actions in BOUNDARIES.items()},
                    'tiers':{role:int(ROLE_MAX_TIER[role]) for role in BOUNDARIES},'t4':'Permanently prohibited'}

    def _write_policy_changes(self,db,settings,permissions,tiers):
        current=self.security_config.current(db)
        desired={'schema_version':current['schema_version'],'application':current['application'],
                 'authentication':{**current['authentication'],**settings},
                 'permissions':{**current['permissions'],**{role:sorted(actions) for role,actions in permissions.items()}},
                 'ai_tiers':{**current['ai_tiers'],**tiers}}
        if desired==current:return False
        for key,value in settings.items():
            db.execute('UPDATE security_policies SET value=? WHERE policy_key=?',(json.dumps(value),key))
        if tiers:
            db.execute('INSERT OR REPLACE INTO security_policies VALUES (?,?)',('ai_tiers',json.dumps(desired['ai_tiers'])))
        for role,actions in permissions.items():
            db.execute('DELETE FROM role_permissions WHERE role=?',(role,))
            db.executemany('INSERT INTO role_permissions VALUES (?,?)',[(role,a) for a in sorted(set(actions))])
        db.execute('UPDATE security_config_state SET revision=revision+1 WHERE singleton=1')
        return True

    def update_policies(self,token,body):
        from copilot.security_configuration import validate_update
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self._authorize(db,token,'manage_security',reauth=True)
            row=self._session(db,token,touch=False);actor=Principal(row['user_id'],row['role'])
            settings,permissions,tiers=validate_update(body,self.policies(db))
            changed=self._write_policy_changes(db,settings,permissions,tiers)
            self.audit('security_policy_changed',actor,db=db)
        return {'ok':True,'changed':changed}

    def audit_records(self,token,filters=None):
        actor=self.principal(token)
        self.authorize(token,'view_security_audit' if actor.role=='security_admin' else 'view_account_audit')
        filters=filters or {}
        with self.db() as db:
            records=[json.loads(r[0]) for r in db.execute('SELECT record FROM audit_events ORDER BY seq DESC')]
        if actor.role=='user_admin':records=[r for r in records if r['action'] in ACCOUNT_EVENTS]
        for key in ('actor','action','result','target'):
            if filters.get(key):records=[r for r in records if r.get(key)==filters[key]]
        if filters.get('start'):records=[r for r in records if r['ts']>=float(filters['start'])]
        if filters.get('end'):records=[r for r in records if r['ts']<=float(filters['end'])]
        return records[:500]

    def monitoring(self,token):
        self.authorize(token,'view_security_audit')
        records=self.audit_records(token,{'start':self.clock()-86400})
        with self.db() as db: locked=db.execute("SELECT COUNT(*) FROM users WHERE account_status='locked' OR locked_until>?",(self.clock(),)).fetchone()[0]
        return {'failed_logins':sum(r['action']=='login_failed' for r in records),'locked_accounts':locked,
                'access_denials':sum(r['result']=='denied' for r in records),
                'role_changes':sum(r['action']=='role_changed' for r in records),
                'ai_denials':sum(r['action']=='ai_tool_execution' and r['result']=='denied' for r in records),
                'policy_changes':sum(r['action']=='security_policy_changed' for r in records),'window':'last 24 hours (latest 500 matching events)'}

    def grant_consent(self,token,body):
        mid=body.get('merchant');self.authorize(token,'manage_consents',mid);actor=self.principal(token)
        with self.db() as db:return self._grant_consent(db,actor,body)

    def _grant_consent(self,db,actor,body):
        # Shared validation for single and atomic multi-merchant Owner grants.
        mid=body.get('merchant')
        if actor.role!='owner' or not db.execute('SELECT 1 FROM memberships WHERE user_id=? AND merchant_id=?',(actor.user_id,mid)).fetchone():raise AccessDenied('Assigned SME Owner required')
        categories=body.get('categories',[])
        if not isinstance(categories,list) or not categories or any(c not in {'reports','assessment','forecasts','financing','applications'} for c in categories):raise InputError('Invalid permitted data categories')
        download=body.get('allow_download',False)
        if type(download) is not bool:raise InputError('Download permission must be explicit true or false')
        expires=body.get('expires_at')
        if type(expires) not in (int,float) or not self.clock()<expires<=self.clock()+366*86400:raise InputError('Consent expiration must be within one year')
        purpose=body.get('purpose','')
        if not isinstance(purpose,str) or not 1<=len(purpose.strip())<=250:raise InputError('Consent purpose required (max 250 characters)')
        recipient=db.execute('SELECT * FROM users WHERE user_id=?',(body.get('recipient_id'),)).fetchone()
        if not recipient or resolve_role(recipient['role'])!='lender_analyst' or recipient['account_status']!='active' or not db.execute('SELECT 1 FROM memberships WHERE user_id=? AND merchant_id=?',(recipient['user_id'],mid)).fetchone():raise InputError('Recipient must be an active Bank scoped to this merchant')
        cid=secrets.token_hex(12)
        db.execute('INSERT INTO consents VALUES (?,?,?,?,?,?,?,?,NULL)',(cid,mid,actor.user_id,recipient['user_id'],purpose.strip(),json.dumps(sorted(set(categories))),self.clock(),expires))
        db.execute('INSERT INTO consent_downloads VALUES (?,?)',(cid,int(download)))
        self.audit('consent_granted',actor,mid,cid,db=db)
        return {'consent_id':cid}

    def consents(self,token,mid):
        self.authorize(token,'manage_consents',mid)
        with self.db() as db:
            rows=[dict(r) for r in db.execute('SELECT c.*,u.display_name AS recipient_name,u.organization FROM consents c JOIN users u ON u.user_id=c.recipient_id WHERE merchant_id=?',(mid,))]
            recipients=[dict(r) for r in db.execute("SELECT u.user_id,u.display_name,u.organization FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE m.merchant_id=? AND u.role='BANK' AND u.account_status='active'",(mid,))]
            for r in rows:r['categories']=json.loads(r['categories'])
            return {'consents':rows,'recipients':recipients}

    def revoke_consent(self,token,cid):
        with self.db() as db:
            row=db.execute('SELECT * FROM consents WHERE consent_id=?',(cid,)).fetchone()
            if not row:raise InputError('Consent not found',404)
            self.authorize(token,'manage_consents',row['merchant_id']);actor=self.principal(token)
            db.execute('UPDATE consents SET revoked_at=? WHERE consent_id=?',(self.clock(),cid))
            self.audit('consent_revoked',actor,row['merchant_id'],cid,db=db)
        return {'ok':True}

    def submit_packet(self,principal,mid,packet):
        with self.db() as db:
            # The call has already passed PolicyGuard and the owner approval token.
            principal.authorizer('submit_application',mid)
            if not isinstance(packet.get('recipient_id'),str):raise AccessDenied('Explicit Bank recipient required')
            consent=self._consent(db,mid,packet.get('recipient_id'),'applications')
            if not consent or consent['owner_id']!=principal.user_id:raise AccessDenied('Explicit Owner-authorized Bank recipient required')
            if packet.get('draft_id'):
                draft=db.execute("SELECT * FROM financing_drafts WHERE draft_id=? AND merchant_id=? AND state='DRAFT'",(packet['draft_id'],mid)).fetchone()
                if not draft:raise InputError('Draft no longer editable',409)
                saved=json.loads(draft['body'])
                if saved['recipient_id']!=packet['recipient_id'] or float(saved['amount'])!=packet['requested_amount']:raise InputError('Draft changed; propose again',409)
            aid='APP-'+secrets.token_hex(10)
            packet={**packet,'application_id':aid,'recipient_id':consent['recipient_id'],'sandbox':True}
            db.execute('INSERT INTO applications VALUES (?,?,?,?,?,?)',(aid,mid,principal.user_id,consent['recipient_id'],self.clock(),json.dumps(packet)))
            if packet.get('draft_id'):db.execute("UPDATE financing_drafts SET state='SUBMITTED',application_id=? WHERE draft_id=?",(aid,packet['draft_id']))
            self.audit('financing_application_submitted',principal,mid,aid,db=db)
            return packet

    def application_list(self,token,mid):
        self.authorize(token,'view_applications',mid);p=self.principal(token)
        with self.db() as db:
            rows=db.execute('SELECT * FROM applications WHERE merchant_id=?',(mid,)).fetchall()
            result=[]
            for row in rows:
                if p.role!='owner' and not (p.role=='lender_analyst' and row['recipient_id']==p.user_id):continue
                packet=json.loads(row['packet'])
                if p.role=='lender_analyst':
                    try:self._authorize(db,token,'view_assessment',mid)
                    except AccessDenied:packet={k:v for k,v in packet.items() if k not in ('scores','stage')}
                packet['status']=neutral_status(packet.get('status'))
                for key in LEGACY_DECISION_FIELDS:packet.pop(key,None)
                packet['submitted_at']=row['created_at']
                packet['reviews']=self.application_reviews(db,row['application_id'])
                result.append(packet)
            return result

    def review_application(self,token,aid,body):
        from copilot.bank_workflow import BankWorkflow
        return BankWorkflow(self,None).record_review(token,aid,body)

    def application_reviews(self,db,aid):
        return [{**dict(row),'outcome':neutral_outcome(row['outcome'])} for row in db.execute("SELECT r.outcome,r.note,r.created_at,u.display_name AS reviewer,u.organization AS bank_name FROM application_reviews r LEFT JOIN users u ON u.user_id=r.actor_id WHERE r.application_id=? ORDER BY r.created_at,r.review_id",(aid,))]


def main():
    from copilot.demo_environment import configure_storage
    configure_storage()
    parser=argparse.ArgumentParser(description='Migrate identity database or bootstrap the first Security Administrator')
    parser.add_argument('command',choices=['migrate','bootstrap'])
    parser.add_argument('--database',default=os.environ.get('COPILOT_IDENTITY_DB','logs/identity.sqlite3'))
    parser.add_argument('--username');parser.add_argument('--email')
    parser.add_argument('--password-env',help='Bootstrap only: name of an environment variable containing the password')
    args=parser.parse_args()
    from copilot.data.synthetic import load_all
    store=AuthStore(args.database,load_all())
    if args.command=='bootstrap':
        if not args.username or not args.email:parser.error('--username and --email are required')
        if args.password_env:
            password=os.environ.pop(args.password_env,None)
            if not password:parser.error('The bootstrap password environment variable is missing or empty')
        else:
            password=getpass.getpass('New administrator password: ')
            if password!=getpass.getpass('Confirm password: '):parser.error('Passwords do not match')
        try:store.bootstrap(args.username,args.email,password)
        except InputError as error:parser.error(str(error))
        print('Security Administrator created; no merchant financial access granted.')
    else:print('Identity/security migrations applied. Existing transaction ledger unchanged.')

if __name__=='__main__':main()
