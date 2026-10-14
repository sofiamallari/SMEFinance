"""Reproducible offline regression evidence. Local keys are disabled by tests."""
import json,sys,time,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tests
root=Path(__file__).resolve().parents[1]
syntax=[]
for folder in ('copilot','tests','scripts'):
    for path in (root/folder).rglob('*.py'):
        compile(path.read_text(encoding='utf-8-sig'),str(path),'exec');syntax.append(str(path.relative_to(root)))
cases=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):
        self.started=time.monotonic();super().startTest(test)
    def addSuccess(self,test):
        super().addSuccess(test);cases.append({'test':test.id(),'status':'PASS','seconds':round(time.monotonic()-self.started,3)})
        if len(cases)%25==0:print('Verified '+str(len(cases))+' methods',flush=True)
    def addFailure(self,test,err):
        super().addFailure(test,err);cases.append({'test':test.id(),'status':'FAIL'})
    def addError(self,test,err):
        super().addError(test,err);cases.append({'test':test.id(),'status':'ERROR'})
    def addSkip(self,test,reason):
        super().addSkip(test,reason);cases.append({'test':test.id(),'status':'SKIP'})
started=time.monotonic()
suite=unittest.defaultTestLoader.discover(str(root/'tests'),top_level_dir=str(root))
result=unittest.TextTestRunner(verbosity=0,resultclass=Result).run(suite)
summary={'assessed_at':datetime.now(timezone.utc).isoformat(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':round(time.monotonic()-started,3),'syntax_files':len(syntax),'cases':cases,'critical_methods':sum('test_reliability.' in c['test'] and c['status']=='PASS' for c in cases),'acceptance_methods':sum('test_financial_partner.' in c['test'] and c['status']=='PASS' for c in cases),'integration_methods':sum('test_partner_integration.' in c['test'] and c['status']=='PASS' for c in cases)}
(root/'evidence/task03-regression-assessment.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='cases'}),flush=True)
sys.exit(0 if result.wasSuccessful() else 1)
