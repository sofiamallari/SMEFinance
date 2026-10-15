"""Run backend tests with disposable startup databases, journals and logs."""
import argparse,json,os,sys,tempfile,time,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
parser=argparse.ArgumentParser();parser.add_argument('--pattern',default='test*.py');args=parser.parse_args()
with tempfile.TemporaryDirectory() as tmp:
 for key,name in [('COPILOT_IDENTITY_DB','startup.sqlite3'),('COPILOT_TRANSACTION_FILE','startup.jsonl'),('COPILOT_AUDIT_LOG','audit.jsonl'),('COPILOT_EXEC_LOG','execution.jsonl')]:os.environ[key]=str(Path(tmp)/name)
 os.environ['COPILOT_AUTH_MODE']='authenticated'
 started=time.monotonic();suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern=args.pattern,top_level_dir=str(root))
 result=unittest.TextTestRunner(verbosity=1).run(suite)
 report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':round(time.monotonic()-started,3),'pattern':args.pattern,'isolated':True}
 out=root/'evidence'/'transaction-settings';out.mkdir(parents=True,exist_ok=True);(out/('backend-'+args.pattern.replace('*','all')+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
 sys.exit(0 if result.wasSuccessful() else 1)
