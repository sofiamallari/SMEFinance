"""Deterministic presentation suggestions. No accounting rules or worksheet-name inference."""
import re
from copilot.canonical_transactions import suggest,TYPES

def report_profile(headers,samples):
    mappings=suggest(headers)
    clean={re.sub(r'\s*\([^)]*\)\s*$','',h.strip().casefold()):h for h in headers}
    type_header=mappings.get('transaction_type')
    kinds={TYPES.get(str(v).strip().casefold()) for v in samples.get(type_header,[]) if str(v).strip()} if type_header else set()
    if kinds and None not in kinds:
        if kinds=={'expense'}:return {'kind':'expense','reasons':['Source transaction types contain Expense.'],'ambiguous':False}
        if kinds<={'sale','refund','reversal'}:return {'kind':'revenue','reasons':['Source transaction types contain sales/refunds/reversals.'],'ambiguous':False}
        return {'kind':None,'reasons':['Mixed source transaction types: separate revenue and expense records into compatible sources. Source types are never silently rewritten.'],'ambiguous':True}
    expense=sum(any(token in h for h in clean) for token in ('expense date','expense id','expense category','subcategory','description / vendor'))
    revenue=sum(any(token in h for h in clean) for token in ('net amount','gross amount','processing fee','sale date','transaction id'))
    has_date='transaction_date' in mappings
    has_amount=bool({'net_amount','gross_amount'}&set(mappings)) or 'amount' in clean
    if has_date and has_amount and expense>=2 and revenue<2:return {'kind':'expense','reasons':['Date/amount columns and multiple expense-specific columns detected.'],'ambiguous':False}
    if has_date and has_amount and revenue>=2 and expense<2:return {'kind':'revenue','reasons':['Date/amount columns and multiple revenue-specific columns detected.'],'ambiguous':False}
    return {'kind':None,'reasons':['Column evidence does not establish a single report profile. Please choose and confirm.'],'ambiguous':True}
