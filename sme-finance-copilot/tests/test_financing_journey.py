"""Focused evidence-based journey checks; no invented completion thresholds."""
import json,os,unittest
from unittest.mock import patch
from tests.auth_support import setup_identity,ALL
from copilot.financing_journey import build
from copilot.reliability import domain
from copilot.security import AccessDenied

class JourneyTests(unittest.TestCase):
    def setUp(self):
        setup_identity(self,all_merchants=True)
        self.owner=self.auth.principal(self.tokens['owner'])
    def test_five_stages_with_evidence_not_inferred_completion(self):
        r=build(self.c,self.owner,'M002')
        self.assertEqual([s['id'] for s in r['stages']],['identify','profile','place','activate','measure'])
        self.assertTrue(all(s['status']=='Not Yet Assessed' and s['missing_requirements'] for s in r['stages']))
        self.assertTrue(all(r['stages'][i]['evidence'] for i in (0,1,2,3)))
        self.assertIsNone(r['current_stage'])
    def test_merchant_isolation_and_different_evidence(self):
        a=build(self.c,self.owner,'M001');b=build(self.c,self.owner,'M002')
        self.assertNotEqual(a['stages'][1]['evidence'],b['stages'][1]['evidence'])
        restricted=__import__('dataclasses').replace(self.owner,merchant_ids={'M002'})
        with self.assertRaises(AccessDenied):build(self.c,restricted,'M001')
    def test_no_permission_leak(self):
        for role in ('staff','security_admin','user_admin'):
            with self.assertRaises(AccessDenied):build(self.c,self.auth.principal(self.tokens[role]),'M002')
        with self.auth.db() as db:db.execute("DELETE FROM role_permissions WHERE role='owner' AND permission IN ('view_assessment','view_dashboard')")
        r=build(self.c,self.auth.principal(self.tokens['owner']),'M002')
        self.assertFalse(r['stages'][0]['evidence']);self.assertFalse(r['stages'][1]['evidence'])
        self.assertIsNone(r['incentive']['data'])
    def test_incentive_agrees_with_existing_tool(self):
        r=build(self.c,self.owner,'M002')
        self.assertEqual(r['incentive']['data'],self.c.call(self.owner,'incentive_status','M002'))
        self.assertEqual(r['incentive']['status'],'Provisional demo rules')
    def test_application_evidence_not_completion(self):
        packet={'application_id':'APP-'+'a'*20,'requested_amount':100,'status':'SUBMITTED_FOR_LENDER_REVIEW'}
        with self.auth.db() as db:
            db.execute('INSERT INTO applications VALUES (?,?,?,?,?,?)',(packet['application_id'],'M002',self.owner.user_id,self.ids['lender_analyst'],self.auth.clock(),json.dumps(packet)))
        r=build(self.c,self.owner,'M002')
        self.assertEqual(r['application_count'],1)
        self.assertEqual(r['stages'][3]['status'],'Not Yet Assessed')
        self.assertIn('count: 1',r['stages'][3]['evidence'][0]['summary'])
        self.assertEqual(build(self.c,self.owner,'M001')['application_count'],0)
    def test_requested_prompts_share_provider_and_exact_mocked_claims(self):
        prompts=['What stage am I currently on?','Why am I at this stage?','What have I completed?','What requirements are missing?','What should I do next?','What incentive milestone have I reached?','How can I progress toward financing?']
        def model(payload,timeout=45):
            if payload.get('tools'):
                return {'choices':[{'message':{'tool_calls':[{'id':'journey','type':'function','function':{'name':'financing_journey','arguments':'{}'}}]}}]}
            claims=json.loads(payload['messages'][-1]['content'])['allowed_claims']
            return {'choices':[{'message':{'content':json.dumps({'claims':claims,'insights':[]})}}]}
        with patch.dict(os.environ,{'COPILOT_LLM_BASE_URL':'https://example.invalid','COPILOT_LLM_API_KEY':'dummy','COPILOT_LLM_MODEL':'fake','COPILOT_AGENT_MODE':'auto'}),patch('copilot.ai_agent._post',side_effect=model):
            for prompt in prompts:
                self.assertEqual(domain(prompt),'journey')
                r=self.c.handle(self.owner,'M002',prompt)
                self.assertEqual(r['data']['stages'],build(self.c,self.owner,'M002')['stages'])
                self.assertIn('missing requirements:',r['reply'])
                self.assertIn('Provisional',r['data']['incentive']['status'])
                self.assertEqual(r['connection_status'],'connected')
    def test_model_invented_completed_claim_falls_back(self):
        def model(payload,timeout=45):
            if payload.get('tools'):
                return {'choices':[{'message':{'tool_calls':[{'id':'journey','type':'function','function':{'name':'financing_journey','arguments':'{}'}}]}}]}
            claims=json.loads(payload['messages'][-1]['content'])['allowed_claims']
            claims[0]['value']='Completed'
            return {'choices':[{'message':{'content':json.dumps({'claims':claims,'insights':[]})}}]}
        with patch.dict(os.environ,{'COPILOT_LLM_BASE_URL':'https://example.invalid','COPILOT_LLM_API_KEY':'dummy','COPILOT_LLM_MODEL':'fake','COPILOT_AGENT_MODE':'auto'}),patch('copilot.ai_agent._post',side_effect=model):
            r=self.c.handle(self.owner,'M002','What have I completed?')
        self.assertEqual(r['connection_status'],'fallback')
        self.assertEqual(r['data']['stages'][0]['status'],'Not Yet Assessed')
        self.assertNotIn('Identify: Completed',r['reply'])
    def test_agent_without_consent_is_denied(self):
        with self.assertRaises(AccessDenied):
            build(self.c,self.auth.principal(self.tokens['lender_analyst']),'M002')
    def test_refresh_stable_and_read_only(self):
        before=self.c.financial_data.version('M002');r=build(self.c,self.owner,'M002')
        self.assertEqual(r,build(self.c,self.owner,'M002'))
        self.assertEqual(before,self.c.financial_data.version('M002'))
        self.assertFalse(self.c.history)
    def test_empty_records_safe(self):
        self.c.financial_data.base['M002'].transactions=[]
        r=build(self.c,self.owner,'M002')
        self.assertFalse(r['stages'][0]['evidence'])
        self.assertTrue(r['stages'][0]['missing_requirements'])

if __name__=='__main__':unittest.main()
