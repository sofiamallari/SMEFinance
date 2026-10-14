"""Authenticated fixtures for existing HTTP and MCP regressions."""
import tempfile
from pathlib import Path
from copilot.auth import AuthStore
from copilot.agent import Copilot
from copilot.modules.transactions import TransactionStore

PASSWORD='Test-Secure-Password-123'
CHANGED='Changed-Secure-Password-456'
ALL={'M001','M002','M003','M004','M005','M006'}

def setup_identity(test, all_merchants=False):
    test.tmp=tempfile.TemporaryDirectory()
    test.addCleanup(test.tmp.cleanup)
    test.c=Copilot()
    test.auth=AuthStore(Path(test.tmp.name)/'identity.sqlite3',test.c.merchants)
    test.admin=test.auth.bootstrap('security','security@example.test',PASSWORD)
    test.tokens={'security_admin':test.auth.login('security',PASSWORD)[0]}
    test.ids={'security_admin':test.admin['user_id']}
    for role in ('owner','staff','lender_analyst','user_admin'):
        body={'username':role,'email':role+'@example.test','display_name':role,'role':role,
              'merchants':[] if role=='user_admin' else sorted(ALL if all_merchants else {'M002'}),
              'organization':'Demo lender' if role=='lender_analyst' else '',
              'optional_permissions':['bulk_import'] if all_merchants and role=='staff' else [],
              'transaction_grants':{m:['create_transactions']+(['bulk_import'] if all_merchants else []) for m in (ALL if all_merchants else {'M002'})} if role=='staff' else {}}
        with test.auth.db() as db:
            user=test.auth._create(db,test.auth.principal(test.tokens['security_admin']),body,PASSWORD,False)
        test.ids[role]=user['user_id'];test.tokens[role]=test.auth.login(role,PASSWORD)[0]
    test.c.identity_store=test.auth;test.c.audit.sink=test.auth.financial_audit
    test.store=TransactionStore(test.c,str(Path(test.tmp.name)/'transactions.jsonl'))

def attach_server(test):
    from copilot import server
    old=server.COPILOT,server.STORE,server.AUTH
    server.COPILOT,server.STORE,server.AUTH=test.c,test.store,test.auth
    test.addCleanup(lambda:set_server(server,old))

def set_server(server,old):
    server.COPILOT,server.STORE,server.AUTH=old
