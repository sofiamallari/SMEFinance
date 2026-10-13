"""Functional tests for the four core modules + assessment engine (synthetic data)."""
import unittest
from datetime import timedelta

from copilot import config
from copilot.data.synthetic import AS_OF, load_all
from copilot.modules import assessment, cashflow, dashboard, matching, rbf
from copilot.modules.payments import PaymentError, PaymentSimulator, _crc16

MS = load_all()
EXPECTED_STAGE = {"M001": 1, "M006": 2, "M002": 3, "M003": 4, "M004": 5, "M005": 6}


class TestSyntheticData(unittest.TestCase):
    def test_deterministic(self):
        again = load_all()
        for k in MS:
            self.assertEqual(MS[k].transactions[:50], again[k].transactions[:50])

    def test_no_brand_names_in_channels(self):
        labels = " ".join(c["label"] for c in config.CHANNELS.values()).lower()
        for brand in ("brimo", "qris", "gcash", "gopay", "ovo", "dana", "maya", "visa", "mastercard"):
            self.assertNotIn(brand, labels)


class TestDashboard(unittest.TestCase):
    def test_shares_sum_to_one(self):
        d = dashboard.build_dashboard(MS["M002"], AS_OF)
        self.assertAlmostEqual(sum(c["revenue_share"] for c in d["mix"]["by_channel"].values()), 1, places=2)
        self.assertAlmostEqual(sum(c["volume_share"] for c in d["mix"]["by_channel"].values()), 1, places=2)

    def test_granularities(self):
        for g in ("daily", "weekly", "monthly", "quarterly", "yearly"):
            self.assertTrue(dashboard.trend(MS["M003"].transactions, g))
        with self.assertRaises(ValueError):
            dashboard.trend(MS["M003"].transactions, "hourly")

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            dashboard.filter_period(MS["M001"].transactions, AS_OF, AS_OF - timedelta(days=1))

    def test_incentive_tiers(self):
        inc = dashboard.incentive_status(MS["M002"].transactions, AS_OF)
        self.assertGreaterEqual(inc["mom_growth"], 0.30)
        self.assertEqual(inc["tier"], 2)
        self.assertEqual(inc["next_milestone"]["tier"], 3)

    def test_incentive_anti_gaming_small_base(self):
        inc = dashboard.incentive_status(MS["M001"].transactions, AS_OF)
        self.assertIsNone(inc["mom_growth"])
        self.assertEqual(inc["tier"], 0)
        self.assertIn("anti-gaming", inc["note"])

    def test_timing_delay_vs_default(self):
        self.assertEqual(dashboard.receivable_behaviour(MS["M002"], AS_OF)["classification"], "timing_delay")
        self.assertEqual(dashboard.receivable_behaviour(MS["M001"], AS_OF)["classification"], "repayment_risk")


class TestRBF(unittest.TestCase):
    def test_fee_steps_down_with_size(self):
        m = MS["M002"]
        lim = rbf.limits(m, AS_OF)
        small = rbf.quote(m, AS_OF, lim["max_advance"] * 0.2)
        large = rbf.quote(m, AS_OF, lim["max_advance"])
        self.assertGreater(small["fee_rate"], large["fee_rate"])
        self.assertLess(small["remittance_rate"], large["remittance_rate"])

    def test_remittance_bounds(self):
        m = MS["M004"]
        q = rbf.quote(m, AS_OF, rbf.limits(m, AS_OF)["max_advance"])
        self.assertLessEqual(q["remittance_rate"], config.RBF["remit_rate_cap"])
        self.assertGreaterEqual(q["remittance_rate"], config.RBF["remit_rate_floor"])

    def test_zero_sales_zero_payment(self):
        q = rbf.quote(MS["M002"], AS_OF, 10_000_000)
        self.assertEqual(q["examples"]["no_sales_day"]["repayment"], 0)
        self.assertAlmostEqual(q["total_repayable"], q["advance"] + q["fee"], places=2)

    def test_exceeds_max(self):
        m = MS["M002"]
        with self.assertRaises(ValueError):
            rbf.quote(m, AS_OF, rbf.limits(m, AS_OF)["max_advance"] * 2)
        with self.assertRaises(ValueError):
            rbf.quote(m, AS_OF, -5)

    def test_recommended_within_target_term(self):
        for mid in ("M002", "M003", "M004"):
            m = MS[mid]
            q = rbf.quote(m, AS_OF, rbf.recommend_advance(m, AS_OF))
            self.assertLessEqual(q["estimated_payoff_days"], config.RBF["target_term_days"])

    def test_incentive_discount(self):
        m = MS["M002"]
        a = rbf.quote(m, AS_OF, 20_000_000, incentive_tier=0)
        b = rbf.quote(m, AS_OF, 20_000_000, incentive_tier=3)
        self.assertLess(b["fee_rate"], a["fee_rate"])

    def test_eligibility(self):
        self.assertFalse(rbf.eligibility(MS["M001"], AS_OF)["eligible"])
        self.assertTrue(rbf.eligibility(MS["M002"], AS_OF)["eligible"])


class TestPayments(unittest.TestCase):
    def setUp(self):
        self.t = [1_000_000.0]
        self.sim = PaymentSimulator(clock=lambda: self.t[0])
        self.m = MS["M002"]

    def test_qr_payload_sandbox_and_crc(self):
        p = self.sim.create(self.m, "qr_pay", 45_000, stage=3)
        self.assertIn("SANDBOX", p.qr_payload)
        self.assertEqual(p.qr_payload[-4:], _crc16(p.qr_payload[:-4]))

    def test_lifecycle_and_settlement(self):
        p = self.sim.create(self.m, "qr_pay", 100_000, stage=3)
        self.sim.simulate_customer_payment(p.ref)
        self.assertEqual(p.status, "PAID")
        self.assertAlmostEqual(p.net_settled, 100_000 * (1 - config.MDR_BY_STAGE[3]))
        with self.assertRaises(PaymentError):
            self.sim.simulate_customer_payment(p.ref)  # no double payment

    def test_qr_expiry(self):
        p = self.sim.create(self.m, "qr_pay", 10_000)
        self.t[0] += config.QR_EXPIRY_SECONDS + 1
        self.assertEqual(self.sim.status(p.ref).status, "EXPIRED")
        with self.assertRaises(PaymentError):
            self.sim.simulate_customer_payment(p.ref)

    def test_idempotency(self):
        a = self.sim.create(self.m, "pay_link", 5_000, idempotency_key="k1")
        b = self.sim.create(self.m, "pay_link", 5_000, idempotency_key="k1")
        self.assertEqual(a.ref, b.ref)

    def test_card_numbers_rejected(self):
        with self.assertRaises(PaymentError):
            self.sim.create(self.m, "tap_pay", 5_000, note="4111 1111 1111 1111")

    def test_external_channel_not_settled(self):
        p = self.sim.create(self.m, "pay_link", 50_000)
        self.sim.simulate_customer_payment(p.ref, "external_wallet")
        self.assertEqual(p.net_settled, 0)
        self.assertEqual(p.mdr_fee, 0)

    def test_channel_mismatch(self):
        p = self.sim.create(self.m, "qr_pay", 50_000)
        with self.assertRaises(PaymentError):
            self.sim.simulate_customer_payment(p.ref, "tap_pay")

    def test_large_amount_held_for_review(self):
        p = self.sim.create(self.m, "qr_pay", 10_000_000_000)
        self.assertIn("requires_review", p.flags)
        with self.assertRaises(PaymentError):
            self.sim.simulate_customer_payment(p.ref)

    def test_engagement_washing_flag(self):
        for _ in range(4):
            p = self.sim.create(self.m, "qr_pay", 77_000)
        self.assertTrue(any("engagement-washing" in f for f in p.flags))

    def test_cart_tax_by_country(self):
        tot = PaymentSimulator.cart_totals([{"price": 100, "qty": 2}], "PHP")
        self.assertEqual(tot["tax"], 24.0)
        with self.assertRaises(PaymentError):
            PaymentSimulator.cart_totals([], "PHP")

    def test_tiered_mdr_cheaper_than_flat(self):
        c = self.sim.mdr_comparison(1000, 1)
        self.assertLess(c["tiered_fee"], c["flat_fee"])

    def test_invalid_inputs(self):
        with self.assertRaises(PaymentError):
            self.sim.create(self.m, "crypto", 100)
        with self.assertRaises(PaymentError):
            self.sim.create(self.m, "qr_pay", 0)


class TestCashflow(unittest.TestCase):
    def test_forecast_shape(self):
        f = cashflow.forecast(MS["M003"], AS_OF)
        self.assertEqual(len(f["path"]), 30)
        self.assertEqual(f["path"][0]["date"], (AS_OF + timedelta(days=1)).isoformat())

    def test_critical_runway_for_survival_stall(self):
        codes = [a["code"] for a in cashflow.alerts(MS["M001"], AS_OF)]
        self.assertIn("RUNWAY_CRITICAL", codes)
        self.assertIn("FUNDS_MIXING", codes)
        self.assertIn("CASH_DEPENDENCE", codes)

    def test_alerts_sorted_by_severity(self):
        order = {"critical": 0, "warning": 1, "info": 2}
        sev = [order[a["severity"]] for a in cashflow.alerts(MS["M001"], AS_OF)]
        self.assertEqual(sev, sorted(sev))

    def test_every_alert_maps_to_intervention(self):
        for m in MS.values():
            for a in cashflow.alerts(m, AS_OF):
                self.assertTrue(a["framework_intervention"])


class TestAssessmentAndMatching(unittest.TestCase):
    def test_all_six_stages_covered(self):
        for mid, st in EXPECTED_STAGE.items():
            self.assertEqual(assessment.assess(MS[mid], AS_OF)["stage"], st, mid)

    def test_scores_in_range_and_explained(self):
        a = assessment.assess(MS["M002"], AS_OF)
        self.assertEqual(set(a["scores"]), set(config.DIMENSIONS))
        for k, v in a["scores"].items():
            self.assertTrue(0 <= v <= 100)
            self.assertTrue(a["factors"][k])

    def test_constraints(self):
        c = lambda mid: [x["constraint"] for x in assessment.assess(MS[mid], AS_OF)["constraints"]]
        self.assertIn("production_bottleneck", c("M002"))
        self.assertIn("confirmed_orders_no_capital", c("M003"))
        self.assertIn("succession_risk", c("M005"))
        self.assertIn("low_digital_adoption", c("M001"))

    def test_gate_caps_stage(self):
        a = assessment.assess(MS["M003"], AS_OF)
        self.assertTrue(a["gate_adjustments"])  # composite reaches 5, operational gate caps at 4

    def test_matching(self):
        ids = lambda mid: [r["id"] for r in matching.match(MS[mid], assessment.assess(MS[mid], AS_OF), AS_OF)["recommendations"]]
        self.assertIn("PO_FIN", ids("M003"))
        self.assertIn("RBF", ids("M002"))
        self.assertIn("LEASE", ids("M002"))
        self.assertIn("SUCCESSION", ids("M005"))
        self.assertNotIn("RBF", ids("M001"))
        r = matching.match(MS["M001"], assessment.assess(MS["M001"], AS_OF), AS_OF)
        self.assertTrue(any(x["id"] == "RBF" and x["why_not_yet"] for x in r["not_yet_eligible"]))

    def test_binding_constraint_product_ranks_first(self):
        top = lambda mid: matching.match(MS[mid], assessment.assess(MS[mid], AS_OF), AS_OF)["recommendations"][0]["id"]
        self.assertEqual(top("M003"), "PO_FIN")
        self.assertEqual(top("M004"), "EXPANSION")
        self.assertEqual(top("M005"), "SUCCESSION")
        self.assertIn(top("M002"), ("RBF", "LEASE"))

    def test_rbf_size_consistent_with_calculator(self):
        r = matching.match(MS["M002"], assessment.assess(MS["M002"], AS_OF), AS_OF)["recommendations"]
        x = next(i for i in r if i["id"] == "RBF")
        self.assertEqual(x["indicative_size"], rbf.limits(MS["M002"], AS_OF)["max_advance"])

    def test_scores_sorted(self):
        r = matching.match(MS["M004"], assessment.assess(MS["M004"], AS_OF), AS_OF)["recommendations"]
        self.assertEqual([x["match_score"] for x in r], sorted([x["match_score"] for x in r], reverse=True))


if __name__ == "__main__":
    unittest.main()
