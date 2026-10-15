"""Relevant backend regressions with isolated initialization, not shared local data."""
import os,sys,tempfile,unittest,json,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));os.chdir(root)
parser=argparse.ArgumentParser();parser.add_argument('--evidence',default='evidence/security-header-backend.json');args=parser.parse_args()
with tempfile.TemporaryDirectory() as directory:
 for key,name in [('COPILOT_IDENTITY_DB','initial.sqlite3'),('COPILOT_TRANSACTION_FILE','initial.jsonl'),('COPILOT_AUDIT_LOG','audit.jsonl'),('COPILOT_EXEC_LOG','execution.jsonl')]:os.environ[key]=str(Path(directory)/name)
 os.environ['COPILOT_AGENT_MODE']='rule_engine'
 suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_authentication','tests.test_security_configuration','tests.test_four_role_workflow'])
 result=unittest.TextTestRunner(verbosity=1).run(suite)
 evidence=root/args.evidence
 if evidence.exists():raise SystemExit('Preserve existing evidence before rerunning.')
 evidence.write_text(json.dumps({'scope':'authentication, security configuration, four-role workflow','data':'isolated synthetic','tests_run':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'failures':[t.id() for t,_ in result.failures],'errors':[t.id() for t,_ in result.errors],'skipped':[t.id() for t,_ in result.skipped]},indent=2),encoding='utf-8')
 sys.exit(0 if result.wasSuccessful() else 1)
