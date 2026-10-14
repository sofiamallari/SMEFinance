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
    version=c.financial_data.version(mid)
    as_of=c.financial_data.as_of(mid).isoformat()
    def read(action,tool):
        if not permitted(p,action,mid):return None,'Not authorized for this evidence source.'
        try:return c.call(p,tool,mid),None
        except AccessDenied:return None,'Not authorized by current tool policy.'
        except ValueError:return None,'Evidence unavailable from current records; review the source module.'
    assessment,assessment_missing=read('view_assessment','assess_business')
    matches,matches_missing=read('view_financing','match_financing')
    incentive,incentive_missing=read('view_dashboard','incentive_status')
    forecast,forecast_missing=read('view_forecasts','cashflow_forecast')
    provenance=c.financial_data.aggregate(mid)['provenance'] if assessment or matches or incentive else []
    provenance_label=', '.join(sorted(provenance)) or 'no_records'
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
    rules={
        'identify':'A team-approved rule linking diagnosed constraints to completion of Identify is not specified.',
        'profile':'A team-approved sufficient-profile rule for the five-step journey is not specified.',
        'place':'A team-approved rule for accepting a financing placement is not specified.',
        'activate':'A team-approved rule mapping confirmed sandbox submission to journey completion is not specified.',
        'measure':'Post-activation baseline, comparison period and outcome/success criteria are not specified.'}
    for stage in stages:
        stage['evidence']=[]
        stage['missing_requirements']=[rules[stage['id']]]
        stage['completion_rule_status']='Not specified'
    def evidence(index,source,summary,origin=provenance_label):
        stages[index]['evidence'].append({'source':source,'summary':summary,'as_of':as_of,'provenance':origin})
    if assessment:
        constraints=assessment['constraints']
        evidence(0,'assess_business','Existing diagnosed constraints: '+('; '.join(item['constraint']+': '+item['evidence'] for item in constraints) or 'None triggered by current rules.'))
        evidence(1,'assess_business','Existing business maturity: '+assessment['stage_name']+'; composite score '+str(assessment['composite_score'])+'/100; credit readiness '+str(assessment['scores']['credit_readiness'])+'/100. These are assessment results, not five-step completion.')
        evidence(1,'assess_business','Recorded history: '+str(assessment['signals']['history_days'])+' days; digital share '+str(assessment['signals']['digital_share'])+'. Profile attributes and thresholds remain demo/provisional.')
    else:
        stages[0]['missing_requirements'].append(assessment_missing)
        stages[1]['missing_requirements'].append(assessment_missing)
    if matches:
        evidence(2,'match_financing','Existing indicative matches: '+('; '.join(item['name']+' (score '+str(item['match_score'])+')' for item in matches['recommendations']) or 'No matches returned.'))
        evidence(2,'match_financing','Existing exclusions: '+('; '.join(item['name']+': '+', '.join(item['why_not_yet']) for item in matches['not_yet_eligible']) or 'None returned.'))
    else:stages[2]['missing_requirements'].append(matches_missing)
    applications=None
    if c.identity_store and permitted(p,'view_applications',mid):
        with c.identity_store.db() as db:
            records=db.execute('SELECT owner_id,recipient_id,packet FROM applications WHERE merchant_id=?',(mid,)).fetchall()
        visible=[json.loads(row['packet']) for row in records if p.role=='owner' or row['recipient_id']==p.user_id]
        applications=len(visible)
        if applications:stages[3]['reason']='An authorized saved simulated application exists, but submission is not an implemented journey-completion rule.'
        else:stages[3]['reason']='No authorized saved application is recorded; no journey-completion rule is implemented.'
    if applications is not None:
        evidence(3,'applications','Authorized saved simulated application count: '+str(applications)+'. Submission is not lender approval or a defined journey completion rule.','simulated_application')
    else:stages[3]['missing_requirements'].append('Authorized saved application evidence is unavailable.')
    if forecast:
        evidence(4,'cashflow_forecast','Current estimated minimum modeled balance: '+str(forecast['min_balance'])+' '+c.merchants[mid].currency+'. This is a current forecast, not measured post-activation improvement.','forecast')
    else:stages[4]['missing_requirements'].append(forecast_missing)
    stages[4]['missing_requirements'].append('Legacy in-memory maturity comparisons do not establish measured post-financing outcomes.')
    milestone={'status':'Provisional demo rules' if incentive else 'Unavailable','data':incentive,
               'reason':incentive_missing or 'Existing calendar-month ecosystem-growth milestone; not a journey stage, eligibility approval or paid reward.',
               'as_of':as_of,'provenance':provenance_label if incentive else 'no_records'}
    if c.financial_data.version(mid)!=version:raise ValueError('Journey data changed; reload for fresh evidence')
    next_stage=next((s for s in stages if s['links']),None)
    result={'merchant_id':mid,'title':'Merchant Financing Journey','stages':stages,'current_stage':None,
            'assessment_status':'Not Yet Assessed','next_action':next_stage['next_action'] if next_stage else 'No linked journey action is authorized for this account.',
            'next_action_code':next_stage['id'] if next_stage else 'none','application_count':applications,
            'data_version':version,'as_of':as_of,'incentive':milestone,'limitations':['The five journey steps are separate from the existing six business maturity stages.','No completion, readiness or outcome has been inferred from page visits or application submission.','No new financial calculations, thresholds or approval rules are applied.']}
    result['journey_version']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result

def explain(result):
    lines=['Merchant Financing Journey: current journey stage cannot be determined because implemented completion rules are unavailable.']
    lines.extend(s['name']+': '+s['status']+'. '+s['reason'] for s in result['stages'])
    for step in result['stages']:
        lines.extend(step['name']+' evidence: '+item['summary']+' [source: '+item['source']+'; as of '+item['as_of']+'; provenance: '+item['provenance']+']' for item in step['evidence'])
        lines.append(step['name']+' missing requirements: '+' '.join(step['missing_requirements']))
    lines.append('Completed journey steps: none established by implemented completion rules.')
    milestone=result['incentive']
    if milestone['data']:
        data=milestone['data']
        lines.append('Incentive milestone: '+data['tier_name']+' (tier '+str(data['tier'])+'). '+milestone['reason'])
        if data['note']:lines.append(data['note'])
        if data['next_milestone']:lines.append('Existing next incentive milestone: '+data['next_milestone']['name']+'. This is not journey advancement.')
    else:lines.append('Incentive milestone unavailable: '+milestone['reason'])
    lines.append('Next recommended action: '+result['next_action'])
    lines.append('These are journey steps, not the six maturity stages. No stage completion, lender approval or financial outcome has been inferred. Applications remain simulated and require existing consent and explicit confirmation.')
    return '\n'.join(lines)
