"""Read-only financing journey; no inferred completion rules or new persistence."""
import hashlib,json
from copilot.authorization import require,BOUNDARIES
from copilot.security import AccessDenied

STEPS=(
 ('identify','Identify','Understand financing needs','view_forecasts','cashflow','Review cash flow and identify your financing need.'),
 ('profile','Profile','Review merchant financial information','view_dashboard','dashboard','Review recorded sales, expenses and transaction sources.'),
 ('place','Place','Explore matched financing options','view_financing','financing','Review the existing financing matches and their limitations.'),
 ('activate','Activate','Review or submit simulated financing applications','view_applications','applications','Review saved applications; an Owner may propose a consent-authorized simulated application.'),
 ('measure','Measure','Monitor financial outcomes','view_forecasts','cashflow','Review Dashboard and Cash Flow after business data changes.'),
)

def permitted(p,action,mid):
    if action not in BOUNDARIES.get(p.role,set()):return False
    try:require(p,action,mid);return True
    except AccessDenied:return False

def build(c,p,mid):
    require(p,'view_financing',mid)
    if mid not in p.merchant_ids or 'view_financing' not in BOUNDARIES.get(p.role,set()):raise AccessDenied('Financing journey access denied')
    stages=[]
    for key,name,purpose,action,tab,next_action in STEPS:
        allowed=permitted(p,action,mid)
        links=[{'tab':tab,'label':'Open '+{'cashflow':'Cash Flow','dashboard':'Dashboard','financing':'Financing Overview','applications':'Applications'}[tab]}] if allowed else []
        if key=='profile' and permitted(p,'view_transactions',mid):links.append({'tab':'transaction-history','label':'Open Transaction History'})
        if key=='measure' and permitted(p,'view_dashboard',mid):links.append({'tab':'dashboard','label':'Open Dashboard'})
        stages.append({'id':key,'name':name,'purpose':purpose,'status':'Not Yet Assessed' if links else 'Blocked',
                       'reason':'No implemented completion rule exists for this journey step.' if links else 'The linked business views are not authorized for this account.',
                       'next_action':next_action if links else 'Ask the Owner or administrator to review the necessary access; this does not indicate business ineligibility.',
                       'links':links})
    applications=None
    if c.identity_store and permitted(p,'view_applications',mid):
        with c.identity_store.db() as db:
            records=db.execute('SELECT owner_id,recipient_id,packet FROM applications WHERE merchant_id=?',(mid,)).fetchall()
        visible=[json.loads(row['packet']) for row in records if p.role=='owner' or row['recipient_id']==p.user_id]
        applications=len(visible)
        if applications:stages[3]['reason']='An authorized saved simulated application exists, but submission is not an implemented journey-completion rule.'
        else:stages[3]['reason']='No authorized saved application is recorded; no journey-completion rule is implemented.'
    next_stage=next((s for s in stages if s['links']),None)
    result={'merchant_id':mid,'title':'Merchant Financing Journey','stages':stages,'current_stage':None,
            'assessment_status':'Not Yet Assessed','next_action':next_stage['next_action'] if next_stage else 'No linked journey action is authorized for this account.',
            'next_action_code':next_stage['id'] if next_stage else 'none','application_count':applications,
            'data_version':c.financial_data.version(mid),'limitations':['The five journey steps are separate from the existing six business maturity stages.','No completion, readiness or outcome has been inferred from page visits or application submission.','No new financial calculations, thresholds or approval rules are applied.']}
    result['journey_version']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result

def explain(result):
    lines=['Merchant Financing Journey: current journey stage cannot be determined because implemented completion rules are unavailable.']
    lines.extend(s['name']+': '+s['status']+'. '+s['reason'] for s in result['stages'])
    lines.append('Next recommended action: '+result['next_action'])
    lines.append('These are journey steps, not the six maturity stages. No stage completion, lender approval or financial outcome has been inferred. Applications remain simulated and require existing consent and explicit confirmation.')
    return '\n'.join(lines)
