"""
SME Finance Copilot – agent core.

Two entry points:
  run_cycle()  – the autonomous progression loop from the framework:
                 IDENTIFY -> PROFILE -> PLACE -> ACTIVATE -> MEASURE & GRADUATE
  handle()     – conversational turn: sanitize -> route intent -> (AI agent | rule engine)
                 -> policy-check each tool call -> execute -> narrate.

Every tool call passes through PolicyGuard and is written to a hash-chained
audit log plus an execution log (used as submission evidence).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date

from copilot import ai_agent, config
from copilot.data.synthetic import AS_OF, load_all
from copilot.llm import get_narrator
from copilot.modules import assessment, cashflow, dashboard, matching, rbf, reporting
from copilot.modules.payments import PaymentError, PaymentSimulator, qr_matrix
from copilot.security import (AccessDenied, ApprovalRequired, AuditLog, PolicyGuard, Principal,
                              RateLimiter, Tier, sanitize_input)


def money(x, cur):
    from copilot.currency_policy import format_money
    return format_money(x,cur)


@dataclass
class Tool:
    name: str
    tier: Tier
    fn: callable
    description: str
    consent: str | None = None


class Copilot:
    def __init__(self, merchants: dict | None = None, as_of: date = AS_OF,
                 audit_path: str | None = None, exec_path: str | None = None, clock=time.time):
        self.merchants = merchants or load_all(as_of)
        self.as_of = as_of
        self.clock = clock
        self.guard = PolicyGuard(clock=clock)
        self.audit = AuditLog(audit_path, clock=clock)
        self.exec_log = AuditLog(exec_path, clock=clock)
        self.limiter = RateLimiter(clock=clock)
        self.payments = PaymentSimulator(clock=clock)
        self.narrator = get_narrator()
        self.history: dict[str, list] = {}       # merchant_id -> assessment snapshots (MEASURE)
        self.identity_store = None
        self.applications: list[dict] = []
        from copilot.financial_data import FinancialData
        self.financial_data = FinancialData(self)
        from copilot.partner_state import PartnerState
        self.partner_states = {}
        self.partner_state = PartnerState(self)
        self.payments.on_event = self.financial_data.record_payment
        self.payments.on_refund = self.financial_data.record_refund
        self.payments.existing_refund = self.financial_data.existing_refund
        self.tools = {t.name: t for t in self._register_tools()}

    def partner_context(self, principal, mid, session=None):
        return self.partner_state.context(principal,mid,session or principal.session_id)

    def save_partner_context(self,principal,mid,session,state):
        return self.partner_state.save(principal,mid,session or principal.session_id,state)

    def financial_result(self,name,mid,args,tool,principal=None):
        m=self.financial_data.project(mid);asof=self.financial_data.as_of(mid)
        if name=="financing_journey":
            from copilot.financing_journey import build
            return build(self,principal,mid)
        if name=="data_quality":
            if not self.identity_store:raise ValueError("Persistent quality monitoring is unavailable")
            with self.identity_store.db() as db:
                count=db.execute("SELECT COUNT(*) FROM quality_alerts WHERE merchant_id=? AND state!='resolved'",(mid,)).fetchone()[0]
                conflicts=db.execute("SELECT COUNT(*) FROM pos_import_runs WHERE merchant_id=? AND state='validation_failed'",(mid,)).fetchone()[0]
            return {"unresolved_quality_alerts":count,"failed_import_validations":conflicts}
        if name=="latest_payment":
            payments=[p for p in self.payments.payments.values() if p.merchant_id==mid]
            if not payments:raise ValueError("Current payment-service status unavailable; review canonical transaction history")
            payment=self.payments.status(max(payments,key=lambda p:p.created_at).ref)
            status="REFUNDED" if payment.refunded_amount==payment.amount else "PARTIALLY_REFUNDED" if payment.refunded_amount else payment.status
            return {"payment_reference":payment.ref,"payment_status":status,"payment_amount":payment.amount,"payment_refunded_amount":payment.refunded_amount,"currency":payment.currency,"recorded_at":payment.created_at}
        if name=="application_status":
            if principal.role=="staff":raise AccessDenied("Staff can inspect delegated drafts in Applications, not submitted packets")
            if not self.identity_store:raise ValueError("Persistent application status unavailable")
            with self.identity_store.db() as db:
                records=db.execute("SELECT * FROM applications WHERE merchant_id=? ORDER BY created_at DESC",(mid,)).fetchall()
                visible=[record for record in records if principal.role=='owner' or record['recipient_id']==principal.user_id]
                if not visible:raise ValueError("No authorized application record is available")
                packet=__import__('json').loads(visible[0]['packet'])
            return {"application_reference":packet['application_id'],"application_status":packet['status'],"requested_amount":packet['requested_amount'],"currency":packet['currency'],"recorded_at":visible[0]['created_at']}
        # New unseeded merchants have canonical records, not synthetic seed rows.
        # Reuse the already-authoritative projection; retain existing MDR formulas/default tier.
        if name in ('payment_create','mdr_compare') and not self.merchants[mid].transactions:
            stage=assessment.assess(m,asof)['stage'] if m.transactions else 1
            if name=='mdr_compare':return self.payments.mdr_comparison(args.get('amount',1000),stage)
            return self.payments.create(m,args['method'],args.get('amount'),args.get('items'),stage,args.get('idempotency_key')).public()
        if name=="get_dashboard":return self.financial_data.dashboard(mid,**args)
        if name=="cashflow_forecast":return cashflow.forecast(m,asof,**args)
        if name=="cashflow_alerts":return cashflow.alerts(m,asof)
        if name=="assess_business":return assessment.assess(m,asof)
        if name=="match_financing":return matching.match(m,assessment.assess(m,asof),asof)
        if name=="incentive_status":return dashboard.incentive_status(m.transactions,asof)
        if name=="financial_report":return reporting.report(m,asof)
        if name=="rbf_quote":return rbf.quote(m,asof,args.get("advance") or rbf.recommend_advance(m,asof),dashboard.incentive_status(m.transactions,asof)["tier"])
        return tool.fn(mid,**args)

    # ------------------------------------------------------------ tools
    def _register_tools(self):
        A = self.as_of
        m = lambda mid: self.merchants[mid]
        return [
            Tool("financing_journey", Tier.T1_ADVISE, lambda mid: {}, "Read-only merchant financing journey with unassessed completion rules"),
            Tool("data_quality", Tier.T0_READ, lambda mid: {}, "Merchant-scoped data quality"),
            Tool("latest_payment", Tier.T0_READ, lambda mid: {}, "Authorized simulated payment status"),
            Tool("application_status", Tier.T0_READ, lambda mid: {}, "Authorized simulated application status"),
            Tool("financial_report", Tier.T0_READ, lambda mid: reporting.report(m(mid), A),
                 "Financial report, risk alerts and 30-day revenue projection from saved transactions"),
            Tool("get_dashboard", Tier.T0_READ,
                 lambda mid, start=None, end=None, granularity="monthly": dashboard.build_dashboard(
                     m(mid), A, date.fromisoformat(start) if start else None,
                     date.fromisoformat(end) if end else None, granularity),
                 "Merchant intelligence dashboard: channel mix, trends, capture, incentive tier"),
            Tool("cashflow_forecast", Tier.T0_READ, lambda mid, days=30: cashflow.forecast(m(mid), A, days),
                 "30-day cash-flow forecast and runway"),
            Tool("cashflow_alerts", Tier.T0_READ, lambda mid: cashflow.alerts(m(mid), A),
                 "Rule-based cash-flow alerts mapped to interventions"),
            Tool("assess_business", Tier.T0_READ, lambda mid: assessment.assess(m(mid), A),
                 "Seven-dimension assessment, stage placement and constraints"),
            Tool("incentive_status", Tier.T0_READ, lambda mid: dashboard.incentive_status(m(mid).transactions, A),
                 "Milestone tier based on MoM growth in ecosystem digital sales"),
            Tool("match_financing", Tier.T1_ADVISE,
                 lambda mid: matching.match(m(mid), assessment.assess(m(mid), A), A),
                 "Rank financing and support options with reasons"),
            Tool("rbf_quote", Tier.T1_ADVISE,
                 lambda mid, advance=None: rbf.quote(
                     m(mid), A, advance or rbf.recommend_advance(m(mid), A),
                     dashboard.incentive_status(m(mid).transactions, A)["tier"]),
                 "Revenue-based financing simulation"),
            Tool("mdr_compare", Tier.T1_ADVISE,
                 lambda mid, amount=1000: self.payments.mdr_comparison(
                     amount, assessment.assess(m(mid), A)["stage"]),
                 "Tiered vs flat merchant discount rate"),
            Tool("payment_create", Tier.T2_SANDBOX_WRITE,
                 lambda mid, method, amount=None, items=None, idempotency_key=None: self.payments.create(
                     m(mid), method, amount, items, assessment.assess(m(mid), A)["stage"],
                     idempotency_key).public(),
                 "Create a sandbox QR Pay / Tap Pay / Pay Link request"),
            Tool("payment_simulate_pay", Tier.T2_SANDBOX_WRITE,
                 lambda mid, ref, channel=None: self._own_payment(mid, ref) and
                 self.payments.simulate_customer_payment(ref, channel).public(),
                 "Simulate the customer completing a sandbox payment"),
            Tool("payment_status", Tier.T0_READ,
                 lambda mid, ref: self._own_payment(mid, ref) and self.payments.status(ref).public(),
                 "Check a sandbox payment status"),
            Tool("prepare_financing_application", Tier.T3_APPROVAL_REQUIRED, self._prepare_application,
                 "Package a consented, owner-approved financing request for a lender to review",
                 consent="share_with_lender"),
            Tool("approve_credit", Tier.T4_PROHIBITED, lambda *a, **k: None, "Prohibited"),
            Tool("disburse_funds", Tier.T4_PROHIBITED, lambda *a, **k: None, "Prohibited"),
            Tool("change_credit_limit", Tier.T4_PROHIBITED, lambda *a, **k: None, "Prohibited"),
        ]

    def _own_payment(self, mid, ref):
        p = self.payments.payments.get(ref)
        if not p or p.merchant_id != mid:
            raise AccessDenied("Payment reference not found for this merchant.")
        return True

    def _prepare_application(self, mid, product_id="RBF", amount=None, recipient_id=None, draft_id=None):
        mer = self.financial_data.project(mid)
        asof = self.financial_data.as_of(mid)
        a = assessment.assess(mer, asof)
        q = rbf.quote(mer, asof, amount or rbf.recommend_advance(mer, asof),dashboard.incentive_status(mer.transactions,asof)["tier"]) if product_id == "RBF" else None
        app = {"application_id": f"APP-{mid}-{len(self.applications) + 1:04d}", "merchant_id": mid,
               "recipient_id":recipient_id,"draft_id":draft_id,"product_id": product_id, "requested_amount": q["advance"] if q else amount,
               "currency": mer.currency, "stage": a["stage"], "scores": a["scores"],
               "status": "SUBMITTED_FOR_LENDER_REVIEW",
               "note": "Packet contains aggregated indicators only; the lender makes the credit decision."}
        self.applications.append(app)
        return app

    def call(self, principal: Principal, name: str, merchant_id: str, approval_token=None, **kwargs):
        tool = self.tools.get(name)
        if not tool:
            raise AccessDenied(f"Unknown tool {name}")
        t0 = time.perf_counter()
        base = {"actor": principal.user_id, "role": principal.role, "tool": name,
                "tier": tool.tier.name, "merchant_id": merchant_id}
        try:
            self.guard.check(principal, name, tool.tier, merchant_id, approval_token, tool.consent)
        except ApprovalRequired:
            self.audit.write(**base, decision="approval_required")
            self.exec_log.write(**base, decision="approval_required", args=kwargs)
            raise
        except AccessDenied as e:
            self.audit.write(**base, decision="denied", reason=str(e))
            self.exec_log.write(**base, decision="denied", reason=str(e), args=kwargs)
            raise
        try:
            result = self.financial_result(name, merchant_id, kwargs, tool, principal)
            if name == "prepare_financing_application" and principal.authenticated:
                result = self.identity_store.submit_packet(principal, merchant_id, result)
        except (PaymentError, ValueError, TypeError) as e:
            self.audit.write(**base, decision="allowed", outcome="error", reason=str(e))
            self.exec_log.write(**base, decision="allowed", outcome="error", reason=str(e), args=kwargs)
            raise ValueError(str(e)) from e
        ms = round((time.perf_counter() - t0) * 1000, 1)
        self.audit.write(**base, decision="allowed", outcome="ok")
        self.exec_log.write(**base, decision="allowed", outcome="ok", args=kwargs, duration_ms=ms,
                            result_summary=_summarize(name, result))
        return result

    # --------------------------------------------------- autonomous cycle
    def run_cycle(self, principal: Principal, merchant_id: str) -> dict:
        """IDENTIFY -> PROFILE -> PLACE -> ACTIVATE -> MEASURE & GRADUATE."""
        a = self.call(principal, "assess_business", merchant_id)            # IDENTIFY + PROFILE + PLACE
        alerts = self.call(principal, "cashflow_alerts", merchant_id)
        inc = self.call(principal, "incentive_status", merchant_id)
        recs = (self.call(principal, "match_financing", merchant_id)
                if principal.max_tier() >= Tier.T1_ADVISE else None)        # ACTIVATE
        rbf_q = None
        if recs and any(r["id"] == "RBF" for r in recs["recommendations"]):
            rbf_q = self.call(principal, "rbf_quote", merchant_id)
        prev = self.history.get(merchant_id, [])[-1] if self.history.get(merchant_id) else None
        self.history.setdefault(merchant_id, []).append(
            {"as_of": a["as_of"], "stage": a["stage"], "composite": a["composite_score"], "scores": a["scores"]})
        measure = {"previous": prev, "current_stage": a["stage"], "composite": a["composite_score"],
                   "graduated": bool(prev and a["stage"] > prev["stage"]),
                   "next_stage": a["next_stage"], "graduation_trigger": a["graduation_trigger"]}
        plan = self._activation_plan(a, alerts, inc, recs)
        return {"merchant_id": merchant_id, "stage": a["stage"], "stage_name": a["stage_name"],
                "composite_score": a["composite_score"], "scores": a["scores"],
                "constraints": a["constraints"], "alerts": alerts, "incentive": inc,
                "recommendations": recs, "rbf_quote": rbf_q, "plan": plan, "measure": measure}

    @staticmethod
    def _activation_plan(a, alerts, inc, recs):
        plan = {"EQUIP": [], "EXPAND": [], "ENTICE": [], "SUSTAIN/EMPOWER": []}
        for c in a["constraints"]:
            lever = c["lever"].split("/")[0]
            key = lever if lever in plan else "SUSTAIN/EMPOWER"
            plan[key].append(c["intervention"])
        if inc["next_milestone"]:
            plan["ENTICE"].append(f"Reach {inc['next_milestone']['name']} by routing "
                                  f"{inc['next_milestone']['additional_monthly_ecosystem_sales_needed']:,.0f} more "
                                  f"monthly sales through QR Pay / Tap Pay / Pay Link.")
        elif inc["tier"]:
            plan["ENTICE"].append(f"Maintain {inc['tier_name']}: {inc['reward']}.")
        elif inc["note"]:
            plan["ENTICE"].append("Build a stable digital sales base to start earning milestone rewards.")
        for al in alerts:
            if al["severity"] == "critical":
                plan["EQUIP"].insert(0, f"URGENT: {al['recommended_action']}")
        return {k: list(dict.fromkeys(v)) for k, v in plan.items() if v}

    # --------------------------------------------------------- chat turn
    INTENTS = [
        ("report", r"\b(report|analy[sz]e|projection|uploaded|repayment capacity)\b"),
        ("prohibited", r"\b(approve|approval of) (my|the|this)? ?(loan|credit|application)|disburse|transfer (the )?(money|funds)|increase (my )?(credit )?limit"),
        ("apply", r"\b(apply|submit|application|proceed with (the )?(loan|financing|offer))\b"),
        ("payment", r"\b(qr|pay ?link|payment link|tap|collect|charge|accept payment|generate)\b"),
        ("rbf", r"\b(rbf|revenue[- ]based|advance|capital flex|how much can i borrow|repay(ment)? as)\b"),
        ("financing", r"\b(loans?|financ\w*|borrow\w*|credit|funding|capital|leas\w*|equipment|purchase orders?|options?)\b"),
        ("alerts", r"\b(alerts?|warnings?|risks?|overdue|runway|run out)\b"),
        ("cashflow", r"\b(cash ?flow|forecast|balance|liquidity|bills?|payables?)\b"),
        ("incentive", r"\b(incentive|milestone|reward|cashback|tier|mdr|discount rate|fee)\b"),
        ("dashboard", r"\b(dashboard|sales|revenue|channel|transactions?|trend|mix)\b"),
        ("progress", r"\b(stages?|progress\w*|graduat\w*|health|scores?|assess\w*|how am i doing|overview|status)\b"),
    ]
    # Intents that must never be delegated to an external model
    RULE_ONLY_INTENTS = ("prohibited", "apply", "payment")

    @staticmethod
    def parse_amount(text: str):
        m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(k|m|mn|million|thousand|b|bn)?\b", text, re.I)
        if not m:
            return None
        v = float(m.group(1).replace(",", ""))
        mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9}
        return v * mult.get((m.group(2) or "").lower(), 1)

    def route(self, text: str) -> str:
        for name, pat in self.INTENTS:
            if re.search(pat, text, re.I):
                return name
        return "help"

    def handle(self, principal: Principal, merchant_id: str, message: str, approval_token: str | None = None,
               history: list | None = None, module: str | None = None, owner_reader=None, explain_actions=False) -> dict:
        if not self.limiter.allow(principal.user_id):
            return {"reply": "Too many requests. Please wait a minute.", "intent": "rate_limited"}
        from copilot.authorization import require
        require(principal, "use_copilot", merchant_id)
        clean = sanitize_input(message)
        text, flags = clean["text"], clean["flags"]
        intent = self.route(text)
        self.audit.write(actor=principal.user_id, event="message", intent=intent, flags=flags,
                         merchant_id=merchant_id)
        mer = self.merchants.get(merchant_id)
        if not mer or merchant_id not in principal.merchant_ids:
            return {"reply": "I can only help with businesses you are authorised to access.", "intent": "denied"}
        cur = mer.currency
        if any(ref!=merchant_id for ref in re.findall(r"\bM[0-9]{3}\b",text)):
            return {"reply":"Access denied: chat cannot change the selected merchant. Select an authorized merchant first.","classification":"UNAUTHORIZED","mode":"rule_engine","tools_used":[],"evidence":[],"data":{}}
        # Explain-only registry runs after sanitization and authorization, before action routing.
        if not flags and not approval_token:
            try:
                from copilot.partner_help import answer
                guidance=answer(principal,merchant_id,text)
                if guidance:
                    self.audit.write(actor=principal.user_id,event="application_help",merchant_id=merchant_id,module=guidance["data"]["help_module"])
                    return guidance
                if owner_reader:
                    result=owner_reader(text)
                    if result:return result
            except AccessDenied:
                return {"reply":"Access denied: this capability is not authorized for your account and selected merchant.","classification":"UNAUTHORIZED","mode":"rule_engine","tools_used":[],"evidence":[],"data":{}}
            except (ValueError,KeyError,TypeError):
                return {"reply":"The requested information is unavailable. Open the authorized source module to review it.","classification":"INSUFFICIENT_EVIDENCE","mode":"rule_engine","tools_used":[],"evidence":[],"data":{}}
        action_requested=bool(re.search(r"(?:^|\b(?:can you|please|i want to)\s+)(?:create|generate|simulate|submit|apply|collect|charge|accept)\b",text,re.I))
        analysis_only=intent in ("payment","apply") and not action_requested
        if explain_actions and action_requested and not flags:
            from copilot.partner_help import answer
            try:
                guidance=answer(principal,merchant_id,"How do I "+text)
                if guidance:
                    self.audit.write(actor=principal.user_id,event="application_help",merchant_id=merchant_id,module=guidance["data"]["help_module"])
                    return guidance
            except AccessDenied:
                return {"reply":"Access denied: use only the workflows delegated to your account.","classification":"UNAUTHORIZED","mode":"rule_engine","tools_used":[],"evidence":[],"data":{}}
        if intent in ("payment","apply") and action_requested and not flags:
            try:
                kind="payment_create" if intent=="payment" else "prepare_financing_application"
                amount=self.parse_amount(text)
                if approval_token:
                    outcome=self.partner_state.confirm(principal,merchant_id,principal.session_id,approval_token,True,expected_amount=amount,expected_kind=kind)
                    result=outcome["result"]
                    return {"reply":"Confirmed simulated action completed: "+str(result.get("ref",result.get("application_id","")))+" · "+str(result.get("status",""))+". No real funds moved or lender approval granted.","intent":intent,"mode":"rule_engine","data":result}
                if amount is None and intent=="apply":amount=self.call(principal,"rbf_quote",merchant_id)["advance"]
                if amount is None:return {"reply":"Please specify the exact amount for the simulated payment.","intent":intent,"mode":"rule_engine","data":{}}
                parameters={"amount":amount,"method":"tap_pay" if "tap" in text.lower() else "pay_link" if "link" in text.lower() else "qr_pay"} if intent=="payment" else {"amount":amount,"product_id":"RBF"}
                proposal=self.partner_state.propose(principal,merchant_id,principal.session_id,kind,parameters)
                return {"reply":"Review the exact simulated action before confirming. Amount: "+str(amount)+" "+cur+". No payment or application has been created yet.","intent":intent,"mode":"rule_engine","data":{"approval_required":True,"approval_token":proposal["action_id"],"action":proposal}}
            except (AccessDenied,ValueError) as exc:
                return {"reply":str(exc),"intent":intent+":denied","mode":"rule_engine","data":{}}

        # AI agent mode: a real LLM plans tool calls for open questions. Sensitive intents
        # (credit approval, applications, payments) and flagged messages stay on the rule engine.
        if (intent not in self.RULE_ONLY_INTENTS or analysis_only) and not flags and not approval_token:
            try:
                r = ai_agent.run(self, principal, merchant_id, text, history, module=module)
                self.audit.write(actor=principal.user_id, event="ai_agent_answer", merchant_id=merchant_id,
                                 tools_used=r["tools_used"])
                return {"reply": r["reply"], "intent": "ai_agent" if r["mode"]=="ai_agent" else intent, "flags": flags,
                        "data": {**r.get("data",{}),"tools_used": r["tools_used"]}, **{k:v for k,v in r.items() if k not in ("reply","data","tools_used")}}
            except Exception as e:
                self.audit.write(actor=principal.user_id, event="ai_agent_fallback", reason=type(e).__name__,
                                 merchant_id=merchant_id)
                return {"reply":"Financial evidence could not be verified. No unsupported financial conclusion or action was produced. Review the reporting period and available records.","intent":intent,"mode":"rule_engine","classification":"UNAUTHORIZED" if isinstance(e,AccessDenied) else "INSUFFICIENT_EVIDENCE","connection_status":"fallback","evidence":[],"data":{},"fallback_reason":type(e).__name__}

        data, lines = {}, []
        try:
            if intent == "prohibited" or "possible_prompt_injection_or_privilege_request" in flags:
                tool = ("approve_credit" if re.search(r"approv", text, re.I) else
                        "change_credit_limit" if re.search(r"limit", text, re.I) else
                        "disburse_funds" if re.search(r"transfer|disburse|funds|money", text, re.I) else None)
                if tool:
                    try:
                        self.call(principal, tool, merchant_id)
                    except AccessDenied as e:
                        lines.append(f"I can't do that: {e}")
                lines.append("I'm an advisory copilot. I can estimate offers, rank options and prepare an "
                             "application for your approval, but lenders make credit decisions.")
                intent = "prohibited"
            elif intent == "report":
                data = self.call(principal, "financial_report", merchant_id)
                lines.append(f"Last 90 days: revenue {money(data['revenue'], cur)}, expenses {money(data['expenses'], cur)}, net income {money(data['net_income'], cur)}.")
                lines.append(f"30-day revenue projection: {money(data['revenue_projection_30_days'], cur)}. Assumption: recent 30-day daily sales continue; not a guarantee.")
                for alert in data['risk_alerts']: lines.append(alert['message'])
            elif intent == "progress":
                c = self.run_cycle(principal, merchant_id)
                data = c
                lines.append(f"{mer.name} is at Stage {c['stage']} – {c['stage_name']} "
                             f"(composite score {c['composite_score']}/100).")
                weakest = sorted(c["scores"].items(), key=lambda kv: kv[1])[:2]
                lines.append("Weakest dimensions: " + ", ".join(f"{k.replace('_', ' ')} {v:.0f}" for k, v in weakest) + ".")
                if c["constraints"]:
                    lines.append("Main constraint: " + c["constraints"][0]["evidence"] + " → " +
                                 c["constraints"][0]["intervention"] + ".")
                ns = c["measure"]["next_stage"]
                if ns:
                    lines.append(f"To reach Stage {ns['target_stage']} ({ns['target_name']}) you need "
                                 f"{ns['composite_gap']} more points" +
                                 (f" and to lift {', '.join(ns['dimension_gaps'])}." if ns["dimension_gaps"] else "."))
            elif intent == "financing":
                r = self.call(principal, "match_financing", merchant_id)
                data = r
                lines.append(f"Top options for your Stage {r['stage']} business:")
                for i, x in enumerate(r["recommendations"][:3], 1):
                    sz = f" (indicative {money(x['indicative_size'], cur)})" if x["indicative_size"] else ""
                    lines.append(f"{i}. {x['name']}{sz} – score {x['match_score']}. {x['rationale']}")
                lines.append(r["disclaimer"])
            elif intent == "rbf":
                amt = self.parse_amount(text)
                q = self.call(principal, "rbf_quote", merchant_id, advance=amt)
                data = q
                lines.append(f"Revenue-based financing estimate: advance {money(q['advance'], cur)}, flat fee "
                             f"{q['fee_rate']:.0%} ({money(q['fee'], cur)}), total {money(q['total_repayable'], cur)}.")
                lines.append(f"Repayment: {q['remittance_rate']:.1%} of each day's QR Pay / Tap Pay / Pay Link sales. "
                             f"On a typical day of {money(q['examples']['typical_day']['sales'], cur)} you'd pay "
                             f"{money(q['examples']['typical_day']['repayment'], cur)}; on a no-sales day you pay nothing.")
                if q["estimated_payoff_days"]:
                    lines.append(f"At your recent sales pace it is repaid in about {q['estimated_payoff_days']} days.")
                lines += q["warnings"]
                lines.append(q["disclaimer"])
            elif intent in ("cashflow", "alerts"):
                fc = self.call(principal, "cashflow_forecast", merchant_id)
                al = self.call(principal, "cashflow_alerts", merchant_id)
                data = {"forecast": fc, "alerts": al}
                lines.append(f"Balance today {money(fc['opening_balance'], cur)}; projected in 30 days "
                             f"{money(fc['closing_balance'], cur)} (lowest point {money(fc['min_balance'], cur)}).")
                lines.append("Cash stays positive for the next 30 days." if fc["runway_days"] is None
                             else f"Cash is projected to go negative on day {fc['runway_days']}.")
                for x in al[:4]:
                    lines.append(f"[{x['severity'].upper()}] {x['message']} → {x['recommended_action']}")
            elif intent == "incentive":
                inc = self.call(principal, "incentive_status", merchant_id)
                mdr = self.call(principal, "mdr_compare", merchant_id, amount=self.parse_amount(text) or 10000)
                data = {"incentive": inc, "mdr": mdr}
                if inc["mom_growth"] is not None:
                    lines.append(f"Ecosystem digital sales are growing {inc['mom_growth']:.0%} month-on-month "
                                 f"(run-rate). Current milestone: {inc['tier_name']}.")
                else:
                    lines.append(inc["note"])
                if inc["reward"]:
                    lines.append(f"Reward unlocked: {inc['reward']}.")
                if inc["next_milestone"]:
                    nm = inc["next_milestone"]
                    lines.append(f"Next: {nm['name']} – route about "
                                 f"{money(nm['additional_monthly_ecosystem_sales_needed'], cur)} more per month digitally.")
                base_amt = mdr['tiered_fee'] / mdr['tiered_rate'] if mdr['tiered_rate'] else 10000
                lines.append(f"Your stage MDR is {mdr['tiered_rate']:.1%} vs a {mdr['flat_benchmark_rate']:.0%} flat rate "
                             f"– saving {money(mdr['saving'], cur)} per {money(base_amt, cur)} sold.")
            elif intent == "dashboard":
                d = self.call(principal, "get_dashboard", merchant_id)
                data = d
                cap = d["capture"]
                lines.append(f"Last 90 days: {money(d['mix']['gross_revenue'], cur)} from "
                             f"{d['mix']['total_transactions']:,} transactions.")
                lines.append(f"Digital share {cap['digital_share']:.0%}, on your own QR/Tap/Link rails "
                             f"{cap['ecosystem_share']:.0%}, cash {cap['cash_share']:.0%}.")
                top = list(d["mix"]["by_channel"].values())[:3]
                lines.append("Top channels: " + "; ".join(f"{t['label']} {t['revenue_share']:.0%}" for t in top) + ".")
                lines.append(d["receivables"]["explanation"])
            elif intent == "payment":
                amt = self.parse_amount(text)
                method = ("pay_link" if re.search(r"link", text, re.I) else
                          "tap_pay" if re.search(r"\btap\b|card", text, re.I) else "qr_pay")
                if not amt:
                    lines.append("Tell me the amount, e.g. 'generate a QR for 250'.")
                else:
                    p = self.call(principal, "payment_create", merchant_id, method=method, amount=amt)
                    data = p
                    if p["method"] == "qr_pay":
                        data["qr_matrix"] = qr_matrix(p["qr_payload"])
                    label = config.CHANNELS[method]["label"]
                    lines.append(f"Sandbox {label} request {p['ref']} created for {money(p['amount'], cur)}.")
                    if p["link_url"]:
                        lines.append(f"Share this link: {p['link_url']}")
                    if p["method"] == "qr_pay":
                        lines.append("QR valid for 5 minutes.")
                    if p["flags"]:
                        lines.append("Integrity flags: " + "; ".join(p["flags"]))
                    lines.append(f"Your MDR at this stage: {p['mdr_rate']:.1%}. No real money moves in the sandbox.")
            elif intent == "apply":
                try:
                    app = self.call(principal, "prepare_financing_application", merchant_id,
                                    approval_token=approval_token, amount=self.parse_amount(text))
                    data = app
                    lines.append(f"Application {app['application_id']} for {money(app['requested_amount'], cur)} "
                                 "has been packaged and sent for lender review. The lender makes the final decision.")
                except ApprovalRequired as e:
                    data = {"approval_required": True, "approval_token": e.token}
                    lines.append("Please confirm: do you approve sharing your aggregated business indicators with "
                                 "the lender and submitting this request? Reply with the approval to continue.")
            else:
                lines.append("I can help with: your progress stage, financing options, a revenue-based financing "
                             "estimate, cash-flow forecast and alerts, your sales dashboard, incentive milestones, "
                             "or creating a sandbox QR / Pay Link / Tap payment.")
        except AccessDenied as e:
            lines.append(f"Access denied: {e}")
            intent = intent + ":denied"
        except (PaymentError, ValueError) as e:
            lines.append(f"I couldn't complete that: {e}")
        if "card_number_detected_and_removed" in flags:
            lines.insert(0, "For your safety I removed what looked like a card number. Never share card details here.")
        reply = self.narrator.narrate("\n".join(lines), {"intent": intent})
        return {"reply": reply, "intent": intent, "flags": flags, "data": data, "mode": "rule_engine"}


def _summarize(name, r):
    """Compact, non-sensitive summary for execution logs."""
    if not isinstance(r, dict):
        return {"type": type(r).__name__, "items": len(r) if isinstance(r, list) else None}
    keys = ["stage", "stage_name", "composite_score", "tier", "tier_name", "mom_growth", "advance", "fee_rate",
            "remittance_rate", "estimated_payoff_days", "runway_days", "min_balance", "status", "ref", "amount",
            "method", "paid_channel", "net_settled", "application_id", "flags"]
    out = {k: r[k] for k in keys if k in r}
    if "recommendations" in r:
        out["top"] = [x["id"] for x in r["recommendations"][:3]]
    if "capture" in r:
        out["capture"] = r["capture"]
    return out
