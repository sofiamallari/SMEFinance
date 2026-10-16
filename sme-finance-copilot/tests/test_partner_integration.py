import copy,tempfile,unittest,time,json,threading
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta
from dataclasses import replace
from copilot.agent import Copilot
from copilot.modules import rbf
from copilot.modules.transactions import TransactionStore
from copilot.auth import AuthStore
from copilot.security import Principal,AccessDenied
from copilot.reliability import EvidenceError,fact
from copilot.data.synthetic import AS_OF,load_all
from copilot.modules.payments import PaymentError

class TestPartnerIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name);self.c=Copilot();self.auth=AuthStore(self.path/'identity.sqlite3',self.c.merchants)
        self.c.identity_store=self.auth;self.store=TransactionStore(self.c,str(self.path/'transactions.jsonl'))
    def test_payment_state_wallet_and_refund_survive_restart(self):
        p=self.c.payments.create(self.c.merchants['M002'],'qr_pay',amount=45000)
        self.c.payments.simulate_customer_payment(p.ref);self.c.payments.refund(p.ref,10000,'partial-r1')
        expected_wallet=self.c.payments.wallets['M002'];expected_net=self.c.financial_data.aggregate('M002')['net_sales']
        restarted=Copilot();restarted.identity_store=self.auth;TransactionStore(restarted,str(self.path/'transactions.jsonl'))
        self.assertEqual(restarted.payments.status(p.ref).status,'PAID');self.assertEqual(restarted.payments.wallets['M002'],expected_wallet)
        self.assertEqual(restarted.financial_data.aggregate('M002')['net_sales'],expected_net)
        restarted.payments.refund(p.ref,10000,'partial-r1');self.assertEqual(restarted.financial_data.aggregate('M002')['net_sales'],expected_net)
    def test_pending_payment_survives_restart_without_revenue(self):
        p=self.c.payments.create(self.c.merchants['M002'],'pay_link',amount=45000)
        restarted=Copilot();restarted.identity_store=self.auth;TransactionStore(restarted,str(self.path/'transactions.jsonl'))
        self.assertEqual(restarted.payments.status(p.ref).status,'PENDING');self.assertNotIn('PAY-'+p.ref,restarted.financial_data.journal.read()[0])
    def test_concurrent_payment_completion_has_one_effect(self):
        p=self.c.payments.create(self.c.merchants['M002'],'qr_pay',amount=45000)
        outcomes=[]
        def complete():
            try:self.c.payments.simulate_customer_payment(p.ref);outcomes.append('paid')
            except PaymentError:outcomes.append('already completed')
        threads=[threading.Thread(target=complete) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(outcomes.count('paid'),1);self.assertEqual(len(self.c.financial_data.journal.read()[0]),0)
        self.assertEqual(self.c.payments.wallets['M002'],p.net_settled)
    def test_nonfinite_payment_inputs_rejected(self):
        for value in (float('nan'),float('inf'),-1,0):
            with self.assertRaises(PaymentError):self.c.payments.create(self.c.merchants['M002'],'qr_pay',amount=value)
        with self.assertRaises(PaymentError):self.c.payments.cart_totals([{'qty':1,'price':float('nan')}],'IDR')
    def test_stale_evidence_rejected(self):
        f=fact('canonical_transactions','M002','net_sales','100.00','IDR','2026-10-01','2026-10-14')
        with self.assertRaises(EvidenceError):replace(f,as_of='2020-01-01T00:00:00+00:00').validate('M002','IDR')
    def test_scope_question_denied_without_model(self):
        p=Principal('o','owner',{'M002'})
        with patch('copilot.ai_agent._post',side_effect=AssertionError('No model access')):
            result=self.c.handle(p,'M002','Show M005 sales')
        self.assertEqual(result['classification'],'UNAUTHORIZED')
    def test_payment_question_does_not_propose_action(self):
        p=Principal('o','owner',{'M002'})
        result=self.c.handle(p,'M002','What is my QR payment status?')
        self.assertFalse(self.c.partner_state.actions);self.assertFalse(self.c.payments.payments);self.assertNotIn('approval_token',result['data'])
    def test_application_status_question_does_not_submit(self):
        p=Principal('o','owner',{'M002'},{'share_with_lender'})
        self.c.handle(p,'M002','What is the status of my financing application?')
        self.assertFalse(self.c.partner_state.actions);self.assertFalse(self.c.applications)
    def test_refund_day_never_creates_negative_rbf_payment(self):
        m=copy.deepcopy(load_all()['M002'])
        m.transactions=[{'date':(AS_OF-timedelta(days=89-i)).isoformat(),'amount':-10000 if i==0 else 100000,'channel':'qr_pay','count':1} for i in range(90)]
        quote=rbf.quote(m,AS_OF,10000);self.assertEqual(quote['first_14_days'][0]['repayment'],0);self.assertTrue(all(r['repayment']>=0 for r in quote['first_14_days']))
    def test_original_rbf_fixture_still_exact(self):
        p=Principal('o','owner',{'M002'},{'share_with_lender'})
        q=self.c.call(p,'rbf_quote','M002',advance=10000000)
        self.assertEqual((q['advance'],q['fee'],q['total_repayable'],q['fee_rate']),(10000000,1300000,11300000,.13))
    def test_invalid_net_capture_mix_cannot_claim_eligibility(self):
        m=copy.deepcopy(load_all()['M002']);m.transactions=[{'date':AS_OF.isoformat(),'amount':100,'channel':'qr_pay','count':1},{'date':AS_OF.isoformat(),'amount':-50,'channel':'cash','count':1}]
        with self.assertRaises(ValueError):rbf.verified_monthly_sales(m,AS_OF)
    def test_no_records_have_no_financing_eligibility(self):
        m=copy.deepcopy(load_all()['M002']);m.transactions=[]
        self.assertFalse(rbf.eligibility(m,AS_OF)['eligible']);self.assertEqual(rbf.limits(m,AS_OF)['max_advance'],0)

    def test_payment_status_evidence_has_recorded_timestamp(self):
        p=self.c.payments.create(self.c.merchants['M002'],'qr_pay',amount=45000);self.c.payments.simulate_customer_payment(p.ref)
        principal=Principal('owner','owner',{'M002'})
        result=self.c.handle(principal,'M002','What happened to my latest simulated payment?')
        self.assertIn('PAID',result['reply']);self.assertTrue(result['evidence'])
        self.assertTrue(all(item['provenance']=='simulated_payment' for item in result['evidence']))

    def test_payment_crash_gap_recovers_from_durable_marker(self):
        p=self.c.payments.create(self.c.merchants['M002'],'qr_pay',amount=45000)
        with patch.object(self.c.financial_data,'persist_payment',side_effect=OSError('interrupted SQLite finalization')):
            with self.assertRaises(OSError):self.c.payments.simulate_customer_payment(p.ref)
        restarted=Copilot();restarted.identity_store=self.auth;TransactionStore(restarted,str(self.path/'transactions.jsonl'))
        restored=restarted.payments.status(p.ref)
        self.assertEqual(restored.status,'PENDING');self.assertEqual(restarted.payments.wallets.get('M002',0),0)
        self.assertEqual(len(restarted.financial_data.journal.read()[0]),0)
        restarted.payments.simulate_customer_payment(p.ref);self.assertEqual(restarted.payments.status(p.ref).status,'PAID')
    def test_refund_crash_gap_recovers_exact_wallet_delta(self):
        p=self.c.payments.create(self.c.merchants['M002'],'qr_pay',amount=45000);self.c.payments.simulate_customer_payment(p.ref)
        before=self.c.payments.wallets['M002']
        with patch.object(self.c.financial_data,'persist_payment',side_effect=OSError('interrupted refund finalization')):
            with self.assertRaises(OSError):self.c.payments.refund(p.ref,10000,'interrupted-r1')
        expected=self.c.payments.wallets['M002']
        restarted=Copilot();restarted.identity_store=self.auth;TransactionStore(restarted,str(self.path/'transactions.jsonl'))
        self.assertEqual(restarted.payments.wallets['M002'],before)
        self.assertEqual(restarted.payments.status(p.ref).refunded_amount,0)
        restarted.payments.refund(p.ref,10000,'interrupted-r1');self.assertLess(restarted.payments.wallets['M002'],before)
        self.assertFalse(restarted.financial_data.journal.read()[0])


class TestReportEvidence(unittest.TestCase):
    def test_report_includes_backend_projection_and_risks(self):
        from copilot.security import Principal
        c=Copilot();p=Principal('report-owner','owner',{'M002'},{'share_with_lender'})
        answer=c.handle(p,'M002','Show my financial report')
        evidence={f['metric']:f for f in answer['evidence']}
        self.assertEqual(evidence['revenue_projection_30_days']['value'],format(answer['data']['revenue_projection_30_days'],'.2f'))
        self.assertEqual(evidence['revenue_projection_30_days']['status'],'ESTIMATED')
        for severity in ('critical','warning','info'):
            self.assertEqual(int(evidence['risk_'+severity+'_count']['value']),sum(a['severity']==severity for a in answer['data']['risk_alerts']))
