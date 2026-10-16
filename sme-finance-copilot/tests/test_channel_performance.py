import unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]
from tests.auth_support import setup_identity
from copilot.bank_workflow import BankWorkflow
from copilot.security import AccessDenied
class ChartChecks(unittest.TestCase):
 def setUp(self):setup_identity(self,all_merchants=True)
 def test_percentages_period_and_isolation(self):
  f=self.c.financial_data
  for mid in ['M002','M003']:
   d=f.dashboard(mid);v=d['channel_performance'];self.assertEqual(v['merchant_id'],mid);self.assertEqual(v['net_sales'],d['financial_metrics']['net_sales']);self.assertAlmostEqual(sum(r['count_percent'] for r in v['channels']),100)
   self.assertAlmostEqual(sum(r['revenue_percent'] for r in v['channels']),100)
  self.assertNotEqual(f.channel_performance('M002')['net_sales'],f.channel_performance('M003')['net_sales'])
  self.assertFalse(f.channel_performance('M002','1900-01-01','1900-01-02')['available'])
 def test_nonpositive_and_negative_channel(self):
  f=self.c.financial_data;m=f.base['M002'];m.transactions=[{'date':'2026-10-15','channel':'cash','amount':-10,'count':1}]
  v=f.channel_performance('M002','2026-10-15','2026-10-15');self.assertFalse(v['revenue_available']);self.assertIsNone(v['channels'][0]['revenue_percent'])
 def test_authorization(self):
  with self.assertRaises(AccessDenied):BankWorkflow(self.auth,self.c).review(self.tokens['lender_analyst'],'M002')
  with self.auth.db() as db:db.execute("DELETE FROM merchant_transaction_grants WHERE user_id=?",(self.ids['staff'],))
  with self.assertRaises(AccessDenied):self.auth.authorize(self.tokens['staff'],'view_dashboard','M002')
 def test_frontend_contract(self):
  s=(p/'web/index.html').read_text(encoding='utf-8');self.assertNotIn('<h3>Business Highlights</h3>',s);self.assertLess(s.index('id="drevtrend"'),s.index('id="channel-performance"'))
  self.assertIn('ChannelPerformance.render', (p/'web/bank-views.js').read_text());self.assertIn('#08663d',(p/'web/channel-performance.js').read_text())
if __name__=='__main__':unittest.main()
