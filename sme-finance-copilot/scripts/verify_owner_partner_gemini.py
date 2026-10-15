"""Explicit live check. Local key is never printed or saved; synthetic data only."""
import json,os,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
def main():
 with tempfile.TemporaryDirectory() as directory:
  for key,name in [('COPILOT_IDENTITY_DB','startup.sqlite3'),('COPILOT_TRANSACTION_FILE','startup.jsonl'),('COPILOT_AUDIT_LOG','audit.jsonl'),('COPILOT_EXEC_LOG','execution.jsonl')]:os.environ[key]=str(Path(directory)/name)
  from copilot import ai_agent
  report={'synthetic_only':True,'key_present':bool(os.environ.get('COPILOT_LLM_API_KEY')),'model':os.environ.get('COPILOT_LLM_MODEL'),'results':[]}
  def record(name,status,**evidence):report['results'].append(dict(name=name,status=status,**evidence));print(name+': '+status,flush=True)
  if ai_agent.configured():
   try:
    result=ai_agent._post({'model':os.environ['COPILOT_LLM_MODEL'],'temperature':0,'messages':[{'role':'user','content':'Reply with exactly: GEMINI_CONNECTION_OK'}]},timeout=20)
    record('Live authentication and basic generation','PASS' if result['choices'][0]['message']['content'].strip()=='GEMINI_CONNECTION_OK' else 'FAIL')
   except Exception as error:
    record('Live authentication and basic generation','BLOCKED',error_type=type(error).__name__,http_status=getattr(error,'code',None))
   else:
    from tests.auth_support import setup_identity
    class Fixture:
     def __init__(self):self.cleanups=[]
     def addCleanup(self,fn):self.cleanups.append(fn)
    fixture=Fixture()
    try:
     setup_identity(fixture)
     result=fixture.c.handle(fixture.auth.principal(fixture.tokens['owner']),'M002','Show recorded sales this month')
     record('Gemini tool planning and typed financial verification','PASS' if result.get('connection_status')=='connected' and result.get('evidence') else 'FAIL',mode=result.get('mode'),connection_status=result.get('connection_status'),tools=result.get('data',{}).get('tools_used'),evidence_count=len(result.get('evidence',[])),fallback_reason=result.get('fallback_reason'))
    finally:
     for cleanup in reversed(fixture.cleanups):cleanup()
  else:record('Live authentication and basic generation','BLOCKED',reason='LLM configuration is unavailable or disabled')
  target=root/'evidence/owner-partner/gemini-assessment.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()
