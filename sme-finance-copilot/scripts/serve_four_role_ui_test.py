import sys,os,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
tmp=tempfile.TemporaryDirectory()
for key,name in [('COPILOT_IDENTITY_DB','initial.sqlite3'),('COPILOT_TRANSACTION_FILE','initial.jsonl'),('COPILOT_AUDIT_LOG','audit.jsonl'),('COPILOT_EXEC_LOG','execution.jsonl')]:os.environ[key]=str(Path(tmp.name)/name)
os.environ['COPILOT_AGENT_MODE']='rule_engine'
from tests.auth_support import setup_identity,attach_server
class F:
 def __init__(self):self.cleanups=[]
 def addCleanup(self,fn):self.cleanups.append(fn)
f=F();setup_identity(f);attach_server(f)
from copilot.server import Handler
from http.server import ThreadingHTTPServer
print('Isolated four-role browser fixture ready',flush=True)
try:ThreadingHTTPServer(('127.0.0.1',8126),Handler).serve_forever()
finally:
 for fn in reversed(f.cleanups):fn()
 tmp.cleanup()
