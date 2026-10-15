"""Preferred operating currency and honest legacy display; no FX or migrations."""
from decimal import Decimal
CODE='CNY'
NAME='RMB'
SYMBOL='¥'
DECIMALS=2
PUBLIC={'code':CODE,'name':NAME,'symbol':SYMBOL,'decimals':DECIMALS,'label':'CNY (RMB ¥)'}
def format_money(value,currency=CODE):
    if value is None:return 'Unavailable'
    number=Decimal(str(value));prefix=SYMBOL if currency==CODE else str(currency)+' '
    return ('-' if number<0 else '')+prefix+format(abs(number),',.2f')
def normalize_source(value,confirmed_yuan=False):
    code=str(value).strip().upper()
    if code=='RMB':return CODE
    if code in ('¥','￥'):
        if not confirmed_yuan:raise ValueError('Yuan symbol is ambiguous. Use explicit CNY/RMB or verify Chinese Yuan source context; no FX conversion.')
        return CODE
    return code
def legacy_note(currency):
    return '' if currency==CODE else 'Legacy '+str(currency)+' workspace: original amounts/currency are preserved and are not RMB totals. Manual migration is required for a CNY-only cutover; no conversion was performed.'
