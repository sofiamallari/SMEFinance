"""Backend-first routing for the AI Financial Partner (docs/technical/ai-chat-logic.md, section 2).

Rules run before Gemini. Fixed routes (blocked actions, not-in-app data, unclear messages,
doubt, return-to-topic) are answered here without a model; record and reasoning routes get
a backend plan so they still answer when the model is unavailable. No financial formulas live here.
"""
import re
from copilot import conversation_state as cs
from copilot.authorization import require
from copilot.security import AccessDenied

TX_REF=re.compile(r'\bTX-[A-Za-z0-9-]{4,120}\b')
APP_REF=re.compile(r'\bAPP-[A-Za-z0-9-]{1,80}\b')
DOUBT=re.compile(r"\s*(?:(?:hmm+|wait|but|ok(?:ay)?|really)[,.!]?\s+)?(?:are you (?:sure|certain)|you sure|is (?:that|this) (?:right|correct|accurate|true)|really|double[- ]check(?: (?:that|it|this))?|(?:can|could) you (?:double[- ]check|re-?check|verify|confirm)(?: (?:that|it|this|those numbers))?|(?:that|this) (?:doesn'?t|does not) (?:look|seem|sound) right|that'?s wrong|i don'?t (?:think so|believe (?:that|it)))\s*[?.!]*\s*",re.I)
VAGUE=re.compile(r"\s*(?:(?:and|so|ok(?:ay)?|hmm+|well)[,.]?\s+)?(?:(?:how|what) about (?:it|that|this|them|those)|and (?:then|that|it|this)|what then|huh|what|so|then what|that one|this one|it|that|this|and)\s*[?.!]*\s*",re.I)
BACK=re.compile(r"^\s*(?:(?:ok(?:ay)?|so|now|alright|right)[,.]?\s+)?(?:(?:let'?s|can we|could we|i want to|please)\s+)?(?:go\s+|get\s+|come\s+)?(?:back|return|resume|continue)\b(?:\s+(?:to|with|on))?",re.I)
EXPORT=re.compile(r"\b(?:export|download|print)\b|\b(?:pdf|excel|xlsx|csv|spreadsheet)\b|\bsend (?:me )?(?:a |the )?(?:report|file|statement)\b|\b(?:generate|create|make|give me) (?:a |an |the )?(?:report|statement|file)\b",re.I)
ACTION=re.compile(r"^\s*(?:(?:please|pls|kindly|ok(?:ay)?|now)[,.]?\s+)?(?:(?:can|could|would|will) you\s+|go ahead and\s+|i want you to\s+|help me\s+)?(?:please\s+)?"
 r"(?P<verb>submit|approve|pay|transfer|send money|purchase|buy|delete|remove|edit|update|modify|change|correct|fix|cancel|apply for|sign|withdraw|refund|record|add|enter|authori[sz]e|grant|revoke)\b(?!\s+(?:me|if|whether)\b)",re.I)
BANK_BALANCE=re.compile(r"\bbank (?:account )?balance\b|\bbalance (?:in|of) (?:my|the|our) bank(?: account)?\b|\bhow much (?:money )?(?:is|do (?:i|we) have) in (?:my|the|our) bank\b|\bmy bank account\b",re.I)
PAYROLL=re.compile(r"\bpayroll\b|\b(?:salar(?:y|ies)|wages?) (?:i|we) (?:paid|pay)\b|\bhow much (?:did|do) (?:i|we) pay (?:my |our )?(?:staff|employees|workers)\b|\b(?:staff|employee) (?:pay|salar(?:y|ies)|wages?) (?:last|this|in)\b",re.I)
OTHERS=re.compile(r"\bcompetitors?'?s?\b|\b(?:rival|neighbou?ring|nearby|another|other) (?:business|shop|store|caf[eé]|restaurant|merchant)s?'?s?\b.{0,40}\b(?:sales|revenue|income|profit|customers|figures|numbers)\b|\bcustomers?'?s? (?:income|salary|bank|personal|address|phone|spending|details)\b|\b(?:supplier|landlord|employee)'?s? (?:bank|personal|salary|income)\b",re.I)
SEARCH=re.compile(r"\b(?:search|research|look (?:it )?up|google|check online|online|on the (?:web|internet)|latest news)\b",re.I)
OUTSIDE=re.compile(r"\bindustry\b|\bbenchmarks?\b|\b(?:average|typical|normal|standard) (?:for|in|among)\b|\b(?:average|typical) (?:margin|profit|sales|revenue|rent|wage|cost)s?\b|\bmarket rates?\b|\bregulations?\b|\b(?:tax|vat) (?:rules?|rates?|law|filing|requirements?)\b|\bfapiao\b|\bminimum wage\b|\blaws?\b|\blicen[cs]e requirements?\b|\b(?:current|today'?s|latest) (?:sme |business )?(?:lending|loan|interest) rates?\b|\blending rates?\b",re.I)
MINE=re.compile(r"\b(?:my|our|mine|i'?m|we'?re|am i|are we)\b",re.I)
RECORD_WORDS=re.compile(r"\b(?:sales|revenue|margins?|profit|expenses?|costs?|income|turnover|growth|rent)\b",re.I)
LOAN=re.compile(r"\b(?:loan|borrow\w*|mortgage|credit line)\b.{0,60}\b(?:monthly|payments?|repay\w*|installments?|amorti[sz]\w*|schedule|interest|pay back|per month|a month|each month|every month|cost)\b|\b(?:repayments?|monthly payments?|installments?|amorti[sz]\w*)\b.{0,40}\b(?:loan|borrow\w*|\d|rates?)\b|\bif (?:interest )?rates? (?:rise|rises|go up|goes up|increase|increases|drop|drops|fall|falls|change|changes)\b",re.I)
PAST=re.compile(r"\b(?:had ?n[o']t|had not|did ?n[o']t|did not|never)\b.{0,25}\b(?:spen[dt]|paid|pay|bought|buy|purchased?|hired?)\b|\bwhat if I had (?:spent|paid|bought|hired)\b|\bwithout (?:the|that|my)\b.{0,30}\b(?:expense|cost|spend\w*|purchase|payment)\b.{0,30}\b(?:in|last|during)\b",re.I)
DIAGNOSE=re.compile(r"\bwhy (?:did|do|does|is|are|was|were|have|has)\b.{0,50}\b(?:drop\w*|fall|fell|falling|declin\w*|decreas\w*|down|low|lower|empty|zero|missing|change\w*|differ\w*|worse|less|go(?:ne)? down)\b|\bwhat (?:caused|is causing|explains)\b.{0,40}\b(?:sales|revenue|drop|decline|fall|difference|change)\b|\bwhy (?:is|are) (?:my )?(?:\w+ )?(?:sales|revenue|records?|numbers?|figures?) (?:so )?(?:low|empty|zero|missing|down)\b",re.I)
# Upload/import status and record counts ("did you record my batch upload?", "how many records were in that import?").
IMPORTS=re.compile(r"\b(?:batch|bulk)\s+(?:pos\s+)?(?:upload|import)s?\b|\b(?:my|the|that|this|last|latest|recent|previous)\s+(?:file\s+)?(?:upload|import)s?\b"
 r"|\b(?:did|was|were|has|have)\b.{0,30}\b(?:upload\w*|import\w*|record\w*|sav\w*)\b.{0,30}\b(?:upload|import|file|template|batch|transactions?|data)\b"
 r"|\bhow many\b.{0,40}\b(?:records?|rows?|entries|transactions?)\b.{0,40}\b(?:import\w*|upload\w*|file|manual\w*|single|entered|in (?:my|the) (?:books|records|system))\b"
 r"|\bhow many\s+(?:manual|single|imported)\s+(?:records?|rows?|entries|transactions?)\b|\bmanual entries\b|\bunfinished uploads?\b",re.I)
QUALITY=re.compile(r"\bdata quality\b|\bimport(?:s|ed)? (?:status|errors?|failed|history)\b|\b(?:is|are) my (?:data|records) (?:complete|up to date|accurate)\b|\bmissing (?:data|records|imports?)\b|\bdata issues?\b",re.I)
PERCENT_CHANGE=re.compile(r"\b(?:sales|revenue|expenses?|costs?)\b.{0,25}[+\-]?\d+(?:\.\d+)?\s*%|[+\-]?\d+(?:\.\d+)?\s*%.{0,25}\b(?:sales|revenue|expenses?|costs?)\b",re.I)
AMOUNT=re.compile(r"(?:RMB|CNY|[¥￥])?\s*\d[\d,]*(?:\.\d+)?\s*(?:k|thousand|m|million)?\b(?!\s*%)",re.I)
COST_WORDS=re.compile(r"\b(?:buy|purchase|spend|invest|pay for|cost|costs|warehouse|equipment|renovat\w*|expan\w*|hire|hiring|salary|rent|oven|vehicle|machine\w*|branch|afford)\b",re.I)
WHATIF=re.compile(r"\bwhat if\b|\bwhat happens if\b|\bcan (?:i|we) afford\b|\bafford\b|\bshould (?:i|we)\b|\bif (?:i|we)\b|\bsimulat\w*|\bscenario\b",re.I)
CASH=re.compile(r"\bcash ?flow\b|\bforecast\b|\brunway\b|\bnext month\b|\b(?:cash|balance) (?:today|now|position)\b|\bmy balance\b|\balerts?\b|\bwarnings?\b",re.I)
SALES=re.compile(r"\bsales\b|\brevenue\b|\bexpenses?\b|\bnet income\b|\bprofit\b|\bbest (?:month|week|period)\b|\bhow (?:am i|are we|is my business) (?:doing|performing)\b|\b(?:compare|vs\.?|versus)\b",re.I)
GROWTH=re.compile(r"\bmaturity\b|\bmy stage\b|\bgrowth stage\b|\bbusiness growth\b|\bready for (?:financing|growth)\b",re.I)
FINANCING=re.compile(r"\bfinancing (?:options|matches)\b|\bwhich (?:loan|financing)\b|\brbf (?:quote|offer)\b|\bhow much can I borrow\b",re.I)
CHANNELS=re.compile(r"\bpayment (?:channel|method)s?\b|\bchannel mix\b|\b(?:which|what) (?:channel|payment)\b|\bhow (?:do )?(?:my )?customers pay\b|\brevenue mix\b",re.I)
# "Why is it 76.6% but the dashboard shows 73.6%?": the chat and the Dashboard looked at different dates.
DASHBOARD_DIFF=re.compile(r"\bdashboard\b.{0,80}\b(?:differ\w*|different|mismatch|not (?:the )?same|doesn'?t match|says|shows?|showing|instead)\b"
 r"|\b(?:why|how come)\b.{0,80}\b(?:on|in|from) the dashboard\b|\b(?:differ\w*|different|mismatch|not (?:the )?same|doesn'?t match)\b.{0,60}\bdashboard\b",re.I)
DIGITAL=re.compile(r"\bdigital capture\b|\bdigital (?:share|payments?|sales)\b|\bcash vs\.? digital\b|\b(?:share|percent(?:age)?|how much)\b.{0,40}\b(?:is|was|were|paid) digital(?:ly)?\b",re.I)
# How a period's sales were paid, method by method ("is this paid in cash or credit card?", "split by payment method").
PAY_WORDS=r"(?:cash|(?:credit |debit )?cards?|qr(?: pay)?|e-?wallets?|tap(?: pay)?|pay ?links?)"
SPLIT=re.compile(r"\b(?:paid|pay|payments?|received|sales)\s+(?:in|by|with|via|through|using)\s+"+PAY_WORDS+r"\b|\b"+PAY_WORDS+r",?\s+(?:or|and|vs\.?|versus)\s+"+PAY_WORDS+r"\b"
 r"|\b(?:by|per|each|for each) (?:payment )?(?:method|channel)s?\b|\b(?:split|breakdown|break(?:s)? ?down|broken down)\b.{0,30}\b(?:methods?|channels?|cash|cards?)\b",re.I)
# The metric a follow-up refers to ("translate it to its amount", "is this paid in cash?").
REFER=re.compile(r"\b(?:it|its|it'?s|that|this|those|these|same)\b",re.I)
AMOUNT_ASK=re.compile(r"\b(?:amount|how much|value|figure|translate|convert|in (?:money|yuan|rmb|cny))\b",re.I)
SHARE_ASK=re.compile(r"\b(?:share|percent(?:age)?|portion|proportion|ratio|capture)\b|%",re.I)

def focus(text,state):
    """'digital_amount', 'digital_share' or 'channels' for this turn; a referring follow-up keeps the previous one."""
    if SPLIT.search(text):return 'channels'
    if DIGITAL.search(text):return 'digital_share' if SHARE_ASK.search(text) and not AMOUNT_ASK.search(text) else 'digital_amount'
    prior=state.get('focus')
    if not prior or not REFER.search(text):return None
    if prior.startswith('digital') and AMOUNT_ASK.search(text):return 'digital_amount'
    if prior.startswith('digital') and SHARE_ASK.search(text):return 'digital_share'
    if SALES.search(text) or CHANNELS.search(text) or CASH.search(text) or TX_REF.search(text):return None
    return prior
# Typo-tolerant ("transsaction", "teansaction"); a single/manual or user-named transaction is a record lookup too.
TXN=r"(?:t[a-z]{0,2}ans?\w{0,3}ctions?|transactions?)"
RECENT=re.compile(r"\b(?:recent|latest|last|newest|today'?s|single|manual)\s+(?:single\s+|manual\s+)?"+TXN+r"\b|\b"+TXN+r" today\b|\b[A-Za-z]*\d[A-Za-z0-9_.-]*\s+"+TXN+r"\b"
 r"|\b(?:my|the|a|any)\s+"+TXN+r"\s+(?:on|for|from|yesterday)\b|\b"+TXN+r"\s+(?:on|from)\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d|yesterday)"
 r"|\b"+TXN+r"\s+yesterday\b|\bwas (?:it|that|this) (?:paid )?(?:by |in |with )?(?:cash|card|qr|visa|mastercard|tap)\b"
 r"|\bwhat (?:card|payment method|payment type)\b|\bwhich (?:card|payment method)\b|\bhow (?:did|was) (?:i|it|they|the customer|that|this) (?:pay|paid)\b|\b(?:paid|pay) (?:by|with) (?:card|cash|qr|visa|mastercard)\b",re.I)
SUBJECTS=re.compile(r"\b(?:warehouse|equipment|oven|vehicle|van|truck|machine|branch|renovation|expansion|inventory|shop|store|kitchen|freezer|fridge|computer|laptop|signage|website)\b",re.I)
MONTHLY=re.compile(r"(?:per|a|each|/)\s*month\b|\bmonthly\b|\bsalary\b|\bhire\b|\bhiring\b|\brent\b|\bwages?\b",re.I)
# Cash Flow tab workbook (uploaded AR/AP): who owes the business, overdue invoices, bills due, 7-day runway, workbook cash on hand.
BOOK=re.compile(r"\bwho owes (?:me|us)\b|\bowe[sd]? (?:me|us)\b|\b(?:accounts? )?receivables?\b|\b(?:accounts? )?payables?\b|\boverdue\b|\bpast due\b|\bunpaid (?:invoices?|bills?)\b|\b(?:open|outstanding) (?:invoices?|bills?)\b"
 r"|\binvoices?\b.{0,30}\bdue\b|\bbills?\b.{0,30}\bdue\b|\bdue\b.{0,20}\bbills?\b|\bbills? (?:to pay|this week|next week)\b|\b7[- ]?days? (?:net )?runway\b|\bnet runway\b|\brunway\b.{0,20}\b(?:next )?7 days\b"
 r"|\bcash on hand\b.{0,40}\b(?:workbook|upload\w*|spreadsheet|sheet)\b|\bworkbook\b|\bcash ?flow (?:tab|book)\b",re.I)
# Dashboard Average Revenue / Average Expense and Expense Split for the business's own records (not industry averages).
OWN_AVERAGE=re.compile(r"\baverage (?:monthly |weekly |daily )?(?:revenue|sales|expenses?|spend\w*|income|costs?)\b|\b(?:revenue|sales|expenses?) (?:on )?average\b|\b(?:monthly|weekly|daily) averages?\b|\bexpense (?:split|breakdown)\b|\bexpenses? by category\b|\bbreak ?down (?:of )?my expenses\b",re.I)
NOT_OWN=re.compile(r"industry|benchmark|typical|peers?|competit|other (?:business|shop|store)|similar business|market",re.I)
RISE=re.compile(r"\b(?:rise|rises|go(?:es)? up|increase[sd]?|higher|drop|drops|fall|falls|lower|decrease[sd]?|change[sd]?|up|down)\b",re.I)

def normalize(text):
    """Common misspellings of "transaction" ("transsaction", "transaciton") read as the word itself."""
    import difflib
    def fix(match):
        word=match.group();plural=word.lower().endswith('s') and not word.lower().endswith('ss')
        base=word[:-1] if plural else word
        return ('transaction'+('s' if plural else '')) if difflib.SequenceMatcher(None,base.lower(),'transaction').ratio()>=0.8 else word
    return re.sub(r'\b[A-Za-z]{8,14}\b',fix,text)

def classify(text,state):
    """The backend route for a message, or None when only the model can classify it."""
    t=text.strip();has_context=bool(state.get('last_requests') or state.get('pending') or state.get('entities'))
    if DOUBT.fullmatch(t):return {'route':'doubt'}
    if BACK.search(t) and (state.get('parked') or state.get('topics') or state.get('entities')):return {'route':'back'}
    if VAGUE.fullmatch(t) and not has_context:return {'route':'unclear'}
    if EXPORT.search(t) and not WHATIF.search(t):return {'route':'export'}
    if ACTION.search(t) and not WHATIF.search(t):return {'route':'action','verb':ACTION.search(t)['verb'].lower()}
    if OTHERS.search(t):return {'route':'not_in_app','kind':'others'}
    if COLUMN.search(t):return {'route':'column'}
    from copilot.category_guide import lookup
    guide=lookup(t)
    if guide:return {'route':'guide','kind':guide[0],'entry':guide[1]}
    term=definition(t)
    if term:return {'route':'define','term':term}
    if MEANING.search(t) and not re.search(r'\b(?:my|our)\b.*\b(?:sales|cash|balance|income|forecast)\b',t,re.I):return {'route':'column','soft':True}
    if BANK_BALANCE.search(t):return {'route':'not_in_app','kind':'bank_balance','intent':'cash_flow'}
    if PAYROLL.search(t) and not (AMOUNT.search(t) and WHATIF.search(t)):return {'route':'not_in_app','kind':'payroll','intent':'sales_analysis'}
    if LOAN.search(t) and not APP_REF.search(t):return {'route':'C','intent':'loan_calculation','strong':True,'search':'sme_lending_rates' if re.search(r'\b(?:market|current|public|today\'?s)\b',t,re.I) else None}
    if OWN_AVERAGE.search(t) and not NOT_OWN.search(t) and not SEARCH.search(t):return {'route':'B','intent':'sales_analysis','strong':True}
    outside=OUTSIDE.search(t) or (SEARCH.search(t) and re.search(r'rates?|industry|tax|regulat|law|benchmark|average',t,re.I))
    if outside or SEARCH.search(t):
        topic=search_topic(t)
        mixed=bool(topic=='industry_benchmarks' and MINE.search(t) and RECORD_WORDS.search(t))
        return {'route':'mixed' if mixed else 'search','topic':topic,'intent':'sales_analysis' if mixed else 'public_research'}
    if SPLIT.search(t) and not TX_REF.search(t) and not re.search(r'\b'+TXN+r'\b',t,re.I) and state.get('intent')!='transactions':
        return {'route':'B','intent':'payment_channels','strong':True,'follow_up':has_context}
    if TX_REF.search(t) or RECENT.search(t):return {'route':'B','intent':'transactions','strong':True}
    if APP_REF.search(t):return {'route':'B','intent':'financing','strong':True}
    if PAST.search(t):return {'route':'C','intent':'past_what_if','strong':True}
    if DIAGNOSE.search(t):return {'route':'E','intent':'sales_analysis','strong':True,'diagnose':True}
    if IMPORTS.search(t) and not re.search(r'\bhow (?:do|can|to)\b',t,re.I):return {'route':'B','intent':'data_quality','strong':True,'imports':True}
    if QUALITY.search(t):return {'route':'B','intent':'data_quality','strong':True}
    if BOOK.search(t) and not WHATIF.search(t):return {'route':'B','intent':'cash_flow','strong':True,'book':True}
    amount=any(not re.search(r'%',m.group()) and re.search(r'\d',m.group()) for m in AMOUNT.finditer(t))
    if PERCENT_CHANGE.search(t) and amount and COST_WORDS.search(t):return {'route':'C','intent':'decision_support','strong':True,'combined':True}
    if PERCENT_CHANGE.search(t) and (WHATIF.search(t) or re.search(r'\bfor \d+ months?\b',t,re.I)):return {'route':'C','intent':'simulation'}
    if (WHATIF.search(t) or COST_WORDS.search(t)) and (amount or state.get('intent')=='decision_support' or re.search(r'\bafford\b',t,re.I)):return {'route':'C','intent':'decision_support'}
    if GROWTH.search(t):return {'route':'B','intent':'business_growth'}
    if FINANCING.search(t):return {'route':'B','intent':'financing'}
    if DASHBOARD_DIFF.search(t):return {'route':'B','intent':'sales_analysis','strong':True,'dashboard':True}
    if DIGITAL.search(t):return {'route':'B','intent':'sales_analysis','strong':True}
    if CHANNELS.search(t):return {'route':'B','intent':'payment_channels','strong':True}
    if CASH.search(t):return {'route':'C' if re.search(r'forecast|next month|runway',t,re.I) else 'B','intent':'cash_flow'}
    if SALES.search(t):return {'route':'B','intent':'sales_analysis'}
    if has_context and state.get('intent') not in (None,'unknown'):return {'route':'B','intent':state['intent'],'follow_up':True}
    return None

# A2: general definitions answered the same way with or without the model; no business figures.
GLOSSARY=[
 (r"revenue[- ]based financ\w*|\brbf\b","Revenue-based financing (RBF) is funding you repay as a fixed share of your future sales until an agreed total is paid, so repayments rise and fall with your sales. In the app, Financing → RBF Calculator shows an indicative quote; the lender makes the credit decision."),
 (r"net income|net profit","Net income is what's left after subtracting expenses from net sales for a period. It isn't the same as cash in the bank, because some sales and costs are paid at different times."),
 (r"net sales","Net sales are your sales after refunds and discounts. They are revenue, not profit or available cash."),
 (r"gross margin|profit margin|\bmargins?\b","A margin is profit shown as a share of sales. Gross margin subtracts only the direct cost of what you sold; net (profit) margin subtracts all expenses."),
 (r"cash[- ]?flow forecast|\bforecast\b","A cash-flow forecast estimates money coming in and going out on future days, based on your recent sales and expenses plus scheduled payments. It's an estimate, not your bank balance."),
 (r"cash[- ]?flow","Cash flow is the money moving in and out of your business over time. Positive cash flow means more came in than went out in that period."),
 (r"working capital","Working capital is your short-term assets (cash, money owed to you, stock) minus short-term debts (bills and loans due soon). It shows whether you can cover near-term payments."),
 (r"\brunway\b","Runway is how long your cash would last at the current rate of spending before it runs out."),
 (r"receivables?","Receivables are money customers owe you for sales already made but not yet paid."),
 (r"payables?","Payables are money you owe suppliers for goods or services you've already received."),
 (r"amorti[sz]\w*","Amortization means repaying a loan in regular instalments that cover both interest and part of the amount borrowed, so the balance falls to zero by the end of the term."),
 (r"interest rate|\bapr\b","An interest rate is the yearly cost of borrowing, shown as a percentage of the amount borrowed. The annual percentage rate (APR) also includes certain fees."),
 (r"transaction volume","Transaction volume is the number of transactions in a period, not their value."),
]
DEFINE=re.compile(r"^\s*(?:what(?:'s| is| are| does)|define|meaning of|explain what)\b",re.I)

def definition(text):
    if not DEFINE.search(text) or re.search(r"\b(?:my|our|mine|me|i|we)\b|\d|\bAPP-|\bTX-",text,re.I):return None
    return next((answer for pattern,answer in GLOSSARY if re.search(pattern,text,re.I)),None)

# Columns of uploaded expense/sales files. Each imported transaction keeps its original row, so columns can be explained after import.
COLUMN=re.compile(r"\b(?:columns?|headers?|fields?)\b.{0,40}\b(?:file|report|upload\w*|import\w*|spreadsheet|excel|csv|sheet|mean|means|stand for)\b|\b(?:file|report|upload\w*|import\w*|spreadsheet|excel|csv|sheet)\b.{0,40}\b(?:columns?|headers?|fields?)\b|\bexplain (?:the |this |that )?['\"]?[\w /&()-]{2,40}['\"]? column\b|\bwhat (?:is|does) (?:the )?['\"]?[\w /&()-]{2,40}['\"]? column\b",re.I)
MEANING=re.compile(r"^\s*what (?:does|do) ['\"]?(?P<name>[\w /&().-]{2,40}?)['\"]? (?:mean|stand for)\b",re.I)
FIELD_TEXT={
 'transaction_date':'the date (and time) of each transaction; the app uses it as the business date.',
 'net_amount':'the amount after discounts and fees; the app records it as the transaction amount.',
 'gross_amount':'the amount before discounts and fees.',
 'discount':'any discount given on the transaction.','tax':'the tax included in the transaction.',
 'refund_amount':'any amount refunded to the customer.',
 'settlement_amount':'the amount the payment provider actually paid out to you; the app never counts it as sales.',
 'currency':'the currency of the amounts.','transaction_type':'whether the row is a sale, expense, refund or reversal.',
 'payment_method':'how the customer paid; the app groups it as cash, card, QR pay, tap-to-pay, e-wallet or pay link.',
 'status':'whether the transaction completed, is pending, failed or was voided.',
 'external_reference':'your own reference or receipt number; you can ask me about a transaction by it.',
 'description':'a free-text description, such as the vendor or item.','category':'the expense or sales category the app groups by.',
 'processing_fee':'the fee the payment provider charged; the app checks that gross minus this fee equals the net amount, and records the net amount.',
 'sub_category':'a more detailed group under Category; the app keeps it with each expense.',
 'classification':'the Copilot Category Guide classification of the row. Loan proceeds, owner contributions and VAT collected are kept out of sales, and loan principal is kept out of expenses.'}
HINTS=[(r'processing fee|\bfees?\b','a fee the payment provider charged for the transaction. The app keeps it with the transaction but does not subtract it again.'),
 (r'sub[- ]?category','a more detailed group under Category. The app keeps it with the transaction for reference.'),
 (r'card (?:type|brand|network|scheme)|\bscheme\b|\bnetwork\b|\bissuer\b','the card network or brand, such as Visa or Mastercard.'),
 (r'\btip','a tip added by the customer.'),(r'cashier|staff|employee','who handled the transaction.'),
 (r'terminal|device|register','the POS terminal or device used.'),(r'store|branch|outlet|location','the shop or branch where it happened.'),
 (r'revenue / cash-in classification|cash-flow / accounting type|classification|accounting type','the Copilot Category Guide classification of the row, such as Sales Revenue, Loan Proceeds or Operating Expense. The app reads it at import: loan proceeds, owner contributions and VAT collected are kept out of sales, and loan principal is kept out of expenses.'),
 (r'tax / copilot note|copilot note','a reminder about tax for the row, for example to record sales tax or VAT separately. It is guidance, not a tax calculation.'),
 (r'indicative tax treatment|tax treatment','an indicative note on how the cost may be treated for tax, such as "potentially deductible; verify rules". It is not a tax decision.'),
 (r'financing / tax note|financing note','a note on records to keep, such as the receipt or invoice and the business purpose.'),
 (r'vendor|supplier|payee','who you paid.'),(r'^amount\b','the amount of each row; in an expense report it is the expense amount the app records.'),(r'\bid\b|number|\bno\.?\b','an identifier for the row in your file.')]

def explain_columns(rows,text):
    """A plain explanation of the user's own uploaded-file columns, with example values from their records."""
    from copilot.canonical_transactions import ALIASES
    columns={}
    for row in rows:
        for name,value in (row.get('source_values') or {}).items():
            columns.setdefault(name,[])
            if value not in columns[name] and len(columns[name])<3:columns[name].append(value)
    if not columns:return "I couldn't find any imported files with their original columns. Columns are kept for transactions imported through Bulk POS Import."
    def core(name):return re.sub(r'\s*\([^)]*\)\s*$','',name).strip().lower()
    meaning_match=MEANING.search(text);asked=meaning_match['name'] if meaning_match else None
    low=text.lower()
    hits=[n for n in columns if core(n) and (core(n) in low or (asked and core(asked) in core(n)))]
    hits=[n for n in hits if not any(core(n)!=core(o) and core(n) in core(o) for o in hits)] # 'Net Amount' wins over 'Amount'
    if not hits:
        return 'Your imported files have these columns: '+', '.join(columns)+'. Which one would you like me to explain?'
    parts=[]
    for name in sorted(hits,key=lambda n:-len(core(n)))[:2]:
        field=next((f for f,names in ALIASES.items() if core(name) in names),None)
        meaning=FIELD_TEXT.get(field) or next((t for p,t in HINTS if re.search(p,name,re.I)),None)
        line='"'+name+'" is '+(meaning if meaning else "a column from your file that the app doesn't use as one of its own fields; it's kept as the original value with each transaction.")
        line+=' Examples from your records: '+', '.join('"'+v+'"' for v in columns[name])+'.'
        parts.append(line)
    return ' '.join(parts)

def search_topic(text):
    if re.search(r'lending|loan|interest rates?|borrow',text,re.I):return 'sme_lending_rates'
    if re.search(r'regulat|\btax|\bvat\b|\blaws?\b|licen[cs]e|fapiao|minimum wage|social insurance|compliance|registration',text,re.I):return 'regulations_tax'
    if re.search(r'industry|benchmark|average|typical|normal|margin|competit|market|peers?',text,re.I):return 'industry_benchmarks'
    return None

def private_terms(text,merchant_name=''):
    """Figures, references or the business name in a search request (they are never searched)."""
    found=bool(re.search(r'\d',text) or TX_REF.search(text) or APP_REF.search(text) or re.search(r'\bM\d{3}\b',text))
    words=[w for w in re.findall(r'[a-z]{3,}',(merchant_name or '').lower()) if w not in ('the','and','shop','store','company','ltd','limited','business')]
    return found or any(re.search(r'\b'+re.escape(w)+r'\b',text,re.I) for w in words)

# X1/X2: blocked actions get the right screen instead of a bare refusal. Paths match partner_help.HELP.
GUIDES=[
 (r'export|download|print|pdf|excel|xlsx|csv|spreadsheet|report|statement|file','view_dashboard',"I can't create or send files from chat. To export, open Dashboard → Overview and choose \"Export overview as PDF\"; your browser's print dialog saves it as a PDF. Transaction History lets you filter and review the records themselves."),
 (r'submit|apply for|application|financing|loan','view_applications',"I can't submit or change applications from chat. Open Financing → Applications to create or review an application; only the business owner submits it, and the lender makes the credit decision."),
 (r'approve','view_applications',"I can't approve anything; credit decisions are made by the lender. You can follow an application's status in Financing → Applications."),
 (r'authori[sz]e|grant|revoke|consent|bank access','manage_consents',"I can't change bank access from chat. Open Bank Authorization in the sidebar to authorize a bank or review and revoke existing grants."),
 (r'pay|transfer|send money|purchase|buy|withdraw|refund','create_transactions',"I can't move money or make purchases. Payments are made through your bank outside this app; once paid, you can record it in Merchant Transactions → Single Transaction."),
 (r'delete|remove|edit|update|modify|change|correct|fix|cancel','view_transactions',"I can't change business records from chat. Review records in Merchant Transactions → Transaction History; corrections go through Single Transaction or a corrected file in Bulk POS Import."),
 (r'record|add|enter','create_transactions',"I can't add records from chat. Use Merchant Transactions → Single Transaction for one entry, or Bulk POS Import for a file."),
]

def guidance(p,mid,text,route):
    """A deterministic pointer to the screen that does the action; only screens the account may open."""
    target=text if route=='export' else (ACTION.search(text)['verb']+' '+text if ACTION.search(text) else text)
    for pattern,permission,message in (GUIDES[:1] if route=='export' else GUIDES[1:]):
        if not re.search(pattern,target,re.I):continue
        try:require(p,permission,mid)
        except AccessDenied:return "I can't do that from chat, and that screen isn't available for your account. Ask the business owner if you need it."
        return message
    return "I can't take actions or change records from chat; I can only look things up and explain them."

# A small bare number ("1 more staff", "2 machines") is a count, not a money amount; amounts carry a currency, a
# magnitude suffix or at least three digits.
SMALL_COUNT=re.compile(r'\s*\d{1,2}\s*')
DIRECTED=re.compile(r'\b(?:decreas\w*|drop\w*|fall\w*|fell|declin\w*|reduc\w*|lower\w*|down|cut\w*|increas\w*|ris\w*|rose|grow\w*|grew|up|higher)\b',re.I)

NOT_IN_APP={
 'others':"Other businesses' figures and customers' private details aren't recorded in the app, and I don't search the web for private business or personal data. I can show your own recorded figures, or search public industry benchmarks if you ask.",
 'bank_balance':"Your bank balance is not recorded in the app, so I can't confirm it.",
 'payroll':"Payroll is not recorded as a separate category in the app, so I can't show what was paid in salaries.",
}

def unclear(state):
    """J1: one clarifying question."""
    return "Could you tell me a bit more about what you'd like to know? For example: your sales for a month, your cash-flow forecast, a planned cost, or a financing question."

# Backend interpretation: typed values from the user's own text, chosen by route and nearby words.
def updates(text,spans,intent,state):
    out=[];taken=set()
    def add(entity,quote):
        if entity in taken:return
        key=next((k for k,v in spans.items() if v==quote),None)
        if key:out.append({'entity':entity,'source':key});taken.add(entity)
    dates=[v for v in spans.values() if re.fullmatch(r'(?:on\s+)?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?|(?:the\s+)?\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*)',v,re.I)]
    periods=[v for v in spans.values() if re.fullmatch(r'last month|this month|previous month|current month|last quarter|Q[1-4](?:\s+\d{4})?|last \d+ days|today|yesterday|this week|last week',v,re.I) or (v.lower().rstrip('.') in cs.MONTHS and len(v)>=3 and v.lower()!='may' and not any(v in d for d in dates))]
    for value in spans.values():
        position=text.find(value);before=text[max(0,position-40):position];after=text[position+len(value):position+len(value)+25];near=before+' '+after
        if re.fullmatch(r'\s*[+-]?\d+(?:\.\d+)?\s*%\s*',value):
            # "a 20% drop", "decreasing by 20%": take the span that carries the direction, so the sign is never lost.
            number=re.escape(value.strip())
            directed=next((v for v in spans.values() if v!=value and len(v.split())<=5 and re.search(r'(?<![\d.])'+number,v) and DIRECTED.search(v)),value)
            if intent=='loan_calculation':add('interest_rate_change' if RISE.search(before[-25:]) else 'annual_interest_rate',value)
            elif re.search(r'sales|revenue',before[-30:]+after[:15],re.I):add('sales_change_percent',directed)
            elif re.search(r'expense|cost',before[-30:]+after[:15],re.I):add('expense_change_percent',directed)
        elif re.fullmatch(r'\d+\s+(?:months?|years?)',value,re.I):
            add('financing_duration' if intent=='loan_calculation' else 'simulation_duration',value)
        elif re.fullmatch(cs.BARE_AMOUNT,value,re.I) and re.search(r'\d',value) and not re.match(r'\s*(?:%|months?|years?|days?|st\b|nd\b|rd\b|th\b)',after,re.I) and not any(value.strip() in d for d in dates) and not re.fullmatch(r'\s*(?:19|20)\d\d\s*',value) and not SMALL_COUNT.fullmatch(value):
            if intent=='loan_calculation':add('financing_amount',value)
            elif intent=='past_what_if':add('past_expense',value)
            elif intent in ('decision_support','simulation'):add('recurring_expense' if MONTHLY.search(before[-20:]+after[:15]) else 'one_time_cost',value)
    if intent=='decision_support':
        # A count of what is bought or hired ("two", "3 machines"): costs stay per unit and the backend multiplies.
        for value in spans.values():
            if len(value.split())>2 or SMALL_COUNT.fullmatch(value) and re.search(r'(?:RMB|CNY|[¥￥])\s*$',text[:max(0,text.find(value))]):continue
            if cs.date_part(text,value):continue # "paid on December 15": the day is not a quantity
            try:cs.scalar('quantity',value,currency='CNY',today=None)
            except Exception:continue
            after=text[text.find(value)+len(value):][:20]
            # "a", "an", "another" mean one, which is already the default.
            if re.match(r'\s*(?:%|k\b|thousand|months?|years?|days?|weeks?|rmb|cny|yuan)',after,re.I) or value.lower().split()[0] in ('a','an','another','single'):continue
            add('quantity',value);break
    if intent in ('decision_support','simulation'):
        dates=dates+[v for v in spans.values() if re.fullmatch(r'next week|tomorrow|today|in a week|next month',v,re.I)]
        # A bare month ("in December", "starting January") is the planned start or payment month.
        if not dates:dates=[v for v in spans.values() if re.fullmatch(r'(?:in|from|starting)\s+(?:jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*',v,re.I)]
    if intent in ('decision_support','simulation') and dates:
        # The date belongs to the cost described in this message: a hiring or salary start is never a purchase payment date.
        recurring=any(u['entity']=='recurring_expense' for u in out) or bool(MONTHLY.search(text))
        one_time=any(u['entity']=='one_time_cost' for u in out) or ('one_time_cost' in state['entities'] and not recurring)
        add('purchase_date' if one_time else 'start_date',dates[0])
    if intent in ('sales_analysis','past_what_if','data_quality','transactions','payment_channels') and periods:
        add('reporting_period',periods[0])
        if len(periods)>1 and intent=='sales_analysis':add('comparison_period',periods[1])
    if intent=='decision_support':
        subject=SUBJECTS.search(text)
        if subject:add('business_subject',subject.group())
    return out

def plan(text,spans,rule,state):
    """A model-free interpretation in the same contract the model fills; the backend binds every tool argument."""
    # A new route on a different topic switches topic (the old one is parked if it has an open question), so its periods and costs don't leak in.
    switch=state.get('intent') not in (None,'unknown',rule['intent']) and not rule.get('follow_up') and rule.get('route')!='answer'
    value={'intent':rule['intent'],'topic_change':bool(switch),'updates':updates(text,spans,rule['intent'],state),'question':None}
    if rule['intent']=='transactions' and TX_REF.search(text):value['tool_requests']=[] # the reference lookup is added by the backend
    return value
