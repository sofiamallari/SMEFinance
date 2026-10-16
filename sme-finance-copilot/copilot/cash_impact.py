"""Non-mutating hypothetical cash schedules; the existing forecast owns the path."""
import copy,calendar
from datetime import date,timedelta
from decimal import Decimal
from copilot.modules.cashflow import forecast

LIMITATIONS=[
 'The opening balance comes from the app and is not reconciled with your bank account.',
 'Imported transactions do not automatically update the opening balance.',
 'Historical variable outflows include only supplies, operating and household_draw; expenses classified other are excluded.',
 'Expense-coverage buffer uses included historical variable outflows and averaged debt service; it does not independently measure all scheduled obligations.',
 'Payroll has no separate existing category. Proposed salary is incremental; existing payroll coverage is incomplete.',
 'Existing scheduled payables and debt service are included once by the baseline forecast; do not add them again.',
 'Hypothetical projections are not guaranteed affordability or financing approval. Digital Payments Simulator activity is excluded.'
]

def latest_data(c,mid):
 m=c.financial_data.project(mid)
 dates=[r['date'] for r in m.transactions+m.expenses]
 return max(dates) if dates else None

def run(c,mid,args):
 assessment=date.fromisoformat(args['assessment_date']);days=args['horizon_days']
 if not 1<=days<=180:raise ValueError('Forecast horizon must be within 180 days')
 end=assessment+timedelta(days=days);schedule=[]
 def add(d,value):
  n=Decimal(str(value))
  if not n.is_finite() or n<0 or n>Decimal('1000000000') or n!=n.quantize(Decimal('.01')):raise ValueError('Invalid hypothetical amount')
  if assessment<=d<=end:schedule.append({'date':d.isoformat(),'amount':format(n,'.2f')})
 if 'one_time_cost' in args:
  d=date.fromisoformat(args.get('purchase_date',args['assessment_date']))
  if d<assessment or d>end:raise ValueError('Purchase date must be inside the forecast horizon')
  add(d,args['one_time_cost'])
 if 'monthly_cost' in args:
  if 'start_date' not in args:raise ValueError('Specify a start date for incremental recurring costs')
  start=date.fromisoformat(args['start_date'])
  if start<assessment or start>end:raise ValueError('Start date must be inside the forecast horizon')
  for offset in range(7):
   month=start.month-1+offset;y=start.year+month//12;mo=month%12+1
   d=date(y,mo,min(start.day,calendar.monthrange(y,mo)[1]))
   if d>end:break
   add(d,args['monthly_cost'])
 if not schedule:raise ValueError('A nonempty explicit hypothetical cost is required')
 m=c.financial_data.project(mid)
 # The synthetic wallet balance is dated c.as_of, so the existing forecast must start there;
 # starting at the assessment date would silently skip the days in between.
 anchor=min(c.as_of,assessment);span=(end-anchor).days
 def metrics(f):
  row={k:format(Decimal(str(f[k])),'.2f') if k in ('closing_balance','min_balance') else f[k] for k in ('closing_balance','min_balance','runway_days','buffer_days')}
  row['first_negative_date']=(anchor+timedelta(days=f['runway_days'])).isoformat() if f['runway_days'] is not None else None
  return row
 # Combined scenario: the stated sales/expense % change applies to the recent pattern across the whole projection.
 changes={k:args.get(k) for k in ('sales_change_percent','expense_change_percent')}
 factors=dict(inflow_factor=1+float(changes['sales_change_percent'] or 0)/100,outflow_factor=1+float(changes['expense_change_percent'] or 0)/100)
 baseline=forecast(m,anchor,span);adjusted=forecast(m,anchor,span,extra_outflows=schedule,**factors)
 result={'currency':m.currency,'assessment_date':assessment.isoformat(),'opening_balance_date':anchor.isoformat(),
  'latest_data_date':latest_data(c,mid) or 'unavailable','synthetic_opening_balance':format(Decimal(str(m.wallet_balance)),'.2f'),
  'horizon_days':days,'baseline':metrics(baseline),'adjusted':metrics(adjusted),
  'user_cash_baseline':None,'user_cash_adjusted':None,'schedule':schedule,'limitations':list(LIMITATIONS),
  'assumed_changes':changes if any(v is not None for v in changes.values()) else None}
 if 'user_cash' in args:
  alternate=copy.deepcopy(m);alternate.wallet_balance=float(args['user_cash'])
  # User-reported cash is "now", so its separate projection starts at the assessment date.
  anchor=assessment;span=days
  result['user_cash_baseline']=metrics(forecast(alternate,assessment,days))
  result['user_cash_adjusted']=metrics(forecast(alternate,assessment,days,extra_outflows=schedule,**factors))
 return result
