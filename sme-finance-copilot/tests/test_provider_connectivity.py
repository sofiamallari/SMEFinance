"""Provider integration checks; doubles do not establish live connectivity."""
import io,json,os,time,unittest
from unittest.mock import patch
from urllib.error import HTTPError
from copilot import governed_partner as gp
from tests import test_ai_governance as governance

class ProviderAdapterTests(unittest.TestCase):
 def setUp(self):
  self.env=patch.dict(os.environ,{'COPILOT_LLM_BASE_URL':'https://example.invalid/v1beta/openai/','COPILOT_LLM_API_KEY':'dummy-test-key','COPILOT_LLM_MODEL':'fixture-model'});self.env.start();self.addCleanup(self.env.stop)
 def test_minimal_request_uses_existing_authenticated_transport(self):
  with patch.object(gp,'post_json',return_value={'choices':[{'message':{'content':'GEMINI_CONNECTION_OK'}}]}) as post:
   result=gp.model_request([{'role':'user','content':'Reply with exactly: GEMINI_CONNECTION_OK'}],[])
  self.assertEqual(result['content'],'GEMINI_CONNECTION_OK');self.assertEqual(post.call_args.args[0],'https://example.invalid/v1beta/openai/chat/completions');self.assertEqual(post.call_args.args[2]['Authorization'],'Bearer dummy-test-key');self.assertEqual(post.call_args.kwargs['timeout'],30);self.assertNotIn('tools',post.call_args.args[1]);self.assertEqual(post.call_count,1)
 def test_503_sanitized_and_not_automatically_retried(self):
  error=HTTPError('https://example.invalid',503,'SECRET_PROVIDER_DETAIL',{},io.BytesIO(b'SECRET_BODY'))
  with patch.object(gp,'post_json',side_effect=error) as post:
   with self.assertRaises(gp.ProviderUnavailable) as raised:gp.model_request([],[])
  self.assertEqual(raised.exception.status,503);self.assertNotIn('SECRET',str(raised.exception));self.assertEqual(post.call_count,1)
 def test_auth_and_rate_limit_errors_not_mislabeled_busy(self):
  for status in (400,401,403,404,429):
   error=HTTPError('https://example.invalid',status,'fixture',{},None)
   with self.subTest(status=status),patch.object(gp,'post_json',side_effect=error),self.assertRaises(HTTPError) as raised:gp.model_request([],[])
   self.assertEqual(raised.exception.code,status)
 def test_timeout_not_mislabeled_provider_busy(self):
  with patch.object(gp,'post_json',side_effect=TimeoutError('fixture')),self.assertRaises(TimeoutError):gp.model_request([],[])

class ProviderFailureRouting(governance.GovernanceTests):
 def test_503_is_provider_failure_not_claim_failure(self):
  self.scripted([gp.ProviderUnavailable()],[])
  r=self.ask('Show sales');self.assertEqual(r['fallback_reason'],'provider_error');self.assertEqual(r['provider_status'],'temporarily_busy');self.assertTrue(r['retry_available']);self.assertNotIn('api key',str(r).lower())
  with self.auth.db() as db:events=[json.loads(row[0]) for row in db.execute('SELECT record FROM audit_events')]
  self.assertTrue(any(e.get('action')=='ai_response_provider_error' for e in events))
 def test_timeout_and_verification_remain_distinct(self):
  self.scripted([TimeoutError('fixture')],[]);self.assertEqual(self.ask('Show sales')['fallback_reason'],'timeout')
  self.scripted([{'intent':'sales_analysis'}],[{'segments':[{'text':'Your cash balance is 999999 CNY.'}]}]);self.assertEqual(self.ask('Show sales')['fallback_reason'],'response_validation')
 def test_synthetic_prompt_size_tool_time_and_busy_call_count(self):
  metrics={};calls=[];start=time.monotonic();self.g.execute(self.token,'M002','get_financial_summary',{});metrics['financial_tool_seconds']=round(time.monotonic()-start,4)
  def request(messages,schema):
   calls.append(True);metrics['synthetic_prompt_bytes']=len(json.dumps(messages).encode());raise gp.ProviderUnavailable()
  self.partner.conversation_request=request;r=self.ask('Show sales');self.assertEqual(len(calls),1);self.assertEqual(r['fallback_reason'],'provider_error')
  print('SYNTHETIC_SIZING_ONLY '+json.dumps(metrics))


def load_tests(loader,tests,pattern):
 suite=loader.loadTestsFromTestCase(ProviderAdapterTests)
 suite.addTests(ProviderFailureRouting(name) for name in ProviderFailureRouting.__dict__ if name.startswith('test_'))
 return suite

if __name__=='__main__':unittest.main()
