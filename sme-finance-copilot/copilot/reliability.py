"""Backend financial claims: model text never establishes financial truth."""
from dataclasses import dataclass,asdict
from datetime import date,datetime,timezone,timedelta
from decimal import Decimal,InvalidOperation
import hashlib,json,re

class EvidenceError(ValueError):pass

STATUSES={'VERIFIED','ESTIMATED','HYPOTHESIS','INSUFFICIENT_EVIDENCE','UNAUTHORIZED'}
PROVENANCE={'historical_pos','manual','simulated_payment','synthetic_seed','mixed','forecast','simulated_application','no_records'}

@dataclass(frozen=True)
class Fact:
    evidence_id:str
    source:str
    merchant_id:str
    metric:str
    value:str
    currency:str|None
    period_start:str
    period_end:str
    as_of:str
    provenance:str
    quality_status:str
    method_version:str
    record_count:int
    assumptions:tuple
    limitations:tuple
    status:str

    def validate(self,merchant,currency):
        if self.merchant_id!=merchant:raise EvidenceError('Evidence belongs to another merchant')
        if self.currency not in (None,currency):raise EvidenceError('Evidence currency mismatch')
        try:
            if date.fromisoformat(self.period_start)>date.fromisoformat(self.period_end):raise ValueError()
            stamp=datetime.fromisoformat(self.as_of.replace('Z','+00:00'))
            if stamp.tzinfo is None or stamp>datetime.now(timezone.utc)+timedelta(seconds=300) or datetime.now(timezone.utc)-stamp>timedelta(seconds=300):raise ValueError()
            if not self.source or not self.method_version:raise ValueError()
            if self.provenance=='forecast' and self.status!='ESTIMATED':raise ValueError()
            if not self.value or not self.metric or not self.evidence_id or self.record_count<0:raise ValueError()
            if self.status not in STATUSES or self.provenance not in PROVENANCE or self.quality_status!='validated':raise ValueError()
            if self.metric=='payment_reference':
                if not re.fullmatch(r'SBX-(QR|TAP|PAY)-'+re.escape(merchant)+r'-[A-F0-9]{8}',self.value):raise ValueError()
            elif self.metric=='application_reference':
                if not re.fullmatch(r'APP-(?:[a-f0-9]{20}|'+re.escape(merchant)+r'-[0-9]{4})',self.value):raise ValueError()
            elif self.metric=='payment_status':
                if self.value not in ('PENDING','PAID','EXPIRED','CANCELLED','FAILED','REFUNDED','PARTIALLY_REFUNDED'):raise ValueError()
            elif self.metric=='application_status':
                if self.value!='SUBMITTED_FOR_LENDER_REVIEW':raise ValueError()
            elif not Decimal(self.value).is_finite():raise ValueError()
        except (ValueError,TypeError,InvalidOperation):raise EvidenceError('Invalid financial evidence') from None
        return self

def fact(source,merchant,metric,value,currency,start,end,provenance='synthetic_seed',status='VERIFIED',count=0,limitations=(),assumptions=(),method='existing-v1'):
    if isinstance(value,(float,int,Decimal)) and not isinstance(value,bool):
        number=Decimal(str(value))
        if not number.is_finite():raise EvidenceError('Non-finite financial value')
        value=format(number,'f')
    if currency is not None:
        number=Decimal(str(value))
        if not number.is_finite() or number!=number.quantize(Decimal('.01')):raise EvidenceError('Invalid monetary evidence precision')
        value=format(number,'.2f')
    payload={'source':source,'merchant_id':merchant,'metric':metric,'value':str(value),'currency':currency,
             'period_start':str(start),'period_end':str(end),'as_of':datetime.now(timezone.utc).isoformat(),
             'provenance':provenance,'quality_status':'validated','method_version':method,'record_count':count,
             'assumptions':tuple(assumptions),'limitations':tuple(limitations),'status':status}
    payload['evidence_id']='EV-'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:24]
    return Fact(**payload)

def validate_claims(response,facts,merchant,currency):
    """Full typed equality, not numeric substrings or model confidence."""
    if not isinstance(response,dict) or set(response)!={'claims','insights'}:raise EvidenceError('Unexpected explanation structure')
    if not isinstance(response['claims'],list) or not 1<=len(response['claims'])<=40:raise EvidenceError('Verified claims are required')
    allowed={f.evidence_id:f.validate(merchant,currency) for f in facts}
    keys={'evidence_id','metric','value','currency','merchant_id','period_start','period_end','status','provenance','source'}
    chosen=[];seen=set()
    for claim in response['claims']:
        if not isinstance(claim,dict) or set(claim)!=keys:raise EvidenceError('Invalid claim fields')
        original=allowed.get(claim['evidence_id'])
        if not original:raise EvidenceError('Unsupported evidence reference')
        if any(claim[k]!=getattr(original,k) for k in keys):raise EvidenceError('Financial claim does not match evidence')
        if original.evidence_id in seen:raise EvidenceError('Repeated evidence reference')
        seen.add(original.evidence_id);chosen.append(original)
    if not isinstance(response['insights'],list) or len(response['insights'])>3 or len(set(response['insights']))!=len(response['insights']) or not set(response['insights'])<=set(allowed_insights(facts)):raise EvidenceError('Unsupported interpretation')
    return chosen,response['insights']

def claim(f):
    return {k:getattr(f,k) for k in ('evidence_id','metric','value','currency','merchant_id','period_start','period_end','status','provenance','source')}

def domain(text):
    t=text.lower().strip()
    if re.search(r'\b(recipe|cake recipe|write.*game|tell.*joke|political|horoscope)\b',t):return 'outside'
    if re.search(r'\b(approve|guarantee|disburse|real transfer|credit limit|approval date)\b',t):return 'unsupported_approval'
    if re.search(r'\b(upload|import).*(pos|csv|xlsx|file)|\b(pos|csv|xlsx).*upload',t):return 'guidance'
    if re.search(r'\binflation\b',t):return 'education'
    if not re.search(r'\b(my|our|recorded|projected)\b',t) and re.search(r'\b(what is|explain|how does|how do).*(financ|rbf|inventory|cash|revenue|payment)',t):return 'education'
    if re.search(r'\b(application|application status)\b',t):return 'applications'
    if re.search(r'\b(milestone|incentive|tier|reward)\b',t):return 'incentive'
    if re.search(r'\b(report)\b',t):return 'report'
    if re.search(r'\b(alerts?|risks?|warnings?)\b',t):return 'cashflow'
    if re.search(r'\b(sales|revenue|income|profits?|expenses?|refund|transactions?|dashboard|declin|growth|last month|this month)\b',t):return 'sales'
    if re.search(r'\b(rbf|advance|borrow|repay)\b',t):return 'rbf'
    if re.search(r'\b(financ\w*|loan|readiness|equipment|capital)\b',t):return 'financing'
    if re.search(r'\b(cash|buffer|forecast|balance|liquidity|runway)\b',t):return 'cashflow'
    if re.search(r'\b(duplicate|unreconciled|quality|invalid|monitoring)\b',t):return 'quality'
    if re.search(r'\b(payment|paid|settled|qr|tap|pay link)\b',t):return 'payments'
    if re.search(r'\b(business|stage|capacity|health|assessment|doing|stuck|operational)\b',t):return 'assessment'
    if re.search(r'\b(why|what about|same|that|fee|total)\b',t):return 'follow_up'
    return 'outside'

EDUCATION={
 'rbf':'Revenue-based financing provides an advance repaid from a share of recorded sales. The lender determines eligibility and terms. The calculator is indicative, and neither a quote nor an assessment is a credit approval.',
 'inflation':'Inflation can raise inventory and operating costs. Compare recorded supplier expenses, selling prices and margins over the same period. Your records may show a change, but they do not establish inflation as its cause.',
 'cash':'Revenue records sales; it is not the same as available cash. Cash balances require balance and settlement evidence. Forecasts are estimates based on documented assumptions and are not guaranteed.'}
REFUSAL='I can help with your business transactions, payments, cash flow, financing, and other SME financial operations.'

def allowed_insights(facts):
    codes=['cause_unconfirmed','indicative_only','forecast_not_guaranteed']
    values={f.metric:Decimal(f.value) for f in facts if f.metric in ('net_sales','previous_net_sales')}
    if 'net_sales' in values and 'previous_net_sales' in values:
        if values['net_sales']<values['previous_net_sales']:codes.append('recorded_sales_decreased')
        elif values['net_sales']>values['previous_net_sales']:codes.append('recorded_sales_increased')
        else:codes.append('recorded_sales_unchanged')
    return codes
