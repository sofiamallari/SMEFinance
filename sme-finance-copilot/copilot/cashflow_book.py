"""Cash Flow tab: uploaded AR/AP ledgers and monthly cash logs, saved per business.

The Owner uploads one workbook (sheets: Accounts Receivable (AR), Accounts Payable (AP), Monthly Cash
Inflow Log, Monthly Cash Outflow Log, and a Current Cash on Hand value). The server validates it and
keeps the parsed records; every figure on the tab is computed here for a chosen reference date.
Outstanding balances are recomputed from amount minus collected/paid, because workbook formulas are
never evaluated.
"""
import base64
import calendar
import json
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from copilot.auth import InputError

MAX_ROWS = 5000
SHEETS = {'ar': 'receivable', 'ap': 'payable', 'inflow': 'inflow', 'outflow': 'outflow'}
COLUMNS = {
 'ar': {'id': ['invoice id', 'invoice #', 'invoice number', 'invoice no'], 'party': ['customer name', 'customer'], 'issued': ['invoice date'], 'due': ['due date'],
        'status': ['payment status', 'status'], 'amount': ['invoice amount', 'amount'], 'settled': ['amount collected', 'collected'], 'balance': ['outstanding balance', 'balance']},
 'ap': {'id': ['bill id', 'bill #', 'bill number', 'bill no'], 'party': ['supplier vendor', 'supplier', 'vendor'], 'issued': ['bill date'], 'due': ['due date'],
        'status': ['payment status', 'status'], 'amount': ['bill amount', 'amount'], 'settled': ['amount paid', 'paid'], 'balance': ['outstanding balance', 'balance']},
 'inflow': {'month': ['month'], 'category': ['revenue channel / category', 'category', 'revenue channel'], 'amount': ['gross inflow', 'inflow', 'amount']},
 'outflow': {'month': ['month'], 'category': ['expense category', 'category'], 'amount': ['gross outflow', 'outflow', 'amount']},
}
REQUIRED = {'ar': ('id', 'party', 'due', 'status', 'amount'), 'ap': ('id', 'party', 'due', 'status', 'amount'), 'inflow': ('month', 'amount'), 'outflow': ('month', 'amount')}
BUCKETS = ('OVERDUE', 'DUE_TOMORROW', 'NEXT_7', 'NEXT_30')
MONTH_NAMES = {name.lower(): i for i, name in enumerate(calendar.month_abbr) if name} | {name.lower(): i for i, name in enumerate(calendar.month_name) if name} | {'sept': 9}


def _core(header):
    return re.sub(r'\s*\([^)]*\)\s*$', '', str(header or '').strip()).lower()


def _money(value, where):
    text = str(value or '').strip().replace(',', '')
    if not text:
        return Decimal('0')
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise InputError(where + ': "' + str(value)[:40] + '" is not a number') from None
    if not number.is_finite() or abs(number) > Decimal('1000000000'):
        raise InputError(where + ': amount is out of range')
    return number.quantize(Decimal('.01'))


def _date(value, where):
    text = str(value or '').strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    for pattern in ('%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise InputError(where + ': "' + text + '" is not a date (use YYYY-MM-DD)')


def _month(value, where):
    text = str(value or '').strip()
    match = re.fullmatch(r'(\d{4})-(\d{1,2})(?:-\d{1,2}(?:T.*)?)?', text)
    if match:
        year, month = int(match[1]), int(match[2])
    else:
        parts = re.split(r'[\s\-/]+', text.lower())
        if len(parts) != 2 or parts[0].rstrip('.') not in MONTH_NAMES or not parts[1].isdigit():
            raise InputError(where + ': "' + text[:30] + '" is not a month (use Oct 2025 or 2025-10)')
        year, month = int(parts[1]), MONTH_NAMES[parts[0].rstrip('.')]
    if not (2000 <= year <= 2100 and 1 <= month <= 12):
        raise InputError(where + ': month is out of range')
    return '%04d-%02d' % (year, month)


def _table(rows, kind, sheet):
    """Find the header row, then read the data rows below it as dicts keyed by our field names."""
    wanted = COLUMNS[kind]
    for position, row in enumerate(rows[:30]):
        cores = [_core(v) for v in row['values']]
        index = {field: next((i for i, c in enumerate(cores) if c in names), None) for field, names in wanted.items()}
        if all(index[f] is not None for f in REQUIRED[kind]):
            records = []
            for data in rows[position + 1:]:
                values = data['values']
                if not any(str(v).strip() for v in values):
                    continue
                if any(re.match(r'\s*total\b', str(v), re.I) for v in values):
                    continue # a "Total Accounts Receivable" summary row, not a record
                get = lambda f: values[index[f]] if index.get(f) is not None and index[f] < len(values) else ''
                record = {f: get(f) for f in wanted if index[f] is not None}
                record['row'] = data['row']
                records.append(record)
            if len(records) > MAX_ROWS:
                raise InputError(sheet + ': at most %d rows' % MAX_ROWS)
            return records
    missing = [wanted[f][0] for f in REQUIRED[kind]]
    raise InputError(sheet + ': header row not found; expected columns ' + ', '.join(m.title() for m in missing))


def _ledger(records, sheet):
    items = []
    for r in records:
        where = sheet + ' row %d' % r['row']
        status = str(r.get('status') or '').strip().lower()
        if status not in ('open', 'paid', 'partially paid', 'partial', 'overdue', 'unpaid'):
            raise InputError(where + ': Payment Status must be Open or Paid')
        amount = _money(r.get('amount'), where)
        settled = _money(r.get('settled'), where) if str(r.get('settled') or '').strip() else None
        if settled is not None:
            outstanding = amount - settled
        else:
            balance = str(r.get('balance') or '').strip()
            outstanding = _money(balance, where) if balance and not balance.startswith('[') else (Decimal('0') if status == 'paid' else amount)
        if status == 'paid':
            outstanding = Decimal('0')
        if outstanding < 0:
            raise InputError(where + ': collected/paid is more than the amount')
        items.append({'id': str(r.get('id') or '').strip()[:60], 'party': str(r.get('party') or '').strip()[:120] or 'Unnamed',
                      'issued': _date(r['issued'], where).isoformat() if str(r.get('issued') or '').strip() else None,
                      'due': _date(r.get('due'), where).isoformat(), 'amount': str(amount), 'outstanding': str(outstanding)})
    return items


def _log(records, sheet):
    months = {}
    for r in records:
        where = sheet + ' row %d' % r['row']
        month = _month(r.get('month'), where)
        category = str(r.get('category') or 'Other').strip()[:80] or 'Other'
        months.setdefault(month, {})
        months[month][category] = str(Decimal(months[month].get(category, '0')) + _money(r.get('amount'), where))
    return months


def _cash_on_hand(rows):
    for row in rows:
        values = row['values']
        for i, v in enumerate(values):
            if re.search(r'cash on hand', str(v), re.I):
                for candidate in values[i + 1:]:
                    text = str(candidate).strip().replace(',', '')
                    if re.fullmatch(r'-?\d+(?:\.\d+)?', text):
                        return str(Decimal(text).quantize(Decimal('.01')))
    return None


def parse(content):
    from copilot.pos_extract import xlsx_table
    deadline = time.monotonic() + 30
    names = [w['name'] for w in xlsx_table(content, deadline, discover=True)]
    found = {kind: next((n for n in names if key in n.lower()), None) for kind, key in SHEETS.items()}
    missing = [label for kind, label in (('ar', 'Accounts Receivable (AR)'), ('ap', 'Accounts Payable (AP)'), ('inflow', 'Monthly Cash Inflow Log'), ('outflow', 'Monthly Cash Outflow Log')) if not found[kind]]
    if missing:
        raise InputError('Workbook is missing sheet(s): ' + ', '.join(missing))
    data = {}
    for kind in SHEETS:
        rows = xlsx_table(content, deadline, found[kind], scan=True)
        records = _table(rows, kind, found[kind])
        data[kind] = _ledger(records, found[kind]) if kind in ('ar', 'ap') else _log(records, found[kind])
    cash = None
    for name in names:
        if name not in found.values():
            cash = _cash_on_hand(xlsx_table(content, deadline, name, scan=True))
            if cash is not None:
                break
    data['cash_on_hand'] = cash
    return data


def bucket(due, ref):
    days = (date.fromisoformat(due) - ref).days
    if days < 0:
        return 'OVERDUE', days, 'Overdue (%dd)' % -days
    if days == 0:
        return 'DUE_TOMORROW', days, 'Due Today'
    if days == 1:
        return 'DUE_TOMORROW', days, 'Due Tomorrow'
    if days <= 7:
        return 'NEXT_7', days, 'Next 7 Days (%dd)' % days
    if days <= 30:
        return 'NEXT_30', days, 'Next 30 Days (%dd)' % days
    return 'BEYOND_30', days, '> 30 Days (%dd)' % days


def summarize(data, ref, cash=None):
    """All Cash Flow tab figures for a reference date. Only open (unpaid) balances are bucketed."""
    cash = Decimal(str(cash)) if cash is not None else Decimal(data.get('cash_on_hand') or '0')
    sides = {}
    for side in ('ar', 'ap'):
        stats = {b: {'amount': Decimal(0), 'count': 0} for b in (*BUCKETS, 'ALL')}
        items = []
        for item in data[side]:
            amount = Decimal(item['outstanding'])
            if amount <= 0:
                continue
            key, days, label = bucket(item['due'], ref)
            stats['ALL']['amount'] += amount; stats['ALL']['count'] += 1
            if key in stats:
                stats[key]['amount'] += amount; stats[key]['count'] += 1
            items.append({**{k: item[k] for k in ('id', 'party', 'due')}, 'amount': str(amount), 'bucket': key, 'days': days, 'label': label})
        items.sort(key=lambda i: (i['due'], i['id']))
        sides[side] = {'buckets': {k: {'amount': str(v['amount']), 'count': v['count']} for k, v in stats.items()}, 'items': items}
    week = lambda side: sum(Decimal(sides[side]['buckets'][b]['amount']) for b in ('DUE_TOMORROW', 'NEXT_7'))
    count = lambda side: sum(sides[side]['buckets'][b]['count'] for b in ('DUE_TOMORROW', 'NEXT_7'))
    collections, payables = week('ar'), week('ap')
    # Chart (as in the reference dashboard): the ending-cash line starts at the cash on hand in the first
    # logged month and adds each later month's net flow; then 3 projected months from open invoices and
    # bills due in each of those months.
    months = sorted(set(data['inflow']) | set(data['outflow']))
    total = lambda log, m: sum(Decimal(v) for v in log.get(m, {}).values())
    trend = [{'month': m, 'inflow': total(data['inflow'], m), 'outflow': total(data['outflow'], m), 'projected': False} for m in months]
    running = cash
    for i, point in enumerate(trend):
        if i:
            running += point['inflow'] - point['outflow']
        point['ending'] = running
    if months:
        year, month = map(int, months[-1].split('-'))
        for _ in range(3):
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
            key = '%04d-%02d' % (year, month)
            due = lambda side: sum(Decimal(i['outstanding']) for i in data[side] if i['due'][:7] == key and Decimal(i['outstanding']) > 0)
            inflow, outflow = due('ar'), due('ap')
            running += inflow - outflow
            trend.append({'month': key, 'inflow': inflow, 'outflow': outflow, 'ending': running, 'projected': True})
    return {'available': True, 'reference_date': ref.isoformat(), 'cash_on_hand': str(cash), 'cash_on_hand_recorded': data.get('cash_on_hand'),
            'kpis': {'expected_collections_7d': str(collections), 'collections_count': count('ar'), 'upcoming_payables_7d': str(payables), 'payables_count': count('ap'),
                     'net_runway_7d': str(cash + collections - payables), 'overdue_receivables': sides['ar']['buckets']['OVERDUE']['amount'],
                     'overdue_receivables_count': sides['ar']['buckets']['OVERDUE']['count'], 'overdue_payables': sides['ap']['buckets']['OVERDUE']['amount'],
                     'overdue_payables_count': sides['ap']['buckets']['OVERDUE']['count']},
            'receivables': sides['ar'], 'payables': sides['ap'],
            'trend': [{**p, **{k: str(p[k]) for k in ('inflow', 'outflow', 'ending')}} for p in trend],
            'notes': ['The ending-cash line starts at the cash on hand in the first logged month and adds each later month\'s net inflow minus outflow.',
                      'Projected months use only open invoices and bills due in those months, not expected sales.']}


class CashflowBook:
    def __init__(self, auth, copilot):
        self.auth, self.c = auth, copilot

    def upload(self, token, mid, file):
        self.auth.authorize(token, 'bulk_import', mid)
        actor = self.auth.principal(token)
        if not isinstance(file, dict) or set(file) - {'filename', 'content'}:
            raise InputError('Choose one Excel workbook')
        name = str(file.get('filename') or 'workbook.xlsx')[-120:]
        if not name.lower().endswith('.xlsx'):
            raise InputError('Upload the cash-flow workbook as .xlsx')
        try:
            content = base64.b64decode(str(file.get('content') or ''), validate=True)
        except ValueError:
            raise InputError('Invalid file data') from None
        if not content or len(content) > 3_000_000:
            raise InputError('The workbook must be non-empty and at most 3 MB')
        data = parse(content)
        with self.auth.db() as db:
            db.execute('INSERT INTO cashflow_books VALUES (?,?,?,?,?) ON CONFLICT(merchant_id) DO UPDATE SET data_json=excluded.data_json,source_filename=excluded.source_filename,uploaded_by=excluded.uploaded_by,uploaded_at=excluded.uploaded_at',
                       (mid, json.dumps(data), name, actor.user_id, self.auth.clock()))
        self.auth.audit('cashflow_book_uploaded', actor, mid, result='success')
        return {'ok': True, 'filename': name, 'receivables': len(data['ar']), 'payables': len(data['ap']), 'months': len(set(data['inflow']) | set(data['outflow'])), 'cash_on_hand': data['cash_on_hand']}

    def view(self, token, mid, ref=None, cash=None):
        self.auth.authorize(token, 'view_forecasts', mid)
        with self.auth.db() as db:
            row = db.execute('SELECT data_json,source_filename,uploaded_at FROM cashflow_books WHERE merchant_id=?', (mid,)).fetchone()
        if not row:
            return {'available': False, 'can_upload': self._can(token, mid)}
        try:
            reference = date.fromisoformat(ref) if ref else date.today()
        except ValueError:
            raise InputError('Reference date must be YYYY-MM-DD') from None
        override = None
        if cash not in (None, ''):
            override = _money(cash, 'Cash on hand')
        result = summarize(json.loads(row[0]), reference, override)
        return {**result, 'source_filename': row[1], 'uploaded_at': row[2], 'can_upload': self._can(token, mid)}

    def template(self, token, mid):
        self.auth.authorize(token, 'bulk_import', mid)
        from copilot.report_template import cashflow_workbook
        m = self.c.merchants[mid]
        return cashflow_workbook(m.name, m.currency)

    def _can(self, token, mid):
        try:
            self.auth.authorize(token, 'bulk_import', mid)
            return True
        except Exception:
            return False
