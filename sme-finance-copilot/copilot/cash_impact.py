"""Non-mutating hypothetical cash schedules; the existing forecast owns the path."""
import copy,calendar
from datetime import date,timedelta
from decimal import Decimal
from copilot.modules.cashflow import forecast

LIMITATIONS=[
 'Synthetic demo opening balance is not current spendable cash, a live wallet or a bank balance.',
 'Imported transactions do not automatically reconcile the synthetic opening balance.',
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
 def metrics(f):
  return {k:format(Decimal(str(f[k])),'.2f') if k in ('closing_balance','min_balance') else f[k] for k in ('closing_balance','min_balance','runway_days','buffer_days')}
 baseline=forecast(m,assessment,days);adjusted=forecast(m,assessment,days,extra_outflows=schedule)
 result={'currency':m.currency,'assessment_date':assessment.isoformat(),'opening_balance_date':c.as_of.isoformat(),
  'latest_data_date':latest_data(c,mid) or 'unavailable','synthetic_opening_balance':format(Decimal(str(m.wallet_balance)),'.2f'),
  'horizon_days':days,'baseline':metrics(baseline),'adjusted':metrics(adjusted),
  'user_cash_baseline':None,'user_cash_adjusted':None,'schedule':schedule,'limitations':list(LIMITATIONS)}
 if 'user_cash' in args:
  alternate=copy.deepcopy(m);alternate.wallet_balance=float(args['user_cash'])
  result['user_cash_baseline']=metrics(forecast(alternate,assessment,days))
  result['user_cash_adjusted']=metrics(forecast(alternate,assessment,days,extra_outflows=schedule))
 return result
