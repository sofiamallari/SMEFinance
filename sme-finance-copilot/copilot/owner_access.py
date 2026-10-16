"""Owner-scoped account associations. Identity, grants and financial consent stay separate."""
import json,re,secrets,sqlite3
from copilot.auth import InputError
from copilot.security import AccessDenied,Principal
from copilot.authorization import STAFF_ACTIONS

ROLES={'SME_STAFF':'staff','BANK':'bank'}
class OwnerAccess:
 def __init__(self,auth):self.a=auth
 def scope(self,db,token,ids=None,role=None):
  row=self.a._session(db,token,touch=False)
  if row['role']!='owner':raise AccessDenied('SME Owner required')
  actor=Principal(row['user_id'],'owner');managed=[]
  for item in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(actor.user_id,)):
   mid=item[0]
   actions=['manage_consents'] if role=='BANK' else ['manage_merchant_staff'] if role=='SME_STAFF' else ['manage_merchant_staff','manage_consents']
   for action in actions:
    try:self.a._authorize(db,token,action,mid)
    except AccessDenied:continue
    managed.append(mid);break
  if ids is not None:
   if not isinstance(ids,list) or not ids or any(not isinstance(m,str) for m in ids) or len(ids)!=len(set(ids)) or not set(ids)<=set(managed):raise AccessDenied('Select only businesses you are authorized to manage')
  return actor,managed
 def target(self,db,uid,role=None):
  user=db.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone()
  if not user or user['role'] not in ROLES or (role and user['role']!=role):raise InputError('Eligible account unavailable',404)
  return user
 def visible(self,db,user,managed):
  mids=[r[0] for r in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(user['user_id'],))]
  permitted=[m for m in mids if m in managed]
  if not permitted:raise AccessDenied('Account is not associated with a business you manage')
  return permitted,mids
 def public(self,db,user,actor,managed):
  mids,allids=self.visible(db,user,managed)
  return {k:user[k] for k in ('user_id','username','email','display_name','role','account_status','organization')}|{
   'merchants':mids,'editable_identity':user['created_by']==actor.user_id and set(allids)<=set(managed),
   'permissions':{m:[r[0] for r in db.execute('SELECT permission FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=?',(user['user_id'],m))] for m in mids} if user['role']=='SME_STAFF' else {},
   'origins':{m:(db.execute('SELECT origin FROM owner_user_links WHERE user_id=? AND merchant_id=?',(user['user_id'],m)).fetchone() or ['existing; origin not recorded'])[0] for m in mids},
   'affiliation_verified':False}
 def listing(self,token):
  with self.a.db() as db:
   actor,managed=self.scope(db,token)
   scopes={role:self.scope(db,token,role=role)[1] for role in ROLES}
   users=db.execute("SELECT DISTINCT u.* FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE u.role IN ('SME_STAFF','BANK')").fetchall()
   result=[]
   for user in users:
    try:result.append(self.public(db,user,actor,scopes[user['role']]))
    except AccessDenied:pass
   consents=[]
   for mid in scopes['BANK']:
    for row in db.execute('SELECT c.*,COALESCE(d.allow_csv,0) AS allow_download FROM consents c LEFT JOIN consent_downloads d ON d.consent_id=c.consent_id WHERE c.merchant_id=? ORDER BY c.granted_at DESC',(mid,)):
     consents.append({**dict(row),'categories':json.loads(row['categories']),'editable':row['owner_id']==actor.user_id})
   return {'users':result,'merchants':managed,'merchant_scopes':scopes,'permissions':sorted(STAFF_ACTIONS),'consents':consents,'affiliation_notice':'Organization is self-reported/demo affiliation, not a verified institution registry.'}
 def candidates(self,token,body):
  role=body.get('role');mids=body.get('merchants')
  if role not in ROLES:raise InputError('Supported account role required')
  if not isinstance(mids,list) or not mids:raise InputError('Select at least one business')
  with self.a.db() as db:
   actor,managed=self.scope(db,token,mids,role=role);result=[]
   for user in db.execute("SELECT * FROM users WHERE role=? AND account_status='active' ORDER BY display_name,username",(role,)):
    if user['user_id']==actor.user_id:continue
    linked={r[0] for r in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(user['user_id'],))}
    if linked.intersection(mids):continue
    if user['created_by']!=actor.user_id and not linked.intersection(managed):continue
    result.append({k:user[k] for k in ('user_id','display_name','username','email','role')})
   return {'users':result}
 def lookup(self,token,body):
  with self.a.db() as db:
   role=body.get('role')
   if role not in ROLES:raise InputError('Supported account role required')
   self.scope(db,token,body.get('merchants'),role=role)
   email=body.get('email','')
   if role not in ROLES or not isinstance(email,str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()) or len(email)>150:raise InputError('Enter an exact email and supported role')
   row=db.execute("SELECT user_id,username,email,display_name,role,organization FROM users WHERE email=? COLLATE NOCASE AND role=? AND account_status='active'",(email.strip(),role)).fetchone()
   return {'match':dict(row)|{'affiliation_verified':False} if row else None}
 def grants(self,db,uid,mid,permissions,actor):
  if not isinstance(permissions,list) or any(not isinstance(p,str) for p in permissions) or not set(permissions)<=STAFF_ACTIONS:raise InputError('Unsupported Staff permissions')
  db.execute('DELETE FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=?',(uid,mid))
  db.executemany('INSERT INTO merchant_transaction_grants VALUES (?,?,?,?,?)',[(uid,mid,p,actor.user_id,self.a.clock()) for p in set(permissions)])
  self.a.audit('staff_permissions_changed',actor,mid,uid,db=db)
 def optional(self,db,uid):
  if db.execute("SELECT 1 FROM merchant_transaction_grants WHERE user_id=? AND permission='bulk_import'",(uid,)).fetchone():db.execute('INSERT OR IGNORE INTO optional_permissions VALUES (?,?)',(uid,'bulk_import'))
  else:db.execute("DELETE FROM optional_permissions WHERE user_id=? AND permission='bulk_import'",(uid,))
 def save(self,token,body,mode,uid=None):
  allowed={'role','merchants','permissions','username','email','display_name','organization','confirmed','user_id'}
  if not isinstance(body,dict) or set(body)-allowed:raise InputError('Unsupported account fields')
  if mode=='link' and body.get('confirmed') is not True:raise InputError('Confirm linking the selected existing user')
  with self.a.db() as db:
   db.execute('BEGIN IMMEDIATE');role=body.get('role')
   if role not in ROLES:raise InputError('Supported account role required')
   actor,managed=self.scope(db,token,body.get('merchants'),role=role)
   mids=body['merchants'];grants=body.get('permissions',{})
   if role not in ROLES or not isinstance(grants,dict) or not set(grants)<=set(mids):raise InputError('Invalid role or merchant permissions')
   if role=='BANK' and grants:raise InputError('Bank financial access requires separate explicit consent')
   if mode=='create':
    existing=db.execute('SELECT 1 FROM users WHERE email=? COLLATE NOCASE OR username=? COLLATE NOCASE',(body.get('email',''),body.get('username',''))).fetchone()
    if existing:raise InputError('Account already registered. Use Link Existing User.',409)
    result=self.a._create(db,actor,{k:body.get(k,'') for k in ('username','email','display_name','organization')}|{'role':role,'merchants':mids},secrets.token_urlsafe(64)+'Aa1!',True)
    uid=result['user_id']
   else:
    uid=uid or body.get('user_id');user=self.target(db,uid,role)
    if mode=='link':
     if user['account_status']!='active' or user['email'].casefold()!=str(body.get('email','')).strip().casefold():raise InputError('Confirm the exact eligible account')
     if any(db.execute('SELECT 1 FROM memberships WHERE user_id=? AND merchant_id=?',(uid,m)).fetchone() for m in mids):raise InputError('User already linked to a selected merchant',409)
    else:
     self.visible(db,user,managed)
     identity={k:body[k] for k in ('username','email','display_name','organization') if k in body and body[k]!=user[k]}
     allids={r[0] for r in db.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(uid,))}
     if identity and (user['created_by']!=actor.user_id or not allids<=set(managed)):raise AccessDenied('Linked or shared global identity cannot be edited by this Owner')
     if identity:
      merged=dict(user)|identity|{'role':'staff' if role=='SME_STAFF' else 'lender_analyst','merchants':list(allids)};self.a._validate_user(merged,actor)
      try:db.execute('UPDATE users SET username=?,email=?,display_name=?,organization=?,updated_at=? WHERE user_id=?',(*(merged[k].strip() for k in ('username','email','display_name','organization')),self.a.clock(),uid))
      except sqlite3.IntegrityError:raise InputError('Username or email already registered',409) from None
      self.a.audit('account_updated',actor,target=uid,db=db)
   for mid in mids:
    exists=db.execute('SELECT 1 FROM memberships WHERE user_id=? AND merchant_id=?',(uid,mid)).fetchone()
    db.execute('INSERT OR IGNORE INTO memberships VALUES (?,?)',(uid,mid))
    if mode=='create' or not exists:
     db.execute('INSERT OR IGNORE INTO owner_user_links VALUES (?,?,?,?,?)',(uid,mid,actor.user_id,'created' if mode=='create' else 'linked',self.a.clock()))
     self.a.audit('account_linked' if mode=='link' else 'merchant_assignment_changed',actor,mid,uid,db=db)
    if role=='SME_STAFF' and mid in grants:self.grants(db,uid,mid,grants[mid],actor)
   if role=='SME_STAFF':self.optional(db,uid)
   if mode=='edit':db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(uid,))
   result=self.public(db,self.target(db,uid),actor,managed)
   return {'user':result,'message':'Account created. A System Admin must privately issue password setup using the existing reset workflow; no password or activation token is exposed here.' if mode=='create' else 'Merchant associations saved. Credentials and other businesses are unchanged.'}
 def remove(self,token,uid,body):
  if body.get('confirmed') is not True:raise InputError('Confirm removal from selected merchants')
  with self.a.db() as db:
   db.execute('BEGIN IMMEDIATE');self.scope(db,token);user=self.target(db,uid);actor,managed=self.scope(db,token,body.get('merchants'),role=user['role'])
   self.visible(db,user,managed)
   for mid in body['merchants']:
    if not db.execute('SELECT 1 FROM memberships WHERE user_id=? AND merchant_id=?',(uid,mid)).fetchone():raise InputError('User is not linked to selected merchant')
    if user['role']=='BANK':
     for consent in db.execute('SELECT consent_id FROM consents WHERE recipient_id=? AND merchant_id=? AND revoked_at IS NULL',(uid,mid)).fetchall():
      db.execute('UPDATE consents SET revoked_at=? WHERE consent_id=?',(self.a.clock(),consent[0]));self.a.audit('consent_revoked',actor,mid,consent[0],db=db)
    db.execute('DELETE FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=?',(uid,mid));db.execute('DELETE FROM owner_user_links WHERE user_id=? AND merchant_id=?',(uid,mid));db.execute('DELETE FROM memberships WHERE user_id=? AND merchant_id=?',(uid,mid))
    self.a.audit('merchant_association_removed',actor,mid,uid,db=db)
   self.optional(db,uid);db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(uid,))
   return {'ok':True}
 def authorize(self,token,body):
  if set(body)-{'recipient_id','grants','purpose','expires_at','confirmed'} or body.get('confirmed') is not True:raise InputError('Explicit Owner consent confirmation required')
  grants=body.get('grants')
  if not isinstance(grants,list) or not grants or any(not isinstance(g,dict) or set(g)-{'merchant','categories','allow_download','replace_id'} for g in grants):raise InputError('Select merchant-specific financial permissions')
  with self.a.db() as db:
   db.execute('BEGIN IMMEDIATE');actor,managed=self.scope(db,token,[g.get('merchant') for g in grants],role='BANK');self.target(db,body.get('recipient_id'),'BANK');ids=[]
   for grant in grants:
    mid=grant['merchant'];old=grant.get('replace_id')
    if old:
     previous=db.execute('SELECT * FROM consents WHERE consent_id=?',(old,)).fetchone()
     if not previous or previous['owner_id']!=actor.user_id or previous['merchant_id']!=mid or previous['recipient_id']!=body['recipient_id']:raise AccessDenied('Authorization is not editable by this Owner')
     db.execute('UPDATE consents SET revoked_at=? WHERE consent_id=? AND revoked_at IS NULL',(self.a.clock(),old));self.a.audit('consent_revoked',actor,mid,old,db=db)
    result=self.a._grant_consent(db,actor,{'merchant':mid,'recipient_id':body['recipient_id'],'categories':grant.get('categories'),'purpose':body.get('purpose'),'expires_at':body.get('expires_at'),'allow_download':grant.get('allow_download',False)})
    ids.append(result['consent_id']);self.a.audit('bank_authorization_modified' if old else 'bank_authorization_created',actor,mid,result['consent_id'],db=db,metadata={'previous_consent_id':old})
   return {'consent_ids':ids}
