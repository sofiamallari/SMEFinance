"""CLDR currency metadata; catalog membership never implies transaction eligibility."""
from functools import lru_cache
from babel.numbers import get_currency_name, get_currency_symbol, get_currency_precision, list_currencies
from zoneinfo import available_timezones

@lru_cache(maxsize=1)
def catalog():
    return tuple({'code':c,'name':get_currency_name(c,locale='en'),'symbol':get_currency_symbol(c,locale='en'),
                  'fraction_digits':get_currency_precision(c)} for c in sorted(list_currencies(locale='en')))

def search(query=''):
    needle=str(query).strip().casefold()[:100]
    return [dict(c) for c in catalog() if needle in c['code'].casefold() or needle in c['name'].casefold()]

def timezones():
    return sorted(available_timezones()-{'localtime','Factory'})
