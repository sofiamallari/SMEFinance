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
        'currency','transaction_type','payment_method','status','external_reference','description','category'}
REQUIRED={'transaction_date','payment_method','transaction_type','status','currency'}
TYPES={'sale':'sale','income':'sale','sales':'sale','expense':'expense','refund':'refund','return':'refund','reversal':'reversal'}
STATUSES={'completed':'completed','paid':'completed','success':'completed','approved':'completed',
          'pending':'pending','on hold':'pending','failed':'failed','declined':'failed',
          'void':'voided','voided':'voided','cancelled':'voided','canceled':'voided'}
METHODS={'cash':'cash','card':'external_card','credit card':'external_card','debit card':'external_card',
         'external_card':'external_card','wallet':'external_wallet','e-wallet':'external_wallet','external_wallet':'external_wallet',
         'qr':'qr_pay','qr pay':'qr_pay','qr_pay':'qr_pay','tap':'tap_pay','tap_pay':'tap_pay','tap-to-pay':'tap_pay','tap pay':'tap_pay','tap to pay':'tap_pay','pay link':'pay_link','pay_link':'pay_link'}
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
 'description':['description','memo','details','notes','description / vendor','vendor description'], 'category':['category','expense category']}

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
    for field in REQUIRED:
        if values.get(field) in (None,''):raise RowError(field,f'{field} is required')
    from copilot.currency_policy import normalize_source
    try:currency=normalize_source(values['currency'],settings.get('review',{}).get('currency_confirmed') is True or settings.get('source_currency_hints')==['CNY'])
    except ValueError as error:raise RowError('currency',str(error)) from None
    if currency not in IMPORT_CURRENCIES or currency!=merchant.currency:raise RowError('currency','Currency must match this merchant; currency conversion is not supported')
    kind=TYPES.get(str(values['transaction_type']).strip().lower())
    status=STATUSES.get(str(values['status']).strip().lower())
    method=METHODS.get(str(values['payment_method']).strip().lower())
    if kind is None:raise RowError('transaction_type','Use sale, expense, refund or reversal')
    if status is None:raise RowError('status','Use completed, pending, failed or voided')
    if method is None:raise RowError('payment_method','Unsupported payment method')
    net_present=values.get('net_amount') not in (None,'');gross_present=values.get('gross_amount') not in (None,'')
    if not net_present and not gross_present:raise RowError('net_amount','Map net amount or gross amount explicitly; settlement is not revenue')
    adjustments={k:money(values.get(k),k,True) for k in ('discount','tax','refund_amount')}
    if any(v<0 for v in adjustments.values()):raise RowError('amount','Discounts, taxes and refund components must be nonnegative')
    net=money(values.get('net_amount'),'net_amount') if net_present else None
    gross=money(values.get('gross_amount'),'gross_amount') if gross_present else None
    if gross is not None:
        if gross<0:raise RowError('gross_amount','Gross amount must be nonnegative')
        calculated=gross-adjustments['discount']+adjustments['tax']-adjustments['refund_amount']
        if calculated<0:raise RowError('net_amount','Adjustments exceed the gross amount')
        if net is not None and abs(net)!=calculated:raise RowError('net_amount','Net does not equal gross minus discounts plus taxes minus refund component')
        net=calculated
    elif any(adjustments.values()):raise RowError('gross_amount','Gross amount is required when mapping monetary adjustment components')
    if kind=='sale' and net<0:raise RowError('net_amount','Negative sales must be classified as refund or reversal')
    net=abs(net)
    if net==0 and status=='completed':raise RowError('net_amount','Completed transactions must have a nonzero amount')
    signed=net if kind=='sale' else -net
    stamp=timestamp(values['transaction_date'],settings.get('timezone',OFFSETS.get(merchant.country,'+00:00')),settings.get('date_format','iso'),now)
    result={'transaction_date':stamp,'business_date':datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(zone(settings.get('merchant_timezone',OFFSETS.get(merchant.country,'+00:00')))).date().isoformat(),
        'amount':format(signed,'.2f'),'effective_amount':format(signed if status=='completed' else Decimal(0),'.2f'),
        'currency':currency,'transaction_type':kind,'payment_method':method,'status':status,
        'external_reference':safe_text(values.get('external_reference'),'external_reference',100),
        'description':safe_text(values.get('description'),'description',250),'category':safe_text(values.get('category') or 'other','category',80),
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
    # Fee accounting has no canonical field. Never auto-combine supplied net with
    # gross/adjustments when a source fee could explain their difference.
    if 'net_amount' in result and any(re.search(r'\b(?:processing|transaction|service)\s+fees?\b|^fees?$',h,re.I) for h in headers):
        for field in ('gross_amount','discount','tax','refund_amount'):result.pop(field,None)
    return result
