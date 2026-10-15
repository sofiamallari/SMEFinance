"""Owner chat read adapters reuse authenticated application services, never model arithmetic.

Not external MCP tools: these are HTTP session-scoped read capabilities. Sensitive
action proposals and confirmations retain their existing separate implementation.
"""
import re,time,threading
from copilot.authorization import require,BOUNDARIES
from copilot.security import AccessDenied,Tier

def read(c,p,mid,text,auth,token,pos,module=None):
    if not re.search(r'\b(my|our|current|show|list|which|what)\b',text,re.I):return None
    topic= ('settings' if re.search(r'currenc|timezone|transaction setting',text,re.I) else
            'staff' if re.search(r'staff|delegated permission',text,re.I) else
            'consents' if re.search(r'bank authoriz|authorized bank|consent|bank access',text,re.I) else
            'applications' if re.search(r'application|financing draft',text,re.I) else None)
    if not topic and module=='applications' and re.search(r'\bstatus\b',text,re.I):topic='applications'
    if not topic:return None
    # Bank has its own consent-aware financial tool path, never this Owner adapter.
    if p.role not in ('owner','staff'):return None
    require(p,'use_copilot',mid)
    capability={'settings':'transaction_settings_read','staff':'staff_delegation_read','consents':'bank_authorization_read','applications':'financing_applications_read'}[topic]
    tier=Tier.T1_ADVISE if topic=='applications' else Tier.T0_READ
    c.guard.check(p,capability,tier,mid)
    from copilot.bank_workflow import BankWorkflow
    flow=BankWorkflow(auth,c)
    if topic=='settings':
        value=pos.settings.get(token,mid)
        reply='Transaction Settings: base currency '+value['base_currency']+'; timezone '+value['timezone']+'; date display '+value['display_date_format']+'. Base currency '+('locked by existing activity.' if value['currency_locked'] else 'is currently editable by an authorized Owner.')
        action='transaction_settings_read'
    elif topic=='staff':
        value=flow.staff(token,mid)
        reply='Own-business User Management:\n'+'\n'.join(r['display_name']+' — '+r['account_status']+'; delegated permissions: '+(', '.join(r['permissions']) or 'none') for r in value['staff']) if value['staff'] else 'No assigned staff accounts were returned.'
        action='staff_delegation_read'
    elif topic=='consents':
        value=auth.consents(token,mid)
        reply='Bank Authorization:\n'+'\n'.join(r['recipient_name']+' — '+('revoked' if r['revoked_at'] else 'expired' if r['expires_at']<=auth.clock() else 'active')+'; categories: '+', '.join(r['categories']) for r in value['consents']) if value['consents'] else 'No Bank authorizations are recorded for this merchant.'
        action='bank_authorization_read'
    else:
        value=flow.draft(token,mid)
        rows=[r['draft_id']+' — '+r['state']+'; requested amount '+str(r['amount'])+' '+c.merchants[mid].currency for r in value['drafts']]
        if p.role=='owner':
            rows += [r['application_id']+' — '+r['status']+'; requested amount '+str(r['requested_amount'])+' '+r['currency'] for r in auth.application_list(token,mid)]
        reply='Financing Applications:\n'+'\n'.join(rows) if rows else 'No authorized financing drafts or applications were returned.'
        reply+='\nSubmission status is not lender approval. Staff see their own delegated drafts only.'
        action='financing_applications_read'
    # Live services above enforce role, membership, explicit grants and consent.
    require(p,'use_copilot',mid)
    c.guard.check(p,capability,tier,mid)
    c.audit.write(actor=p.user_id,event='partner_owner_read',merchant_id=mid,capability=action)
    return {'reply':reply+'\nSource: existing authorized '+topic+' service; retrieved just now.', 'mode':'rule_engine',
            'classification':'VERIFIED','tools_used':[action],'evidence':[],'connection_status':'deterministic',
            'data':{'source':action,'retrieved_at':time.time()}}

class SessionConversations:
    """Bounded server memory only: no financial browser storage or cross-session history.

    Changing live permissions invalidates old transcript content. Actions, tokens,
    raw provider errors and model diagnostics are never persisted here.
    """
    def __init__(self):self.records={};self.lock=threading.RLock()
    def scope(self,p,mid):
        require(p,'use_copilot',mid)
        if mid not in p.merchant_ids:raise AccessDenied('Merchant access denied')
        allowed=[]
        for permission in sorted(BOUNDARIES.get(p.role,())):
            try:allowed.append((permission,require(p,permission,mid)))
            except AccessDenied:pass
        return (p.user_id,p.session_id,mid),tuple(allowed)
    def get(self,p,mid):
        key,permissions=self.scope(p,mid)
        with self.lock:
            now=time.time()
            for old in list(self.records):
                if now-self.records[old]['at']>1800:self.records.pop(old)
            record=self.records.get(key)
            if not record or record['permissions']!=permissions:return []
            record['at']=now
            return [dict(row) for row in record['messages']]
    def append(self,p,mid,question,result):
        key,permissions=self.scope(p,mid)
        with self.lock:
            messages=self.get(p,mid)
            messages.extend([{'role':'user','content':question[:2000]},{'role':'assistant','content':result.get('reply','')[:16000]}])
            if len(self.records)>=1024:self.records.pop(next(iter(self.records)))
            self.records[key]={'permissions':permissions,'at':time.time(),'messages':messages[-40:]}

conversations=SessionConversations()
