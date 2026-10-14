import tempfile
import unittest
from pathlib import Path
from copilot.llm_config import load_llm_env

class TestLLMConfig(unittest.TestCase):
    def check(self,text,env=None):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'.env';path.write_text(text,encoding='utf-8')
            env={} if env is None else env
            loaded=load_llm_env(path,env)
            return env,loaded
    def test_whitelist_and_quotes(self):
        env,loaded=self.check('COPILOT_LLM_API_KEY="dummy-local-key"\nCOPILOT_LLM_MODEL=gemini-2.5-flash # comment\nCOPILOT_AUTH_MODE=demo\n')
        self.assertEqual(env,{'COPILOT_LLM_API_KEY':'dummy-local-key','COPILOT_LLM_MODEL':'gemini-2.5-flash'})
        self.assertEqual(len(loaded),2)
    def test_process_precedence_including_empty(self):
        env,_=self.check('COPILOT_LLM_API_KEY=local',{'COPILOT_LLM_API_KEY':''})
        self.assertEqual(env['COPILOT_LLM_API_KEY'],'')
    def test_no_interpolation_or_execution(self):
        env,_=self.check('export COPILOT_LLM_MODEL=$(whoami)\nCOPILOT_LLM_API_KEY=${SECRET}')
        self.assertEqual(env['COPILOT_LLM_MODEL'],'$(whoami)')
        self.assertEqual(env['COPILOT_LLM_API_KEY'],'${SECRET}')
    def test_disabled(self):
        env,loaded=self.check('COPILOT_LLM_MODEL=test',{'COPILOT_LOAD_LLM_ENV':'no'})
        self.assertEqual(loaded,());self.assertNotIn('COPILOT_LLM_MODEL',env)
    def test_missing_file(self):
        self.assertEqual(load_llm_env(Path('nonexistent-llm-assessment.env'),{}),())
    def test_error_does_not_include_secret(self):
        with self.assertRaisesRegex(ValueError,'^Malformed quoted local LLM setting$'):
            self.check('COPILOT_LLM_API_KEY="never-display-this')
    def test_hash_inside_key_preserved(self):
        env,_=self.check("COPILOT_LLM_API_KEY='dummy#value'")
        self.assertEqual(env['COPILOT_LLM_API_KEY'],'dummy#value')
