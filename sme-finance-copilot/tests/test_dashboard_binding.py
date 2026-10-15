"""Focused source-of-truth checks for the POC dashboard composition."""
import unittest
from pathlib import Path
from copilot import config
from copilot.modules import assessment,cashflow
from tests.auth_support import setup_identity
from copilot.security import AccessDenied

class DashboardBindingTests(unittest.TestCase):
 def setUp(self):setup_identity(self,all_merchants=True);self.p=self.auth.principal(self.tokens['owner'])
 def test_assessment_matches_existing_canonical_formula(self):
  mid='M002';actual=self.c.call(self.p,'assess_business',mid)
  expected=assessment.assess(self.c.financial_data.project(mid),self.c.financial_data.as_of(mid))
  self.assertEqual(actual,expected);self.assertEqual(set(actual['scores']),set(config.DIMENSIONS))
 def test_financing_and_growth_share_same_stage(self):
  for mid in ('M002','M003'):
   a=self.c.call(self.p,'assess_business',mid);matches=self.c.call(self.p,'match_financing',mid)
   self.assertEqual(a['stage'],matches['stage'])
 def test_original_alerts_unchanged(self):
  actual=self.c.call(self.p,'cashflow_alerts','M002')
  self.assertEqual(actual,cashflow.alerts(self.c.financial_data.project('M002'),self.c.financial_data.as_of('M002')))
 def test_dashboard_metrics_use_canonical_values(self):
  d=self.c.call(self.p,'get_dashboard','M002');f=self.c.financial_data.aggregate('M002')
  for metric in ('net_sales','expenses','net_income'):self.assertEqual(d['financial_metrics'][metric],f[metric])
 def test_maturity_stage_labels_match_config(self):
  source=(Path(__file__).parents[1]/'web/dashboard-tabs.js').read_text(encoding='utf-8')
  for name in config.STAGES.values():self.assertIn(name,source)
 def test_staff_maturity_and_forecasts_stay_independent(self):
  p=self.auth.principal(self.tokens['staff'])
  with self.assertRaises(AccessDenied):self.c.call(p,'assess_business','M002')
  self.c.call(p,'cashflow_alerts','M002')
 def test_admin_has_no_dashboard_or_assessment(self):
  p=self.auth.principal(self.tokens['security_admin'])
  for name in ('get_dashboard','assess_business','cashflow_alerts'):
   with self.assertRaises(AccessDenied):self.c.call(p,name,'M002')
