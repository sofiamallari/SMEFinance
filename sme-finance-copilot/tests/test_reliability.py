import unittest
from dataclasses import replace
from copilot.reliability import *

class TestCriticalReliability(unittest.TestCase):
    def setUp(self):
        self.f=fact('rbf_quote','M002','total_repayable','11300000.00','IDR','2026-09-01','2026-09-30',limitations=('Indicative simulation only',))
    def test_correct_fact_preserved(self):
        self.assertEqual(validate_claims({'claims':[claim(self.f)],'insights':['indicative_only']},[self.f],'M002','IDR')[0],[self.f])
    def test_all_unsupported_claim_dimensions(self):
        for key,value in [('metric','approved_limit'),('value','987654'),('value','999'),('value','12300000.00'),('currency','PHP'),('merchant_id','M005'),('period_end','2027-01-01'),('status','ESTIMATED'),('provenance','historical_pos'),('source','bank_approval'),('evidence_id','invented_transaction_reference')]:
            with self.subTest(key=key,value=value),self.assertRaises(EvidenceError):
                validate_claims({'claims':[{**claim(self.f),key:value}],'insights':[]},[self.f],'M002','IDR')
    def test_correct_mixed_with_fabricated_claim_fails(self):
        with self.assertRaises(EvidenceError):validate_claims({'claims':[claim(self.f),{**claim(self.f),'value':'999'}],'insights':[]},[self.f],'M002','IDR')
    def test_free_text_no_tool_claim_rejected(self):
        for value in ('Your approved credit is 987654 IDR.',{'claims':[],'insights':[]},{'claims':[claim(self.f)],'insights':[],'explanation':'bank approved on 2026-10-14'}):
            with self.assertRaises(EvidenceError):validate_claims(value,[self.f],'M002','IDR')
    def test_unsupported_cause_rejected(self):
        with self.assertRaises(EvidenceError):validate_claims({'claims':[claim(self.f)],'insights':['sales declined because competitors opened']},[self.f],'M002','IDR')
    def test_forecast_cannot_be_actual(self):
        forecast=replace(self.f,status='ESTIMATED',provenance='forecast')
        with self.assertRaises(EvidenceError):validate_claims({'claims':[claim(self.f)],'insights':[]},[forecast],'M002','IDR')
    def test_domain_acceptance_and_refusal(self):
        for text in ('Give me a chocolate cake recipe','Write a Python game','Tell a joke'):
            self.assertEqual(domain(text),'outside')
        for text in ('How does inflation affect my inventory costs?','Explain revenue-based financing.','How do I upload a POS file?','What were my sales last month?'):
            self.assertNotEqual(domain(text),'outside')
    def test_invalid_evidence(self):
        for bad in (replace(self.f,period_end='invalid'),replace(self.f,quality_status='unreconciled'),replace(self.f,currency='USD'),replace(self.f,merchant_id='M005')):
            with self.assertRaises(EvidenceError):bad.validate('M002','IDR')
