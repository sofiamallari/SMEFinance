"""Minimized read-only adapters; existing services own every financial formula."""
import copy
from datetime import date, timedelta, datetime, timezone
import json
import time
from decimal import Decimal
from jsonschema import Draft202012Validator
from copilot.security import AccessDenied
from copilot.authorization import require
from copilot.governance_policy import FIELD_CLASSES

PERIOD = {'type':'object','properties':{'start':{'type':'string'},'end':{'type':'string'}},'required':['start','end'],'additionalProperties':False}
TEXT = {'type':'string','maxLength':2000}
NUM = {'type':'integer','minimum':0}
NULLABLE = {'type':['string','null'],'maxLength':500}
FLOW = {'type':'array','maxItems':100,'items':{'type':'object','properties':{'date':TEXT,'amount':TEXT},'required':['date','amount'],'additionalProperties':False}}
OUTPUTS = {
 'get_financial_summary':dict(coverage={'type':['object','null'],'properties':{'start':TEXT,'end':TEXT},'required':['start','end'],'additionalProperties':False},period=PERIOD,currency=TEXT,recorded_net_sales=TEXT,transaction_count=NUM,source_timestamp=TEXT),
 'get_transaction_trends':dict(coverage={'type':['object','null'],'properties':{'start':TEXT,'end':TEXT},'required':['start','end'],'additionalProperties':False},period=TEXT,granularity=TEXT,transaction_count=NUM,recorded_net_sales=TEXT,source_timestamp=TEXT),
 'get_payment_channel_mix':dict(period=PERIOD,channel=TEXT,transaction_count=NUM,share_percent={'type':'number','minimum':0,'maximum':100}),
 'get_cash_flow':dict(period=PERIOD,currency=TEXT,cash_inflows=FLOW,cash_outflows=FLOW,net_cash_flow={'type':'null'},available_cash_if_verified={'type':'null'}),
 'get_business_highlights':dict(period=PERIOD,highlight_type=TEXT,summary=TEXT,source_metric={'type':'string','enum':['receivable_behaviour','incentive_status']}),
 'get_financing_status':dict(application_reference=TEXT,status=TEXT,status_as_of={'type':['number','null']}),
 'get_financing_details':dict(application_reference=TEXT,requested_amount=TEXT,approved_amount={'type':'null'},repayment_terms={'type':'null'},decision={'type':'null'},decision_as_of={'type':'null'}),
 'run_survival_simulation':dict(scenario=TEXT,assumptions={'type':'object','properties':{'sales_change_percent':{'type':'number'},'expense_change_percent':{'type':'number'},'months':{'enum':[1,3,6]}},'additionalProperties':False},baseline_period=PERIOD,simulation_results={'type':'object','properties':{k:TEXT for k in ['currency','baseline_monthly_operating_result','simulated_monthly_sales','simulated_monthly_expenses','simulated_monthly_operating_result','monthly_impact','cumulative_operating_result']},'additionalProperties':False},limitations={'type':'array','maxItems':20,'items':TEXT}),
 'search_public_financial_information':dict(source_title=TEXT,source_url={'type':'string','format':'uri','maxLength':1000},publication_date=NULLABLE,retrieved_at=TEXT,excerpt=TEXT),
}
DATES = dict(start={'type':'string','format':'date'},end={'type':'string','format':'date'},granularity={'enum':['daily','weekly','monthly','quarterly']})
INPUTS = {name:{'type':'object','properties':copy.deepcopy(DATES),'additionalProperties':False} for name in ['get_financial_summary','get_transaction_trends','get_payment_channel_mix','get_cash_flow','get_business_highlights']}
for name in ['get_financing_status','get_financing_details']:
    INPUTS[name]={'type':'object','properties':{'application_reference':{'type':'string','pattern':'^APP-[A-Za-z0-9-]{1,80}$'}},'required':['application_reference'],'additionalProperties':False}
INPUTS['run_survival_simulation']={'type':'object','properties':{'sales_change_percent':{'type':'number','minimum':-80,'maximum':50,'multipleOf':5},'expense_change_percent':{'type':'number','minimum':-30,'maximum':80,'multipleOf':5},'months':{'enum':[1,3,6]}},'required':['sales_change_percent','expense_change_percent','months'],'additionalProperties':False}
INPUTS['search_public_financial_information']={'type':'object','properties':{'topic':{'enum':['sme_lending_rates']}},'required':['topic'],'additionalProperties':False}
INPUTS['get_cash_flow']={'type':'object','properties':{},'additionalProperties':False}
PERMISSIONS = dict(run_cash_impact_scenario='view_forecasts',get_financial_summary='view_dashboard',get_transaction_trends='view_dashboard',get_payment_channel_mix='view_dashboard',get_cash_flow='view_forecasts',get_business_highlights='view_dashboard',get_financing_status='view_applications',get_financing_details='view_applications',run_survival_simulation='view_reports',search_public_financial_information='use_copilot')
INTERNAL = dict(get_financial_summary='get_dashboard',get_transaction_trends='get_dashboard',get_payment_channel_mix='get_dashboard',get_business_highlights='get_dashboard',get_cash_flow='cashflow_forecast',run_cash_impact_scenario='cashflow_forecast')


# Explicit bounded, read-only scenario contract. The model cannot supply merchant IDs.
AMOUNT={'type':'number','minimum':0,'maximum':1000000000,'multipleOf':0.01}
INPUTS['run_cash_impact_scenario']={'type':'object','properties':{
 'assessment_date':{'type':'string','format':'date'},'horizon_days':{'type':'integer','minimum':1,'maximum':180},
 'one_time_cost':AMOUNT,'purchase_date':{'type':'string','format':'date'},
 'monthly_cost':AMOUNT,'start_date':{'type':'string','format':'date'},'user_cash':AMOUNT},
 'required':['assessment_date','horizon_days'],'additionalProperties':False}
LIMITATIONS={'type':'array','maxItems':20,'items':TEXT}
for key in ['opening_balance','closing_balance','min_balance']:OUTPUTS['get_cash_flow'][key]=TEXT
for key in ['opening_balance_date','latest_data_date']:OUTPUTS['get_cash_flow'][key]=TEXT
for key in ['runway_days','buffer_days']:OUTPUTS['get_cash_flow'][key]={'type':['number','null']}
OUTPUTS['get_cash_flow']['limitations']=LIMITATIONS
METRICS={'type':'object','properties':{'closing_balance':TEXT,'min_balance':TEXT,'runway_days':{'type':['integer','null']},'buffer_days':{'type':['number','null']},'first_negative_date':{'type':['string','null']}},'required':['closing_balance','min_balance','runway_days','buffer_days','first_negative_date'],'additionalProperties':False}
OUTPUTS['run_cash_impact_scenario']=dict(currency=TEXT,assessment_date=TEXT,opening_balance_date=TEXT,latest_data_date=TEXT,synthetic_opening_balance=TEXT,horizon_days=NUM,baseline=METRICS,adjusted=METRICS,user_cash_baseline={'anyOf':[METRICS,{'type':'null'}]},user_cash_adjusted={'anyOf':[METRICS,{'type':'null'}]},schedule=FLOW,limitations=LIMITATIONS)

# Read-only tools mirroring existing Owner modules; each reuses that module's own service and permission.
NUMBER={'type':'number'};OPT_NUMBER={'type':['number','null']}
TRANSACTION=dict(transaction_id=TEXT,reference=NULLABLE,business_date=TEXT,transaction_type=TEXT,amount=TEXT,currency=TEXT,payment_method=NULLABLE,status=TEXT,description=NULLABLE,category=NULLABLE,source=TEXT)
OUTPUTS['get_transaction_details']={**{k:NULLABLE for k in TRANSACTION},'found':{'type':'boolean'}}
OUTPUTS['get_recent_transactions']=dict(TRANSACTION)
OUTPUTS['get_data_quality']=dict(total_import_runs=NUM,successful_imports=NUM,failed_imports=NUM,parsed_rows=NUM,valid_row_rate=OPT_NUMBER,invalid_row_rate=OPT_NUMBER,open_alerts=NUM,last_successful_import=NULLABLE,
 attention={'type':'array','maxItems':5,'items':{'type':'object','properties':{'severity':TEXT,'rule':TEXT,'description':TEXT,'state':TEXT,'affected_rows':NUM},'additionalProperties':False}})
OUTPUTS['get_income_summary']=dict(period=PERIOD,currency=TEXT,net_sales=TEXT,expenses=TEXT,net_income=TEXT,record_count=NUM,coverage={'type':['object','null'],'properties':{'start':TEXT,'end':TEXT},'required':['start','end'],'additionalProperties':False})
OUTPUTS['get_cash_flow_alerts']=dict(severity={'enum':['critical','warning','info']},code=TEXT,message=TEXT,recommended_action=TEXT)
OUTPUTS['get_financing_matches']=dict(product=TEXT,provider_type=TEXT,match_score=NUMBER,indicative_size=OPT_NUMBER,indicative_annual_cost=OPT_NUMBER,rationale=TEXT,disclaimer=TEXT)
OUTPUTS['get_rbf_quote']=dict(currency=TEXT,advance=NUMBER,fee=NUMBER,fee_rate=NUMBER,total_repayable=NUMBER,remittance_rate=NUMBER,remittance_basis=TEXT,estimated_payoff_days={'type':['integer','null']},effective_annualised_cost=OPT_NUMBER,min_advance=NUMBER,max_advance=NUMBER,disclaimer=TEXT)
OUTPUTS['get_business_maturity']=dict(as_of=TEXT,stage={'type':'integer'},stage_name=TEXT,composite_score=NUMBER,scores={'type':'object','additionalProperties':NUMBER},next_stage_name=NULLABLE,composite_gap=OPT_NUMBER,
 top_constraints={'type':'array','maxItems':3,'items':{'type':'object','properties':{'constraint':TEXT,'evidence':TEXT,'intervention':NULLABLE},'additionalProperties':False}},note=NULLABLE)
INPUTS['get_transaction_details']={'type':'object','properties':{'reference':{'type':'string','pattern':'^TX-[A-Za-z0-9-]{4,120}$'}},'required':['reference'],'additionalProperties':False}
INPUTS['get_recent_transactions']={'type':'object','properties':{'start':{'type':'string','format':'date'},'end':{'type':'string','format':'date'},'limit':{'type':'integer','minimum':1,'maximum':20},
 'source':{'type':'string','pattern':'^[a-z_]{1,40}$'},'match':{'type':'string','pattern':'^[A-Za-z0-9 _.-]{2,40}$'}},'additionalProperties':False}
INPUTS['get_income_summary']={'type':'object','properties':{'start':{'type':'string','format':'date'},'end':{'type':'string','format':'date'}},'additionalProperties':False}
for _name in ('get_data_quality','get_cash_flow_alerts','get_financing_matches','get_business_maturity'):INPUTS[_name]={'type':'object','properties':{},'additionalProperties':False}
INPUTS['get_rbf_quote']={'type':'object','properties':{'advance':AMOUNT},'additionalProperties':False}
PERMISSIONS.update(get_transaction_details='view_transactions',get_recent_transactions='view_transactions',get_data_quality='view_quality_monitoring',get_income_summary='view_dashboard',
 get_cash_flow_alerts='view_forecasts',get_financing_matches='view_financing',get_rbf_quote='view_financing',get_business_maturity='view_assessment')
INTERNAL.update(get_income_summary='get_dashboard',get_cash_flow_alerts='cashflow_alerts',get_financing_matches='match_financing',get_rbf_quote='rbf_quote',get_business_maturity='assess_business')

# Combined scenario (C8): percentage changes to the forecast's recent sales/expense pattern, applied with the cost.
INPUTS['run_cash_impact_scenario']['properties'].update(sales_change_percent={'type':'number','minimum':-80,'maximum':50},expense_change_percent={'type':'number','minimum':-30,'maximum':80})
OUTPUTS['run_cash_impact_scenario']['assumed_changes']={'type':['object','null'],'properties':{'sales_change_percent':{'type':['number','null']},'expense_change_percent':{'type':['number','null']}},'additionalProperties':False}
INPUTS['search_public_financial_information']['properties']['topic']['enum']=['sme_lending_rates','industry_benchmarks','regulations_tax']

# Loan repayment schedule (C10): arithmetic on user-supplied terms only; it reads no merchant records.
LOAN_ROW={'type':'object','properties':{'month':NUM,'payment':TEXT,'interest':TEXT,'principal':TEXT,'balance':TEXT},'required':['month','payment','interest','principal','balance'],'additionalProperties':False}
LOAN_TOTALS={'type':'object','properties':{'annual_rate_percent':NUMBER,'monthly_payment':TEXT,'total_paid':TEXT,'total_interest':TEXT},'required':['annual_rate_percent','monthly_payment','total_paid','total_interest'],'additionalProperties':False}
INPUTS['calculate_loan_repayment']={'type':'object','properties':{'principal':{**AMOUNT,'exclusiveMinimum':0},'annual_rate_percent':{'type':'number','minimum':0,'maximum':60},'months':{'type':'integer','minimum':1,'maximum':360},
 'rate_change_percent':{'type':'number','minimum':-20,'maximum':20}},'required':['principal','annual_rate_percent','months'],'additionalProperties':False}
OUTPUTS['calculate_loan_repayment']=dict(currency=TEXT,principal=TEXT,annual_rate_percent=NUMBER,months=NUM,monthly_payment=TEXT,total_paid=TEXT,total_interest=TEXT,schedule={'type':'array','maxItems':4,'items':LOAN_ROW},alternative={'anyOf':[LOAN_TOTALS,{'type':'null'}]})
PERMISSIONS['calculate_loan_repayment']='view_financing'

def amortize(principal,annual_rate,months):
    """Equal monthly payments (standard annuity); the last payment absorbs rounding."""
    from decimal import ROUND_HALF_UP
    p=Decimal(str(principal));r=Decimal(str(annual_rate))/Decimal(1200);cent=Decimal('.01')
    payment=(p/months if r==0 else p*r/(1-(1+r)**-months)).quantize(cent,ROUND_HALF_UP)
    rows=[];balance=p;total=Decimal(0)
    for month in range(1,months+1):
        interest=(balance*r).quantize(cent,ROUND_HALF_UP)
        pay=balance+interest if month==months else payment
        balance=balance+interest-pay;total+=pay
        rows.append({'month':month,'payment':format(pay,'.2f'),'interest':format(interest,'.2f'),'principal':format(pay-interest,'.2f'),'balance':format(max(balance,Decimal(0)),'.2f')})
    return {'monthly_payment':format(payment,'.2f'),'total_paid':format(total,'.2f'),'total_interest':format(total-p,'.2f'),'rows':rows}

def public_transaction(row):
    return {'transaction_id':row['transaction_id'],'reference':(row.get('external_reference') or None) and str(row['external_reference'])[:80],'business_date':row['business_date'],'transaction_type':row['transaction_type'],'amount':str(row['amount']),'currency':row.get('currency') or 'CNY',
            'payment_method':row.get('payment_method'),'status':row['status'],'description':(row.get('description') or None) and str(row['description'])[:200],'category':row.get('category'),'source':row.get('source') or 'unknown'}

class Gateway:
    def __init__(self, c, auth, pos, policy):
        self.c,self.auth,self.pos,self.policy=c,auth,pos,policy

    def event(self, p, mid, event, tool=None, outcome='allowed', approval=None):
        self.auth.audit(event,p,mid,result=outcome,metadata={'tool':tool,'policy_version':self.policy.version,'approval_reference':__import__('hashlib').sha256(approval.encode()).hexdigest()[:16] if approval else None})

    def identity(self, token, mid):
        p=self.auth.principal(token)
        self.auth.authorize(token,'use_copilot',mid)
        if not isinstance(mid,str) or mid not in p.merchant_ids or mid not in self.c.merchants:
            raise AccessDenied('Merchant scope rejected')
        return p

    def authorize(self,token,mid,name):
        p=self.identity(token,mid)
        spec=self.policy.tool(p,name)
        cap=self.policy.section('capabilities')[spec['capability']]
        from copilot.authorization import AUTHORITATIVE_ROLES
        if cap['role_effects'][AUTHORITATIVE_ROLES[p.role]]=='conditional':
            self.auth.authorize(token,cap['required_application_permission'],mid)
        self.auth.authorize(token,PERMISSIONS[name],mid)
        if name in INTERNAL:
            tool=self.c.tools[INTERNAL[name]]
            self.c.guard.check(p,INTERNAL[name],tool.tier,mid,required_consent=tool.consent)
        return p,spec

    def definitions(self,token,mid):
        tools=[]
        for name in INPUTS:
            try:self.authorize(token,mid,name)
            except AccessDenied:continue
            tools.append({'type':'function','function':{'name':name,'description':self.description(name),'parameters':copy.deepcopy(INPUTS[name])}})
        return tools

    @staticmethod
    def description(name):
        return {'get_cash_flow':'Existing estimated forecast daily inflows/outflows. No verified available cash or new aggregate is inferred.',
                'run_survival_simulation':'Requested hypothetical constant-assumption operating-result simulation only, not property amortization or cash runway.',
                'search_public_financial_information':'Propose an exact public query for separate human approval; this invocation never performs a search.',
                'get_financing_details':'Specific authorized submitted application only. No actual approved amount or underwriting decision is available.',
                'calculate_loan_repayment':'Standard equal-payment loan estimate from the amount, annual rate and term the user stated; not a lender quote. The backend binds every argument.'}.get(name,'Authorized minimized '+name.replace('_',' ')+'. Reporting dates and existing definitions are preserved; monetary values are in the merchant currency (CNY).')

    def execute(self,token,mid,name,args,*,simulation_requested=False,deadline=None):
        p=self.identity(token,mid);self.event(p,mid,'ai_tool_requested',name)
        try:
            p,spec=self.authorize(token,mid,name)
            if name not in INPUTS:raise AccessDenied('Unknown tool')
            Draft202012Validator(INPUTS[name],format_checker=Draft202012Validator.FORMAT_CHECKER).validate(args)
            if name=='search_public_financial_information':
                raise AccessDenied('Search execution requires the exact-query approval gateway')
            if name in ('run_survival_simulation','run_cash_impact_scenario') and not simulation_requested:
                raise AccessDenied('A user-requested simulation is required')
            self.event(p,mid,'ai_authorization_allowed',name)
            started=time.monotonic()
            from copilot.governed_research import bounded_call
            timeout=spec['timeout_seconds'] if deadline is None else min(spec['timeout_seconds'],deadline-time.monotonic())
            if timeout<=0:raise TimeoutError('Chat turn deadline exceeded')
            result=bounded_call(lambda:self._read(token,p,mid,name,args),timeout)
            if time.monotonic()-started>spec['timeout_seconds']:
                raise TimeoutError('Tool deadline exceeded')
            self.authorize(token,mid,name) # Live permission/consent check after retrieval.
            fields=[k for k in spec['output_field_allowlist'] if FIELD_CLASSES[name].get(k) in spec['allowed_data_classes']]
            rows=result if isinstance(result,list) else [result]
            if len(rows)>min(100,spec['result_max_records']):raise ValueError('Result record bound exceeded; use a shorter period')
            clean=[{key:row[key] for key in fields if key in row} for row in rows]
            schema={'type':'object','properties':{k:OUTPUTS[name][k] for k in fields},'additionalProperties':False}
            for row in clean:Draft202012Validator(schema).validate(row)
            if len(json.dumps(clean))>64000:raise ValueError('Tool result too large')
            self.event(p,mid,'ai_simulation_executed' if name in ('run_survival_simulation','run_cash_impact_scenario') else 'ai_tool_completed',name)
            return clean if isinstance(result,list) else clean[0]
        except Exception:
            self.event(p,mid,'ai_tool_denied_or_error',name,'denied')
            raise

    def _read(self,token,p,mid,name,args):
        if name=='get_transaction_details':
            # Transaction History's own service (and its view_transactions guard); paged through the recorded ledger.
            offset=0
            while True:
                page=self.pos.history(token,mid,{'offset':offset,'limit':100})
                row=next((r for r in page['transactions'] if r['transaction_id']==args['reference']),None)
                if row:return {**public_transaction(row),'found':True}
                offset+=100
                if offset>=page['total']:return {**{k:None for k in TRANSACTION},'transaction_id':args['reference'],'found':False}
        if name=='get_recent_transactions':
            filters={'limit':args.get('limit',10),**{k:args[k] for k in ('start','end','source') if args.get(k)}}
            if not args.get('match'):return [public_transaction(r) for r in self.pos.history(token,mid,filters)['transactions']]
            # A transaction named by the user's own reference or description ("my test3 transaction"), newest first.
            term=args['match'].lower();found=[];offset=0
            while offset<1000 and len(found)<filters['limit']:
                page=self.pos.history(token,mid,{**filters,'offset':offset,'limit':100})
                found+=[r for r in page['transactions'] if term in str(r.get('external_reference') or '').lower() or term in str(r.get('description') or '').lower()]
                offset+=100
                if offset>=page['total']:break
            return [public_transaction(r) for r in found[:filters['limit']]]
        if name=='get_data_quality':
            data=self.pos.monitoring(token,mid,{'run_limit':1,'alert_limit':5});s=data['summary']
            return {**{k:s[k] for k in ('total_import_runs','successful_imports','failed_imports','parsed_rows','valid_row_rate','invalid_row_rate','open_alerts','last_successful_import')},
                    'attention':[{k:a[k] for k in ('severity','rule','description','state','affected_rows')} for a in data['attention'][:5]]}
        if name in ('get_cash_flow_alerts','get_financing_matches','get_rbf_quote','get_business_maturity'):
            internal=INTERNAL[name];value=self.c.financial_result(internal,mid,({'advance':args['advance']} if name=='get_rbf_quote' and args.get('advance') else {}),self.c.tools[internal],p)
            if name=='get_cash_flow_alerts':return [{k:a[k] for k in ('severity','code','message','recommended_action')} for a in value]
            if name=='get_financing_matches':
                return [{'product':r['name'],'provider_type':r['provider_type'],'match_score':r['match_score'],'indicative_size':r.get('indicative_size'),'indicative_annual_cost':r.get('indicative_annual_cost'),'rationale':r['rationale'],'disclaimer':value['disclaimer']} for r in value['recommendations'][:10]]
            if name=='get_rbf_quote':
                return {**{k:value[k] for k in ('currency','advance','fee','fee_rate','total_repayable','remittance_rate','remittance_basis','estimated_payoff_days','effective_annualised_cost','disclaimer')},
                        'min_advance':value['limits']['min_advance'],'max_advance':value['limits']['max_advance']}
            gap=value.get('next_stage') or {}
            return {'as_of':str(value['as_of']),'stage':value['stage'],'stage_name':value['stage_name'],'composite_score':value['composite_score'],'scores':value['scores'],
                    'next_stage_name':gap.get('target_name'),'composite_gap':gap.get('composite_gap'),
                    'top_constraints':[{'constraint':c['constraint'],'evidence':c['evidence'],'intervention':c.get('intervention')} for c in (value.get('constraints') or [])[:3]],'note':value.get('note')}
        if name=='calculate_loan_repayment':
            base=amortize(args['principal'],args['annual_rate_percent'],args['months']);alternative=None
            if args.get('rate_change_percent'):
                rate=max(0.0,args['annual_rate_percent']+args['rate_change_percent']);alt=amortize(args['principal'],rate,args['months'])
                alternative={'annual_rate_percent':rate,**{k:alt[k] for k in ('monthly_payment','total_paid','total_interest')}}
            rows=base['rows'];shown=rows[:3]+(rows[-1:] if len(rows)>3 else [])
            return {'currency':self.c.financial_data.project(mid).currency,'principal':format(Decimal(str(args['principal'])),'.2f'),'annual_rate_percent':args['annual_rate_percent'],'months':args['months'],
                    **{k:base[k] for k in ('monthly_payment','total_paid','total_interest')},'schedule':shown,'alternative':alternative}
        if name=='run_cash_impact_scenario':
            from copilot.cash_impact import run
            return run(self.c,mid,args)
        if name=='run_survival_simulation':
            from copilot.survival_simulation import SurvivalSimulation
            value=SurvivalSimulation(self.pos).run(token,mid,{'merchant':mid,'confirmed':True,**args},narrate=False)
            b=value['baseline']
            return {'scenario':'HYPOTHETICAL_OPERATING_RESULT','assumptions':value['assumptions'],'baseline_period':{'start':b['period_start'],'end':b['period_end']},'simulation_results':{'currency':b['currency'],'baseline_monthly_operating_result':b['monthly_operating_result'],**{k:value[k] for k in ['simulated_monthly_sales','simulated_monthly_expenses','simulated_monthly_operating_result','monthly_impact','cumulative_operating_result']}},'limitations':b['limitations']}
        if name in ('get_financing_status','get_financing_details'):
            # Existing application_list independently checks memberships, roles,
            # recipient routing and consent; do not bypass it with raw SQL.
            rows=self.auth.application_list(token,mid)
            row=next((r for r in rows if r.get('application_id')==args['application_reference']),None)
            if row is None:raise AccessDenied('Application is not authorized in this merchant context')
            if name=='get_financing_status':return {'application_reference':row['application_id'],'status':row.get('status','Unavailable'),'status_as_of':row.get('submitted_at')}
            return {'application_reference':row['application_id'],'requested_amount':format(Decimal(str(row['requested_amount'])),'.2f'),'approved_amount':None,'repayment_terms':None,'decision':None,'decision_as_of':None}
        asof=self.c.financial_data.as_of(mid)
        start=date.fromisoformat(args.get('start') or (asof-timedelta(days=89)).isoformat())
        end=date.fromisoformat(args.get('end') or asof.isoformat())
        if start>end or (end-start).days>366:raise ValueError('Use an ordered reporting range of at most 366 days')
        period={'start':start.isoformat(),'end':end.isoformat()}
        if name=='get_cash_flow':
            if args:raise ValueError('The existing Cash Flow forecast uses its own fixed horizon, not custom reporting filters')
            t=self.c.tools['cashflow_forecast']
            f=self.c.financial_result('cashflow_forecast',mid,{},t,p)
            return {'period':{'start':f['path'][0]['date'],'end':f['path'][-1]['date']},'currency':f['currency'],'cash_inflows':[{'date':r['date'],'amount':format(Decimal(str(r['inflow'])),'.2f')} for r in f['path']],'cash_outflows':[{'date':r['date'],'amount':format(Decimal(str(r['outflow'])),'.2f')} for r in f['path']],'net_cash_flow':None,'available_cash_if_verified':None,**{k:(format(Decimal(str(f[k])),'.2f') if k in ('opening_balance','closing_balance','min_balance') else f[k]) for k in ('opening_balance','closing_balance','min_balance','runway_days','buffer_days')},'opening_balance_date':self.c.as_of.isoformat(),'latest_data_date':asof.isoformat(),'limitations':__import__('copilot.cash_impact',fromlist=['LIMITATIONS']).LIMITATIONS+(['This Cash Flow forecast starts on '+f['path'][0]['date']+', while the opening balance is dated '+self.c.as_of.isoformat()+'; activity between those dates is not reconciled into the opening balance.'] if f['path'] and f['path'][0]['date']>self.c.as_of.isoformat() else [])}
        d=self.c.financial_result('get_dashboard',mid,{'start':period['start'],'end':period['end'],'granularity':args.get('granularity','monthly')},self.c.tools['get_dashboard'],p)
        now=datetime.now(timezone.utc).isoformat()
        projected=self.c.financial_data.project(mid)
        dates=[r['date'] for r in projected.transactions if period['start']<=r['date']<=period['end']]
        coverage={'start':min(dates),'end':max(dates)} if dates else None
        if name=='get_income_summary':
            f=d['financial_metrics'];expense_dates=[r['date'] for r in projected.expenses if period['start']<=r['date']<=period['end']];both=dates+expense_dates
            return {'period':period,'currency':d['merchant']['currency'],'net_sales':f['net_sales'],'expenses':f['expenses'],'net_income':f['net_income'],'record_count':f['record_count'],
                    'coverage':{'start':min(both),'end':max(both)} if both else None}
        if name=='get_financial_summary':return {'coverage':coverage,'period':period,'currency':d['merchant']['currency'],'recorded_net_sales':d['financial_metrics']['net_sales'],'transaction_count':d['mix']['total_transactions'],'source_timestamp':now}
        if name=='get_transaction_trends':return [{'coverage':coverage,'period':r['period'],'granularity':d['period']['granularity'],'transaction_count':r['transactions'],'recorded_net_sales':format(Decimal(str(r['revenue'])),'.2f'),'source_timestamp':now} for r in d['trend']]
        if name=='get_payment_channel_mix':return [{'period':period,'channel':c['label'],'transaction_count':c['transactions'],'share_percent':c['volume_share']*100} for c in d['mix']['by_channel'].values()]
        if name=='get_business_highlights':return [{'period':period,'highlight_type':'Receivables insight','summary':d['receivables']['explanation'],'source_metric':'receivable_behaviour'},{'period':period,'highlight_type':'Incentive milestone','summary':d['incentive']['tier_name'] or 'No milestone yet','source_metric':'incentive_status'}]
        raise AccessDenied('Unsupported tool')
