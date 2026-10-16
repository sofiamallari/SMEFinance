"""Four-role POC workflows. Existing financial tools remain authoritative."""
import csv,io,json,secrets
from decimal import Decimal,InvalidOperation
from copilot.auth import InputError
from copilot.security import AccessDenied,Principal
from copilot.authorization import STAFF_ACTIONS

class BankWorkflow:
    def __init__(self,auth,copilot):self.a=auth;self.c=copilot
    def invite_bank(self,token,body):
        """Owner-scoped provisioning; never reset or edit an existing account."""
        from copilot.auth import digest
        if not isinstance(body,dict) or set(body)-{'merchant','username','email','display_name','organization'}:raise InputError('Unsupported Bank invitation fields')
        mid=body.get('merchant')
        if not isinstance(mid,str) or not mid:raise InputError('Merchant required')
        with self.a.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.a._authorize(db,token,'manage_consents',mid)
            session=self.a._session(db,token,touch=False)
            actor=Principal(session['user_id'],session['role'])
            if actor.role!='owner':raise AccessDenied('SME Owner required')
            email=body.get('email','')
            if not isinstance(email,str) or '@' not in email or len(email)>150:raise InputError('Valid Bank email required')
            existing=db.execute('SELECT * FROM users WHERE lower(email)=lower(?)',(email.strip(),)).fetchone()
            if existing:
                if existing['role']!='BANK' or existing['account_status']!='active':raise InputError('This account cannot receive Bank access',409)
                uid=existing['user_id'];invitation=None
            else:
                user=self.a._create(db,actor,{'username':body.get('username'),'email':email.strip(),'display_name':body.get('display_name'),'organization':body.get('organization'),'role':'BANK','merchants':[mid]},secrets.token_urlsafe(48)+'Aa1!',True)
                uid=user['user_id'];invitation=secrets.token_urlsafe(32)
                db.execute('INSERT INTO reset_tokens VALUES (?,?,?,0)',(digest(invitation),uid,self.a.clock()+self.a.policies(db)['reset_expiration']))
                self.a.audit('bank_invitation_created',actor,mid,uid,db=db)
            db.execute('INSERT OR IGNORE INTO memberships VALUES (?,?)',(uid,mid))
            self.a.audit('bank_membership_assigned',actor,mid,uid,db=db)
            row=db.execute('SELECT display_name,organization FROM users WHERE user_id=?',(uid,)).fetchone()
            return {'recipient':{'user_id':uid,**dict(row)},'created':invitation is not None,'invitation_token':invitation,'expires_in':self.a.policies(db)['reset_expiration'] if invitation else None,'message':'New Bank invitation: securely deliver the one-time activation token to the intended recipient. No email was sent.' if invitation else 'Existing Bank linked. Its credentials and profile were not changed. Grant explicit data categories separately.'}

    def merchants(self,token):
        """Own active Owner grants only; never a directory of unrelated users."""
        self.a.authorize(token,'view_bank_review');p=self.a.principal(token)
        if p.role!='lender_analyst':raise AccessDenied('Bank review only')
        result=[]
        for mid,m in self.c.merchants.items():
            try:self.a.authorize(token,'view_bank_review',mid)
            except AccessDenied:continue
            can_audit=True
            try:self.a.authorize(token,'view_bank_audit',mid)
            except AccessDenied:can_audit=False
            with self.a.db() as db:
                grants=[{'categories':json.loads(r['categories']),'granted_at':r['granted_at'],'expires_at':r['expires_at'],'allow_download':bool(db.execute('SELECT 1 FROM consent_downloads WHERE consent_id=? AND allow_csv=1',(r['consent_id'],)).fetchone())} for r in db.execute("SELECT c.* FROM consents c JOIN users o ON o.user_id=c.owner_id WHERE c.merchant_id=? AND c.recipient_id=? AND c.revoked_at IS NULL AND c.expires_at>? AND o.account_status='active' AND o.role='SME_OWNER' AND EXISTS(SELECT 1 FROM memberships x WHERE x.user_id=o.user_id AND x.merchant_id=c.merchant_id)",(mid,p.user_id,self.a.clock()))]
                last=None
                for row in (db.execute('SELECT record FROM audit_events ORDER BY seq DESC') if can_audit else []):
                    event=json.loads(row[0])
                    if event.get('actor')==p.user_id and event.get('merchant_id')==mid and event.get('action')=='bank_review_accessed':last=event.get('ts');break
            self.a.authorize(token,'view_bank_review',mid)
            if can_audit:
                try:self.a.authorize(token,'view_bank_audit',mid)
                except AccessDenied:last=None
            if grants:result.append({'id':mid,'name':m.name,'currency':m.currency,'authorizations':grants,'last_review_at':last})
        self.a.authorize(token,'view_bank_review')
        return result

    def _routed(self,db,token,aid=None,action='view_bank_review'):
        # Application routing is not authorization to financial data categories.
        self.a._authorize(db,token,'view_bank_review')
        if action!='view_bank_review':self.a._authorize(db,token,action)
        session=self.a._session(db,token,touch=False)
        actor=Principal(session['user_id'],session['role'])
        if actor.role!='lender_analyst':raise AccessDenied('Bank role required')
        query="SELECT a.* FROM applications a JOIN memberships m ON m.user_id=a.recipient_id AND m.merchant_id=a.merchant_id LEFT JOIN merchant_profiles p ON p.merchant_id=a.merchant_id WHERE a.recipient_id=? AND COALESCE(p.status,'active')='active'"
        args=[actor.user_id]
        if aid:query+=' AND a.application_id=?';args.append(aid)
        rows=db.execute(query+' ORDER BY a.created_at DESC,a.application_id',args).fetchall()
        authorized=[]
        for row in rows:
            try:
                self.a._authorize(db,token,'view_applications',row['merchant_id'])
                if action!='view_bank_review':self.a._authorize(db,token,action,row['merchant_id'])
            except AccessDenied:continue
            authorized.append(row)
        rows=authorized
        if aid and not rows:raise AccessDenied('Application is not available to this Bank')
        return actor,rows

    def applications(self,token,aid=None):
        with self.a.db() as db:
            _,rows=self._routed(db,token,aid);result=[]
            for row in rows:
                packet=json.loads(row['packet'])
                # Explicit safe request metadata; assessment snapshots are never exposed here.
                item={k:packet.get(k) for k in ('product_id','requested_amount','currency','status')}
                merchant=self.c.merchants.get(row['merchant_id'])
                bank=db.execute('SELECT display_name,organization FROM users WHERE user_id=?',(row['recipient_id'],)).fetchone()
                item.update(application_id=row['application_id'],merchant_id=row['merchant_id'],merchant_name=merchant.name if merchant else row['merchant_id'],created_at=row['created_at'],submitted_at=row['created_at'],bank_name=(bank['organization'] or bank['display_name']) if bank else 'Bank',reviews=self.a.application_reviews(db,row['application_id']))
                result.append(item)
            return result[0] if aid else result

    def record_review(self,token,aid,body):
        if not isinstance(body,dict) or set(body)-{'outcome','note'}:raise InputError('Unsupported review fields')
        outcome=body.get('outcome');note=body.get('note','')
        if outcome not in ('reviewed','more_information_needed','ready_for_further_assessment','approved','rejected'):raise InputError('Select a supported simulated review outcome')
        if not isinstance(note,str) or len(note.strip())>1000:raise InputError('Review notes must be text, at most 1000 characters')
        note=note.strip()
        if outcome in ('more_information_needed','rejected') and not note:raise InputError('Review notes are required when more information is needed')
        with self.a.db() as db:
            db.execute('BEGIN IMMEDIATE');actor,rows=self._routed(db,token,aid,'record_bank_review');row=rows[0];packet=json.loads(row['packet'])
            if packet.get('status')!='SUBMITTED_FOR_LENDER_REVIEW':raise InputError('Application is not in a reviewable submitted state',409)
            stamp=self.a.clock()
            if outcome in ('approved','rejected'):
                packet.update(status=outcome.upper(),decision_at=stamp,decision_by=actor.user_id,decision_note=note,simulated_decision=True)
                db.execute('UPDATE applications SET packet=? WHERE application_id=?',(json.dumps(packet),aid))
                self.a.audit('financing_simulated_'+outcome,actor,row['merchant_id'],aid,db=db,reason=outcome)
            db.execute('INSERT INTO application_reviews VALUES (?,?,?,?,?,?)',(secrets.token_hex(12),aid,actor.user_id,outcome,note,stamp))
            self.a.audit('financing_review_recorded',actor,row['merchant_id'],aid,db=db,reason=outcome)
            return {'ok':True,'outcome':outcome,'created_at':stamp,'sandbox':True,'disclaimer':'Simulated decision/review only; no real credit approval, loan or disbursement'}

    def staff(self,token,mid,uid=None,body=None):
        self.a.authorize(token,'manage_merchant_staff',mid);p=self.a.principal(token)
        with self.a.db() as db:
            rows=db.execute("SELECT u.user_id,u.username,u.display_name,u.account_status FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE m.merchant_id=? AND u.role='SME_STAFF'",(mid,)).fetchall()
            if uid:
                if not any(r['user_id']==uid for r in rows):raise AccessDenied('Staff account is not assigned to this merchant')
                if not isinstance(body,dict) or set(body)!={'permissions'} or not isinstance(body['permissions'],list) or any(not isinstance(x,str) for x in body['permissions']) or not set(body['permissions'])<=STAFF_ACTIONS:raise InputError('Select supported delegated permissions only')
                db.execute('DELETE FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=?',(uid,mid))
                db.executemany('INSERT INTO merchant_transaction_grants VALUES (?,?,?,?,?)',[(uid,mid,x,p.user_id,self.a.clock()) for x in set(body['permissions'])])
                if db.execute("SELECT 1 FROM merchant_transaction_grants WHERE user_id=? AND permission='bulk_import'",(uid,)).fetchone():db.execute('INSERT OR IGNORE INTO optional_permissions VALUES (?,?)',(uid,'bulk_import'))
                else:db.execute("DELETE FROM optional_permissions WHERE user_id=? AND permission='bulk_import'",(uid,))
                db.execute('UPDATE sessions SET revoked=1 WHERE user_id=?',(uid,))
                self.a.audit('staff_permissions_changed',p,mid,uid,db=db)
            return {'permissions':sorted(STAFF_ACTIONS),'staff':[dict(r,permissions=[x[0] for x in db.execute('SELECT permission FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=?',(r['user_id'],mid))]) for r in rows]}
    def audit(self,token,mid):
        p=self.a.principal(token);self.a.authorize(token,'view_bank_audit' if p.role=='lender_analyst' else 'view_merchant_audit',mid)
        with self.a.db() as db:
            records=[json.loads(r[0]) for r in db.execute('SELECT record FROM audit_events ORDER BY seq DESC')]
        # Bank receives only its own merchant-scoped event metadata, never another Bank's records.
        return {'records':[{k:r.get(k) for k in ('ts','actor','action','merchant_id','target','result','reason_code')} for r in records if r.get('merchant_id')==mid and (p.role=='owner' or r.get('actor')==p.user_id)][:100]}
    def draft(self,token,mid,did=None,body=None):
        self.a.authorize(token,'create_financing_draft' if body is not None and did is None else 'edit_financing_draft' if body is not None else 'view_applications',mid)
        p=self.a.principal(token)
        if p.role not in ('owner','staff'):raise AccessDenied('Only merchant users manage drafts')
        with self.a.db() as db:
            record=db.execute('SELECT * FROM financing_drafts WHERE draft_id=? AND merchant_id=?',(did,mid)).fetchone() if did else None
            if did and (not record or p.role=='staff' and record['creator_id']!=p.user_id):raise AccessDenied('Draft not available')
            if body is not None:
                if record and record['state']!='DRAFT':raise InputError('Submitted draft cannot be edited',409)
                if not isinstance(body,dict) or set(body)-{'amount','recipient_id','product_id'}:raise InputError('Unsupported draft fields')
                value={**(json.loads(record['body']) if record else {}),**body}
                if value.get('product_id','RBF')!='RBF':raise InputError('This POC supports RBF drafts')
                try:amount=Decimal(str(value.get('amount')))
                except InvalidOperation:raise InputError('Invalid draft amount') from None
                if not amount.is_finite() or not 0<amount<=Decimal('1e12') or amount!=amount.quantize(Decimal('.01')):raise InputError('Positive exact-cent amount required')
                value={'amount':str(amount),'product_id':'RBF','recipient_id':value.get('recipient_id')}
                if value['recipient_id']:
                    recipient=db.execute("SELECT 1 FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE u.user_id=? AND m.merchant_id=? AND u.role='BANK' AND u.account_status='active'",(value['recipient_id'],mid)).fetchone()
                    if not recipient:raise InputError('Choose an active scoped Bank')
                did=did or 'DRAFT-'+secrets.token_hex(12)
                db.execute('INSERT INTO financing_drafts VALUES (?,?,?,?,?,?,NULL) ON CONFLICT(draft_id) DO UPDATE SET updated_at=excluded.updated_at,body=excluded.body',(did,mid,p.user_id,self.a.clock(),'DRAFT',json.dumps(value)))
                self.a.audit('financing_draft_saved',p,mid,did,db=db)
            rows=db.execute('SELECT * FROM financing_drafts WHERE merchant_id=? ORDER BY updated_at DESC',(mid,)).fetchall()
            banks=[dict(r) for r in db.execute("SELECT u.user_id,u.display_name,u.organization FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE m.merchant_id=? AND u.role='BANK' AND u.account_status='active'",(mid,))]
            return {'drafts':[dict(draft_id=r['draft_id'],state=r['state'],application_id=r['application_id'],updated_at=r['updated_at'],**json.loads(r['body'])) for r in rows if p.role=='owner' or r['creator_id']==p.user_id],'banks':banks}
    def propose(self,token,mid,did):
        self.a.authorize(token,'submit_application',mid);p=self.a.principal(token)
        with self.a.db() as db:
            row=db.execute("SELECT * FROM financing_drafts WHERE draft_id=? AND merchant_id=? AND state='DRAFT'",(did,mid)).fetchone()
            if not row:raise InputError('Editable draft unavailable',404)
            body=json.loads(row['body'])
            if not body.get('recipient_id'):raise InputError('Owner must explicitly select a Bank before submission')
            consent=self.a._consent(db,mid,body['recipient_id'],'applications')
            if not consent or consent['owner_id']!=p.user_id:raise AccessDenied('Owner Bank authorization for applications is required')
        return self.c.partner_state.propose(p,mid,p.session_id,'prepare_financing_application',{'product_id':'RBF','amount':body['amount'],'recipient_id':body['recipient_id'],'draft_id':did})
    def _bank_principal(self,token,mid,action):
        self.a.authorize(token,'view_bank_review',mid);p=self.a.principal(token)
        if p.role!='lender_analyst':raise AccessDenied('Bank review only')
        self.a.authorize(token,action,mid)
        return p
    def dashboard(self,token,mid,start=None,end=None,granularity='monthly'):
        """Owner-style Overview under the Owner's reports grant; never SME Dashboard authority."""
        from datetime import date
        p=self._bank_principal(token,mid,'view_reports')
        if granularity not in ('daily','weekly','monthly','quarterly'):raise InputError('Unsupported granularity')
        try:parsed=[date.fromisoformat(v) if v else None for v in (start,end)]
        except (TypeError,ValueError):raise InputError('Dates must use YYYY-MM-DD')
        if parsed[0] and parsed[1] and parsed[0]>parsed[1]:raise InputError('Start date must be on or before end date.')
        m=self.c.merchants[mid];result=self.c.financial_data.dashboard(mid,start,end,granularity)
        result['merchant']={**result.get('merchant',{}),'id':mid,'name':m.name,'currency':m.currency}
        self.a.authorize(token,'view_reports',mid)
        self.a.audit('bank_review_accessed',p,mid,None)
        return result
    def cashflow(self,token,mid):
        """Existing forecast and alerts under the Owner's forecasts grant."""
        p=self._bank_principal(token,mid,'view_forecasts')
        result={'forecast':self.c.call(p,'cashflow_forecast',mid),'alerts':self.c.call(p,'cashflow_alerts',mid),'currency':self.c.merchants[mid].currency}
        self.a.authorize(token,'view_forecasts',mid)
        return result
    def review(self,token,mid,aid=None,export=False):
        self.a.authorize(token,'export_bank_review' if export else 'view_bank_review',mid);p=self.a.principal(token)
        if p.role!='lender_analyst':raise AccessDenied('Bank review only')
        try:apps=self.a.application_list(token,mid)
        except AccessDenied:
            if aid:raise
            apps=[]
        if aid and not any(a['application_id']==aid for a in apps):raise AccessDenied('Application is not routed to this Bank')
        m=self.c.merchants[mid];data={'merchant_id':mid,'merchant_name':m.name,'currency':m.currency,'application':next((a for a in apps if a['application_id']==aid),None),'as_of':self.c.financial_data.as_of(mid).isoformat(),'retrieved_at':self.a.clock(),'data_version':self.c.financial_data.version(mid),'disclaimer':'Simulated financial review; not an official lending decision. Synthetic/demo attributes and provisional rules may apply.','applications':apps,'sections':{},'missing':[]}
        for name,tool,action in [('historical','financial_report','view_reports'),('assessment','assess_business','view_assessment'),('forecast','cashflow_forecast','view_forecasts'),('risk_indicators','cashflow_alerts','view_forecasts'),('financing','match_financing','view_financing'),('journey','financing_journey','view_financing'),('rbf','rbf_quote','view_financing')]:
            try:
                self.a.authorize(token,action,mid)
                if export:
                    from copilot.authorization import CATEGORIES
                    with self.a.db() as db:
                        if not self.a._consent(db,mid,p.user_id,CATEGORIES[action],download=True):raise AccessDenied('Download is not authorized for this category')
                data['sections'][name]=self.c.call(p,tool,mid)
            except AccessDenied:data['missing'].append(name+': category not authorized')
            except ValueError:data['missing'].append(name+': evidence unavailable')
        # Existing aggregate/trends used only under report authorization, never SME Dashboard authority.
        if 'historical' in data['sections']:
            self.a.authorize(token,'view_reports',mid)
            data['sections']['recorded_metrics']=self.c.financial_data.aggregate(mid)
            data['sections']['channel_performance']=self.c.financial_data.channel_performance(mid)
            from copilot.modules import dashboard
            merchant=self.c.financial_data.project(mid);asof=self.c.financial_data.as_of(mid)
            data['sections']['trends']=self.c.financial_data.dashboard(mid)['trend']
        if data['currency']!='CNY':
            from copilot.currency_policy import legacy_note
            data['disclaimer']+=' '+legacy_note(data['currency'])
        data['missing'].append('Historical bank cash and post-financing outcome baseline are unavailable; current cash-flow chart is a forecast.')
        self.a.authorize(token,'export_bank_review' if export else 'view_bank_review',mid)
        actions={'channel_performance':'view_reports','historical':'view_reports','recorded_metrics':'view_reports','trends':'view_reports','assessment':'view_assessment','forecast':'view_forecasts','risk_indicators':'view_forecasts','financing':'view_financing','journey':'view_financing','rbf':'view_financing'}
        for section in data['sections']:
            self.a.authorize(token,actions[section],mid)
            if export:
                from copilot.authorization import CATEGORIES
                with self.a.db() as db:
                    if not self.a._consent(db,mid,p.user_id,CATEGORIES[actions[section]],download=True):raise AccessDenied('Download authorization changed; refresh report')
        if apps:self.a.authorize(token,'view_applications',mid)
        if self.c.financial_data.version(mid)!=data['data_version']:raise InputError('Financial data changed; refresh report',409)
        self.a.audit('bank_report_exported' if export else 'bank_review_accessed',p,mid,aid)
        with self.a.db() as db:
            data['download_available']=bool(self.a._consent(db,mid,p.user_id,download=True))
            data['download_categories']=[category for category in ('reports','assessment','forecasts','financing','applications') if self.a._consent(db,mid,p.user_id,category,download=True)]
            if export and data['application'] and 'assessment' not in data['download_categories']:data['application']={k:v for k,v in data['application'].items() if k not in ('stage','scores')}
            if export and not self.a._consent(db,mid,p.user_id,'applications',download=True):data['application']=None
        if not export:return data
        out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(['merchant_id','section','field','value','classification'])
        def safe(v):
            text=str(v)
            return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
        for key in ('merchant_name','currency','as_of','retrieved_at','disclaimer'):writer.writerow([mid,'metadata',key,safe(data[key]),'simulated review'])
        if data['application']:writer.writerow([mid,'application','packet',safe(json.dumps(data['application'],default=str)),'simulated submitted packet'])
        for section,value in data['sections'].items():
            for field,item in (value.items() if isinstance(value,dict) else [('items',value)]):writer.writerow([mid,section,field,safe(json.dumps(item,default=str)), 'estimated' if section=='forecast' else 'existing calculated/demo evidence'])
        for message in data['missing']:writer.writerow([mid,'missing','note',safe(message),'unavailable'])
        return out.getvalue().encode('utf-8-sig')
