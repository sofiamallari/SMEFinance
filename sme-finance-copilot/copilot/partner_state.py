"""Server-scoped conversation preferences and exact, confirmed sandbox actions."""
import hashlib,json,secrets,threading
from decimal import Decimal
from copilot.security import AccessDenied,ApprovalRequired
from copilot.authorization import require
from copilot.auth import InputError

class PartnerState:
    def __init__(self,c):self.c=c;self.memory={};self.actions={};self.lock=threading.RLock()
    def key(self,p,session):return hashlib.sha256((p.user_id+'|'+(session or 'trusted-internal')).encode()).hexdigest()
    def context(self,p,mid,session):
        require(p,'use_copilot',mid);key=self.key(p,session)
        if p.authenticated and self.c.identity_store:
            with self.c.identity_store.db() as db:
                record=db.execute('SELECT state_json FROM partner_context WHERE context_key=? AND user_id=?',(key,p.user_id)).fetchone()
                state=json.loads(record[0]) if record else {}
        else:state=self.memory.get(key,{})
        same=state.get('merchant_id')==mid and state.get('role')==p.role
        version=self.c.financial_data.version(mid)
        if not same:state={}
        elif state.get('data_version')!=version or self.c.clock()-state.get('last_verified_at',0)>300:
            state={k:v for k,v in state.items() if k in ('intent','period_start','period_end','advance','active_module')}
        state.update(merchant_id=mid,role=p.role)
        return state
    def save(self,p,mid,session,state):
        require(p,'use_copilot',mid);key=self.key(p,session)
        if p.authenticated and self.c.identity_store:
            with self.c.identity_store.db() as db:
                db.execute('INSERT INTO partner_context(context_key,user_id,merchant_id,state_json,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(context_key) DO UPDATE SET merchant_id=excluded.merchant_id,state_json=excluded.state_json,updated_at=excluded.updated_at',(key,p.user_id,mid,json.dumps(state),self.c.clock()))
        else:
            self.memory[key]=state
            if len(self.memory)>1000:self.memory.pop(next(iter(self.memory)))
    def propose(self,p,mid,session,kind,parameters):
        if not isinstance(parameters,dict):raise InputError('Action parameters must be an object')
        if kind not in ('payment_create','prepare_financing_application'):raise AccessDenied('Action is not supported')
        allowed={'method','amount','items'} if kind=='payment_create' else {'product_id','amount'}
        if set(parameters)-allowed:raise InputError('Unexpected action parameters')
        if kind=='payment_create' and parameters.get('method') not in ('qr_pay','tap_pay','pay_link'):raise InputError('Select a supported sandbox payment method')
        if kind=='payment_create' and parameters.get('items'):
            parameters={**parameters,'amount':self.c.payments.cart_totals(parameters['items'],self.c.merchants[mid].currency)['total']}
        try:amount=Decimal(str(parameters.get('amount','')))
        except ArithmeticError:raise InputError('Provide an exact positive action amount') from None
        if not amount.is_finite() or amount<=0 or amount>Decimal('1e12') or amount!=amount.quantize(Decimal('.01')):raise InputError('Provide a positive exact amount with two decimal places')
        parameters={**parameters,'amount':float(amount)}
        if kind=='prepare_financing_application' and parameters.get('product_id','RBF')!='RBF':raise InputError('Confirmed action currently supports the configured RBF application')
        tool=self.c.tools[kind];approval=None
        try:self.c.guard.check(p,kind,tool.tier,mid,required_consent=tool.consent)
        except ApprovalRequired as exc:approval=exc.token
        if kind=='prepare_financing_application':self.c.call(p,'rbf_quote',mid,advance=float(amount))
        aid='ACT-'+secrets.token_hex(16)
        action={'action_id':aid,'user_id':p.user_id,'merchant_id':mid,'session_hash':self.key(p,session),'kind':kind,'parameters':parameters,'approval_token':approval,
                'expires_at':self.c.clock()+300,'data_version':self.c.financial_data.version(mid),'state':'proposed','result':None}
        self.write(action,p)
        self.c.audit.write(actor=p.user_id,event='action_proposed',merchant_id=mid,action_id=aid,kind=kind,parameters=parameters)
        return self.public(action)
    def write(self,action,p):
        if p.authenticated and self.c.identity_store:
            with self.c.identity_store.db() as db:
                db.execute('INSERT INTO partner_actions(action_id,user_id,merchant_id,session_hash,state,action_json,expires_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(action_id) DO UPDATE SET state=excluded.state,action_json=excluded.action_json',(action['action_id'],p.user_id,action['merchant_id'],action['session_hash'],action['state'],json.dumps(action),action['expires_at']))
        else:self.actions[action['action_id']]=action
    def public(self,action):return {k:action[k] for k in ('action_id','merchant_id','kind','parameters','expires_at','state','result')}
    def confirm(self,p,mid,session,aid,confirmed,expected_amount=None,expected_kind=None):
        if confirmed is not True:raise InputError('Explicit action confirmation is required')
        with self.lock:
            if p.authenticated and self.c.identity_store:
                with self.c.identity_store.db() as db:
                    record=db.execute('SELECT action_json FROM partner_actions WHERE action_id=? AND user_id=?',(aid,p.user_id)).fetchone()
                    action=json.loads(record[0]) if record else None
            else:action=self.actions.get(aid)
            if not action or (action['user_id'],action['merchant_id'],action['session_hash'])!=(p.user_id,mid,self.key(p,session)):raise AccessDenied('Action is not available in this authenticated context')
            if expected_kind is not None and action['kind']!=expected_kind:raise InputError('Confirmation refers to a different action',409)
            if expected_amount is not None and Decimal(str(expected_amount))!=Decimal(str(action['parameters']['amount'])):raise InputError('Confirmation amount differs from the reviewed proposal',409)
            tool=self.c.tools[action['kind']]
            require(p,'simulate_payments' if action['kind']=='payment_create' else 'submit_application',mid)
            if action['state']=='executed':
                try:self.c.guard.check(p,action['kind'],tool.tier,mid,required_consent=tool.consent)
                except ApprovalRequired:pass
                return self.public(action)
            if action['state']!='proposed':raise InputError('Action is already executing or needs review',409)
            if action['expires_at']<=self.c.clock():raise InputError('Action expired; propose it again',409)
            if action['data_version']!=self.c.financial_data.version(mid):raise InputError('Financial evidence changed; review a new proposal',409)
            # The explicit, session-bound action confirmation is the human approval.
            # Issue a fresh existing PolicyGuard token after live reauthorization;
            # proposal tokens from a previous server process must not bypass or break that check.
            try:self.c.guard.check(p,action['kind'],tool.tier,mid,required_consent=tool.consent)
            except ApprovalRequired as exc:action['approval_token']=exc.token
            if p.authenticated and self.c.identity_store:
                with self.c.identity_store.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    changed=db.execute("UPDATE partner_actions SET state='executing' WHERE action_id=? AND user_id=? AND state='proposed'",(aid,p.user_id)).rowcount
                    if changed!=1:raise InputError('Action already claimed; fetch its outcome',409)
            action['state']='executing';self.write(action,p)
            parameters=dict(action['parameters'])
            if action['kind']=='payment_create':parameters['idempotency_key']=aid
            try:
                result=self.c.call(p,action['kind'],mid,approval_token=action['approval_token'],**parameters)
                if action['kind']=='payment_create' and result.get('qr_payload'):
                    from copilot.modules.payments import qr_matrix
                    result={**result,'qr_matrix':qr_matrix(result['qr_payload'])}
                action.update(state='executed',result=result);self.write(action,p)
                self.c.audit.write(actor=p.user_id,event='action_executed',merchant_id=mid,action_id=aid,kind=action['kind'])
                return self.public(action)
            except Exception:
                action['state']='review_required';self.write(action,p)
                self.c.audit.write(actor=p.user_id,event='action_failed',merchant_id=mid,action_id=aid,reason='execution_failure')
                raise InputError('Action outcome needs review; no automatic retry is permitted',409) from None
