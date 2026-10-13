"""Portable, bounded security policy snapshots and confirmation-bound imports."""
import copy
import hashlib
import json
import secrets
from copilot.auth import POLICIES, RANGES, InputError, AuthError, digest
from copilot.authorization import BOUNDARIES
from copilot.security import AccessDenied, ROLE_MAX_TIER, Principal

APPLICATION = 'sme-finance-copilot'
SCHEMA_VERSION = 1
MAX_CONFIG_BYTES = 65536
PREVIEW_LIFETIME = 600

def validate_update(body, current):
    """One validator for both existing partial edits and complete portable imports."""
    if not isinstance(body, dict) or set(body) - {'settings','permissions','ai_tiers'}:
        raise InputError('Unsupported security configuration')
    settings = body.get('settings', {})
    if not isinstance(settings, dict) or set(settings) - set(POLICIES):
        raise InputError('Unknown authentication setting')
    for key, value in settings.items():
        if key == 'password_require_mixed':
            if value is not True: raise InputError('Mixed password policy cannot be disabled')
        elif type(value) is not int or not RANGES[key][0] <= value <= RANGES[key][1]:
            raise InputError(f'Unsafe value for {key}')
    combined = {**current, **settings}
    if combined['max_session_lifetime'] < combined['idle_timeout']:
        raise InputError('Maximum session lifetime must be at least the idle timeout')
    permissions = body.get('permissions', {})
    if not isinstance(permissions, dict): raise InputError('Permission matrix must be an object')
    for role, actions in permissions.items():
        if role not in BOUNDARIES or not isinstance(actions, list) or any(not isinstance(a,str) for a in actions) or not set(actions) <= BOUNDARIES[role] or len(set(actions)) != len(actions):
            raise InputError('Permissions exceed fixed role boundaries or contain duplicates')
        if role == 'security_admin' and not {'manage_users','manage_security','view_security_audit'} <= set(actions):
            raise InputError('Essential Security Administrator controls cannot be disabled')
    tiers = body.get('ai_tiers', {})
    if not isinstance(tiers, dict) or any(role not in BOUNDARIES or type(tier) is not int or not 0 <= tier <= int(ROLE_MAX_TIER[role]) for role,tier in tiers.items()):
        raise InputError('AI tiers exceed fixed limits; T4 is permanently prohibited')
    return settings, permissions, tiers

def normalize(configuration):
    if not isinstance(configuration,dict) or set(configuration) != {'schema_version','application','authentication','permissions','ai_tiers'}:
        raise InputError('Configuration must contain exactly the documented top-level fields')
    if type(configuration['schema_version']) is not int or configuration['schema_version'] != SCHEMA_VERSION:
        raise InputError('Unsupported configuration schema version')
    if configuration['application'] != APPLICATION:
        raise InputError('Configuration is for a different application')
    settings, permissions, tiers = configuration['authentication'], configuration['permissions'], configuration['ai_tiers']
    if not isinstance(settings,dict) or set(settings) != set(POLICIES):
        raise InputError('Authentication configuration must contain all supported settings and no other fields')
    if not isinstance(permissions,dict) or set(permissions) != set(BOUNDARIES):
        raise InputError('Permission configuration must include every supported role and no other roles')
    if not isinstance(tiers,dict) or set(tiers) != set(BOUNDARIES):
        raise InputError('AI tier configuration must include every supported role and no other roles')
    validate_update({'settings':settings,'permissions':permissions,'ai_tiers':tiers},POLICIES)
    return {'schema_version':SCHEMA_VERSION,'application':APPLICATION,
            'authentication':{k:settings[k] for k in sorted(POLICIES)},
            'permissions':{role:sorted(permissions[role]) for role in sorted(BOUNDARIES)},
            'ai_tiers':{role:tiers[role] for role in sorted(BOUNDARIES)}}

def parse_file(filename, content):
    if not isinstance(filename,str) or not filename.lower().endswith('.json'):
        raise InputError('Choose a JSON configuration file')
    if not isinstance(content,str) or not content:
        raise InputError('Configuration file must be nonempty and no larger than 64 KiB')
    try: size=len(content.encode('utf-8'))
    except UnicodeError:raise InputError('Configuration must use valid UTF-8 text') from None
    if size>MAX_CONFIG_BYTES:raise InputError('Configuration file must be no larger than 64 KiB')
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result: raise InputError('Duplicate JSON properties are not allowed')
            result[key] = value
        return result
    def invalid_constant(_): raise InputError('JSON values must be finite')
    try:
        data=json.loads(content.lstrip('\ufeff'),object_pairs_hook=unique,parse_constant=invalid_constant)
        return normalize(data)
    except InputError:raise
    except (ValueError,RecursionError,UnicodeError):
        raise InputError('Malformed JSON configuration') from None

def configuration_digest(configuration):
    return hashlib.sha256(json.dumps(configuration,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def difference(current, imported):
    rows=[]
    for group in ('authentication','permissions','ai_tiers'):
        for key in sorted(imported[group]):
            old,new=current[group][key],imported[group][key]
            rows.append({'setting':f'{group}.{key}','current':old,'imported':new,'changed':old != new})
    return rows

class SecurityConfiguration:
    def __init__(self, store):
        self.store=store
        self.previews={}

    def current(self,db):
        settings=self.store.policies(db)
        return normalize({'schema_version':SCHEMA_VERSION,'application':APPLICATION,
            'authentication':{k:settings[k] for k in POLICIES},
            'permissions':{role:[r[0] for r in db.execute('SELECT permission FROM role_permissions WHERE role=?',(role,))] for role in BOUNDARIES},
            'ai_tiers':{role:settings.get('ai_tiers',{}).get(role,int(ROLE_MAX_TIER[role])) for role in BOUNDARIES}})

    def revision(self,db):
        return db.execute('SELECT revision FROM security_config_state WHERE singleton=1').fetchone()[0]

    def authorize(self,db,token,reauth=False):
        self.store._authorize(db,token,'manage_security',reauth=reauth,touch=False)
        row=self.store._session(db,token,touch=False)
        if row['role'] != 'security_admin':raise AccessDenied('Security Administrator required')
        return Principal(row['user_id'],row['role'])

    def rejected(self,token,action,error,reason):
        # Resolve metadata directly, without trusting payloads or logging credentials.
        with self.store.db() as db:
            row=db.execute('SELECT u.user_id,u.role FROM sessions s JOIN users u ON u.user_id=s.user_id WHERE s.token_hash=?',(digest(token or ''),)).fetchone()
            actor=Principal(row['user_id'],row['role']) if row else None
            self.store.audit(action,actor,result='denied' if isinstance(error,AccessDenied) else 'failed',reason=reason,db=db,
                             metadata={'schema_version':SCHEMA_VERSION})

    def export(self,token):
        try:
            with self.store.db() as db:
                db.execute('BEGIN IMMEDIATE')
                actor=self.authorize(db,token)
                configuration=self.current(db)
                self.store.audit('security_config_export',actor,db=db,metadata={'schema_version':SCHEMA_VERSION,'configuration_digest':configuration_digest(configuration)})
                return configuration
        except (AccessDenied,InputError) as error:
            self.rejected(token,'security_config_export',error,'authorization' if isinstance(error,AccessDenied) else 'invalid_configuration')
            raise

    def preview(self,token,body):
        with self.store.lock:
            return self._preview(token,body)

    def _preview(self,token,body):
        try:
            with self.store.db() as db:
                db.execute('BEGIN IMMEDIATE')
                actor=self.authorize(db,token)
                now=self.store.clock()
                self.previews={k:v for k,v in self.previews.items() if v['expires_at']>now}
                if len(self.previews)>=256:raise InputError('Too many pending previews; retry later',429)
                if not isinstance(body,dict) or set(body) != {'filename','content'}:raise InputError('Provide only filename and JSON file content')
                imported=parse_file(body['filename'],body['content'])
                current=self.current(db);revision=self.revision(db)
                rows=difference(current,imported)
                change_count=sum(row['changed'] for row in rows)
                self.store.audit('security_config_validate',actor,db=db,metadata={'schema_version':SCHEMA_VERSION,'configuration_digest':configuration_digest(imported),'change_count':change_count})
            with self.store.lock:
                now=self.store.clock()
                preview_token=secrets.token_urlsafe(32)
                self.previews[preview_token]={'actor':actor.user_id,'session':digest(token),'configuration':copy.deepcopy(imported),
                    'revision':revision,'base_digest':configuration_digest(current),'expires_at':now+PREVIEW_LIFETIME}
            return {'valid':True,'schema_version':SCHEMA_VERSION,'preview_token':preview_token,
                    'expires_in':PREVIEW_LIFETIME,'base_revision':revision,'differences':rows,'change_count':change_count}
        except (AccessDenied,InputError) as error:
            self.rejected(token,'security_config_validate',error,'authorization' if isinstance(error,AccessDenied) else 'validation_rejected')
            raise

    def apply(self,token,body):
        with self.store.lock:
            return self._apply(token,body)

    def _apply(self,token,body):
        try:
            with self.store.db() as db:
                db.execute('BEGIN IMMEDIATE')
                actor=self.authorize(db,token,reauth=True)
                if not isinstance(body,dict) or set(body) != {'preview_token','confirmed'} or body['confirmed'] is not True:
                    raise InputError('Explicit confirmation of a validated preview is required')
                supplied=body['preview_token']
                preview=self.previews.get(supplied) if isinstance(supplied,str) else None
                if not preview or preview['actor'] != actor.user_id or preview['session'] != digest(token) or preview['expires_at']<=self.store.clock():
                    raise InputError('Preview is expired, unavailable or belongs to a different session',409)
                configuration=normalize(copy.deepcopy(preview['configuration']))
                current=self.current(db)
                if self.revision(db) != preview['revision'] or configuration_digest(current) != preview['base_digest']:
                    raise InputError('Policies changed since preview. Validate the file again.',409)
                rows=difference(current,configuration);count=sum(row['changed'] for row in rows)
                self.store._write_policy_changes(db,configuration['authentication'],configuration['permissions'],configuration['ai_tiers'])
                metadata={'schema_version':SCHEMA_VERSION,'configuration_digest':configuration_digest(configuration),'change_count':count}
                self.store.audit('security_config_import',actor,db=db,metadata=metadata)
                if count:self.store.audit('security_policy_changed',actor,db=db,metadata=metadata)
                revision=self.revision(db)
            with self.store.lock:self.previews.pop(supplied,None)
            return {'ok':True,'changed':bool(count),'change_count':count,'revision':revision}
        except (AccessDenied,InputError) as error:
            self.rejected(token,'security_config_import',error,'authorization_or_reauthentication' if isinstance(error,AccessDenied) else 'import_rejected')
            raise
        except Exception:
            # A failed write rolls back before recording its failure. No internal payload/exception leaks.
            error=InputError('Configuration could not be applied; no policy changes were saved',500)
            self.rejected(token,'security_config_import',error,'transaction_failed')
            raise error from None
