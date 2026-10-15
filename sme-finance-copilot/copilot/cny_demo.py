"""Explicit, idempotent CNY demonstration preparation. Never opens original storage for writes."""
import argparse, json, os, sqlite3, hashlib
from pathlib import Path
from decimal import Decimal
from copilot.demo_environment import NAME,configure_storage

def write_json(path,value):
    temporary=path.with_suffix('.pending')
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True),encoding='utf-8')
    temporary.replace(path)

def runtime(root):
    from copilot.agent import Copilot
    from copilot.auth import AuthStore
    from copilot.modules.transactions import TransactionStore
    from copilot.pos_import import POSImportService
    c=Copilot(audit_path=str(root/'audit.jsonl'),exec_path=str(root/'execution.jsonl'))
    a=AuthStore(root/'identity.sqlite3',c.merchants);c.identity_store=a;c.audit.sink=a.financial_audit
    store=TransactionStore(c,str(root/'transactions.jsonl'))
    return c,a,POSImportService(a,store)

def validate(root):
    c,a,pos=runtime(root)
    records,_=pos.journal.read()
    assert all(m.currency=='CNY' for m in c.merchants.values())
    assert all(r['currency']=='CNY' for r in records.values())
    with a.db() as db:
        assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
        assert not db.execute('pragma foreign_key_check').fetchall()
        assert not db.execute("SELECT 1 FROM memberships m JOIN users u USING(user_id) WHERE u.role='SYSTEM_ADMIN'").fetchone()
        for table,column in [('applications','packet'),('simulated_payment_state','state_json')]:
            assert all(json.loads(r[0])['currency']=='CNY' for r in db.execute('SELECT '+column+' FROM '+table))
        counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in
                ['users','memberships','merchant_profiles','pos_import_runs','quality_alerts','consents','applications','application_reviews','simulated_payment_state']}
    for payment in c.payments.payments.values():
        if payment.status=='PAID':
            assert Decimal(str(payment.amount))-Decimal(str(payment.mdr_fee))==Decimal(str(payment.net_settled))
    counts['canonical_transactions']=len(records)
    counts['seed_sales_rows']=sum(len(m.transactions) for m in c.financial_data.base.values())
    counts['seed_expense_rows']=sum(len(m.expenses) for m in c.financial_data.base.values())
    counts['receivables']=sum(len(m.receivables) for m in c.financial_data.base.values())
    counts['payables']=sum(len(m.payables) for m in c.financial_data.base.values())
    return {'dataset':NAME,'currency':'CNY','counts':counts,'integrity':'PASS','settlements':'PASS'}

def seed(root,source,password,reference_json=None):
    from copilot.security import AccessDenied
    if (root/'dataset.json').exists():
        report=validate(root);print(json.dumps(report,indent=2));return
    root.mkdir(parents=True,exist_ok=True)
    # A partial seed is deliberately not retried: avoids duplicating confirmed actions.
    if any(root.iterdir()):raise RuntimeError('Target is not empty; inspect partial preparation before retrying')
    write_json(root/'preparation.json',{'dataset':NAME,'state':'preparing','version':1})
    c,a,pos=runtime(root)
    a.bootstrap('demo_admin','admin@example.test',password)
    admin=a.login('demo_admin',password)[0];actor=a.principal(admin)
    # Read only structural memberships/grants. No names, addresses, passwords or tokens copied.
    if reference_json:
        model=json.loads(reference_json.read_text(encoding='utf-8'))
        if model.get('synthetic') is not True:raise RuntimeError('Synthetic reference manifest required')
        reference=sqlite3.connect(':memory:')
        reference.executescript('CREATE TABLE users(user_id,role); CREATE TABLE memberships(user_id,merchant_id); CREATE TABLE merchant_transaction_grants(user_id,merchant_id,permission); CREATE TABLE consents(merchant_id,owner_id,recipient_id,categories,revoked_at); CREATE TABLE applications(merchant_id,created_at);')
        for user in model['users']:
            reference.execute('INSERT INTO users VALUES (?,?)',(user['user_id'],user['role']))
            reference.executemany('INSERT INTO memberships VALUES (?,?)',[(user['user_id'],mid) for mid in user['merchants']])
            reference.executemany('INSERT INTO merchant_transaction_grants VALUES (?,?,?)',[(user['user_id'],mid,permission) for mid,permission in user['grants']])
        for consent in model['consents']:reference.execute('INSERT INTO consents VALUES (?,?,?,?,?)',tuple(consent[k] for k in ['merchant_id','owner_id','recipient_id','categories','revoked_at']))
        reference.executemany('INSERT INTO applications VALUES (?,?)',[(mid,i) for i,mid in enumerate(model['applications'])])
    else:reference=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
    reference.row_factory=sqlite3.Row
    identities={};tokens={};mapping={};ordinal={}
    for row in reference.execute('SELECT user_id,role FROM users ORDER BY role,user_id'):
        role=row['role']
        if role=='SYSTEM_ADMIN':mapping[row['user_id']]=actor.user_id;continue
        alias={'SME_OWNER':'owner','SME_STAFF':'staff','BANK':'bank'}.get(role)
        if not alias:raise RuntimeError('Unsupported source role requires operator review')
        ordinal[alias]=ordinal.get(alias,0)+1
        name='demo_'+alias+('' if ordinal[alias]==1 else str(ordinal[alias]))
        mids=[r[0] for r in reference.execute('SELECT merchant_id FROM memberships WHERE user_id=?',(row['user_id'],))]
        if set(mids)-set(c.merchants):raise RuntimeError('Source contains merchants outside the six reference personas')
        grants={m:[r[0] for r in reference.execute('SELECT permission FROM merchant_transaction_grants WHERE user_id=? AND merchant_id=?',(row['user_id'],m))] for m in mids} if alias=='staff' else {}
        body={'username':name,'email':name+'@example.test','display_name':name.replace('_',' ').title(),
              'role':role,'merchants':mids,'transaction_grants':grants,
              'organization':'Synthetic Shenzhen Bank' if alias=='bank' else ''}
        with a.db() as db:user=a._create(db,actor,body,password,False)
        mapping[row['user_id']]=user['user_id'];identities[alias]=user['user_id'];tokens[alias]=a.login(name,password)[0]
    # Retain only the membership graph and allowed grants; no consent is inherited.
    owner=tokens['owner'];p=a.principal(owner)
    day='2026-09-25'
    for mid in c.merchants:
        a.authorize(owner,'create_transactions',mid)
        for kind,amount in [('sale','148.50'),('expense','46.25'),('refund','12.50')]:
            pos.single(owner,mid,{'transaction_date':day,'net_amount':amount,'currency':'CNY',
               'transaction_type':kind,'payment_method':'cash','status':'completed','category':'supplies' if kind=='expense' else 'sales',
               'description':'Synthetic CNY demonstration '+kind,'external_reference':mid+'-CNY-'+kind},'cny-demo-'+mid+'-'+kind)
    # Recreate consent relationships using fresh parties and fresh validity; no routing-implied grant.
    for row in reference.execute('SELECT merchant_id,owner_id,recipient_id,categories,revoked_at FROM consents'):
        recipient=mapping[row['recipient_id']]
        grant=a.grant_consent(owner,{'merchant':row['merchant_id'],'recipient_id':recipient,
             'purpose':'Synthetic demonstration financial review','categories':json.loads(row['categories']),
             'expires_at':a.clock()+180*86400})
        if row['revoked_at'] is not None:a.revoke_consent(owner,grant['consent_id'])
    application_merchants=[r[0] for r in reference.execute("SELECT merchant_id FROM applications ORDER BY created_at")]
    reference.close()
    # Explicit scenario initialization confirmations; not AI-generated actions.
    for method,state,value in [('qr_pay','PAID','68.50'),('tap_pay','PAID','125.00'),
                               ('pay_link','PENDING','89.00'),('qr_pay','CANCELLED','42.00')]:
        action=c.partner_state.propose(p,'M002',p.session_id,'payment_create',{'method':method,'amount':value})
        result=c.partner_state.confirm(p,'M002',p.session_id,action['action_id'],True)
        ref=result['result']['ref']
        if state=='PAID':c.payments.simulate_customer_payment(ref)
        elif state=='CANCELLED':c.payments.cancel(ref)
    # Expiry uses the simulator clock and normal status transition; no state is fabricated.
    action=c.partner_state.propose(p,'M002',p.session_id,'payment_create',{'method':'qr_pay','amount':'36.50'})
    result=c.partner_state.confirm(p,'M002',p.session_id,action['action_id'],True)
    ref=result['result']['ref'];saved_clock=c.payments.clock
    try:
        c.payments.clock=lambda:saved_clock()+301
        c.payments.status(ref)
    finally:c.payments.clock=saved_clock
    # POS-integrated cart collection is a distinct checkout, not an imported receipt.
    action=c.partner_state.propose(p,'M002',p.session_id,'payment_create',{'method':'tap_pay','items':[{'name':'Synthetic lunch','price':38.50,'qty':2}]})
    result=c.partner_state.confirm(p,'M002',p.session_id,action['action_id'],True)
    c.payments.simulate_customer_payment(result['result']['ref'])
    # Independent, explicitly synthetic source receipts; never settlement duplicates.
    import base64,csv,io,zipfile
    from xml.sax.saxutils import escape
    headers=['date','net_amount','currency','type','channel','status','reference']
    def source_file(kind):
        rows=[headers]+[['2026-09-24',format(Decimal('28.50')+Decimal(i)*Decimal('.75'),'.2f'),'CNY','sale','cash','completed',kind+'-CNY-'+str(i)] for i in range(100)]
        if kind=='CSV':
            out=io.StringIO();csv.writer(out).writerows(rows);payload=out.getvalue().encode()
        else:
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
                z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
                z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Synthetic Revenue" sheetId="1" r:id="rId1"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
                xml=[]
                for i,row in enumerate(rows,1):
                    cells=''.join('<c r="'+chr(65+j)+str(i)+'" t="inlineStr"><is><t>'+escape(str(v))+'</t></is></c>' for j,v in enumerate(row))
                    xml.append('<row r="'+str(i)+'">'+cells+'</row>')
                z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(xml)+'</sheetData></worksheet>')
            payload=out.getvalue()
        name='synthetic-cny.'+('csv' if kind=='CSV' else 'xlsx')
        (root/name).write_bytes(payload)
        return {'filename':name,'content':base64.b64encode(payload).decode()}
    for kind in ['CSV','XLSX']:
        file=source_file(kind);staged=pos.stage(owner,'M002',[file])
        mappings={f['file_id']:{'columns':dict(f['suggestions']),'defaults':{'currency':'CNY','transaction_type':'sale','status':'completed'},'timezone':'+08:00','date_format':'iso','report_kind':'transactions','review':{'type_confirmed':True},'control_totals':{}} for f in staged['files']}
        checked=pos.validate(owner,'M002',staged['batch_id'],mappings)
        if not checked['valid']:raise RuntimeError('Synthetic import validation failed: '+json.dumps(checked.get('findings')))
        pos.commit(owner,'M002',staged['batch_id'],checked['preview_token'],True)
        # Re-upload demonstrates duplicate prevention; preview is retained, never committed.
        duplicate=pos.stage(owner,'M002',[file]);pos.validate(owner,'M002',duplicate['batch_id'],{f['file_id']:{**next(iter(mappings.values())),'columns':dict(f['suggestions'])} for f in duplicate['files']})
    from copilot.bank_workflow import BankWorkflow
    workflow=BankWorkflow(a,c)
    for mid in application_merchants:
        # A submission needs the pre-existing applications-category authorization.
        with a.db() as db:consent=a._consent(db,mid,identities['bank'],'applications')
        if not consent:continue
        from copilot.modules import rbf
        a.authorize(owner,'view_financing',mid)
        limits=rbf.limits(c.financial_data.project(mid),c.financial_data.as_of(mid))
        value=Decimal(str(limits['max_advance']))*Decimal('.20')
        value=value.quantize(Decimal('.01'))
        draft=workflow.draft(owner,mid,body={'amount':str(value),'recipient_id':identities['bank'],'product_id':'RBF'})
        did=draft['drafts'][0]['draft_id'];action=workflow.propose(owner,mid,did)
        result=c.partner_state.confirm(p,mid,p.session_id,action['action_id'],True)
        with a.db() as db:aid=db.execute('SELECT application_id FROM applications WHERE merchant_id=? ORDER BY created_at DESC',(mid,)).fetchone()[0]
        for outcome in ['reviewed','more_information_needed','ready_for_further_assessment']:
            workflow.record_review(tokens['bank'],aid,{'outcome':outcome,'note':'Synthetic demonstration review: '+outcome.replace('_',' ')})
    # Negative permission checks use the same backend, not UI visibility.
    for token,action,mid in [(admin,'view_reports','M002'),(tokens['staff'],'submit_application','M002'),(tokens['bank'],'view_reports','M003')]:
        try:a.authorize(token,action,mid)
        except AccessDenied:pass
        else:raise RuntimeError('Expected authorization denial did not occur')
    # Seeding does not reuse cached assessment scores or old monetary values.
    report=validate(root)
    write_json(root/'dataset.json',{'dataset':NAME,'version':1,'as_of':c.as_of.isoformat(),
               'financial_seed':20261015,'synthetic':True,'tax_assumption':'zero sandbox tax, not Chinese VAT',
               'accounts':['demo_admin','demo_owner','demo_staff','demo_bank'],
               'counts':report['counts']})
    write_json(root/'validation.json',report)
    print(json.dumps(report,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['seed','verify'])
    parser.add_argument('--source-database',type=Path)
    parser.add_argument('--reference-json',type=Path,default=Path(__file__).parent/'data/shenzhen_reference.json')
    parser.add_argument('--password-env',default='COPILOT_CNY_DEMO_PASSWORD')
    args=parser.parse_args()
    if os.environ.get('COPILOT_DATASET',NAME)!=NAME:parser.error('Set COPILOT_DATASET=shenzhen_cny_demo')
    root=configure_storage(require_ready=args.command=='verify')
    if args.command=='verify':print(json.dumps(validate(root),indent=2));return
    if args.source_database:
        if not args.source_database.is_file():parser.error('Source database does not exist')
        if root==args.source_database.resolve().parent or args.source_database.resolve().is_relative_to(root):parser.error('Source and replacement storage must be separate')
    elif not args.reference_json.is_file():parser.error('Synthetic relationship manifest is required')
    password=os.environ.pop(args.password_env,None)
    if not password and not (root/'dataset.json').exists():parser.error('Provide a strong synthetic account password via the named environment variable')
    seed(root,args.source_database,password,None if args.source_database else args.reference_json)

if __name__=='__main__':main()
