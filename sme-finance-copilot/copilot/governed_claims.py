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
            'user_assumption','backend_fact','derived_calculation','simulation_result','external_fact','unsupported_claim']}},
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


def purchase_context(text,previous=None):
    """Only extract explicitly stated assumptions; never infer liquidity or costs."""
    result=dict(previous or {})
    if re.search(r'\b(?:state|pretend|fabricate|invent|assume|imagine)\b.{0,90}\b(?:cash|balance)\b',text,re.I):return result
    item=re.search(r'\b(oven|equipment|inventory|warehouse(?: lot)?|property|shop|branch|investment|machinery|vehicle)\b',text,re.I)
    if item:result['item']=item.group(0).lower()
    amounts=list(re.finditer(r'(RMB|CNY|USD|PHP|¥|￥)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)',text,re.I))
    if amounts:
        first=amounts[0];currency=first.group(1).upper()
        clause=re.split(r'[.!?;\n]',text[:first.start()])[-1]
        cash_statement=bool(re.search(r'(?:available cash|cash balance|cash on hand|bank balance|cash reserves)(?:\s+(?:is|of|are|equals|totals))?\s*[:=]?\s*$',clause,re.I) or (re.search(r'\b(?:I|we)\s+(?:currently\s+)?have\s*$',clause,re.I) and re.match(r'\s+(?:in cash|cash available|cash on hand)\b',text[first.end():],re.I)))
        extra=bool(result.get('price') and re.search(r'installation|delivery|setup|additional',text[max(0,first.start()-35):first.start()],re.I))
        if cash_statement and not re.search(r'\b(?:state|pretend|fabricate|invent|assume|imagine|hypothetical)\b',clause,re.I):
            result['reported_cash']=format(Decimal(first.group(2).replace(',','')),'.2f')
            result['reported_cash_currency']='CNY' if currency in ('RMB','CNY','¥','￥') else currency
        elif extra:
            result['extra_costs']='additional costs stated by user; not verified or summed'
            result['additional_cost']=format(Decimal(first.group(2).replace(',','')),'.2f')
        elif not result.get('price') or re.search(r'price|worth|oven|equipment|inventory|warehouse|purchase',text,re.I):
            amount=Decimal(first.group(2).replace(',',''))
            scale=re.match(r'\s*(thousand|million|billion)\b',text[first.end():],re.I)
            if scale:amount*=Decimal({'thousand':1000,'million':1000000,'billion':1000000000}[scale.group(1).lower()])
            result['price']=format(amount,'.2f')
            result['currency']='CNY' if currency in ('RMB','CNY','¥','￥') else currency
    for amount in amounts:
        before=text[max(0,amount.start()-35):amount.start()]
        label='down_payment' if re.search(r'down[- ]?payment',before,re.I) else 'additional_cost' if re.search(r'installation|delivery|setup|additional|acquisition',before,re.I) else None
        if label:
            result[label]=format(Decimal(amount.group(2).replace(',','')),'.2f')
            code=amount.group(1).upper();result[label+'_currency']='CNY' if code in ('RMB','CNY','¥','￥') else code
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
    elif re.search(r'(installation|delivery|setup|additional|acquisition).{0,30}(?:RMB|CNY|¥|\d)',text,re.I):result['extra_costs']='additional costs stated by user; not verified or summed'
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
        span=value['period'];currency=value['currency']
        add('net_sales','recorded_net_sales',value['recorded_net_sales'],'Recorded net sales: '+money(value['recorded_net_sales'],currency)+', for '+period(span)+'. Revenue is not profit or available cash.',currency=currency,period=span)
        add('transaction_count','sales_payment_transaction_count',value['transaction_count'],'Sales/payment transaction count: '+format(value['transaction_count'],',')+', for '+period(span)+'. Transaction volume is not cash balance.',period=span)
    elif name=='run_survival_simulation':
        r=value['simulation_results'];span=value['baseline_period'];currency=r['currency']
        for metric,label in [('baseline_monthly_operating_result','Baseline monthly operating result'),('simulated_monthly_operating_result','Simulated monthly operating result'),('cumulative_operating_result','Cumulative simulated operating result')]:
            kind='deterministic_result' if metric.startswith('baseline') else 'simulation_output'
            add(metric,metric,r[metric],label+': '+money(r[metric],currency)+'. Baseline period: '+period(span)+'. Hypothetical operating-result calculation; not verified cash or purchase affordability.',kind,currency=currency,period=span)
    elif name=='get_cash_flow':
        for field,label in [('cash_inflows','Estimated inflow'),('cash_outflows','Estimated outflow')]:
            for index,row in enumerate(value[field]):
                add(field+str(index),field,row['amount'],label+' on '+day(row['date'])+': '+money(row['amount'],value['currency'])+'. Forecast result, not actual available cash.', 'deterministic_result',currency=value['currency'],period=value['period'])
    elif name=='get_transaction_trends':
        for index,row in enumerate(value):
            add('sales'+str(index),'recorded_net_sales',row['recorded_net_sales'],'Recorded net sales for '+row['period']+': '+money(row['recorded_net_sales'],currency)+'. Sales are not profit or cash.',currency=currency,period=row['period'])
            add('count'+str(index),'sales_payment_transaction_count',row['transaction_count'],'Sales/payment count for '+row['period']+': '+format(row['transaction_count'],',')+'.',period=row['period'])
    elif name=='get_payment_channel_mix':
        for index,row in enumerate(value):
            add('share'+str(index),'transaction_volume_share',str(row['share_percent']),row['channel']+': '+format(row['share_percent'],'.2f')+'% of transaction volume, not revenue share.','deterministic_result',period=row['period'])
    elif name in ('get_financing_status','get_financing_details'):
        reference=value['application_reference']
        if name=='get_financing_status':add('status','submitted_application_status',value['status'],'Application '+reference+': '+value['status']+' (submission status; not credit approval).',application_reference=reference)
        else:add('requested_amount','requested_amount',value['requested_amount'],'Application '+reference+' requested amount: '+money(value['requested_amount'],currency)+'. Approved amount and repayment terms are unavailable.',currency=currency,application_reference=reference)
    return records


def verify_response(content,records):
    """Model selects typed records; backend owns values, labels and provenance.

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
            output.append(record['display']);used.append(key)
        elif set(segment)=={'text'} and isinstance(segment['text'],str):
            text=segment['text'].strip()
            # Text is connective explanation/clarification. Numeric assertions use
            # typed records, not a numeric allowlist that launders assumptions.
            text=re.sub(r'(?m)^\s*\d{1,2}[.)]\s+','',text)
            if re.search(r'\d|\b(?:million|billion|thousand|hundred)\b',text,re.I):raise ClaimError('untyped_numeric_claim')
            conclusion_text=re.sub(r"(?:I |we )?(?:cannot|can't|do not|don't) (?:yet )?(?:determine|establish|confirm|know) (?:whether|if) (?:your business|you) (?:can|could|will) afford",'',text,flags=re.I)
            if re.search(r'https?://|(?:you|your business)\s+(?:can|could|will)\s+afford|(?:purchase|oven|investment)\s+is\s+affordable|definitely afford|guaranteed|credit (?:is )?approved|loan (?:is )?approved|I (?:submitted|paid|purchased|transferred)',conclusion_text,re.I):raise ClaimError('unsupported_financial_conclusion')
            for clause in re.split(r'[.;\n]',text):
                if clause.strip().lower() in {
                    'affordability assessments require a comprehensive review of your current cash flow and outstanding liabilities',
                    'no approved one-time purchase affordability calculation is available'
                }:continue
                uncertain=bool(re.search(r"cannot|can't|not|unverified|unavailable|missing|unknown|uncertain|whether|depends|need|verify|verification|assuming|hypothetical|\bif\b|could|\?",clause,re.I))
                risky=re.search(r'(?:your|our|recorded|the business).{0,35}(?:profitable|healthy|strong|cash|balance|profit|reserves|grew|increased|decreased)|you have (?:enough|sufficient)|you (?:have|hold|possess).{0,20}(?:cash|balance)|available cash is|bank balance is|profit is|\bverified (?:available )?cash|sales (?:are|is|equals?|means?) (?:your )?(?:available )?cash|spend (?:your |the )?(?:net )?sales|sales.{0,20}spendable|(?:our|your).{0,25}(?:loan|financing application)|afford(?:able|ability)?',clause,re.I)
                if risky and not uncertain:raise ClaimError('unsupported_business_fact')
            output.append(text)
        else:raise ClaimError('invalid_claim_segment')
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
        return text+'\nSource: existing authorized backend services. Includes synthetic/sandbox data where applicable.'
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
