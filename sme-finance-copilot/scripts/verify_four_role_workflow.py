"""Repeatable synthetic verification; initializes no shared/demo database."""
import argparse,json,os,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));os.chdir(root)
parser=argparse.ArgumentParser();parser.add_argument('--full',action='store_true');parser.add_argument('--evidence');args=parser.parse_args()
with tempfile.TemporaryDirectory() as directory:
 for key,name in [('COPILOT_IDENTITY_DB','initial.sqlite3'),('COPILOT_TRANSACTION_FILE','initial.jsonl'),('COPILOT_AUDIT_LOG','audit.jsonl'),('COPILOT_EXEC_LOG','execution.jsonl')]:os.environ[key]=str(Path(directory)/name)
 os.environ['COPILOT_AGENT_MODE']='rule_engine'
 suite=unittest.defaultTestLoader.discover(str(root/'tests'),top_level_dir=str(root)) if args.full else unittest.defaultTestLoader.loadTestsFromName('tests.test_four_role_workflow')
 result=unittest.TextTestRunner(verbosity=1).run(suite)
 if args.evidence:
  path=Path(args.evidence)
  if path.exists():raise SystemExit('Choose a new evidence filename; existing evidence is preserved.')
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'full regression' if args.full else 'four-role workflow','data':'isolated synthetic fixtures','tests_run':result.testsRun,'failures':[test.id() for test,_ in result.failures],'errors':[test.id() for test,_ in result.errors],'skipped':[test.id() for test,_ in result.skipped],'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'live_gemini':'NOT TESTED'},indent=2),encoding='utf-8')
 sys.exit(0 if result.wasSuccessful() else 1)
