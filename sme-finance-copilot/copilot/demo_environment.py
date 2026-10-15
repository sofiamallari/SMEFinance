"""Active CNY demo environment. Fail closed; never silently recreate legacy storage."""
import json, os
from pathlib import Path
NAME='shenzhen_cny_demo'
def selected():return os.environ.get('COPILOT_DATASET',NAME)==NAME
def configure_storage(require_ready=True):
    if not selected():raise RuntimeError('The application only serves shenzhen_cny_demo; legacy_fixture is reserved for offline compatibility checks')
    if os.environ.get('COPILOT_AUTH_MODE','authenticated')!='authenticated':
        raise RuntimeError('The CNY dataset requires authenticated mode')
    value=os.environ.get('COPILOT_DATA_DIR')
    if not value:
        if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_ENVIRONMENT_ID'):
            raise RuntimeError('Railway requires COPILOT_DATA_DIR on a persistent volume')
        value=str(Path(__file__).resolve().parents[1]/'logs'/NAME)
    root=Path(value).resolve()
    if require_ready:
        marker=root/'dataset.json'
        if not marker.exists() or json.loads(marker.read_text(encoding='utf-8')).get('dataset')!=NAME:
            raise RuntimeError('CNY dataset is not initialized; run python -m copilot.cny_demo seed first')
    for key,name in {'COPILOT_IDENTITY_DB':'identity.sqlite3','COPILOT_TRANSACTION_FILE':'transactions.jsonl',
                     'COPILOT_AUDIT_LOG':'audit.jsonl','COPILOT_EXEC_LOG':'execution.jsonl'}.items():
        target=root/name
        if os.environ.get(key) and Path(os.environ[key]).resolve()!=target:
            raise RuntimeError('Conflicting '+key+'; CNY data must remain in its dedicated directory')
        os.environ[key]=str(target)
    return root

def merchants(as_of):
    from copy import deepcopy
    from copilot.data.synthetic import PERSONAS,build_merchant
    # Fresh RMB scenario budgets, selected by business scale, NOT exchange rates.
    # daily sales / debt service / synthetic opening wallet / confirmed orders.
    budgets={'M001':(680,720,430,0),'M006':(1850,1200,8600,0),
             'M002':(3600,5400,19800,0),'M003':(8200,12500,96000,210000),
             'M004':(26500,42000,580000,0),'M005':(11800,18000,245000,0)}
    result={}
    for original in PERSONAS:
        p=deepcopy(original);daily,debt,wallet,orders=budgets[p['merchant_id']]
        p.update(currency='CNY',base_daily=daily,monthly_debt_service=debt,
                 wallet_balance=wallet,confirmed_orders_value=orders,seed=p['seed']+20261015)
        result[p['merchant_id']]=build_merchant(p,as_of)
    return result
