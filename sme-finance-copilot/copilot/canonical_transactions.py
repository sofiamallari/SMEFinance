"""Canonical, decimal-safe records. No downstream financial projections in Task 02."""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from copilot.auth import InputError
from copilot.config import CURRENCIES
IMPORT_CURRENCIES = frozenset(CURRENCIES) | {"CNY"} # Import only; no simulator tax/FX assumptions.

FIELDS={'transaction_date','net_amount','gross_amount','discount','tax','refund_amount','settlement_amount',
        'currency','transaction_type','payment_method','status','external_reference','description','category','classification','processing_fee','sub_category'}
REQUIRED={'transaction_date','payment_method','transaction_type','status','currency'}
TYPES={'sale':'sale','income':'sale','sales':'sale','expense':'expense','refund':'refund','return':'refund','reversal':'reversal'}
STATUSES={'completed':'completed','paid':'completed','success':'completed','approved':'completed',
          'pending':'pending','on hold':'pending','failed':'failed','declined':'failed',
          'void':'voided','voided':'voided','cancelled':'voided','canceled':'voided'}
METHODS={'cash':'cash','card':'external_card','credit card':'external_card','debit card':'external_card',
         'external_card':'external_card','wallet':'external_wallet','e-wallet':'external_wallet','external_wallet':'external_wallet',
         'qr':'qr_pay','qr pay':'qr_pay','qr_pay':'qr_pay','tap':'tap_pay','tap_pay':'tap_pay','tap-to-pay':'tap_pay','tap pay':'tap_pay','tap to pay':'tap_pay','pay link':'pay_link','pay_link':'pay_link',
         'bank transfer':'bank_transfer','bank_transfer':'bank_transfer','transfer':'bank_transfer','wire transfer':'bank_transfer','not recorded':'not_recorded','not_recorded':'not_recorded'}
# Expense-side ways to pay that are not customer payment channels; never part of the sales channel mix.
EXPENSE_METHODS={'bank_transfer','not_recorded'}
OFFSETS={'CN':'+08:00','PH':'+08:00','MY':'+08:00','SG':'+08:00','ID':'+07:00','TH':'+07:00','VN':'+07:00'}
ALIASES={
 'transaction_date':['date','datetime','timestamp','sale date','expense date','transaction date','sale_date','transaction_date'],
 'net_amount':['net amount','net_amount','total paid','total_paid','net sales','transaction amount'],
 'gross_amount':['gross amount','gross_amount','gross sales'], 'discount':['discount','discounts'],
 'tax':['tax','taxes','vat'], 'refund_amount':['refund amount','refund_amount'],
 'settlement_amount':['settlement amount','settlement_amount','settled amount'],
 'currency':['currency','currency code'], 'transaction_type':['type','transaction type','transaction_type'],
 'payment_method':['channel','payment method','payment_method','tender type','tender_type','payment type'],
 'status':['status','transaction status','transaction_status'],
 'external_reference':['reference','reference number','external_reference','receipt no.','receipt no','receipt_no','receipt number','invoice id','transaction id','transaction_id','pos id','expense id'],
 'description':['description','memo','details','notes','description / vendor','vendor description'], 'category':['category','expense category'],
 'processing_fee':['processing fee','processing fees','transaction fee','service fee','merchant fee','mdr fee'],
 'sub_category':['sub-category','sub category','subcategory'],
 'classification':['revenue / cash-in classification','cash-flow / accounting type','cash-in classification','accounting type','classification']}
# Standard revenue/expense template classifications (Copilot Category Guide). A cash-in or cash-out that is not
# revenue or expense (loan proceeds, owner capital, VAT collected, loan principal) gets its own type, so it is never
# counted as sales or expenses. Unrecognised labels are kept and flagged for review, never guessed.
CLASSIFICATIONS={'sales revenue':('sales_revenue',None),'other business income':('other_income',None),
 'customer refund / sales return':('customer_refund','refund'),'customer refund':('customer_refund','refund'),'sales return':('customer_refund','refund'),
 'loan proceeds':('loan_proceeds','cash_in'),'owner contribution':('owner_contribution','cash_in'),'sales tax / vat collected':('vat_collected','cash_in'),
 'operating expense':('operating_expense',None),'tax / permit / government fee':('tax_permit_fee',None),'loan interest / financing fee':('loan_interest',None),
 'loan principal repayment':('loan_principal','cash_out'),'equipment / capital purchase':('capital_purchase',None),
 'income tax / business tax payment':('income_tax',None),'unknown / needs review':('needs_review',None)}

class RowError(InputError):
    def __init__(self,field,message,correction='Correct the source value or mapping and validate again.'):
        super().__init__(message);self.field=field;self.correction=correction

def money(value,field='amount',optional=False):
    if optional and value in (None,''):return Decimal('0.00')
    if isinstance(value,bool):raise RowError(field,'A decimal amount is required')
    text=str(value).strip()
    if not re.fullmatch(r'-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?',text):
        raise RowError(field,'Use a decimal point and optional comma thousands separators')
    try:amount=Decimal(text.replace(',',''))
    except InvalidOperation:raise RowError(field,'Invalid decimal amount')
    if not amount.is_finite() or abs(amount)>Decimal('1e12') or amount!=amount.quantize(Decimal('.01')):
        raise RowError(field,'Amount must be finite, at most 1 trillion, with at most 2 decimal places')
    return amount.quantize(Decimal('.01'))

def zone(value):
    if value in ('Z','UTC','+00:00'):return timezone.utc
    if isinstance(value,str) and '/' in value:
        try:return ZoneInfo(value)
        except (ZoneInfoNotFoundError,ValueError):raise RowError('timezone','Choose a valid IANA timezone')
    if not isinstance(value,str) or not re.fullmatch(r'[+-]\d{2}:\d{2}',value):raise RowError('timezone','Choose an IANA timezone or explicit UTC offset')
    hours,minutes=map(int,value[1:].split(':'))
    if hours>14 or minutes>59 or (hours==14 and minutes):raise RowError('timezone','Invalid UTC offset')
    return timezone(timedelta(minutes=(hours*60+minutes)*(1 if value[0]=='+' else -1)))

def timestamp(value,offset,date_format,now):
    if not isinstance(value,str) or not value.strip():raise RowError('transaction_date','Transaction date/time is required')
    text=value.strip()
    try:
        if '/' in text:
            formats={'day_first':['%d/%m/%Y %H:%M:%S','%d/%m/%Y %H:%M','%d/%m/%Y'],
                     'month_first':['%m/%d/%Y %H:%M:%S','%m/%d/%Y %H:%M','%m/%d/%Y']}.get(date_format,[])
            parsed=None
            for fmt in formats:
                try:parsed=datetime.strptime(text,fmt);break
                except ValueError:continue
            if parsed is None:raise ValueError()
        else:parsed=datetime.fromisoformat(text.replace('Z','+00:00'))
        if parsed.tzinfo is None:
            tz=zone(offset);local=parsed
            parsed=local.replace(tzinfo=tz)
            if isinstance(tz,ZoneInfo):
                if parsed.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)!=local or parsed.utcoffset()!=local.replace(tzinfo=tz,fold=1).utcoffset():
                    raise RowError('transaction_date','Ambiguous or nonexistent local time; supply an explicit UTC offset')
        utc=parsed.astimezone(timezone.utc)
        if utc.year<2000 or utc.timestamp()>now+300:raise ValueError()
        return utc.isoformat().replace('+00:00','Z')
    except ValueError:raise RowError('transaction_date','Invalid or future date; select the correct date format and timezone')

def safe_text(value,field,limit):
    if value is not None and not isinstance(value,str):raise RowError(field,'Text fields must contain text')
    text=str(value or '').strip()
    if len(text)>limit:raise RowError(field,f'{field} exceeds {limit} characters')
    if text and text[0] in '=+@-' and not re.fullmatch(r'-?\d+(?:\.\d+)?',text):
        raise RowError(field,'Spreadsheet formula-like text is not accepted')
    if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+',text) or re.search(r'\b(?:\d[ -]?){13,19}\b',text):
        raise RowError(field,'Possible personal or card information is not accepted')
    if re.search(r'(?i)\bbearer\s+|\bgh[pousr]_|\bsk-[a-z0-9]',text):raise RowError(field,'Credentials are not accepted in transaction text')
    return text

def normalize(values,merchant,settings,now,strict=True):
    if not isinstance(values,dict) or (strict and set(values)-FIELDS):raise RowError('record','Unsupported or protected transaction fields')
    for field in REQUIRED-{'payment_method'}: # an expense report may not record how it was paid
        if values.get(field) in (None,''):raise RowError(field,f'{field} is required')
    from copilot.currency_policy import normalize_source
    try:currency=normalize_source(values['currency'],settings.get('review',{}).get('currency_confirmed') is True or settings.get('source_currency_hints')==['CNY'])
    except ValueError as error:raise RowError('currency',str(error)) from None
    if currency not in IMPORT_CURRENCIES or currency!=merchant.currency:raise RowError('currency','Currency must match this merchant; currency conversion is not supported')
    kind=TYPES.get(str(values['transaction_type']).strip().lower())
    status=STATUSES.get(str(values['status']).strip().lower())
    if kind is None:raise RowError('transaction_type','Use sale, expense, refund or reversal')
    label=re.sub(r'\s+',' ',str(values.get('classification') or '')).strip().lower()
    classification,override=CLASSIFICATIONS.get(label,('needs_review' if label else None,None))
    if override=='refund' and kind=='expense':override=None # a refund line in an expense report stays an expense
    if override=='cash_in' and kind=='expense':raise RowError('classification','A cash-in classification cannot appear in an expense report')
    if override=='cash_out' and kind!='expense':raise RowError('classification','A cash-out classification belongs in an expense report')
    kind=override or kind
    raw=str(values.get('payment_method') or '').strip().lower()
    spending=kind in ('expense','cash_out')
    if not raw:
        if not spending:raise RowError('payment_method','payment_method is required for sales and other cash-in')
        method='not_recorded' # expense reports normally record what a cost was for, not how it was paid
    else:
        method=METHODS.get(raw)
        if method is None:raise RowError('payment_method','Unsupported payment method')
        if method in EXPENSE_METHODS and not spending:
            if method!='bank_transfer':raise RowError('payment_method','A sale needs the customer payment method')
            method='external_wallet' # a customer bank transfer is an other-bank payment
    if status is None:raise RowError('status','Use completed, pending, failed or voided')

    net_present=values.get('net_amount') not in (None,'');gross_present=values.get('gross_amount') not in (None,'')
    if not net_present and not gross_present:raise RowError('net_amount','Map net amount or gross amount explicitly; settlement is not revenue')
    adjustments={k:money(values.get(k),k,True) for k in ('discount','tax','refund_amount','processing_fee')}
    if any(v<0 for v in adjustments.values()):raise RowError('amount','Discounts, taxes and refund components must be nonnegative')
    net=money(values.get('net_amount'),'net_amount') if net_present else None
    gross=money(values.get('gross_amount'),'gross_amount') if gross_present else None
    if gross is not None:
        if gross<0:raise RowError('gross_amount','Gross amount must be nonnegative')
        calculated=gross-adjustments['discount']+adjustments['tax']-adjustments['refund_amount']-adjustments['processing_fee']
        if calculated<0:raise RowError('net_amount','Adjustments exceed the gross amount')
        if net is not None and abs(net)!=calculated:raise RowError('net_amount','Net does not equal gross minus discounts plus taxes minus refund component minus processing fee')
        net=calculated
    elif any(adjustments.values()):raise RowError('gross_amount','Gross amount is required when mapping monetary adjustment components')
    if kind=='sale' and net<0:raise RowError('net_amount','Negative sales must be classified as refund or reversal')
    net=abs(net)
    if net==0 and status=='completed':raise RowError('net_amount','Completed transactions must have a nonzero amount')
    signed=net if kind in ('sale','cash_in') else -net
    stamp=timestamp(values['transaction_date'],settings.get('timezone',OFFSETS.get(merchant.country,'+00:00')),settings.get('date_format','iso'),now)
    result={'transaction_date':stamp,'business_date':datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(zone(settings.get('merchant_timezone',OFFSETS.get(merchant.country,'+00:00')))).date().isoformat(),
        'amount':format(signed,'.2f'),'effective_amount':format(signed if status=='completed' else Decimal(0),'.2f'),
        'currency':currency,'transaction_type':kind,'payment_method':method,'status':status,
        'external_reference':safe_text(values.get('external_reference'),'external_reference',100),
        'description':safe_text(values.get('description'),'description',250),'category':safe_text(values.get('category') or 'other','category',80),
        **({'classification':classification} if classification else {}),
        **({'sub_category':safe_text(values.get('sub_category'),'sub_category',120)} if values.get('sub_category') not in (None,'') else {}),
        'gross_amount':format(gross,'.2f') if gross is not None else None,
        **{k:format(v,'.2f') for k,v in adjustments.items()},
        'settlement_amount':format(money(values['settlement_amount'],'settlement_amount'),'.2f') if values.get('settlement_amount') not in (None,'') else None,
        'normalization_version':1,'source_timezone':settings.get('timezone',OFFSETS.get(merchant.country,'+00:00'))}
    return result

def fingerprint(row):
    keys=('transaction_date','amount','currency','transaction_type','payment_method','status','external_reference','description','category',
          'gross_amount','discount','tax','refund_amount','settlement_amount')
    value={k:row.get(k) for k in keys};value['external_reference']=(row.get('external_reference') or '').casefold()
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def suggest(headers):
    normalized={}
    for h in headers:
        key=re.sub(r'\s*\([^)]*\)\s*$','',h.strip().lower())
        normalized.setdefault(key,[]).append(h)
    result={}
    for field,aliases in ALIASES.items():
        matches=[h for a in aliases for h in normalized.get(a,[])]
        if len(set(matches))==1:result[field]=matches[0]
    # A processing fee reconciles gross and net (gross - fee = net) only when all three are mapped; otherwise
    # never auto-combine supplied net with gross/adjustments that a fee could explain.
    fee=any(re.search(r'\b(?:processing|transaction|service)\s+fees?\b|^fees?$',h,re.I) for h in headers)
    if fee and not {'net_amount','gross_amount','processing_fee'}<=set(result):result.pop('processing_fee',None)
    if 'net_amount' in result and fee and 'processing_fee' not in result:
        for field in ('gross_amount','discount','tax','refund_amount'):result.pop(field,None)
    return result
