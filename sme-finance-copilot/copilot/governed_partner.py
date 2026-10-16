"""Governed page-session conversation. No durable transcripts or execution tools."""
import copy
import hashlib
import json
import os
import re
import secrets
import threading
import time
from contextlib import contextmanager
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from copilot.governed_claims import (render_tool, RESPONSE_SCHEMA)
from urllib.parse import urlsplit
from urllib.error import HTTPError
from copilot.conversation_state import fresh as fresh_conversation_state
from copilot.security import AccessDenied
from copilot.authorization import AUTHORITATIVE_ROLES
from copilot.governance_policy import Policy
from copilot.governed_tools import Gateway, INPUTS
from copilot.governed_research import Research, post_json, bounded_call

FINANCE = re.compile(r'financ|loan|lender|repayment|outstanding|rbf',re.I)
INJECTION = re.compile(r'ignore.{0,40}(?:permission|instruction|rule)|system prompt|api.?key|password|session.?token|approval.?secret|environment variable|private key',re.I)
EXECUTION = re.compile(r'^\s*(?:(?:please|can you|go ahead and)\s+)?(?:approve|submit|execute|transfer|pay|purchase|modify|delete|change (?:the )?balance)\b',re.I)


LLM_REQUEST_TIMEOUT=30
CHAT_TURN_TIMEOUT=60

def remaining(deadline,limit):
    budget=deadline-time.monotonic()
    if budget<=0:raise TimeoutError('Chat turn deadline exceeded')
    return min(limit,budget)

@contextmanager
def turn_lock(lock,deadline):
    if not lock.acquire(timeout=remaining(deadline,CHAT_TURN_TIMEOUT)):
        raise AccessDenied('This conversation is busy. Please try again.')
    try:yield
    finally:lock.release()

def minimized_text(text):
    from copilot.security import sanitize_input
    text=sanitize_input(text)['text']
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','[email removed]',text)
    text=re.sub(r'(?i)\b(?:bearer\s+\S+|(?:password|token|secret|api.?key)\s*[:=]\s*\S+)','[secret removed]',text)
    return re.sub(r'\b[A-Za-z0-9_\-]{24,}\b','[opaque value removed]',text)[:2000]


def live_configured():
    from copilot import ai_agent
    return os.environ.get('COPILOT_GOVERNED_LIVE','no')=='yes' and ai_agent.configured()


class ProviderUnavailable(RuntimeError):
    status=503
    def __init__(self):super().__init__('AI service temporarily unavailable')

def model_request(messages,tools,*,response_schema=None):
    base=os.environ.get('COPILOT_LLM_BASE_URL','').rstrip('/')
    parsed=urlsplit(base)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('A trusted HTTPS LLM endpoint is required')
    payload={'model':os.environ['COPILOT_LLM_MODEL'],'temperature':0,'messages':messages,'max_tokens':1200,'response_format':{'type':'json_schema','json_schema':{'name':'financial_response','strict':True,'schema':RESPONSE_SCHEMA}}}
    if not any(m.get('role')=='system' and 'typed claim' in str(m.get('content','')) for m in messages):payload.pop('response_format',None)
    if 'response_format' in payload:
        schema=copy.deepcopy(RESPONSE_SCHEMA)
        ids=set()
        for message in messages:
            ids.update(re.findall(r'"((?:user|fact[0-9]*)\.[A-Za-z0-9_]+)"\s*:',str(message.get('content',''))))
        if ids:schema['properties']['segments']['items']['anyOf'][1]['properties']['claim']['enum']=sorted(ids)
        payload['response_format']['json_schema']['schema']=schema
    if response_schema is not None:
        payload['response_format']={'type':'json_schema','json_schema':{'name':'review_response','strict':True,'schema':copy.deepcopy(response_schema)}}
    if tools:payload['tools']=tools;payload['tool_choice']='auto'
    try:
        result=post_json(base+'/chat/completions',payload,{'Authorization':'Bearer '+os.environ['COPILOT_LLM_API_KEY']},timeout=LLM_REQUEST_TIMEOUT)
    except HTTPError as error:
        if error.code==503:raise ProviderUnavailable() from None
        raise
    return result['choices'][0]['message']


class Partner:
    def __init__(self,c,auth,pos,*,clock=time.time,provider=None,research_provider=None):
        self.c,self.auth,self.pos,self.clock=c,auth,pos,clock
        self.policy=Policy();self.gateway=Gateway(c,auth,pos,self.policy)
        auth.audit('ai_governance_loaded',result='allowed' if self.policy.available else 'disabled',metadata={'policy_version':self.policy.version})
        self.research=Research(self.gateway,clock,research_provider)
        self.provider=provider or model_request
        self.records={};self.lock=threading.RLock()

    def sweep(self):
        now=self.clock()
        for key,row in list(self.records.items()):
            if now-row['at']>row['ttl']:self.records.pop(key,None)

    def fingerprint(self,token,p,mid):
        permissions=[]
        from copilot.governed_tools import PERMISSIONS
        for action in sorted(set(PERMISSIONS.values())):
            try:self.auth.authorize(token,action,mid);permissions.append(action)
            except AccessDenied:pass
        return (p.role,tuple(sorted(p.permissions)),tuple(sorted(p.merchant_ids)),tuple(permissions),self.policy.version)

    def create(self,token,mid):
        with self.lock:
            self.sweep();p=self.gateway.identity(token,mid);self.policy.capability(p,'financial_education')
            if len(self.records)>=512:raise ValueError('Conversation capacity reached; try later')
            self.forget_session(p.session_id) # New page/merchant invalidates previous temporary contexts.
            reference=secrets.token_urlsafe(32)
            self.records[reference]={'user':p.user_id,'session':p.session_id,'merchant':mid,'fingerprint':self.fingerprint(token,p,mid),'at':self.clock(),'ttl':min(1800,self.policy.section('conversation_policy')['session_idle_timeout_minutes']*60),'messages':[],'approvals':{},'assumptions':{},'conversation_state':fresh_conversation_state(),'lock':threading.RLock()}
            return {'conversation':reference,'policy_version':self.policy.version,'mode':'live' if live_configured() else 'deterministic','retention':'active-page-memory-only'}

    def context(self,token,mid,reference):
        with self.lock:
            self.sweep();row=self.records.get(reference)
            try:p=self.gateway.identity(token,mid)
            except Exception:
                if row and row['session']==hashlib.sha256(token.encode()).hexdigest():self.records.pop(reference,None)
                raise
            if not row or (row['user'],row['session'],row['merchant'])!=(p.user_id,p.session_id,mid):
                raise AccessDenied('Conversation is not available in this page/session/merchant context')
            if row['fingerprint']!=self.fingerprint(token,p,mid):
                self.records.pop(reference,None);raise AccessDenied('Permissions changed. Start a New Conversation')
            row['at']=self.clock();return p,row

    def close(self,token,mid,reference):
        self.context(token,mid,reference)
        with self.lock:self.records.pop(reference,None)

    def forget_session(self,session):
        with self.lock:
            for key,row in list(self.records.items()):
                if row['session']==session:self.records.pop(key,None)

    def forget_merchant(self,token,reference):
        # A close after merchant change is bound by authenticated session, not new mid.
        p=self.auth.principal(token)
        with self.lock:
            row=self.records.get(reference)
            if row and row['user']==p.user_id and row['session']==p.session_id:self.records.pop(reference,None)

    @staticmethod
    def response(reply,classification='ANALYSIS',**extra):
        return {'reply':reply,'mode':'governed_deterministic','connection_status':'deterministic','classification':classification,'tools_used':[],'evidence':[],**extra}

    def reply(self,token,mid,reference,text):
        from copilot.conversation_review import Conversation
        request=getattr(self,'conversation_request',None)
        return Conversation(self,request).reply(token,mid,reference,text)

    def review_reply(self,token,mid,reference,text):
        # Compatibility for local test runners, never a second engine or API.
        return self.reply(token,mid,reference,text)

    @staticmethod
    def render_tool(name,value):return render_tool(name,value)

    def decide(self,token,mid,reference,body):
        _,row=self.context(token,mid,reference)
        with row['lock']:
            result=self.research.decide(token,mid,row,body.get('approval_reference'),body.get('exact_query'),body.get('decision'))
            self.context(token,mid,reference)
            return self.response(**result)
