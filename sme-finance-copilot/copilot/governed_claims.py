"""Source-linked financial statements; numeric equality never grants provenance."""
import json
import re
from datetime import date, datetime
from decimal import Decimal
from copilot.currency_policy import format_money


class ClaimError(ValueError):
    """Only this sanitized code, never model text, belongs in diagnostic events."""
    def __init__(self,code):self.code=code;super().__init__('Financial response could not be verified')


# Public contract names map to existing server-owned provenance records.
CLAIM_KINDS = {'user_date':'user_assumption', 'deterministic_result':'derived_calculation',
               'simulation_output':'simulation_result'}
RESPONSE_SCHEMA = {'type':'object','properties':{'segments':{'type':'array','minItems':1,'maxItems':16,
    'items':{'anyOf':[
        {'type':'object','properties':{'text':{'type':'string','pattern':r'^[^0-9]*$'}},'required':['text'],'additionalProperties':False},
        {'type':'object','properties':{'claim':{'type':'string'},'kind':{'type':'string','enum':[
            'user_assumption','backend_fact','derived_calculation','simulation_result','external_fact','data_limitation','recommendation','unsupported_claim']}},
         'required':['claim','kind'],'additionalProperties':False}]}}},'required':['segments'],'additionalProperties':False}

def public_records(records):
    return {key:{**record,'kind':CLAIM_KINDS.get(record['kind'],record['kind'])}
            for key,record in records.items()}


def day(value):
    try:return date.fromisoformat(value).strftime('%B %d, %Y').replace(' 0',' ')
    except (ValueError,TypeError):return str(value)


def period(value):
    return day(value['start'])+' to '+day(value['end'])


def money(value,currency='CNY'):
    return format_money(value,currency)+(' CNY (RMB)' if currency=='CNY' else ' '+currency)


# Compact backend renderings for inline chat; full `display` text stays in Sources & Tools.
def cash(value,currency='CNY'):
    return format_money(value,currency)


def span_text(value):
    """'October 2026', 'October 1-16, 2026' or a full range; always backend formatted."""
    try:start,end=date.fromisoformat(value['start']),date.fromisoformat(value['end'])
    except (KeyError,TypeError,ValueError):return str(value)
    import calendar
    if (start.year,start.month)==(end.year,end.month):
        if start.day==1 and end.day==calendar.monthrange(end.year,end.month)[1]:return start.strftime('%B %Y')
        if start==end:return day(value['start'])
        return start.strftime('%B ')+str(start.day)+'–'+str(end.day)+end.strftime(', %Y')
    return day(value['start'])+' to '+day(value['end'])


def days_in(value):
    return (date.fromisoformat(value['end'])-date.fromisoformat(value['start'])).days+1


def coverage_gap(value):
    """True when returned record dates do not span the requested period."""
    coverage=value.get('coverage')
    return 'coverage' in value and (not coverage or coverage['start']>value['period']['start'] or coverage['end']<value['period']['end'])


def purchase_context(text,previous=None):
    """Only extract explicitly stated assumptions; never infer liquidity or costs."""
    result=dict(previous or {})
    if re.search(r'\b(?:state|pretend|fabricate|invent|assume|imagine)\b.{0,90}\b(?:cash|balance)\b',text,re.I):return result
    item=re.search(r'\b(oven|equipment|inventory|warehouse(?: lot)?|property|shop|branch|investment|machinery|vehicle)\b',text,re.I)
    if item:result['item']=item.group(0).lower()
    amounts=list(re.finditer(r'(RMB|CNY|USD|PHP|ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥|ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¿ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)',text,re.I))
    if amounts:
        first=amounts[0];currency=first.group(1).upper()
        clause=re.split(r'[.!?;\n]',text[:first.start()])[-1]
        cash_statement=bool(re.search(r'(?:available cash|cash balance|cash on hand|bank balance|cash reserves)(?:\s+(?:is|of|are|equals|totals))?\s*[:=]?\s*$',clause,re.I) or (re.search(r'\b(?:I|we)\s+(?:currently\s+)?have\s*$',clause,re.I) and re.match(r'\s+(?:in cash|cash available|cash on hand)\b',text[first.end():],re.I)))
        extra=bool(result.get('price') and re.search(r'installation|delivery|setup|additional',text[max(0,first.start()-35):first.start()],re.I))
        if cash_statement and not re.search(r'\b(?:state|pretend|fabricate|invent|assume|imagine|hypothetical)\b',clause,re.I):
            result['reported_cash']=format(Decimal(first.group(2).replace(',','')),'.2f')
            result['reported_cash_currency']='CNY' if currency in ('RMB','CNY','ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥','ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¿ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥') else currency
        elif extra:
            result['extra_costs']='additional costs stated by user; not verified or summed'
            result['additional_cost']=format(Decimal(first.group(2).replace(',','')),'.2f')
        elif not result.get('price') or re.search(r'price|worth|oven|equipment|inventory|warehouse|purchase',text,re.I):
            amount=Decimal(first.group(2).replace(',',''))
            scale=re.match(r'\s*(thousand|million|billion)\b',text[first.end():],re.I)
            if scale:amount*=Decimal({'thousand':1000,'million':1000000,'billion':1000000000}[scale.group(1).lower()])
            result['price']=format(amount,'.2f')
            result['currency']='CNY' if currency in ('RMB','CNY','ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥','ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¿ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥') else currency
    for amount in amounts:
        before=text[max(0,amount.start()-35):amount.start()]
        label='down_payment' if re.search(r'down[- ]?payment',before,re.I) else 'additional_cost' if re.search(r'installation|delivery|setup|additional|acquisition',before,re.I) else None
        if label:
            result[label]=format(Decimal(amount.group(2).replace(',','')),'.2f')
            code=amount.group(1).upper();result[label+'_currency']='CNY' if code in ('RMB','CNY','ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥','ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¿ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥') else code
            if label=='additional_cost':result['extra_costs']='additional costs stated by user; not verified or summed'
    dates=re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',text,re.I)
    if dates:
        parsed=[]
        for raw in dates:
            try:parsed.append(date.fromisoformat(raw).isoformat() if re.match(r'\d{4}-',raw) else datetime.strptime(raw.replace(',',''),'%B %d %Y').date().isoformat())
            except ValueError:result['date_issue']=True
        if len(set(parsed))==1:result['assessment_date']=parsed[0];result.pop('date_issue',None)
        elif len(set(parsed))>1:result['date_issue']=True
    # A short answer to an existing purchase question selects funding only;
    # it never supplies an available-cash amount or authorizes a payment.
    if previous and previous.get('item'):
        choice=text.strip().lower().rstrip('.!?')
        if choice in ('cash','in cash','cash please'):result['funding']='cash'
        elif choice in ('financing','finance','through financing'):result['funding']='financing'
    if re.search(r'\b(?:pay|paid|paying|fund(?:ed)?)\s+(?:in |with |by )?cash\b|cash[- ]funded|pay upfront|buy outright',text,re.I):result['funding']='cash'
    elif re.search(r'\bfinanced?\b|use financing|with financing|bank loan|borrow',text,re.I):result['funding']='financing'
    if re.search(r'(?:no|without) (?:additional|extra|installation|delivery|setup) costs|includes? (?:installation|delivery|all costs)|all[- ]in',text,re.I):result['extra_costs']='included or none, as stated by the user'
    elif re.search(r'(installation|delivery|setup|additional|acquisition).{0,30}(?:RMB|CNY|ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¥|\d)',text,re.I):result['extra_costs']='additional costs stated by user; not verified or summed'
    term=re.search(r'\b\d+\s+(?:months?|years?)\b',text,re.I)
    if term:result['repayment_term']=term.group(0)
    return result


def assumptions(context):
    records={}
    if context.get('price'):
        records['user.purchase_price']={'kind':'user_assumption','metric':'proposed_purchase_price','value':context['price'],'currency':context['currency'],'display':'Your proposed '+context.get('item','purchase')+' price is '+money(context['price'],context['currency'])+' (your assumption, not a verified business expense).'}
    if context.get('assessment_date'):
        records['user.assessment_date']={'kind':'user_date','metric':'requested_assessment_date','value':context['assessment_date'],'display':'Requested assessment date: '+day(context['assessment_date'])+(' (resolved using '+context['assessment_timezone']+'; not a verified cash snapshot).' if context.get('assessment_date_source')=='backend_business_date' else ' (user-specified; not a verified cash snapshot).')}
    for metric,label in [('additional_cost','Additional purchase cost'),('down_payment','Proposed down payment')]:
        if context.get(metric):
            code=context.get(metric+'_currency',context.get('currency','CNY'))
            records['user.'+metric]={'kind':'user_assumption','metric':metric,'value':context[metric],'currency':code,'display':label+': '+money(context[metric],code)+' (user-stated assumption; not verified or automatically summed).'}
    if context.get('reported_cash'):
        records['user.reported_cash']={'kind':'user_assumption','metric':'user_reported_cash','value':context['reported_cash'],'currency':context.get('reported_cash_currency','CNY'),'display':'User-reported cash: '+money(context['reported_cash'],context.get('reported_cash_currency','CNY'))+' (unverified assumption; not a backend cash balance).'}
    return records


def tool_claims(name,value,currency='CNY',prefix='fact'):
    """Only caller-owned, already authorized gateway results may enter here."""
    records={}
    def add(key,metric,number,display,kind='backend_fact',**provenance):
        records[prefix+'.'+key]={'kind':kind,'metric':metric,'value':str(number),'source':name,'display':display,**provenance}
    if name=='get_financial_summary':
        requested=value['period'];currency=value['currency'];gap=coverage_gap(value)
        requires=[prefix+'.coverage_gap'] if gap else []
        add('net_sales','recorded_net_sales',value['recorded_net_sales'],'Recorded net sales: '+money(value['recorded_net_sales'],currency)+', for '+period(requested)+'. Revenue is not profit or available cash.',currency=currency,period=requested,
            brief='Recorded net sales for '+span_text(requested)+' are '+cash(value['recorded_net_sales'],currency)+'.',requires=requires)
        add('transaction_count','sales_payment_transaction_count',value['transaction_count'],'Sales/payment transaction count: '+format(value['transaction_count'],',')+', for '+period(requested)+'. Transaction volume is not cash balance.',period=requested,
            brief=format(value['transaction_count'],',')+' sales transaction'+('' if value['transaction_count']==1 else 's')+' were recorded for '+span_text(requested)+'.',requires=requires)
        if value.get('digital_capture_percent') is not None:
            share=format(value['digital_capture_percent'],'.1f')
            add('digital_capture','digital_capture_share',share,'Digital Capture for '+period(requested)+': '+share+'% of recorded net sales were paid digitally (card, QR, tap-to-pay, e-wallet or pay link); the rest was cash.','deterministic_result',period=requested,
                brief='Digital Capture for '+span_text(requested)+' is '+share+'%: that share of your sales was paid digitally rather than in cash.',requires=requires)
            if value.get('digital_sales') is not None:
                # The amount behind the share: "how much was paid digitally", "translate it to its amount".
                add('digital_sales','digital_sales_amount',value['digital_sales'],'Digital payments received for '+period(requested)+': '+money(value['digital_sales'],currency)+' ('+share+'% of recorded net sales of '+money(value['recorded_net_sales'],currency)+'); cash sales: '+money(value['cash_sales'],currency)+'. Revenue is not profit or available cash.',currency=currency,period=requested,
                    brief='Digital payments received for '+span_text(requested)+' were '+cash(value['digital_sales'],currency)+' ('+share+'% of recorded net sales of '+cash(value['recorded_net_sales'],currency)+'); cash sales were '+cash(value['cash_sales'],currency)+'.',requires=requires)
        if 'coverage' in value:
            coverage=value['coverage']
            display=('Available sales/payment record dates within the requested period: '+period(coverage)+'. This is record coverage, not proof of complete business activity.' if coverage else 'No sales/payment records were returned within this requested period; other periods may contain records.')
            add('coverage','sales_record_coverage','coverage',display,period=requested,
                brief=('Records cover all of '+span_text(requested)+'.' if not gap else 'Records for '+span_text(requested)+' only cover '+span_text(coverage)+'.' if coverage else 'No sales records were found for '+span_text(requested)+'.'))
        if gap:
            add('coverage_gap','incomplete_record_coverage','incomplete',('Requested period '+period(requested)+'; returned record dates '+(period(value['coverage']) if value['coverage'] else 'none')+'. Some transactions may not be imported, so recorded totals may understate activity for this period.'),'data_limitation',period=requested,
                brief=('Records for '+span_text(requested)+' only cover '+span_text(value['coverage'])+', so some transactions may not be imported yet.' if value['coverage'] else 'No records were found for '+span_text(requested)+', so transactions may not be imported yet.'))
    elif name=='run_survival_simulation':
        r=value['simulation_results'];span=value['baseline_period'];currency=r['currency']
        for metric,label in [('baseline_monthly_operating_result','Baseline monthly operating result'),('simulated_monthly_operating_result','Simulated monthly operating result'),('cumulative_operating_result','Cumulative simulated operating result')]:
            kind='deterministic_result' if metric.startswith('baseline') else 'simulation_output'
            brief={'baseline_monthly_operating_result':'Your baseline monthly operating result is '+cash(r[metric],currency)+'.',
                   'simulated_monthly_operating_result':'Under these assumptions, the simulated monthly operating result is '+cash(r[metric],currency)+' (hypothetical, not verified cash).',
                   'cumulative_operating_result':'Over the simulated period, the cumulative operating result is '+cash(r[metric],currency)+' (hypothetical, not verified cash).'}[metric]
            add(metric,metric,r[metric],label+': '+money(r[metric],currency)+'. Baseline period: '+period(span)+'. Hypothetical operating-result calculation; not verified cash or purchase affordability.',kind,currency=currency,period=span,brief=brief)
    elif name=='run_cash_impact_scenario':
        records.update(scenario_claims(value,prefix))
    elif name=='get_cash_flow':
        add('synthetic_basis','synthetic_cash_basis','synthetic','The forecast starts from the opening balance recorded in the app as of '+day(value['opening_balance_date'])+'. It is an estimate and is not reconciled with your bank account.','data_limitation',period=value['period'],
            brief='This is a forecast estimate and is not reconciled with your bank balance.')
        briefs={'opening_balance':'The forecast starts from an opening balance of '+cash(value['opening_balance'],value['currency'])+'.',
                'closing_balance':'The forecast projects a closing balance of '+cash(value['closing_balance'],value['currency'])+' on '+day(value['period']['end'])+'.',
                'min_balance':'The lowest projected balance is '+cash(value['min_balance'],value['currency'])+'.'}
        for metric,label in [('opening_balance','Opening balance as of '+day(value['opening_balance_date'])),('closing_balance','Projected closing balance'),('min_balance','Minimum projected balance')]:
            add(metric,metric,value[metric],label+': '+money(value[metric],value['currency'])+'. Forecast estimate, not reconciled with your bank.','derived_calculation' if metric!='opening_balance' else 'backend_fact',currency=value['currency'],period=value['period'],
                brief=briefs[metric],requires=[prefix+'.synthetic_basis'])
        # The three headline figures the Cash Flow page shows, as one backend-rendered sentence.
        add('overview','cash_flow_overview','overview','Cash-flow forecast '+period(value['period'])+': opening balance '+money(value['opening_balance'],value['currency'])+' (dated '+day(value['opening_balance_date'])+'), minimum projected balance '+money(value['min_balance'],value['currency'])+', projected closing balance '+money(value['closing_balance'],value['currency'])+'.','derived_calculation',currency=value['currency'],period=value['period'],
            brief='Your cash-flow forecast starts from an opening balance of '+cash(value['opening_balance'],value['currency'])+', with a lowest projected balance of '+cash(value['min_balance'],value['currency'])+' and a projected closing balance of '+cash(value['closing_balance'],value['currency'])+' on '+day(value['period']['end'])+'.',requires=[prefix+'.synthetic_basis'])
        add('composition','cash_flow_composition','composition','Method: weekday-seasonal moving average of recent sales inflows and included operating outflows (supplies, operating, household draw), plus scheduled supplier payables, expected receivables and monthly debt service. Expenses classified "other" and existing payroll are not separately covered.','backend_fact',period=value['period'],
            brief='The forecast projects daily inflows from your recent sales pattern and outflows from typical operating expenses, scheduled supplier payments and loan repayments; some expense types and existing payroll are not fully covered.')
        if value.get('buffer_days') is not None:add('buffer_days','buffer_days',value['buffer_days'],'Expense-coverage estimate: '+str(value['buffer_days'])+' days. Uses historical included variable expenses and averaged debt service; not a verified liquidity buffer.','derived_calculation',period=value['period'],
            brief='The opening balance covers about '+str(value['buffer_days'])+' days of typical expenses.',requires=[prefix+'.synthetic_basis'])
        if value.get('runway_days') is not None:
            negative=(date.fromisoformat(value['period']['start'])+__import__('datetime').timedelta(days=value['runway_days']-1)).isoformat()
            add('runway_days','runway_days',value['runway_days'],'First projected negative balance on day '+str(value['runway_days'])+' ('+day(negative)+').','derived_calculation',period=value['period'],
                brief='The forecast first goes negative around '+day(negative)+'.',requires=[prefix+'.synthetic_basis'])
        add('limitations','forecast_limitations','limitations',' '.join(value['limitations']),period=value['period'],brief=value['limitations'][-1] if value['limitations'] else 'Forecast limitations apply.')
        for field,label in [('cash_inflows','Estimated inflow'),('cash_outflows','Estimated outflow')]:
            for index,row in enumerate(value[field][:3]):
                add(field+str(index),field,row['amount'],label+' on '+day(row['date'])+': '+money(row['amount'],value['currency'])+'. Forecast result, not actual available cash.', 'deterministic_result',currency=value['currency'],period=value['period'],
                    brief=label+' on '+day(row['date'])+': '+cash(row['amount'],value['currency'])+'.',requires=[prefix+'.synthetic_basis'])
    elif name=='get_transaction_trends':
        for index,row in enumerate(value):
            add('sales'+str(index),'recorded_net_sales',row['recorded_net_sales'],'Recorded net sales for '+row['period']+': '+money(row['recorded_net_sales'],currency)+'. Sales are not profit or cash.',currency=currency,period=row['period'],
                brief='Recorded net sales for '+row['period']+' were '+cash(row['recorded_net_sales'],currency)+'.')
            add('count'+str(index),'sales_payment_transaction_count',row['transaction_count'],'Sales/payment count for '+row['period']+': '+format(row['transaction_count'],',')+'.',period=row['period'],
                brief=format(row['transaction_count'],',')+' sales transactions were recorded for '+row['period']+'.')
            if row.get('recorded_expenses') is not None:
                add('expenses'+str(index),'recorded_expenses',row['recorded_expenses'],'Recorded expenses for '+row['period']+': '+money(row['recorded_expenses'],currency)+'.',currency=currency,period=row['period'],
                    brief='Recorded expenses for '+row['period']+' were '+cash(row['recorded_expenses'],currency)+'.')
    elif name=='get_payment_channel_mix':
        for index,row in enumerate(value):
            add('share'+str(index),'transaction_volume_share',str(row['share_percent']),row['channel']+': '+format(row['share_percent'],'.2f')+'% of transaction volume, not revenue share.','deterministic_result',period=row['period'],
                brief=row['channel']+' made up '+format(row['share_percent'],'.2f')+'% of transactions (by count, not revenue).')
            if row.get('revenue_share_percent') is not None:
                add('revenue_share'+str(index),'revenue_share',str(row['revenue_share_percent']),row['channel']+': '+format(row['revenue_share_percent'],'.2f')+'% of recorded revenue.','deterministic_result',period=row['period'],
                    brief=row['channel']+' brought in '+format(row['revenue_share_percent'],'.2f')+'% of your revenue.')
        rows=[r for r in value if r.get('revenue') is not None]
        if rows:
            # How the period's sales were paid, method by method (Dashboard Channel Performance).
            c=rows[0].get('currency') or currency;total=sum((Decimal(r['revenue']) for r in rows),Decimal(0));requested=rows[0]['period']
            parts=[r['channel']+' '+cash(r['revenue'],c)+' ('+format(r['revenue_share_percent'],'.2f')+'%)' for r in rows]
            add('channel_split','revenue_by_channel',format(total,'.2f'),'Recorded sales for '+period(requested)+' by payment method: '+'; '.join(r['channel']+' '+money(r['revenue'],c)+' ('+format(r['revenue_share_percent'],'.2f')+'% of revenue, '+format(r['transaction_count'],',')+' transactions)' for r in rows)+'. Total '+money(format(total,'.2f'),c)+'.','deterministic_result',currency=c,period=requested,
                brief='Recorded sales of '+cash(format(total,'.2f'),c)+' for '+span_text(requested)+' were paid by: '+', '.join(parts)+'.')
    elif name in ('get_financing_status','get_financing_details'):
        reference=value['application_reference']
        if name=='get_financing_status':add('status','submitted_application_status',value['status'],'Application '+reference+': '+value['status']+' (submission status; not credit approval).',application_reference=reference,
            brief='Application '+reference+' has status '+value['status']+' (not a credit approval).')
        else:add('requested_amount','requested_amount',value['requested_amount'],'Application '+reference+' requested amount: '+money(value['requested_amount'],currency)+'. Approved amount and repayment terms are unavailable.',currency=currency,application_reference=reference,
            brief='Application '+reference+' requested '+cash(value['requested_amount'],currency)+'; the approved amount and terms are not available.')
    elif name in MODULE_CLAIMS:
        MODULE_CLAIMS[name](value,add,prefix)
    return records


METHOD_LABELS={'external_card':'card','qr_pay':'QR pay','tap_pay':'tap-to-pay','cash':'cash','external_wallet':'e-wallet','pay_link':'pay link','bank_transfer':'bank transfer'}
CARD_COLUMN=re.compile(r'card (?:type|brand|network|scheme)|\bscheme\b|\bnetwork\b|\bissuer\b|\bbrand\b',re.I)

def _source(row,pattern):
    """The uploaded file's own value for a column, e.g. Payment Method -> "Credit Card"."""
    values=row.get('source_values') or {}
    return next((str(v) for k,v in values.items() if re.search(pattern,k,re.I) and str(v).strip()),None)

def _paid(row):
    method=row.get('payment_method')
    if not method:return None
    if method=='not_recorded':return 'payment method not recorded in your expense report'
    label=METHOD_LABELS.get(method,str(method).replace('_',' '))
    original=_source(row,r'payment|tender|channel');brand=_source(row,CARD_COLUMN.pattern)
    detail=[x for x in (brand,original) if x and x.strip().lower()!=label.lower()]
    return 'paid by '+label+(' ("'+'", "'.join(dict.fromkeys(detail))+'" in your file)' if detail else '')

def _txn(row,dated=True):
    kind={'sale':'sale','refund':'refund','expense':'expense','cash_in':'cash-in (not revenue)','cash_out':'cash-out (not an expense)'}.get(row.get('transaction_type'),row.get('transaction_type') or 'transaction')
    parts=([day(row['business_date'])] if dated else [])+[cash(row['amount'],row.get('currency') or 'CNY')+' '+kind]
    if _paid(row):parts.append(_paid(row))
    parts.append(str(row.get('status') or 'unknown'))
    if row.get('reference'):parts.append('reference '+str(row['reference']))
    from copilot.category_guide import label
    if label(row.get('classification')) and row.get('classification') not in ('sales_revenue','operating_expense'):parts.append('classified as '+label(row['classification'])+(' (needs review)' if row['classification'] in ('needs_review','capital_purchase') else ''))
    return ', '.join(parts)+(' ("'+row['description']+'")' if row.get('description') else '')

def _file_values(row):
    values=row.get('source_values') or {}
    return '; '.join(str(k)+': '+str(v) for k,v in list(values.items())[:12])

def _transaction_details(value,add,prefix):
    ref=value['transaction_id']
    if not value.get('found'):
        add('transaction','transaction_lookup','not_found','No recorded transaction with reference '+ref+' was found in Transaction History for this business.','backend_fact',
            brief='I couldn’t find transaction '+ref+' in your recorded transactions for this business.');return
    add('transaction','transaction_lookup',value['amount'],'Transaction '+ref+': '+day(value['business_date'])+'; type '+value['transaction_type']+'; amount '+money(value['amount'],value.get('currency') or 'CNY')+'; payment method '+str(value.get('payment_method'))+'; status '+value['status']+'; source '+value['source']+'; description '+str(value.get('description'))+'.'+(' Uploaded file values: '+_file_values(value)+'.' if value.get('source_values') else ''),
        'backend_fact',currency=value.get('currency') or 'CNY',brief='Transaction '+ref+': '+_txn(value)+'.')
    if value.get('source_values'):
        add('transaction_file','transaction_file_values','file','From your uploaded file: '+_file_values(value)+'.','backend_fact',brief='In your uploaded file this row shows '+_file_values(value)+'.')

def _recent_transactions(rows,add,prefix):
    if not rows:
        add('recent','recent_transactions','0','No recorded transactions were returned for that request.','backend_fact',brief='I didn’t find any recorded transactions matching that.');return
    shown=rows[:5]
    add('recent','recent_transactions',str(len(rows)),'Recorded transactions (latest first): '+'; '.join(r['transaction_id']+' '+_txn(r) for r in rows)+'.','backend_fact',
        brief=(('On '+day(rows[0]['business_date'])+': ' if len({r['business_date'] for r in rows})==1 and len(rows)>1 else 'Your latest recorded transaction'+('s are: ' if len(shown)>1 else ' is '))+'; '.join(_txn(r,dated=not (len({x['business_date'] for x in rows})==1 and len(rows)>1)) for r in shown)+'.'+(' (Showing '+str(len(shown))+' of '+str(len(rows))+'.)' if len(rows)>len(shown) else '')))
    days=sorted({r['business_date'] for r in rows})
    if len(days)==1 and len(rows)>1:
        # "What card did I use on Oct 2?": how that day's returned transactions were paid.
        mix={}
        for r in rows:
            label=METHOD_LABELS.get(r.get('payment_method'),str(r.get('payment_method') or 'unknown').replace('_',' '));mix[label]=mix.get(label,0)+1
        text=', '.join(str(n)+' '+label for label,n in sorted(mix.items(),key=lambda x:-x[1]))
        add('recent_day','transactions_by_payment_method',str(len(rows)),'Payment methods for '+str(len(rows))+' returned transactions on '+day(days[0])+': '+text+'.','backend_fact',
            brief='On '+day(days[0])+', the '+str(len(rows))+' transactions I found were paid by '+text+'.'+(' This is the latest '+str(len(rows))+' of that day.' if len(rows)>=20 else ''))
    if len(rows)==1 and rows[0].get('source_values'):
        add('recent_file','transaction_file_values','file','From your uploaded file: '+_file_values(rows[0])+'.','backend_fact',brief='In your uploaded file this row shows '+_file_values(rows[0])+'.')

def _data_quality(value,add,prefix):
    rate=lambda v:'n/a' if v is None else format(Decimal(str(v))*100,'.1f')+'%'
    add('quality','data_quality_summary',str(value['open_alerts']),'Imports: '+str(value['total_import_runs'])+' runs, '+str(value['successful_imports'])+' successful, '+str(value['failed_imports'])+' failed; parsed rows '+str(value['parsed_rows'])+'; valid-row rate '+rate(value['valid_row_rate'])+'; invalid-row rate '+rate(value['invalid_row_rate'])+'; open alerts '+str(value['open_alerts'])+'; last successful import '+str(value['last_successful_import'] or 'none')+'. Run counts include earlier imports; each Bulk POS Import replaces all earlier imported transactions (manual entries are kept), so only the latest import is in your records.','backend_fact',
        brief='You have '+str(value['total_import_runs'])+' import runs ('+str(value['successful_imports'])+' successful, '+str(value['failed_imports'])+' failed), '+rate(value['valid_row_rate'])+' of parsed rows were valid, and there '+('is 1 open data-quality alert' if value['open_alerts']==1 else 'are '+str(value['open_alerts'])+' open data-quality alerts')+(', with the last successful import on '+day(str(value['last_successful_import'])[:10]) if value['last_successful_import'] else '')+'.')
    if value['attention']:
        top=value['attention'][0]
        add('quality_top_alert','data_quality_alert',str(top['affected_rows']),'Open data-quality alert ('+top['severity']+', '+top['state']+'): '+top['description']+' Affected rows: '+str(top['affected_rows'])+'.','backend_fact',
            brief='The top open alert ('+top['severity']+') is: '+top['description'].rstrip('.')+' ('+str(top['affected_rows'])+' rows).')

def _income(value,add,prefix):
    requested=value['period'];c=value['currency'];gap=coverage_gap(value)
    if gap:
        add('coverage_gap','incomplete_record_coverage','incomplete','Requested period '+period(requested)+'; returned record dates '+(period(value['coverage']) if value['coverage'] else 'none')+'. Some transactions may not be recorded yet.','data_limitation',period=requested,
            brief=('Records for '+span_text(requested)+' only cover '+span_text(value['coverage'])+', so some transactions may not be recorded yet.' if value['coverage'] else 'No records were found for '+span_text(requested)+'.'))
    add('income','income_summary',value['net_income'],'Income summary '+period(requested)+': recorded net sales '+money(value['net_sales'],c)+', recorded expenses '+money(value['expenses'],c)+', net income '+money(value['net_income'],c)+' ('+str(value['record_count'])+' records). Net income is not available cash.','derived_calculation',currency=c,period=requested,
        brief='For '+span_text(requested)+', recorded net sales were '+cash(value['net_sales'],c)+', expenses '+cash(value['expenses'],c)+' and net income '+cash(value['net_income'],c)+'.',requires=[prefix+'.coverage_gap'] if gap else [])
    _income_extra(value,add,prefix)

def _alerts(rows,add,prefix):
    add('alerts_basis','alerts_basis','estimate','Alerts are rule-based results from the cash-flow forecast; the forecast is an estimate and is not reconciled with your bank.','data_limitation',
        brief='These alerts come from the forecast estimate, which is not reconciled with your bank.')
    if not rows:
        add('alerts','cash_flow_alerts','0','No cash-flow alerts are currently raised.','backend_fact',brief='There are no cash-flow alerts right now.');return
    order={'critical':0,'warning':1,'info':2};rows=sorted(rows,key=lambda r:order.get(r['severity'],3))
    add('alerts','cash_flow_alerts',str(len(rows)),' '.join(r['severity'].title()+' ('+r['code']+'): '+r['message']+' Recommended: '+r['recommended_action'] for r in rows),'backend_fact',
        brief=('You have '+str(len(rows))+' cash-flow alert'+('s' if len(rows)>1 else '')+'; the most important is: '+rows[0]['message'].rstrip('.')+'. Suggested action: '+rows[0]['recommended_action']),requires=[prefix+'.alerts_basis'])

def _matches(rows,add,prefix):
    if not rows:
        add('matches','financing_matches','0','No financing products currently match.','backend_fact',brief='No financing products match your business right now.');return
    add('match_basis','financing_match_basis','indicative',rows[0]['disclaimer'],'data_limitation',brief='These are indicative matches, not offers or approvals.')
    def one(r):return r['product']+' (match '+format(r['match_score'],'.0f')+'/100'+(', indicative size '+cash(r['indicative_size']) if r.get('indicative_size') else '')+(', about '+format(r['indicative_annual_cost']*100,'.1f')+'% a year' if r.get('indicative_annual_cost') is not None else '')+')'
    add('matches','financing_matches',str(len(rows)),'Indicative financing matches: '+'; '.join(one(r)+' — '+r['rationale'] for r in rows)+'.','derived_calculation',
        brief='Your best financing matches are '+'; '.join(one(r) for r in rows[:3])+'.',requires=[prefix+'.match_basis'])

def _rbf(value,add,prefix):
    c=value['currency']
    add('rbf_basis','rbf_basis','indicative',value['disclaimer'],'data_limitation',brief='This is an indicative simulation, not a financing offer or approval.')
    days=value.get('estimated_payoff_days')
    add('rbf','rbf_quote',str(value['total_repayable']),'Indicative revenue-based financing: advance '+money(value['advance'],c)+', fee '+money(value['fee'],c)+' ('+format(value['fee_rate']*100,'.2f')+'%), total repayable '+money(value['total_repayable'],c)+', remittance '+format(value['remittance_rate']*100,'.2f')+'% of '+value['remittance_basis']+', estimated payoff '+(str(days)+' days' if days else 'not within the simulation limit')+'. Allowed advance range '+money(value['min_advance'],c)+' to '+money(value['max_advance'],c)+'.','simulation_result',currency=c,
        brief='An indicative advance of '+cash(value['advance'],c)+' would carry a fee of '+cash(value['fee'],c)+' ('+format(value['fee_rate']*100,'.0f')+'%), repaid as '+format(value['remittance_rate']*100,'.0f')+'% of daily digital sales'+(' over about '+str(days)+' days' if days else '')+'.',requires=[prefix+'.rbf_basis'])

def _maturity(value,add,prefix):
    add('maturity_basis','maturity_basis','indicative','Indicative business assessment from recorded data and existing scoring rules; not a credit decision. '+str(value.get('note') or ''),'data_limitation',brief='This is an indicative assessment, not a credit decision.')
    gap=(' Reaching '+value['next_stage_name']+' needs about '+format(value['composite_gap'],'.1f')+' more points.') if value.get('next_stage_name') and value.get('composite_gap') is not None else ''
    add('maturity','business_maturity',str(value['composite_score']),'Business maturity as of '+value['as_of']+': stage '+str(value['stage'])+' ('+value['stage_name']+'), composite '+format(value['composite_score'],'.1f')+'/100. Scores: '+', '.join(k.replace('_',' ')+' '+format(v,'.1f') for k,v in value['scores'].items())+'.'+gap,'derived_calculation',
        brief='Your business is at stage '+str(value['stage'])+' ('+value['stage_name']+') with a composite score of '+format(value['composite_score'],'.1f')+'/100.'+gap,requires=[prefix+'.maturity_basis'])
    if value['top_constraints']:
        c=value['top_constraints'][0]
        add('maturity_constraint','maturity_constraint',c['constraint'],'Top constraint: '+c['constraint'].replace('_',' ')+' — '+c['evidence']+(' Suggested support: '+c['intervention'] if c.get('intervention') else ''),'backend_fact',
            brief='Your main constraint is '+c['constraint'].replace('_',' ')+': '+c['evidence'].rstrip('.')+'.')

def _rate(value):
    return format(Decimal(str(value)).normalize(),'f')+'%'

def _loan(value,add,prefix):
    c=value['currency'];basis=prefix+'.loan_basis'
    add('loan_basis','loan_basis','estimate','Standard fixed-rate amortization (equal monthly payments) from the amount, rate and term you supplied. Not a lender quote: fees, insurance, rate type and actual terms may differ.','data_limitation',
        brief='This is a standard equal-payment estimate from your numbers, not a lender quote.')
    term=str(value['months'])+' months'
    add('loan','loan_repayment',value['monthly_payment'],'Loan estimate: '+money(value['principal'],c)+' at '+_rate(value['annual_rate_percent'])+' a year over '+term+': monthly payment '+money(value['monthly_payment'],c)+', total repaid '+money(value['total_paid'],c)+', total interest '+money(value['total_interest'],c)+'. First months: '+
        '; '.join('month '+str(r['month'])+' payment '+cash(r['payment'],c)+' (interest '+cash(r['interest'],c)+', principal '+cash(r['principal'],c)+', balance '+cash(r['balance'],c)+')' for r in value['schedule'])+'.','derived_calculation',currency=c,
        brief='Borrowing '+cash(value['principal'],c)+' at '+_rate(value['annual_rate_percent'])+' a year over '+term+' works out to about '+cash(value['monthly_payment'],c)+' a month, '+cash(value['total_paid'],c)+' in total ('+cash(value['total_interest'],c)+' interest).',requires=[basis])
    alt=value.get('alternative')
    if alt:
        diff=Decimal(alt['monthly_payment'])-Decimal(value['monthly_payment'])
        add('loan_alternative','loan_repayment_rate_change',alt['monthly_payment'],'At '+_rate(alt['annual_rate_percent'])+' a year: monthly payment '+money(alt['monthly_payment'],c)+', total repaid '+money(alt['total_paid'],c)+', total interest '+money(alt['total_interest'],c)+'.','derived_calculation',currency=c,
            brief='At '+_rate(alt['annual_rate_percent'])+' the payment would be about '+cash(alt['monthly_payment'],c)+' a month ('+cash(abs(diff),c)+(' more' if diff>=0 else ' less')+'), '+cash(alt['total_paid'],c)+' in total.',requires=[basis])

BOOK_UPLOAD='Cash Flow tab > Upload workbook'

def _book_item(i,c):
    when=('overdue '+str(-i['days'])+' day'+('' if i['days']==-1 else 's')) if i['days']<0 else 'due today' if i['days']==0 else 'due tomorrow' if i['days']==1 else 'due '+day(i['due'])
    return i['party']+' '+cash(i['amount'],c)+' ('+when+')'

def _import_summary(value,add,prefix):
    """Bulk POS Import and manual entries. Each upload replaces the earlier imported data; manual entries are kept."""
    count=lambda n,word:format(n,',')+' '+word+('' if n==1 else 's')
    last=value.get('latest_import')
    if last:
        files=', '.join(f for f in last['files'] if f) or count(last['file_count'],'file')
        when=day(str(last['imported_at'])[:10]);extra=[]
        if last['duplicates_excluded']:extra.append(count(last['duplicates_excluded'],'row')+' excluded as duplicates')
        if last['rejected_rows']:extra.append(count(last['rejected_rows'],'row')+' rejected')
        replaced=' It replaced the earlier imported data; manual entries were kept.' if last['replaced_imports'] else ''
        add('latest_import','latest_import',last['imported_rows'],'Latest Bulk POS Import: '+when+' ('+files+'); '+count(last['imported_rows'],'transaction')+' imported'+('; '+'; '.join(extra) if extra else '')+'.'+replaced,
            brief='Yes. Your latest Bulk POS Import was saved on '+when+' ('+files+'), with '+count(last['imported_rows'],'transaction')+' imported'+(' and '+' and '.join(extra) if extra else '')+'.'+replaced)
    else:
        add('latest_import','latest_import','none','No Bulk POS Import has been completed for this business yet.',brief='No Bulk POS Import has been completed for this business yet.')
    dates=value.get('imported_dates');n=value['imported_rows_current']
    split=format(value['imported_revenue_rows'],',')+' revenue and '+format(value['imported_expense_rows'],',')+' expense'
    add('imports_current','imported_rows_current',n,'Imported transactions in the records now: '+format(n,',')+' ('+split+')'+(', dated '+period(dates) if dates else '')+'. Only the latest import is kept.',
        brief='Your records now hold '+count(n,'imported transaction')+' ('+split+')'+(' dated '+span_text(dates) if dates else '')+'.')
    m=value['manual_entries'];latest=value.get('latest_manual_entry_date')
    add('manual_entries','manual_entries',m,'Manual Single Transaction entries: '+format(m,',')+(', latest dated '+day(latest) if latest else '')+'. They are kept when a new import replaces imported data.',
        brief='You have '+(count(m,'manual Single Transaction entry').replace('entrys','entries'))+(', the latest dated '+day(latest) if latest else '')+'.')
    if value['unfinished_uploads']:
        u=value['unfinished_uploads']
        add('unfinished_uploads','unfinished_uploads',u,'Unfinished uploads (staged or validated, never imported): '+format(u,',')+'. They are not in the records.',
            brief='You also have '+count(u,'unfinished upload')+' that '+('was' if u==1 else 'were')+' never imported, so '+('it is' if u==1 else 'they are')+' not in your records.')

def _cashflow_book(value,add,prefix):
    """Cash Flow tab figures from the uploaded workbook; every figure is qualified by its upload and reference dates."""
    if not value.get('available'):
        add('book_missing','cashflow_book_missing','none','No cash-flow workbook has been uploaded for this business, so receivables, payables and the 7-day runway are not available. Upload one in '+BOOK_UPLOAD+'.','data_limitation',
            brief='You haven’t uploaded a cash-flow workbook yet, so I can’t show who owes you, bills due or your 7-day runway. Upload it in '+BOOK_UPLOAD+'.');return
    c=value['currency'];ref=value['reference_date'];basis=prefix+'.book_basis'
    uploaded=(' uploaded '+day(value['uploaded_at'])) if value.get('uploaded_at') else ''
    add('book_basis','cashflow_book_basis','workbook','Based on your cash-flow workbook'+uploaded+', as of '+day(ref)+'. Balances are invoice or bill amounts minus amounts collected or paid; cash on hand is the value in your workbook, not a bank-verified balance; projections are not guarantees.','data_limitation',
        brief='Based on your cash-flow workbook'+uploaded+', as of '+day(ref)+'; projections are not guarantees.')
    ar=value['top_receivables'];ap=value['top_payables']
    add('book_summary','cashflow_book_summary',value['total_receivables'],'Workbook as of '+day(ref)+': open receivables '+money(value['total_receivables'],c)+' ('+str(value['receivables_count'])+' invoices), of which overdue '+money(value['overdue_receivables'],c)+' ('+str(value['overdue_receivables_count'])+'); open payables '+money(value['total_payables'],c)+' ('+str(value['payables_count'])+' bills), of which overdue '+money(value['overdue_payables'],c)+' ('+str(value['overdue_payables_count'])+').','backend_fact',currency=c,
        brief='Customers owe you '+cash(value['total_receivables'],c)+' ('+cash(value['overdue_receivables'],c)+' overdue), and you owe suppliers '+cash(value['total_payables'],c)+' ('+cash(value['overdue_payables'],c)+' overdue).',requires=[basis])
    if value['receivables_count']:
        add('book_receivables','cashflow_book_receivables',value['total_receivables'],'Open receivables (earliest due first): '+'; '.join(_book_item(i,c) for i in ar)+('; and '+str(value['receivables_count']-len(ar))+' more' if value['receivables_count']>len(ar) else '')+'.','backend_fact',currency=c,
            brief='Customers owe you '+cash(value['total_receivables'],c)+' across '+str(value['receivables_count'])+' open invoice'+('s' if value['receivables_count']!=1 else '')+'; the earliest due are '+', '.join(_book_item(i,c) for i in ar[:3])+'.',requires=[basis])
    else:add('book_receivables','cashflow_book_receivables','0','No open receivables in the workbook.','backend_fact',brief='Your workbook shows no open customer invoices.',requires=[basis])
    late=[i for i in ar if i['bucket']=='OVERDUE'];late_bills=[i for i in ap if i['bucket']=='OVERDUE']
    if value['overdue_receivables_count'] or value['overdue_payables_count']:
        parts=[]
        if value['overdue_receivables_count']:parts.append(cash(value['overdue_receivables'],c)+' in '+str(value['overdue_receivables_count'])+' overdue customer invoice'+('s' if value['overdue_receivables_count']!=1 else '')+(': '+', '.join(_book_item(i,c) for i in late[:3]) if late else ''))
        if value['overdue_payables_count']:parts.append(cash(value['overdue_payables'],c)+' in '+str(value['overdue_payables_count'])+' overdue supplier bill'+('s' if value['overdue_payables_count']!=1 else '')+(': '+', '.join(_book_item(i,c) for i in late_bills[:3]) if late_bills else ''))
        add('book_overdue','cashflow_book_overdue',value['overdue_receivables'],'Overdue as of '+day(ref)+': '+'; '.join(parts)+'.','backend_fact',currency=c,brief='Overdue: '+'; and '.join(parts)+'.',requires=[basis])
    else:add('book_overdue','cashflow_book_overdue','0','Nothing is overdue in the workbook as of '+day(ref)+'.','backend_fact',brief='Nothing in your workbook is overdue.',requires=[basis])
    week=[i for i in ap if i['bucket'] in ('DUE_TOMORROW','NEXT_7')]
    add('book_payables','cashflow_book_payables_7d',value['upcoming_payables_7d'],'Bills due in the next 7 days (including today): '+money(value['upcoming_payables_7d'],c)+' ('+str(value['payables_7d_count'])+' bills)'+(': '+'; '.join(_book_item(i,c) for i in week) if week else '')+'. Open payables in total: '+money(value['total_payables'],c)+'.','backend_fact',currency=c,
        brief=('You have '+cash(value['upcoming_payables_7d'],c)+' in '+str(value['payables_7d_count'])+' bill'+('s' if value['payables_7d_count']!=1 else '')+' due in the next 7 days'+(': '+', '.join(_book_item(i,c) for i in week[:3]) if week else '')+'.') if value['payables_7d_count'] else 'No supplier bills are due in the next 7 days.',requires=[basis])
    cash_label='cash on hand from your workbook' if value.get('cash_on_hand_recorded') else 'cash on hand (not set in your workbook, so zero)'
    add('book_runway','cashflow_book_runway_7d',value['net_runway_7d'],'7-day net runway: '+cash_label+' '+money(value['cash_on_hand'],c)+' plus expected collections '+money(value['expected_collections_7d'],c)+' ('+str(value['collections_count'])+' invoices) minus upcoming payables '+money(value['upcoming_payables_7d'],c)+' ('+str(value['payables_7d_count'])+' bills) = '+money(value['net_runway_7d'],c)+'.','derived_calculation',currency=c,
        brief='Your 7-day net runway is '+cash(value['net_runway_7d'],c)+': '+cash_label+' '+cash(value['cash_on_hand'],c)+', plus '+cash(value['expected_collections_7d'],c)+' expected from customers, minus '+cash(value['upcoming_payables_7d'],c)+' in bills due.',requires=[basis])
    if value.get('projected_months'):
        months=value['projected_months']
        month=lambda m:date.fromisoformat(m['month']+'-01').strftime('%B %Y')
        add('book_projection','cashflow_book_projection',months[-1]['ending'],'Projected months (open invoices and bills due in each month only, not expected sales): '+'; '.join(month(m)+' in '+money(m['inflow'],c)+', out '+money(m['outflow'],c)+', ending cash '+money(m['ending'],c) for m in months)+'.','derived_calculation',currency=c,
            brief='Projected ending cash: '+', '.join(month(m)+' '+cash(m['ending'],c) for m in months)+' (from open invoices and bills only).',requires=[basis])

def _income_extra(value,add,prefix):
    """Dashboard Average Revenue / Average Expense and Expense Split for the same period."""
    requested=value['period'];c=value['currency'];gap=[prefix+'.coverage_gap'] if coverage_gap(value) else []
    a=value.get('averages')
    if a:
        add('income_averages','income_averages',a['monthly']['net_sales'],'Averages over '+period(requested)+' ('+str(a['days'])+' days, '+format(a['weeks'],'.2f')+' weeks, '+format(a['months'],'.2f')+' months; a partial month counts by its days): average revenue '+money(a['monthly']['net_sales'],c)+' a month, '+money(a['weekly']['net_sales'],c)+' a week, '+money(a['daily']['net_sales'],c)+' a day; average expense '+money(a['monthly']['expenses'],c)+' a month, '+money(a['weekly']['expenses'],c)+' a week, '+money(a['daily']['expenses'],c)+' a day.','derived_calculation',currency=c,period=requested,
            brief='For '+span_text(requested)+', average revenue was '+cash(a['monthly']['net_sales'],c)+' a month ('+cash(a['weekly']['net_sales'],c)+' a week, '+cash(a['daily']['net_sales'],c)+' a day) and average expense '+cash(a['monthly']['expenses'],c)+' a month ('+cash(a['weekly']['expenses'],c)+' a week, '+cash(a['daily']['expenses'],c)+' a day).',requires=gap)
    split=value.get('expense_split')
    if split is not None:
        label=lambda k:str(k).replace('_',' ')
        if split:add('expense_split','expense_split',split[0]['amount'],'Expense split '+period(requested)+': '+'; '.join(label(r['category'])+' '+money(r['amount'],c)+' ('+format(r['share_percent'],'.1f')+'%)' for r in split)+'.','backend_fact',currency=c,period=requested,
            brief='Your expenses for '+span_text(requested)+' split as '+', '.join(label(r['category'])+' '+cash(r['amount'],c)+' ('+format(r['share_percent'],'.1f')+'%)' for r in split[:4])+'.',requires=gap)
        else:add('expense_split','expense_split','0','No recorded expenses in '+period(requested)+'.','backend_fact',period=requested,brief='No expenses were recorded for '+span_text(requested)+'.',requires=gap)

MODULE_CLAIMS={'calculate_loan_repayment':_loan,'get_transaction_details':_transaction_details,'get_recent_transactions':_recent_transactions,'get_data_quality':_data_quality,'get_income_summary':_income,
 'get_cash_flow_alerts':_alerts,'get_financing_matches':_matches,'get_rbf_quote':_rbf,'get_business_maturity':_maturity,'get_cashflow_book':_cashflow_book,'get_import_summary':_import_summary}


def verify_response(content,records,*,inline=False):
    """Model selects typed records; backend owns values, labels and provenance.

    inline=True renders each record's compact `brief`, joins segments as one
    paragraph and requires every claim's material qualifications (`requires`).

    Example: {"segments":[{"claim":"user.purchase_price","kind":"user_assumption",
    "value":"10000.00"},{"text":"Will you pay cash or use financing?"}]}.
    Values/kind/metric/currency/period, if echoed, must match the source exactly.
    """
    content=content.strip()
    if content.startswith('```'):
        content=re.sub(r'^```(?:json)?\s*|\s*```$','',content)
    try:payload=json.loads(content)
    except (ValueError,TypeError):payload={'segments':[{'text':content}]}
    if not isinstance(payload,dict) or set(payload)!={'segments'} or not isinstance(payload['segments'],list) or not 1<=len(payload['segments'])<=16:raise ClaimError('invalid_claim_envelope')
    output=[];used=[]
    for segment in payload['segments']:
        if not isinstance(segment,dict):raise ClaimError('invalid_claim_segment')
        if 'claim' in segment:
            if set(segment)-{'claim','kind','value','metric','currency','period'}:raise ClaimError('unsupported_claim_fields')
            key=segment['claim'];record=records.get(key) if isinstance(key,str) else None
            if segment.get('kind')=='unsupported_claim':raise ClaimError('unsupported_claim')
            if record is None:raise ClaimError('claim_without_authorized_source')
            for field in ('kind','value','metric','currency','period'):
                if field not in segment:continue
                actual,expected=segment[field],record.get(field)
                if field=='value':
                    try:
                        left=Decimal(str(actual).replace(',',''));right=Decimal(str(expected).replace(',',''))
                        equal=left.is_finite() and right.is_finite() and left==right
                    except Exception:equal=actual==expected
                elif field=='kind':equal=CLAIM_KINDS.get(actual,actual)==CLAIM_KINDS.get(expected,expected)
                elif field=='currency':equal=('CNY' if actual=='RMB' else actual)==expected
                else:equal=actual==expected
                if not equal:raise ClaimError('claim_source_mismatch')
            if record['kind']=='external_fact' and not all(record.get(k) for k in ('approved_search','source_url','retrieved_at')):raise ClaimError('external_claim_without_approved_provenance')
            # An empty brief deliberately renders nothing inline (the record stays in Sources & Tools).
            output.append((record['brief'] if 'brief' in record else record['display']) if inline else record['display']);used.append(key)
        elif set(segment)=={'text'} and isinstance(segment['text'],str):
            text=segment['text'].strip()
            # Text is connective explanation/clarification. Numeric assertions use
            # typed records, not a numeric allowlist that launders assumptions.
            text=re.sub(r'(?m)^\s*\d{1,2}[.)]\s+','',text)
            if re.search(r'\d|\b(?:million|billion|thousand|hundred)\b',text,re.I):raise ClaimError('untyped_numeric_claim')
            # Qualitative liquidity verdicts also require a server-rendered calculation.
            if re.search(r'(?:still|remaining|left over|leftover).{0,30}(?:cash|balance)|(?:cash|balance).{0,25}(?:left|remaining|positive)|(?:no|without) (?:cash )?shortfall',text,re.I) and not re.search(r"cannot|can't|not established|unknown",text,re.I):raise ClaimError('unsupported_financial_conclusion')
            conclusion_text=re.sub(r"(?:I |we )?(?:cannot|can't|do not|don't) (?:yet )?(?:determine|establish|confirm|know) (?:whether|if) (?:your business|you) (?:can|could|will) afford",'',text,flags=re.I)
            if re.search(r'https?://|(?:you|your business)\s+(?:can|could|will)\s+afford|(?:purchase|oven|investment)\s+is\s+affordable|definitely afford|guaranteed|credit (?:is )?approved|loan (?:is )?approved|I (?:submitted|paid|purchased|transferred)',conclusion_text,re.I):raise ClaimError('unsupported_financial_conclusion')
            for clause in re.split(r'[.;\n]',text):
                if clause.strip().lower() in {
                    'affordability assessments require a comprehensive review of your current cash flow and outstanding liabilities',
                    'no approved one-time purchase affordability calculation is available'
                }:continue
                if re.fullmatch(r'I can explain how (?:your |the )?(?:cash.flow forecast|sales report|payment.channel mix) works',clause.strip(),re.I):continue
                if re.search(r'(?:historical|financial|sales) data (?:is|are) missing',clause,re.I):raise ClaimError('unsupported_data_coverage_claim')
                uncertain=bool(re.search(r"cannot|can't|not|unverified|unavailable|missing|unknown|uncertain|whether|depends|need|verify|verification|assuming|hypothetical|\bif\b|could|\?",clause,re.I))
                # "your cash flow forecast" names a report, not a cash position; "your cash", "your balance" still need evidence.
                risky=re.search(r'(?:your|our|recorded|the business).{0,35}(?:profitable|healthy|strong|cash(?![- ]?(?:flow|impact))|balance|profit|reserves|grew|increased|decreased)|you have (?:enough|sufficient)|you (?:have|hold|possess).{0,20}(?:cash|balance)|available cash is|bank balance is|profit is|\bverified (?:available )?cash|sales (?:are|is|equals?|means?) (?:your )?(?:available )?cash|spend (?:your |the )?(?:net )?sales|sales.{0,20}spendable|(?:our|your).{0,25}(?:loan|financing application)|afford(?:able|ability)?',clause,re.I)
                if risky and not uncertain:raise ClaimError('unsupported_business_fact')
            output.append(text)
        else:raise ClaimError('invalid_claim_segment')
    if inline:
        for key in used:
            missing=[r for r in records[key].get('requires',[]) if r not in used]
            if missing:
                error=ClaimError('missing_required_qualification');error.detail={'claim':key,'required':missing[0]};raise error
        return ' '.join(part.strip() for part in output if part.strip()),used
    return '\n\n'.join(part for part in output if part),used


def affordability_guidance(context):
    """No new affordability formula: verified liquidity/commitments are absent."""
    if context.get('date_issue'):return 'Which single assessment date should I use?'
    if not context.get('funding'):return 'Will you pay in cash or use financing?'
    if context['funding']=='financing' and not context.get('repayment_term'):return 'What repayment period are you considering? The existing engine cannot calculate equipment or property-loan amortization.'
    if not context.get('price'):return 'What purchase price and currency are you assuming?'
    if not context.get('extra_costs'):return 'Does the stated price include delivery, installation and other purchase costs?'
    if context.get('reported_cash'):return 'Your reported cash remains an unverified assumption. Can its source and the obligations due before your next expected receipts be verified? No purchase-affordability conclusion has been established.'
    return 'I cannot yet establish affordability: verified available cash and complete upcoming operating commitments are unavailable. Can you provide a verified cash position and the obligations due before your next expected receipts? User-reported amounts remain assumptions until independently verified.'


def render_tool(name,value,currency='CNY'):
    records=tool_claims(name,value,currency)
    if records:
        text='\n'.join(r['display'] for r in list(records.values())[:8])
        if len(records)>8:text+='\nShowing selected reporting entries; open the source module for the complete authorized series.'
        if name=='run_survival_simulation':
            a=value['assumptions'];text+='\nAssumptions: sales change '+str(a['sales_change_percent'])+'%; expense change '+str(a['expense_change_percent'])+'%; '+str(a['months'])+' months. This is not actual available cash, property-loan amortization or cash runway.'
        return text+'\nSource: existing authorized backend services. Digital Payments Simulator activity is excluded.'
    if name=='get_cash_flow':
        lines=['Estimated cash-flow forecast: '+period(value['period'])+'. Verified available cash is unavailable; a forecast is not a cash-account balance.']
        for field,label in [('cash_inflows','Estimated inflow'),('cash_outflows','Estimated outflow')]:
            lines.extend(label+' on '+day(row['date'])+': '+money(row['amount'],value['currency'])+'.' for row in value[field][:3])
        return '\n'.join(lines)+'\nShowing the first forecast dates only; this does not establish purchase affordability.'
    if name=='get_transaction_trends':return '\n'.join(str(row['period'])+': '+format(row['transaction_count'],',')+' sales/payment transactions; recorded net sales '+money(row['recorded_net_sales'],currency)+'.' for row in value[:12])+'\nExisting reporting buckets; sales are not profit or cash.'
    if name=='get_payment_channel_mix':return '\n'.join(row['channel']+': '+format(row['transaction_count'],',')+' transactions; '+format(row['share_percent'],'.2f')+'% of transaction volume.' for row in value)
    if name=='get_business_highlights':return '\n'.join(row['highlight_type']+': '+row['summary'] for row in value)
    return 'This authorized result has no supported conversational presentation. Review the source module.'


def render_purchase(context, records, followup=False):
    """Deterministic presentation of independently checked source records.

    Model prose is never rewritten into authoritative money claims. Required
    assumption references are checked again against server conversation state;
    financial values and dates are rendered only from authorized catalog entries.
    """
    expected=assumptions(context)
    keys=list(expected)
    if any(key not in records for key in keys):raise ClaimError('claim_without_authorized_source')
    for key in keys:
        if records[key]!=expected[key]:raise ClaimError('claim_source_mismatch')
    sales=next((key for key,record in records.items()
                if record.get('source')=='get_financial_summary' and record.get('metric')=='recorded_net_sales'),None)
    if sales and not followup:keys.append(sales)
    if keys:verify_response(json.dumps({'segments':[{'claim':key,'kind':records[key]['kind']} for key in keys]}),records)
    parts=[]
    if context.get('price'):
        amount=money(records['user.purchase_price']['value'],records['user.purchase_price']['currency'])
        item=context.get('item','purchase')
        if followup and context.get('funding')=='cash':
            included=', including the costs you mentioned' if context.get('extra_costs')=='included or none, as stated by the user' else ''
            parts.append('Understood. You plan to pay '+amount+' in cash for the '+item+included+'.')
        else:parts.append("You're considering buying "+('an ' if item[:1] in 'aeiou' else 'a ')+item+' for '+amount+'.')
    else:parts.append("Let's look at the purchase you're considering.")
    if context.get('date_issue'):return '\n\n'.join(parts+['Which single date should I use for this assessment?'])
    if not followup and sales:
        record=records[sales]
        parts.append('Your business recorded '+money(record['value'],record['currency'])+' in net sales from '+period(record['period'])+". Sales alone don't tell us how much cash is available for this purchase.")
    if context.get('reported_cash'):
        record=records['user.reported_cash']
        parts.append('You told me you have '+money(record['value'],record['currency'])+" available. I haven't independently confirmed that balance, so I can't yet say whether the purchase is affordable.")
        question='What business expenses and payments are due before your next expected receipts?'
    elif not context.get('funding'):question='Are you planning to pay in cash or through financing?'
    elif context['funding']=='financing' and not context.get('repayment_term'):question='What repayment period are you considering?'
    elif not context.get('price'):question='What price and currency are you considering?'
    elif not context.get('extra_costs'):question='Does that price include delivery, installation and other purchase costs?'
    else:question='How much cash do you currently have available for business expenses?'
    parts.append(question)
    return '\n\n'.join(parts)

def analytical_claims(results):
    """Approved Decimal comparisons from authorized tool results, never model inputs."""
    records={}
    summaries=[(key,v) for key,name,v in results if name=='get_financial_summary']
    if len(summaries)>=2:
        (left,a),(right,b)=summaries[:2]
        if a['currency']!=b['currency']:raise ClaimError('comparison_currency_mismatch')
        current,prior=Decimal(a['recorded_net_sales']),Decimal(b['recorded_net_sales'])
        delta=current-prior;percent_value=(delta/prior*100).quantize(Decimal('.01')) if prior else None
        display='Recorded net sales comparison: '+period(a['period'])+' versus '+period(b['period'])+'. Difference: '+money(delta,a['currency'])+'.'
        display+=(' Change: '+str(percent_value)+'%.' if percent_value is not None else ' Percentage change is undefined because prior recorded sales are zero.')
        a_days=(date.fromisoformat(a['period']['end'])-date.fromisoformat(a['period']['start'])).days+1
        b_days=(date.fromisoformat(b['period']['end'])-date.fromisoformat(b['period']['start'])).days+1
        display+=' Period lengths: '+str(a_days)+' versus '+str(b_days)+' days; totals are not day-normalized.'
        display+=' Transaction-count difference: '+str(a['transaction_count']-b['transaction_count'])+'. Requested periods may have unequal calendar days; inspect coverage before interpreting.'
        if percent_value is None:brief='Recorded sales for '+span_text(a['period'])+' were '+cash(a['recorded_net_sales'],a['currency'])+'; a percentage change is undefined because '+span_text(b['period'])+' had no recorded sales.'
        else:brief='Recorded sales for '+span_text(a['period'])+' ('+cash(a['recorded_net_sales'],a['currency'])+') are '+str(abs(percent_value))+'% '+('lower' if delta<0 else 'higher' if delta>0 else 'unchanged')+(' than ' if delta else ' from ')+span_text(b['period'])+' ('+cash(b['recorded_net_sales'],b['currency'])+').'
        reasons=[]
        for key,v in ((left,a),(right,b)):
            if coverage_gap(v):reasons.append(span_text(v['period'])+' records '+('only cover '+span_text(v['coverage']) if v['coverage'] else 'are missing'))
        def whole_month(p):
            s,e=date.fromisoformat(p['start']),date.fromisoformat(p['end'])
            return s.day==1 and (s.year,s.month)==(e.year,e.month) and (e+__import__('datetime').timedelta(days=1)).day==1
        # Whole calendar months differ by a day or two by design; that is not a material caveat.
        if a_days!=b_days and not (whole_month(a['period']) and whole_month(b['period'])):
            reasons.append('the periods differ in length ('+str(a_days)+' vs '+str(b_days)+' days)')
            records['analysis.unequal_periods']={'kind':'data_limitation','metric':'unequal_period_lengths','value':str(a_days-b_days),'source':'get_financial_summary','display':'Compared periods have different lengths: '+str(a_days)+' versus '+str(b_days)+' days. Totals are not day-normalized.','brief':'The periods differ in length ('+str(a_days)+' vs '+str(b_days)+' days), so the totals are not directly comparable.'}
        requires=[]
        if reasons:
            # One combined qualification keeps a comparison answer short without dropping any caveat.
            requires=['analysis.comparison_caveat']
            text=reasons[0][:1].upper()+reasons[0][1:]+(' and '+', '.join(reasons[1:]) if len(reasons)>1 else '')
            records['analysis.comparison_caveat']={'kind':'data_limitation','metric':'comparison_limitations','value':str(len(reasons)),'source':'get_financial_summary',
                'display':'Comparison limitations: '+'; '.join(reasons)+'. Recorded-sales differences are not verified changes in business performance.',
                'brief':text+', so this does not show a verified change in business performance.'}
        records['analysis.comparison']={'kind':'derived_calculation','metric':'sales_comparison','value':str(delta),'currency':a['currency'],'source':'get_financial_summary','inputs':[left+'.net_sales',right+'.net_sales'],'formula':'current_minus_prior; percent=delta/prior*100 when prior != 0','display':display,'brief':brief,'requires':requires}
    scenarios=[(key,v) for key,name,v in results if name=='run_cash_impact_scenario']
    if len(scenarios)>=2:
        # Lower-risk ordering uses only recalculated metrics: no negative day first, then the higher minimum balance.
        def cost(v):return sum(Decimal(r['amount']) for r in v['schedule'])
        def rank(item):
            a=item[1]['adjusted']
            return (a['first_negative_date'] is None,a['first_negative_date'] or '',Decimal(a['min_balance']))
        ordered=sorted(scenarios,key=rank,reverse=True);best=ordered[0];currency=best[1]['currency']
        parts=[]
        for key,v in scenarios:
            a=v['adjusted']
            parts.append('a '+cash(cost(v),currency)+' payment leaves a lowest projected balance of '+cash(a['min_balance'],currency)+(' and first goes negative on '+day(a['first_negative_date']) if a['first_negative_date'] else ' with no projected negative balance'))
        tie=rank(ordered[0])==rank(ordered[1])
        brief='In the projections, '+'; '.join(parts)+'.'+('' if tie else ' The '+cash(cost(best[1]),currency)+' option carries less projected cash-flow risk.')
        records['analysis.scenario_comparison']={'kind':'derived_calculation','metric':'scenario_comparison','value':'' if tie else str(cost(best[1])),'currency':currency,'source':'run_cash_impact_scenario',
            'inputs':[key+'.adjusted' for key,v in scenarios],'formula':'rank by no projected negative balance, later first negative date, then higher minimum projected balance',
            'display':'Scenario comparison (hypothetical, recalculated this turn): '+'; '.join(parts)+'. Ranking: no projected negative balance first, then the later first negative date, then the higher minimum projected balance.','brief':brief,
            'requires':[scenarios[0][0]+'.scenario_basis']}
    for prefix,name,rows in results:
        if name!='get_transaction_trends' or not rows:continue
        # One backend sentence for "how is the trend": each month's recorded sales and transaction count, oldest first.
        currency=rows[0].get('currency','CNY');shown=rows[-6:]
        label=lambda p:datetime.strptime(p,'%Y-%m').strftime('%b %Y') if re.fullmatch(r'\d{4}-\d{2}',str(p)) else str(p)
        bucket=lambda r:label(r['period'])+' '+cash(r['recorded_net_sales'],currency)+' ('+format(r['transaction_count'],',')+(' transaction)' if r['transaction_count']==1 else ' transactions)')
        records['analysis.trend']={'kind':'derived_calculation','metric':'sales_trend','value':str(Decimal(shown[-1]['recorded_net_sales'])-Decimal(shown[0]['recorded_net_sales'])),'currency':currency,'source':name,
            'inputs':[prefix+'.sales'+str(i) for i in range(len(rows))],'formula':'returned buckets, oldest first',
            'display':'Recorded sales and transaction volume by period: '+'; '.join(bucket(r) for r in rows)+'. The latest period may be partial; sales are not profit or cash.',
            'brief':'Recorded sales and transaction volume by period: '+'; '.join(bucket(r) for r in shown)+'.'+(' The latest period may be partial.' if len(shown)>1 else '')}
        if all(r.get('recorded_expenses') is not None for r in rows):
            # Dashboard Revenue vs Expense trend: each period's recorded sales and expenses, oldest first.
            pair=lambda r:label(r['period'])+' sales '+cash(r['recorded_net_sales'],currency)+', expenses '+cash(r['recorded_expenses'],currency)
            records['analysis.revenue_expense_trend']={'kind':'derived_calculation','metric':'revenue_expense_trend','value':str(Decimal(shown[-1]['recorded_net_sales'])-Decimal(shown[-1]['recorded_expenses'])),'currency':currency,'source':name,
                'inputs':[prefix+k+str(i) for i in range(len(rows)) for k in ('.sales','.expenses')],'formula':'returned buckets, oldest first',
                'display':'Recorded sales and expenses by period: '+'; '.join(pair(r) for r in rows)+'. The latest period may be partial; sales minus expenses is not cash.',
                'brief':'Recorded sales and expenses by period: '+'; '.join(pair(r) for r in shown)+'.'+(' The latest period may be partial.' if len(shown)>1 else '')}
        top=max(Decimal(r['recorded_net_sales']) for r in rows)
        winners=[r['period'] for r in rows if Decimal(r['recorded_net_sales'])==top]
        records['analysis.best_period']={'kind':'derived_calculation','metric':'best_recorded_period','value':str(top),'source':name,'inputs':[prefix+'.sales'+str(i) for i in range(len(rows))],'formula':'max(recorded_net_sales); retain all ties','display':'Highest recorded net-sales bucket'+('s' if len(winners)>1 else '')+': '+', '.join(winners)+' at '+money(top,rows[0].get('currency','CNY'))+'. Basis: available returned '+rows[0]['granularity']+' buckets, including partial buckets where present; not profit or available cash.',
            'brief':'Your highest recorded sales '+('periods were ' if len(winners)>1 else 'period was ')+' and '.join(winners)+', at '+cash(top,rows[0].get('currency','CNY'))+'.'}
    return records

def cost_claims(records,entities):
    """Illustrative cost-vs-forecast arithmetic before a dated scenario exists; clearly not a recalculated forecast."""
    out={};cost=entities.get('one_time_cost')
    if not cost:return out
    subject=(entities.get('business_subject') or {}).get('value') or 'planned purchase'
    scenario=any(r.get('source')=='run_cash_impact_scenario' for r in records.values())
    minimum=next(((k,r) for k,r in records.items() if r.get('metric')=='min_balance' and r.get('source')=='get_cash_flow'),None)
    if minimum and not scenario and cost.get('currency')==minimum[1].get('currency'):
        key,record=minimum;low=Decimal(record['value']);amount=Decimal(cost['value']);rest=low-amount;currency=record['currency']
        if rest>0:
            narrow=rest<amount*Decimal('0.25')
            brief=('If the full '+cash(amount,currency)+' were deducted at the forecast’s lowest point ('+cash(low,currency)+'), about '+cash(rest,currency)+' would remain'
                   +(', a narrow cushion, so I wouldn’t conclude the '+subject+' is affordable yet.' if narrow else ', but that still needs verified cash and the payment date to confirm.'))
        else:
            brief='Deducting the full '+cash(amount,currency)+' at the forecast’s lowest point ('+cash(low,currency)+') would leave a shortfall of about '+cash(-rest,currency)+', so the '+subject+' does not fit this forecast without changes.'
        out['analysis.cost_cushion']={'kind':'derived_calculation','metric':'illustrative_cost_deduction','value':str(rest),'currency':currency,'source':'get_cash_flow','inputs':[key,'user.one_time_cost'],
            'formula':'minimum projected balance - user-stated one-time cost (illustrative; timing not modeled)',
            'display':'Illustrative arithmetic only: minimum projected balance '+money(low,currency)+' minus your stated cost '+money(amount,currency)+' = '+money(rest,currency)+'. This is not a recalculated forecast: the payment date is not modeled and the forecast is not reconciled with your bank.',
            'brief':brief,'requires':[key.split('.')[0]+'.synthetic_basis']}
    if minimum and not scenario:
        out['analysis.cost_not_applied']={'kind':'data_limitation','metric':'cost_not_in_forecast','value':str(cost['value']),'source':'conversation context',
            'display':'Your stated one-time cost is not part of the baseline forecast; it has not been modeled as a dated outflow.',
            'brief':'Your '+cash(cost['value'],cost.get('currency','CNY'))+' '+subject+' cost is not included in this forecast yet'+('; I need the payment date to model it.' if 'purchase_date' not in entities else '.')}
    return out


def past_what_if_claims(results,entities,direction):
    """C9: remove or add a past cost against recorded totals; arithmetic only, never a performance claim."""
    out={};cost=entities.get('past_expense')
    income=next(((k,v) for k,n,v in results if n=='get_income_summary'),None)
    if not cost or not income:return out
    key,v=income;c=v['currency']
    if cost.get('currency')!=c:raise ClaimError('scenario_currency_mismatch')
    amount=Decimal(cost['value']);sign=-1 if direction=='remove' else 1
    expenses=Decimal(v['expenses'])+sign*amount;net=Decimal(v['net_income'])-sign*amount;span=span_text(v['period'])
    requires=['analysis.past_basis']+([key+'.coverage_gap'] if coverage_gap(v) else [])
    out['analysis.past_basis']={'kind':'data_limitation','metric':'past_what_if_basis','value':'','source':'get_income_summary',
        'display':'Past what-if: recorded totals recalculated with your stated cost '+('removed' if sign<0 else 'added')+'. It does not show how sales or other costs would actually have changed.',
        'brief':'This only recalculates recorded totals; it can’t show how the business would actually have done.'}
    if sign<0 and amount>Decimal(v['expenses']):
        out['analysis.past_exceeds']={'kind':'data_limitation','metric':'past_cost_exceeds_expenses','value':str(amount),'source':'get_income_summary',
            'display':'Your stated cost is larger than all recorded expenses for '+span+' ('+money(v['expenses'],c)+'), so it may not be recorded in that period.',
            'brief':'That is more than all recorded expenses for '+span+' ('+cash(v['expenses'],c)+'), so the cost may not be recorded in that period.'}
        requires.append('analysis.past_exceeds')
    out['analysis.past_what_if']={'kind':'derived_calculation','metric':'past_what_if','value':str(net),'currency':c,'source':'get_income_summary','inputs':[key+'.income','user.past_expense'],
        'formula':'recorded net income '+('+' if sign<0 else '-')+' stated cost; recorded expenses '+('-' if sign<0 else '+')+' stated cost',
        'display':'Past what-if for '+period(v['period'])+': recorded expenses '+money(v['expenses'],c)+' → '+money(expenses,c)+'; net income '+money(v['net_income'],c)+' → '+money(net,c)+'.',
        'brief':('Without the' if sign<0 else 'With an extra')+' '+cash(amount,c)+' cost'+', recorded net income for '+span+' would have been '+cash(net,c)+' instead of '+cash(v['net_income'],c)+' (expenses '+cash(expenses,c)+' instead of '+cash(v['expenses'],c)+').',
        'requires':requires}
    return out


def recommendation_claims(records):
    """Backend-authorized next steps, each derived from evidence already in this turn's records."""
    out={}
    def add(key,brief,display,basis):
        out['advice.'+key]={'kind':'recommendation','metric':key,'value':'','source':'backend_recommendation','basis':basis,'display':display,'brief':brief}
    gaps=[k for k,r in records.items() if r.get('metric')=='incomplete_record_coverage']
    if gaps:
        periods=[span_text(records[k]['period']) for k in gaps if records[k].get('period')]
        add('check_imports','First, check that all transactions for '+' and '.join(dict.fromkeys(periods))+' have been imported before judging performance.',
            'Recommended: confirm transaction imports are complete for periods with incomplete record coverage before interpreting sales changes.',gaps)
    negative=[k for k,r in records.items() if r.get('source')=='run_cash_impact_scenario' and r.get('metric') in ('adjusted','user_cash_adjusted') and ('goes negative' in r.get('brief',''))]
    if negative:
        add('review_expense_timing','Consider changing the timing or size of the payment, since the projection goes negative.',
            'Recommended: review the timing or amount of the planned expense because a modeled scenario projects a negative balance.',negative)
    synthetic=[k for k,r in records.items() if r.get('metric') in ('synthetic_cash_basis','scenario_basis')]
    if synthetic:
        add('confirm_cash','Before committing, check this against your bank balance, because the forecast is not reconciled with your bank.',
            'Recommended: compare the forecast with your bank balance; it is not reconciled with your bank.',synthetic)
    recurring=[k for k,r in records.items() if r.get('metric')=='schedule' and 'monthly payments' in r.get('brief','')]
    if recurring:
        add('verify_payroll','Also confirm your existing payroll obligations, because payroll is not tracked separately.',
            'Recommended: verify existing payroll obligations; there is no separate payroll category.',recurring)
    return out


def scenario_claims(value,prefix):
    records={};currency=value['currency']
    def add(key,display,number='',kind='simulation_result',**source):
        records[prefix+'.'+key]={'kind':kind,'metric':key,'value':str(number),'source':'run_cash_impact_scenario','currency':currency,'display':display,**source}
    basis=prefix+'.scenario_basis'
    add('scenario_basis','Hypothetical projection from the opening balance dated '+day(value['opening_balance_date'])+'; not reconciled with your bank, and not guaranteed affordability or financing approval.','',
        'data_limitation',brief='This is a hypothetical projection and is not reconciled with your bank balance.')
    add('opening','Opening balance as of '+day(value['opening_balance_date'])+': '+money(value['synthetic_opening_balance'],currency)+'. Not reconciled with your bank or with imported transactions.',value['synthetic_opening_balance'],'backend_fact',
        brief='The forecast starts from an opening balance of '+cash(value['synthetic_opening_balance'],currency)+' on '+day(value['opening_balance_date'])+'.',requires=[basis])
    end=(date.fromisoformat(value['assessment_date'])+__import__('datetime').timedelta(days=value['horizon_days'])).isoformat()
    add('period','Hypothetical assessment date: '+day(value['assessment_date'])+'; forecast horizon: '+str(value['horizon_days'])+' days, through '+day(end)+'. Forecast starts on the opening-balance date '+day(value['opening_balance_date'])+'. Latest financial-data date: '+day(value['latest_data_date'])+'.',
        brief='The projection runs through '+day(end)+'.')
    schedule=value['schedule'];total=sum(Decimal(r['amount']) for r in schedule)
    # A recurring cost is described per month, never as a summed one-off amount.
    if len(schedule)==1:cost_text='the '+cash(total,currency)+' payment on '+day(schedule[0]['date'])
    else:cost_text='the new cost of '+cash(schedule[0]['amount'],currency)+' per month from '+day(schedule[0]['date'])+' ('+str(len(schedule))+' monthly payments in the projection)'
    # Combined scenario (C8): the user's % change to recent sales/expenses travels with every adjusted figure.
    changes=value.get('assumed_changes') or {};parts=[]
    for field,word in (('sales_change_percent','sales'),('expense_change_percent','expenses')):
        if changes.get(field):parts.append(word+' '+format(abs(Decimal(str(changes[field]))).normalize(),'f')+'% '+('lower' if changes[field]<0 else 'higher'))
    requires=[basis]
    if parts:
        cost_text+=' and '+' and '.join(parts)+' than the recent pattern'
        add('assumed_changes','Your assumption: '+' and '.join(parts)+' than the recent daily pattern, applied across the whole projection; scheduled payables, receivables and loan repayments are unchanged.','', 'data_limitation',
            brief='The '+' and '.join(p.split()[0] for p in parts)+' change is your assumption, applied to the whole projection.')
        requires=[basis,prefix+'.assumed_changes']
    for key,label in [('baseline','Baseline forecast'),('adjusted','Hypothetical cost-adjusted forecast'),('user_cash_baseline','Separate user-reported cash baseline (unverified)'),('user_cash_adjusted','Separate cost-adjusted user-cash forecast (unverified)')]:
        row=value.get(key)
        if row is None:continue
        display=label+': projected closing balance '+money(row['closing_balance'],currency)+'; minimum projected balance '+money(row['min_balance'],currency)+'. '
        display+=('First projected negative balance: '+day(row['first_negative_date'])+' (day '+str(row['runway_days'])+').' if row['runway_days'] is not None else 'No negative balance projected within this horizon.')
        if row['buffer_days'] is not None:display+=' Expense-coverage estimate: '+str(row['buffer_days'])+' days.'
        display+=' This does not establish actual affordability.'
        lead={'baseline':'Without these changes' if parts else 'Without the new cost','adjusted':'With '+cost_text,'user_cash_baseline':'Starting from the cash you reported, without the new cost','user_cash_adjusted':'Starting from the cash you reported, with '+cost_text}[key]
        brief=lead+', the lowest projected balance is '+cash(row['min_balance'],currency)+(' and the balance first goes negative on '+day(row['first_negative_date'])+'.' if row['first_negative_date'] else ' with no projected negative balance through '+day(end)+'.')
        add(key,display,row['closing_balance'],inputs=['authorized forecast', 'explicit hypothetical schedule'],formula='existing weekday forecast plus incremental scheduled outflows',brief=brief,requires=requires if key in ('adjusted','user_cash_adjusted') else [basis])
    add('schedule','Incremental hypothetical outflow schedule: '+'; '.join(day(r['date'])+': '+money(r['amount'],currency) for r in schedule)+'. Existing scheduled obligations are included once by the baseline.',
        brief='The projection includes '+cost_text+'.')
    add('limitations',' '.join(value['limitations']))
    return records


CALCULATION_OPS=('percent_of','sum','difference','ratio')
CALCULATION_IDS=('calc0','calc1','calc2')

def is_percent(record):
    metric=str(record.get('metric',''))
    return not record.get('currency') and (metric.endswith(('_share','_percent','share_percent','_rate')) or record.get('unit')=='percent')

def calculation_claims(requests,records):
    """The `calculate` tool: arithmetic over existing claim IDs only (server-owned facts or recorded user assumptions).
    The model names the operation and operand IDs; the server checks compatibility, computes and renders the result."""
    out={}
    for request in requests or []:
        key,op,operands=request.get('id'),request.get('op'),request.get('operands') or []
        if key not in CALCULATION_IDS or key in out or op not in CALCULATION_OPS or len(operands)!=2:raise ClaimError('invalid_calculation')
        try:a,b=(records[k] for k in operands)
        except KeyError:raise ClaimError('calculation_operand_without_source') from None
        if any(r.get('kind') in ('recommendation','data_limitation','external_fact') for r in (a,b)):raise ClaimError('invalid_calculation')
        try:x,y=Decimal(str(a['value']).replace(',','')),Decimal(str(b['value']).replace(',',''))
        except Exception:raise ClaimError('invalid_calculation') from None
        if not (x.is_finite() and y.is_finite()):raise ClaimError('invalid_calculation')
        pa,pb=a.get('period'),b.get('period')
        cent=Decimal('.01')
        if op=='percent_of':
            if not is_percent(a) or not b.get('currency') or (pa and pb and pa!=pb):raise ClaimError('incompatible_calculation_operands')
            value,currency,period=(y*x/100).quantize(cent),b['currency'],pb or pa
            shown=cash(value,currency);how=format(x,'f')+'% of '+cash(y,currency)
        elif op in ('sum','difference'):
            if a.get('currency')!=b.get('currency') or is_percent(a)!=is_percent(b):raise ClaimError('incompatible_calculation_operands')
            value,currency=(x+y if op=='sum' else x-y).quantize(cent),a.get('currency')
            period=pa if pa==pb else None
            fmt=(lambda v:cash(v,currency)) if currency else (lambda v:format(v,'f')+('%' if is_percent(a) else ''))
            shown=fmt(value);how=fmt(x)+(' plus ' if op=='sum' else ' minus ')+fmt(y)
        else:
            if a.get('currency')!=b.get('currency') or is_percent(a) or is_percent(b) or y==0:raise ClaimError('incompatible_calculation_operands')
            value,currency=(x/y*100).quantize(Decimal('.1')),None
            period=pa if pa==pb else None
            fmt=(lambda v:cash(v,a['currency'])) if a.get('currency') else (lambda v:format(v,'f'))
            shown=format(value,'f')+'%';how=fmt(x)+' as a share of '+fmt(y)
        assumption=[k for k,r in zip(operands,(a,b)) if r.get('kind') in ('user_assumption','user_date')]
        when=' for '+span_text(period) if period else ''
        basis=' using your assumption' if assumption else ''
        out[key]={'kind':'derived_calculation','metric':'calculation_'+op,'value':str(value),**({'currency':currency} if currency else {}),**({'period':period} if period else {}),
                  'source':'calculate','inputs':list(operands),'formula':op,'unit':None if currency else 'percent',
                  'display':'Calculated by the app'+basis+': '+how+' = '+shown+when+'.','brief':'That is '+shown+when+' ('+how+')'+basis+'.',
                  'requires':list(dict.fromkeys([*assumption,*a.get('requires',[]),*b.get('requires',[])]))}
        records={**records,key:out[key]}
    return out
