"""Conservative structural detection. Never evaluates cells or classifies money."""
import re

VERSION=1
DATE_HEADERS={'date','datetime','timestamp','transaction date','transaction datetime','transaction date time','sale date','expense date','payment date'}
AMOUNT_HEADERS={'amount','net amount','gross amount','net sales','gross sales','total paid','expense amount','amount paid','transaction amount'}
MONEY_HEADERS=AMOUNT_HEADERS|{'processing fee','processing fees','fee','fees','discount','discounts','tax','taxes','vat','refund amount','settlement amount'}
ID_HEADERS={'transaction id','expense id','external reference','reference','reference number','receipt no','receipt number','invoice id','pos id'}
SUMMARY=re.compile(r'(?:grand total|total|subtotal|sub total|summary)(?: (?:revenue|sales|expenses|expense|amount|net|gross|fees|payments|transactions))?\Z')
DATE_VALUE=re.compile(r'(?:\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?|\d{1,2}/\d{1,2}/\d{4}(?: \d{1,2}:\d{2}(?::\d{2})?)?)\Z')
NUMBER=re.compile(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\Z')

def header_text(value):
    text=re.sub(r'\([^)]*\)','',str(value)).casefold().replace('_',' ')
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]',' ',text)).strip()

def header_shape(row):
    values=row['values']
    if row.get('formula_columns') or not values or any(not v.strip() for v in values):return None
    headers=[header_text(v) for v in values]
    if len({v.casefold() for v in values})!=len(values):return None
    dates=[i for i,h in enumerate(headers) if h in DATE_HEADERS]
    amounts=[i for i,h in enumerate(headers) if h in AMOUNT_HEADERS]
    if len(dates)!=1 or not amounts:return None
    return {'date':dates[0],'amounts':amounts,'money':{i for i,h in enumerate(headers) if h in MONEY_HEADERS},'ids':{i for i,h in enumerate(headers) if h in ID_HEADERS},'width':len(values)}

def cell(row,index):return row['values'][index].strip() if index<len(row['values']) else ''

def summary_row(row,shape):
    # A formula alone is never evidence of a summary. Identity/date must be blank.
    if cell(row,shape['date']) or any(cell(row,i) for i in shape['ids']):return False
    formulas=set(row.get('formula_columns',[]))
    if not formulas<=shape['money']:return False
    labels=[]
    for i,value in enumerate(row['values']):
        value=value.strip()
        if not value or i in formulas:continue
        if i in shape['money'] and NUMBER.fullmatch(value):continue
        if SUMMARY.fullmatch(header_text(value)):labels.append(value)
        else:return False
    return bool(labels)

def detect_table(rows):
    nonempty=[r for r in rows if any(v.strip() for v in r['values']) or r.get('formula_columns')]
    candidates=[(r,header_shape(r)) for r in nonempty if header_shape(r)]
    result={'version':VERSION,'status':'review_required','reasons':[],'header_row':None,'last_data_row':None,'transaction_count':None,
            'header_candidates':[r['row'] for r,_ in candidates],'excluded_summary_rows':[],'empty_rows':len(rows)-len(nonempty),'introduction_rows':0,'review_rows':[]}
    numbers=[r['row'] for r in rows]
    result['nonempty_row_count']=len(nonempty)
    if any(type(n) is not int or n<1 for n in numbers) or any(a>=b for a,b in zip(numbers,numbers[1:])):
        result['reasons']=['Source row order or numbering is ambiguous; review is required.']
        result['review_rows']=nonempty[:20]
        return result
    if len(candidates)!=1:
        result['reasons']=['No unique date-and-amount header found.' if not candidates else 'Multiple possible headers or transaction tables found. No table was selected automatically.']
        if candidates:result['header_row']=candidates[0][0]['row']
        sample=[*nonempty[:10],*[r for r,_ in candidates[:5]],*nonempty[-5:]]
        result['review_rows']=list({r['row']:r for r in sample}.values())
        return result
    header,shape=candidates[0];result['header_row']=header['row'];before=[r for r in nonempty if r['row']<header['row']]
    result['introduction_rows']=len(before)
    if any((sum(bool(v.strip()) for v in r['values'])>=2 and any(NUMBER.fullmatch(v.strip()) for v in r['values'])) or ((cell(r,shape['date']) or any(cell(r,i) for i in shape['ids'])) and any(NUMBER.fullmatch(cell(r,i)) or i in r.get('formula_columns',[]) for i in shape['money'])) for r in before):
        result['reasons'].append('Possible transaction records appear before the header; review the range.')
    data=[r for r in nonempty if r['row']>header['row']]
    summaries=[]
    while data and summary_row(data[-1],shape):summaries.insert(0,data.pop())
    result['excluded_summary_rows']=[r['row'] for r in summaries]
    if not data:result['reasons'].append('No individual transaction records found after the header.')
    questionable=[]
    for row in data:
        issues=[]
        if row.get('formula_columns'):issues.append('Formula cells occur inside the candidate transaction table; values are not trustworthy source data.')
        if len(row['values'])>shape['width']:issues.append('Values extend beyond the detected header.')
        if summary_row(row,shape):issues.append('A summary occurs before later records; the boundary is uncertain.')
        if not DATE_VALUE.fullmatch(cell(row,shape['date'])):issues.append('A nonempty row has a missing or unrecognized transaction date; it has not been discarded.')
        if issues:
            questionable.append(row)
            for issue in issues:
                if issue not in result['reasons']:result['reasons'].append(issue)
    result['transaction_count']=len(data);result['last_data_row']=data[-1]['row'] if data else None
    # Sample includes records at both boundaries plus every represented issue type.
    sample=[header,*data[:3],*questionable[:12],*data[-3:],*summaries[:3]]
    result['review_rows']=list({r['row']:r for r in sample}.values())[:24]
    if not result['reasons']:result['status']='ready'
    return result
