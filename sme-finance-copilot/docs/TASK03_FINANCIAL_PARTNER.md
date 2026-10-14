# Task 03: AI Financial Partner

Implemented in the existing application on `feature/ai-financial-partner`, baseline
`32deb7034acd9e90b04011e9a7164c4a79adb6ba` (merged Task 02). Work is uncommitted;
no push, merge, production migration or live financial action was performed.
Task 03.1 Financial Survival Simulation is not implemented.

## Run locally

Open `C:\Users\User\source\repos\SMEFinance\sme-finance-copilot` in VS Code.
In its PowerShell terminal:

```powershell
python -m copilot.auth migrate
# Only on a fresh installation with no users; password is entered privately:
python -m copilot.auth bootstrap --username admin --email admin@example.test
$env:COPILOT_LLM_MODEL = "gemini-3.1-flash-lite"
python -m copilot.server --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/login. Existing accounts/passwords remain unchanged.
Bootstrap is deliberately unavailable after the first user exists; use the existing
administrator account and User Administration to create business accounts.
Create a Business Owner with merchant membership, or a Staff account with explicit
transaction grants. A User/Security Administrator does not gain financial access.
Financing Agents require membership, assignment and current category consent.
Owner financing consent remains at `/consents`; admin pages remain `/admin/users`
and `/admin/security`.

The only automatically loaded `.env` values are the four LLM settings. Process
variables override them. The local key and `.env` were preserved and are ignored
by Git. The owner’s `.env` still names its original model; the command above selects
the verified provisional model without editing the secret. Model availability is
provider/key dependent. A failed provider request displays deterministic fallback.
Do not paste credentials into chat, source, screenshots or reports.

## Architecture and financial data flow

The existing standard-library HTTP application, SQLite identity/policy store,
append-only transaction journal, MCP tools, PolicyGuard and financial modules are
retained. New migrations 005/006 are additive and preserve existing transaction
data. No replacement application or new frontend framework was introduced.

```mermaid
flowchart LR
  POS[CSV / XLSX / manual transactions] --> Validate[Existing validation / mapping / reconciliation]
  Validate --> Preview[Authorized signed staging and preview]
  Preview --> Confirm[Explicit import confirmation]
  Confirm --> Journal[Canonical transaction journal]
  Simulator[Sandbox payment service] --> Journal
  Simulator --> SQLite[Durable payment / refund / wallet state]
  Journal --> Projection[Shared merchant and currency projection]
  Projection --> Dashboard[Existing dashboard]
  Projection --> Tools[Cash flow / matching / RBF / reporting]
  Tools --> Facts[Typed evidence and exact claims]
  Facts --> Verifier[Backend claim verifier]
  Verifier --> Panel[Persistent AI Financial Partner]
```

`financial_data.py` snapshots original synthetic inputs and projects validated
canonical records into the existing merchant model. Downstream tools and dashboard
reuse this projection and its data date. Saved manual/POS records are counted once,
even if legacy code also updated an in-memory merchant. Completed sales increase
recorded net sales; refunds/reversals reduce them; expenses are separate. Pending,
failed and voided records do not become revenue. Decimal aggregation retains cents.
Records in another currency fail validation instead of being silently combined.

Synthetic seed, historical POS, manual, simulated payment and mixed provenance are
explicit. Synthetic/demo data is not bank settlement evidence. Recorded net sales
are not wallet balance. Gross sales remain unknown when source components are absent;
the old compatible `mix.gross_revenue` API field now represents recorded net sales,
and the UI labels it accordingly. Dashboard volume counts sales/refund activity;
the report's completed transaction count also includes expense activity.
“This month” is anchored to the latest available business-data date, not an assumed
live trading date. Dates and limitations are shown in evidence.

## AI orchestration and verification

```mermaid
sequenceDiagram
  participant U as Authenticated user
  participant B as Existing backend
  participant G as Gemini
  participant T as Authorized financial tools
  U->>B: Question + merchant + active module
  B->>B: Authenticate, authorize, finance-domain route
  B->>G: Only requested authorized read-tool schema
  G-->>B: Structured tool plan
  B->>T: Server-selected merchant, dates and amount
  T-->>B: Deterministic financial result
  B->>B: Build typed evidence, check data version
  B->>G: Allowed claims and bounded insight codes
  G-->>B: Structured claims
  B->>B: Exact verification, freshness, final authorization
  B-->>U: Backend-rendered verified answer or safe fallback
```

1. Finance-domain routing rejects unrelated requests and unavailable credit approvals.
   Guidance and generic education use bounded backend templates, not arbitrary prose.
2. Tool exposure intersects financial role boundaries, current permissions, merchant
   membership, consent and the configured tier ceiling. Analysis offers no write tool.
   The server fixes merchant/date/amount; model substitutions never change scope.
3. Financial functions remain authoritative. Gemini plans a permitted tool and copies
   the permitted claims; it cannot calculate final financial facts or authorize actions.
4. Every fact carries source, evidence ID, merchant, currency, metric, exact value,
   period, retrieval timestamp, provenance, quality, method version, record count,
   assumptions, limitations and classification.
5. Claims must match every typed field exactly; unsupported IDs, values, dates,
   currencies, merchants, statuses, free prose, extra fields and mixed fabricated claims
   reject the model response. Required findings cannot be omitted. Forecast evidence
   is ESTIMATED. VERIFIED means verified against authorized sandbox records, not a
   real-world lender certification. HYPOTHESIS is reserved in the schema; unsupported
   causal explanations are withheld rather than asserted.
6. Financial-data versions are checked around retrieval and explanation. Evidence
   expires after five minutes; changed records cause safe rejection/refresh. Live
   authorization runs again before publication. Missing/invalid provider configuration,
   invalid JSON, timeout or unsupported claims use verified deterministic rendering.
7. Only bounded backend-rendered labels and condition-checked insight codes reach the
   final financial answer. Imported descriptions, raw tool messages and raw supplied
   history are not model authority. There is no claim of universal injection resistance.

Reports include recorded totals, the existing repeat-recent-sales 30-day projection
and counts from existing cash-flow risk rules. Projections and rule alerts are marked
estimated. Forecast methods/assumptions are preserved. Match names come from the
configured product catalog; they are indicative, never lender approvals.

## Permissions, context and actions

T0 reads, T1 advice, T2 sandbox writes and T3 human approval retain their existing
PolicyGuard roles/tier ceilings; T4 credit approval/disbursement/limit changes remain
permanently prohibited. `owner`, `staff`, `lender_analyst` and compatible `coach`
identifiers are retained. Administrator permissions remain independent of finance.
Authenticated HTTP/MCP uses server-derived principals and live authorization;
client demo headers and API keys do not create merchant access.

Conversation preferences persist in SQLite, keyed to authenticated user and session,
with merchant and role checks. Only intent, dates, reviewed advance and active module
are retained when financial evidence becomes stale. Each answer retrieves fresh
facts. Browser conversation display survives module navigation and keeps separate
merchant threads; old action buttons require a fresh proposal. It is not a persistent
full transcript after logout/browser reload.

Payment/application proposals bind exact parameters to user, session, merchant,
data version and a five-minute expiry. Confirmation is explicit and boolean, with
fresh authorization and the existing T3 token where required. SQLite atomically
claims execution; repeated confirmed actions return the saved outcome, not another
payment/application. Uncertain action outcomes require review instead of automatic
retry. Application submission remains simulated; no lender approval is inferred.
The legacy explicit authenticated sandbox payment endpoints remain for compatibility.

Paid simulation events append deterministic canonical markers. Full/partial refunds
are linked, negative, capped and idempotent. Payment/refund/wallet state survives
restart; canonical markers repair the tested interruption window between journal
append and SQLite finalization. Ambiguous inconsistent effects fail closed. This is
not a general distributed exactly-once guarantee. No real money or payment network
is used; the QR is a sandbox visual, not a usable bank QR.

## Three-panel workspace

The existing shell now has left navigation, center workspace and persistent right
AI Financial Partner. Authorized Dashboard is the default landing view. Merchant
Transactions retains its four subviews. Digital Payments, Cash Flow and Financing
remain; Financing contains Overview, RBF Calculator and Applications. Old `/copilot`
and `/payment-sandbox` routes remain compatible. Direct routes, refresh, merchant
selection, logout and administrator navigation are preserved.

The AI panel collapses on desktop and becomes a focus-managed drawer on smaller
screens, closed automatically when crossing the mobile breakpoint. Module-specific
questions respect visible financial permissions. Evidence/status/fallback indicators
are explicit; past responses get a stale-data notice after changes. Tool names shown
after completion are actual executed tools; the pending message is not a fabricated
live tool trace.

## Verified defects changed

No lending fee or sizing coefficients were redesigned. A reproduced negative-sales
day produced a negative RBF repayment of -602.7; repayment is now bounded below by
zero. Nonpositive financial history no longer implies positive eligibility/limits,
and invalid capture ratios are rejected. Positive baseline regression retains the
10,000,000 advance, 1,300,000 fee and 11,300,000 total. Payment validation rejects
nonfinite/capped/overprecision amounts instead of accepting invalid floats. The MCP
RBF eligibility metadata now uses the same canonical projection as its quote.

## Testing and demo

```powershell
python -m unittest tests.test_reliability -q
python -m unittest tests.test_financial_partner tests.test_partner_integration -q
python -m unittest discover -s tests -q
# Opt-in real provider assessment; only synthetic/disposable merchant data:
python scripts/assess_partner.py
# Optional Playwright with installed Microsoft Edge (serial; same fixture port):
node scripts/verify_partner_ui.cjs
node scripts/verify_auth_ui.cjs
node scripts/verify_pos_ui.cjs
node scripts/verify_security_ui.cjs
```

Normal tests deliberately disable local LLM credentials and isolate identities and
transaction journals. Browser scripts use temporary users/data, never the running
owner database. See `TASK03_REPORT.md` and JSON evidence for actual results. T01–T35
and T37–T40 are backend acceptance cases; T36 is the persistent conversation browser
journey. Eight critical verifier methods include multiple adversarial subcases.

Demo: sign in as Owner → inspect source/period on Dashboard → upload a CSV/XLSX
through mapping, reconciliation and preview → explicitly commit → verify history
and dashboard net sales → ask the partner for recorded sales using the same dates →
inspect provenance → create/confirm/pay a simulated QR → inspect canonical history
and ask its status → open Financing/RBF → verify indicative terms → grant consent
before simulated application submission → confirm exact action → review as assigned
Financing Agent → revoke consent and verify denial. Repeat Staff financing/foreign
merchant and cake-recipe requests to demonstrate backend refusals.

## Security self-assessment and risk register

| Risk or limit | Implemented control / remaining work |
|---|---|
| Model fabricates amounts, dates, references or approval | Exact typed equality, complete claims and backend rendering; finite tests do not prove all possible attacks |
| Cross-merchant/role leakage | Server principal, live permission/consent checks, fixed scope, session-bound actions; old displayed answers cannot be retroactively recalled |
| Imported instructions | Descriptions/raw tool prose excluded from explanation; numeric facts only; no external document/RAG parser |
| Stale evidence / concurrent changes | Data version and five-minute freshness, final reauthorization; no single distributed snapshot across all stores |
| Generic finance language | Conservative English routing and templates; incomplete multilingual/ambiguous intent support; no unrestricted finance conversation |
| Missing finance inputs | No FX, bank settlement, real credit score/limit/approval source; gross components can be unknown |
| Synthetic historical balances and obligations | Explicit provenance/limitations; forecasts may combine imported activity with synthetic base assumptions |
| Interrupted action | Durable CAS/idempotent outcomes; uncertain execution requires operator review |
| Provider failures | Safe deterministic fallback; availability, pricing and model lifecycle outside application control |
| Deployment | Local sandbox demonstration; not independently penetration-tested, externally deployed or certified for real lending |
| Presentation | No new dark-theme system; existing design retained, responsive tests run in Edge only |
| Hypotheses | Schema supports HYPOTHESIS but free causal hypotheses are intentionally not generated |

The pre-Task 03 Gemini baseline report/evidence is preserved as historical evidence;
its failures describe the baseline, not the current verified implementation.
