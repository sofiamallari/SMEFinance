# Possible Scenarios — SME Finance Copilot User Journeys

This folder contains a separate scenario README for every current business and administration module. These pathways describe implemented behavior and failure/permission branches. They do not define new rules or promise exhaustive coverage of every input combination.

## Module guides

- [Login and Account Recovery](01_Login_and_Account_Recovery.md)
- [Dashboard](02_Dashboard.md)
- [Merchant Transactions](03_Merchant_Transactions.md)
- [Digital Payments / Payment Sandbox](04_Digital_Payments.md)
- [Cash Flow](05_Cash_Flow.md)
- [Financing — Overview, RBF and Applications](06_Financing.md)
- [Progression Engine — Merchant Financing Journey](07_Progression_Engine.md)
- [AI Financial Partner](08_AI_Financial_Partner.md)
- [Financing Consent](09_Financing_Consent.md)
- [User Management](10_User_Management.md)
- [Security Controls and Configuration](11_Security_Controls.md)

## End-to-end journeys

### A. Onboard a merchant team

Authorized administrator creates an Owner and selectively granted Staff accounts → each changes temporary password → signs in separately → selects assigned merchant → Staff encodes or imports permitted transactions → Owner reviews History, Data Quality and Dashboard → AI explains same-period records.

### B. Import POS data and consider financing

Owner selects merchant → maps synthetic CSV/XLSX → validates duplicates and reconciliation → previews → confirms import → reviews History/Data Quality → checks Dashboard dates → reviews Cash Flow assumptions → asks AI for available report/financing evidence → explores Overview/RBF. Importing data does not automatically establish wallet settlement, eligibility or approval.

### C. Demonstrate a simulated sale

Authorized Owner/Staff proposes QR/Tap/Link payment → reviews exact amount/method → confirms → simulates customer completion → checks saved reference and PAID state → reviews canonical history, Dashboard and Cash Flow → asks AI about latest simulation. No real money moves; external-channel settlement does not credit the internal wallet.

### D. Owner-to-Agent sandbox financing

Administrator provisions an appropriately scoped local demo Agent → Owner grants current category consent → Owner requests supported RBF application and confirms exact proposal → assigned Agent signs in separately → reviews authorized packet and records simulated review → Owner can revoke consent. Consent and packet submission are not lender approval or disbursement.

### E. Explore the five-step financing journey

Owner opens Progression Engine → follows Identify/Profile/Place/Activate/Measure links when authorized → asks AI about the journey → reviews truthful Not Yet Assessed status. Viewing modules or submitting a packet does not complete a stage; completion rules are absent.

### F. Recover access and check governance

Authorized administrator issues private single-use reset token → intended user resets password → signs in again → administrator reviews recorded audit events. Security Administrator may separately export/validate/preview approved configuration; applying a change requires the existing confirmation/reauthentication controls.

## Suggested team execution order

1. Read Login, User Management and the module's permission prerequisites.
2. Use separate role accounts; do not rely on changing a visible role selector.
3. Pick one merchant and a synthetic dataset with dates inside the reporting window.
4. Execute successful scenario, then relevant denied/invalid/expired alternatives in isolated data.
5. Compare actual versus expected outcomes and capture nonsecret evidence by scenario ID.
6. Report limitations as limitations, not failed promises or invented completed features.

## Current boundaries

No real credit approval, disbursement, unrestricted AI writes, automatic progression completion, full transcript restoration after logout/reload, or Task 03.1 survival simulation is provided. Some backend capabilities, such as linked simulator refunds, have no end-user UI/API pathway. Forecasts, financing catalog terms and synthetic profile attributes remain demo/provisional assumptions.

Creation of this folder changed documentation only. No scenarios were executed as part of generating these files; no accounts, permissions, transactions or production settings were changed, and no commit/push/merge was performed.
