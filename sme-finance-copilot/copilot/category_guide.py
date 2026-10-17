"""Reviewed Copilot Category Guide for the standard revenue and expense report template.

The chat answers from this registry, never from an uploaded workbook's text (files are untrusted).
Each entry says when a category applies, how the copilot treats it and what the app does with it at import.
No tax rates, deductibility verdicts, offers or approvals belong here.
"""
import re

DISCLAIMER = "This isn't financial, legal or tax advice; rules and eligibility vary by location and change over time."

CATEGORIES = [
 dict(key='sales_revenue', area='Revenue', name='Sales Revenue', match=r'sales revenue|customer (?:sales|payments?)\b',
      use='a customer pays for your goods or services',
      handling='include it in revenue, and track sales tax or VAT separately where it applies',
      app='The app counts it in recorded sales.', tax=True),
 dict(key='other_income', area='Revenue', name='Other Business Income', match=r'other (?:business )?income|interest received|commission',
      use='you receive interest, commission or other non-core income',
      handling='note where it came from and keep it apart from customer sales if you report them separately',
      app='The app counts it in recorded sales and flags its classification.'),
 dict(key='customer_refund', area='Revenue / cash-in', name='Customer Refund / Sales Return', match=r'refund|sales return|money (?:returned|back) to (?:a )?customer',
      use='money is returned to a customer',
      handling='treat it as a reduction of sales, not as a normal expense',
      app='The app records it as a refund, which reduces recorded sales.'),
 dict(key='loan_proceeds', area='Cash-in (not revenue)', name='Loan Proceeds', match=r'loan proceeds|borrowed (?:funds|money)|loan (?:money|deposit|disbursement)|receiv\w* (?:a )?loan',
      use='the business receives borrowed money',
      handling="don't count it as revenue; record the loan you owe and its repayment terms",
      app='The app keeps it out of sales and net income, as non-revenue cash-in.'),
 dict(key='owner_contribution', area='Cash-in (not revenue)', name='Owner Contribution', match=r'owner(?:\'s)? (?:contribution|capital|investment|cash)|capital injection|put (?:my )?own money',
      use='you, the owner, add cash to the business',
      handling="don't count it as revenue; classify it as owner equity (capital)",
      app='The app keeps it out of sales and net income, as non-revenue cash-in.'),
 dict(key='operating_expense', area='Expense', name='Operating Expense', match=r'operating expenses?|\brent\b|\bwages?\b|utilit|marketing|software|supplies',
      use='you pay for rent, wages, utilities, marketing, software or supplies',
      handling='it may be deductible depending on local rules, so keep the receipt or invoice and its business purpose',
      app='The app counts it in recorded expenses.', tax=True),
 dict(key='tax_permit_fee', area='Expense', name='Tax / Permit / Government Fee', match=r'permits?|licen[cs]e fee|government fee|local fees?',
      use='you pay business permits, licences, local fees or taxes',
      handling="track the type, period, due or renewal date and receipt; don't assume every tax is deductible",
      app='The app counts it in recorded expenses.', tax=True),
 dict(key='loan_interest', area='Expense / financing', name='Loan Interest / Financing Fee', match=r'loan interest|interest (?:paid|payment)|financing fees?|bank (?:loan )?fees?',
      use='you pay interest or lender or bank fees on a loan',
      handling='keep it separate from the principal; whether it is deductible depends on your location and what the loan was for',
      app='The app counts it in recorded expenses.', tax=True),
 dict(key='loan_principal', area='Cash-out (not expense)', name='Loan Principal Repayment', match=r'principal|loan repayment|repay\w* (?:the |a )?loan|pay(?:ing)? back (?:the |a )?loan',
      use='you repay part of the amount you borrowed',
      handling="it reduces what you owe; don't classify the principal as an operating expense",
      app='The app keeps it out of expenses and net income, as non-expense cash-out.'),
 dict(key='capital_purchase', area='Expense / asset', name='Equipment / Capital Purchase', match=r'equipment|capital purchase|\boven\b|fridge|refrigerator|freezer|pos hardware|furniture|long[- ]life asset|machine',
      use='you buy a fridge, oven, POS hardware, furniture or another long-life asset',
      handling='flag it for review, because it may need to be capitalised and depreciated rather than expensed at once',
      app='The app counts it in recorded expenses and flags it for review.', tax=True),
 dict(key='vat_collected', area='Tax', name='Sales Tax / VAT Collected', match=r'vat collected|sales tax collected|output tax|tax collected from customers',
      use='you collect tax from customers, if that applies to you',
      handling='keep it separate from sales revenue where possible; the amount and rate depend on your location and registration',
      app='The app keeps it out of sales, as non-revenue cash-in.', tax=True),
 dict(key='income_tax', area='Tax', name='Income Tax / Business Tax Payment', match=r'income tax|business tax (?:payment|paid)|tax paid to',
      use='you pay tax to the tax authority',
      handling='record it separately; the treatment depends on your business type and location',
      app='The app counts it in recorded expenses with its own classification.', tax=True),
 dict(key='needs_review', area='Copilot guardrail', name='Unknown / Needs Review', match=r'needs review|not sure (?:how|what|which)|unclear (?:category|expense|item)|don\'t know (?:how|which) (?:to )?(?:classify|categori[sz]e)',
      use="the description is unclear or the tax treatment is uncertain",
      handling='ask a follow-up question; never guess a tax rate, deductibility, permit fee or loan terms',
      app='The app keeps the row with its stated type and flags it for review.'),
]

FINANCING = [
 dict(name='Bank / SME Loan', match=r'bank loan|sme loan|business loan', helps='working capital, equipment or expansion',
      collect='amount, interest rate or APR, fees, term, collateral and repayment frequency', guidance='compare the total repayment and the monthly cash-flow effect, not just the rate'),
 dict(name='Microfinance / Small Business Lending', match=r'microfinanc\w*|micro[- ]?loan|small business lending', helps='smaller or early-stage funding needs',
      collect='loan size, effective rate, fees, repayment schedule and eligibility', guidance='check the total cost, how often you repay, and that the provider is regulated'),
 dict(name='Government-backed Financing / Guarantee', match=r'government[- ]backed|guarantee (?:scheme|program\w*)|state[- ]backed', helps='better access to credit',
      collect='country or region, business size, sector, registration and what the money is for', guidance='only programs verified from official sources apply, and eligibility varies'),
 dict(name='Grants / Subsidies', match=r'\bgrants?\b|subsid\w*', helps='non-debt support for eligible activities',
      collect='location, sector, business age, project purpose and deadlines', guidance='they are usually competitive and restricted, so check the application window and which costs are eligible'),
 dict(name='Equipment Financing / Leasing', match=r'equipment (?:financing|loan|lease)|leasing|lease (?:an? )?(?:oven|fridge|vehicle|equipment)', helps='ovens, refrigerators, vehicles or POS hardware',
      collect='asset cost, deposit, term, who owns it at the end, and fees', guidance='compare the total cost and ownership terms against buying outright'),
 dict(name='Invoice / Receivables Financing', match=r'invoice (?:financing|factoring)|receivables? financing|factoring', helps='cash flow while you wait for customers to pay',
      collect='invoice amount, the customer who owes it, due date, advance rate and fees', guidance='check recourse, fees and how much depends on a few customers'),
 dict(name='Business Development Support', match=r'mentoring|training|business development|incubator|digiti[sz]ation support', helps='training, mentoring, digitisation and market access',
      collect='location, sector, stage and what support you need', guidance='start with official SME agencies, chambers of commerce, incubators and reputable programs'),
]

ASKS = re.compile(r"^\s*(?:is|are|does|do|can)\b|\b(?:how (?:should|do|can|would) (?:i|we)|should (?:i|we|this|it)|is (?:it|this|that|a|an|my|the)\b|are (?:these|they|my)\b|what (?:is|are|counts|category|type)|where (?:does|do|should)|which category|count(?:ed)? as|treat|record|classif\w*|categori[sz]\w*|deductible|revenue or|expense or|income or)\b", re.I)
OPTIONS = re.compile(r"\b(?:what|which|tell me about|explain|how does|how do|options?|kinds?|types?|ways?)\b", re.I)

def lookup(text):
    """A guide category or financing option the question is about, or None."""
    if ASKS.search(text):
        for entry in CATEGORIES:
            if re.search(entry['match'], text, re.I) and re.search(r'revenue|income|expense|deduct|tax|classif|categor|record|treat|count|book|loan|capital|asset|owner|refund|vat|principal|needs review|what is|what are', text, re.I):
                return ('category', entry)
    if OPTIONS.search(text):
        for entry in FINANCING:
            if re.search(entry['match'], text, re.I):return ('financing', entry)
    return None

def answer(kind, entry):
    if kind == 'category':
        reply = entry['name'] + ' (' + entry['area'] + ') applies when ' + entry['use'] + '. How to handle it: ' + entry['handling'] + '. ' + entry['app']
        return reply + (' ' + DISCLAIMER if entry.get('tax') else '')
    return (entry['name'] + ' helps with ' + entry['helps'] + '. To compare options, collect: ' + entry['collect'] + '. Guidance: ' + entry['guidance'] + '. '
            'Tell me your country or region and whether your business is registered before I point to specific programs. ' + DISCLAIMER + ' I never invent offers or promise approval.')

def label(key):
    entry = next((c for c in CATEGORIES if c['key'] == key), None)
    return entry['name'] if entry else None
