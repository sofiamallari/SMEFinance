"""Single-use exact-query approvals; no model-selected URL fetching."""
import hashlib
import json
import os
import re
import secrets
import time
import ipaddress
import queue
import threading
from datetime import datetime, timezone
from urllib.parse import urlsplit
import urllib.request
from copilot.security import AccessDenied

SLOTS=threading.BoundedSemaphore(4)

def bounded_call(operation,timeout):
    """Bound response time and concurrent workers; timed-out reads cannot write finance."""
    if not SLOTS.acquire(blocking=False):raise TimeoutError('AI service is busy')
    result=queue.Queue(maxsize=1)
    def work():
        try:result.put((True,operation()))
        except Exception as error:result.put((False,error))
        finally:SLOTS.release()
    threading.Thread(target=work,daemon=True).start()
    try:ok,value=result.get(timeout=timeout)
    except queue.Empty:raise TimeoutError('AI operation timed out') from None
    if not ok:raise value
    return value

def public_url(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:return False
    host=parsed.hostname.lower()
    if host=='localhost' or host.endswith(('.local','.localhost')):return False
    try:return ipaddress.ip_address(host).is_global
    except ValueError:return '.' in host


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Provider redirects are disabled')


def post_json(url, payload, headers, timeout=10, maximum=262144):
    request=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=timeout) as response:
        data=response.read(maximum+1)
        if len(data)>maximum:raise ValueError('Provider response exceeds limit')
    return json.loads(data)


def public_query(topic):
    if topic!='sme_lending_rates':raise AccessDenied('This public research topic is not supported')
    year=datetime.now(timezone.utc).year
    return f'Shenzhen SME business loan interest rates {year} official bank sources'


def configured():
    return os.environ.get('COPILOT_RESEARCH_PROVIDER')=='tavily' and bool(os.environ.get('COPILOT_RESEARCH_API_KEY'))


def search(query, timeout=10):
    if not configured():raise ValueError('Public research provider unavailable')
    if query!=public_query('sme_lending_rates'):raise AccessDenied('Unapproved or unsafe public query')
    # One fixed provider endpoint; no redirects, alternate providers or retries.
    data=post_json('https://api.tavily.com/search',{'query':query,'max_results':5,'include_answer':False,'include_raw_content':False}, {'Authorization':'Bearer '+os.environ['COPILOT_RESEARCH_API_KEY']},timeout)
    rows=[]
    for item in data.get('results',[])[:5]:
        url=item.get('url','');parsed=urlsplit(url)
        if not public_url(url):continue
        # URLs are displayed as citations only. They are never fetched by the app.
        rows.append({'source_title':str(item.get('title','Public source'))[:500],'source_url':url[:1000],'publication_date':str(item.get('published_date'))[:100] if item.get('published_date') else None,'retrieved_at':datetime.now(timezone.utc).isoformat(),'excerpt':str(item.get('content',''))[:2000]})
    return rows


class Research:
    def __init__(self,gateway,clock=time.time,provider=None):
        self.gateway=gateway;self.clock=clock;self.provider=provider or search

    def propose(self,token,mid,conversation,topic):
        p,spec=self.gateway.authorize(token,mid,'search_public_financial_information')
        if not configured() and self.provider is search:
            return {'available':False,'message':'Public research is unavailable because no approved provider is configured. No search was executed.'}
        query=public_query(topic);reference=secrets.token_urlsafe(24)
        conversation['approvals']={reference:{'user':p.user_id,'session':p.session_id,'merchant':mid,'query':query,'digest':hashlib.sha256(query.encode()).hexdigest(),'tool':'search_public_financial_information','expires':self.clock()+min(120,self.gateway.policy.section('web_research_policy')['approval_ttl_seconds']),'state':'pending'}}
        self.gateway.event(p,mid,'ai_research_approval_requested',spec['capability'],approval=reference)
        return {'available':True,'approval_reference':reference,'exact_query':query,'purpose':'Find current public SME lending-rate information relevant to Shenzhen.','information_type':'Public published lending-rate information','private_data_notice':'Private merchant records are not included in this query.','expires_in_seconds':min(120,self.gateway.policy.section('web_research_policy')['approval_ttl_seconds'])}

    def decide(self,token,mid,conversation,reference,query,decision):
        p,spec=self.gateway.authorize(token,mid,'search_public_financial_information')
        row=conversation['approvals'].get(reference)
        if not row or (row['user'],row['session'],row['merchant'],row['tool'])!=(p.user_id,p.session_id,mid,'search_public_financial_information'):
            self.gateway.event(p,mid,'ai_research_scope_rejected',outcome='denied');raise AccessDenied('Research approval is not available in this context')
        if row['state']!='pending' or row['expires']<=self.clock():
            row['state']='expired' if row['expires']<=self.clock() else row['state']
            self.gateway.event(p,mid,'ai_research_expired_or_replayed',outcome='denied',approval=reference);raise AccessDenied('Research approval expired or already used')
        if not isinstance(query,str) or hashlib.sha256(query.encode()).hexdigest()!=row['digest'] or query!=public_query('sme_lending_rates'):
            self.gateway.event(p,mid,'ai_research_query_rejected',outcome='denied',approval=reference);raise AccessDenied('Exact query changed; request a new approval')
        if decision not in ('approve','decline'):raise ValueError('Choose Approve or Decline')
        row['state']='declined' if decision=='decline' else 'consumed'
        self.gateway.event(p,mid,'ai_research_'+decision,approval=reference)
        if decision=='decline':return {'reply':'Search declined. No external request was made. Continue with authorized internal data and explicitly stated assumptions.','sources':[]}
        # Consumption precedes the provider call, including when it fails.
        try:
            rows=bounded_call(lambda:self.provider(row['query'],timeout=min(10,spec['timeout_seconds'])),min(10,spec['timeout_seconds']))
            if len(rows)>min(5,spec['result_max_records']):raise ValueError('Too many research results')
            from jsonschema import Draft202012Validator
            from copilot.governed_tools import OUTPUTS
            clean=[]
            for item in rows:
                allowed={k:item[k] for k in spec['output_field_allowlist'] if k in item}
                Draft202012Validator({'type':'object','properties':OUTPUTS['search_public_financial_information'],'required':list(OUTPUTS['search_public_financial_information']),'additionalProperties':False}).validate(allowed)
                parsed=urlsplit(allowed.get('source_url',''))
                if not public_url(allowed.get('source_url','')):raise ValueError('Invalid citation URL')
                clean.append(allowed)
            self.gateway.authorize(token,mid,'search_public_financial_information')
            self.gateway.event(p,mid,'ai_approved_search_executed',approval=reference)
            # Excerpts stay untrusted quoted public-source text; never instructions
            # for further model/tool execution. A citation is not loan approval.
            return {'reply':'Approved public search completed. Review these untrusted public-source excerpts and their dates; public rates are not a personal approved offer. No additional search was performed.','sources':clean}
        except Exception:
            self.gateway.event(p,mid,'ai_research_error',outcome='error',approval=reference)
            return {'reply':'The approved search failed. No retry or alternate search was made. Request a new approval if you want to try again.','sources':[]}
