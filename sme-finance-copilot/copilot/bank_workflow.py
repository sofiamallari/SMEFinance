"""Four-role POC workflows. Existing financial tools remain authoritative."""
import csv,io,json,secrets
from decimal import Decimal,InvalidOperation
from copilot.auth import InputError
from copilot.security import AccessDenied
from copilot.authorization import STAFF_ACTIONS

class BankWorkflow:
    def __init__(self,auth,copilot):self.a=auth;self.c=copilot
    def staff(self,token,mid,uid=None,body=None):
        self.a.authorize(token,'manage_merchant_staff',mid);p=self.a.principal(token)
        with self.a.db() as db:
            rows=db.execute("SELECT u.user_id,u.display_name,u.account_status FROM users u JOIN memberships m ON m.user_id=u.user_id WHERE m.merchant_id=? AND u.role='SME_STAFF'",(mid,)).fetchall()
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
            return {'drafts':[dict(draft_id=r['draft_id'],state=r['state'],application_id=r['application_id'],**json.loads(r['body'])) for r in rows if p.role=='owner' or r['creator_id']==p.user_id],'banks':banks}
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
            try:self.a.authorize(token,action,mid);data['sections'][name]=self.c.call(p,tool,mid)
            except AccessDenied:data['missing'].append(name+': category not authorized')
            except ValueError:data['missing'].append(name+': evidence unavailable')
        # Existing aggregate/trends used only under report authorization, never SME Dashboard authority.
        if 'historical' in data['sections']:
            self.a.authorize(token,'view_reports',mid)
            data['sections']['recorded_metrics']=self.c.financial_data.aggregate(mid)
            from copilot.modules import dashboard
            merchant=self.c.financial_data.project(mid);asof=self.c.financial_data.as_of(mid)
            data['sections']['trends']=self.c.financial_data.dashboard(mid)['trend']
        data['missing'].append('Historical bank cash and post-financing outcome baseline are unavailable; current cash-flow chart is a forecast.')
        self.a.authorize(token,'export_bank_review' if export else 'view_bank_review',mid)
        actions={'historical':'view_reports','recorded_metrics':'view_reports','trends':'view_reports','assessment':'view_assessment','forecast':'view_forecasts','risk_indicators':'view_forecasts','financing':'view_financing','journey':'view_financing','rbf':'view_financing'}
        for section in data['sections']:self.a.authorize(token,actions[section],mid)
        if apps:self.a.authorize(token,'view_applications',mid)
        if self.c.financial_data.version(mid)!=data['data_version']:raise InputError('Financial data changed; refresh report',409)
        self.a.audit('bank_report_exported' if export else 'bank_review_accessed',p,mid,aid)
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
