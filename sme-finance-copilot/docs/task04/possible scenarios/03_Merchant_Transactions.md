# Merchant Transactions — User Journey Scenarios

**Entry point:** /merchant-transactions/single; /merchant-transactions/import; /merchant-transactions/history; /merchant-transactions/data-quality. Routes are relative to your application server.

## How to use these scenarios

Use synthetic data in the intended local demo/test environment. Check the selected merchant, role, enabled permissions and currency before each journey. Run only actions you are authorized to perform. Administrator accounts do not inherit financial access. Do not include credentials or customer personal data in evidence.

These are source-aligned scenario instructions, **not a claim that every scenario was newly executed**. The set covers meaningful implemented branches, not every possible input or combination. Unsupported pathways are explicitly marked in expected outcomes.

## 03-01: Single completed income or expense

**Prerequisites:** Owner or Staff with explicit create_transactions grant for the merchant.

**Pathway:** Single Transaction → enter supported date, positive amount, type, method, status, reference/category → Save → inspect ID → History → Dashboard.

**Expected result / boundary:** Type determines the internal sign; only completed records affect financial totals.

## 03-02: Pending transaction

**Prerequisites:** Authorized entry permission.

**Pathway:** Save a valid pending record → inspect History and Dashboard.

**Expected result / boundary:** History can contain the record without completed-sales financial effect.

## 03-03: Invalid single entry

**Prerequisites:** Isolated synthetic inputs.

**Pathway:** Try invalid date, currency, nonfinite/overprecision amount or unsupported value → read validation → correct and save.

**Expected result / boundary:** Invalid records must not be saved. Do not enter card numbers, secrets or personal customer data.

## 03-04: Successful CSV/XLSX import

**Prerequisites:** Owner or explicitly upload-authorized Staff; transaction-level synthetic files.

**Pathway:** Select Files → Map Columns → Validate → Preview → Confirm Import → inspect outcome, History and Dashboard.

**Expected result / boundary:** Selection/preview do not save. Map net/gross meaning explicitly; settlement is not sales revenue.

## 03-05: Mapping or reconciliation failure

**Prerequisites:** Synthetic source with missing/ambiguous fields or mismatched monetary controls.

**Pathway:** Validate → inspect row errors and reconciliation → correct source/mapping → validate again.

**Expected result / boundary:** Conflicting references/ambiguous duplicates block commit. Missing controls are warnings, not proof of reconciliation.

## 03-06: Exact duplicate batch

**Prerequisites:** Previously imported synthetic transaction records.

**Pathway:** Upload again → validate → inspect eligible/duplicate/invalid counts → review preview.

**Expected result / boundary:** Exact duplicates are excluded according to implemented merchant/source identity rules; do not assume all similar rows are duplicates.

## 03-07: Cancel or expired preview

**Prerequisites:** Staged uncommitted batch.

**Pathway:** Cancel before confirmation, or return after staging expiry → restage/revalidate when necessary.

**Expected result / boundary:** Cancel leaves batch uncommitted. Staging expires after 30 minutes; stale/session-mismatched previews cannot commit.

## 03-08: Ledger changes after preview

**Prerequisites:** Two authorized synthetic sessions or a new transaction.

**Pathway:** Preview → change underlying ledger → attempt commit → revalidate as requested.

**Expected result / boundary:** New duplicates or changed state require fresh validation rather than blindly reusing the preview.

## 03-09: Partial Staff grants

**Prerequisites:** Staff assigned to merchant with only selected grants.

**Pathway:** Try permitted entry → attempt upload/alert changes without required grants.

**Expected result / boundary:** Each action requires its own grant. Upload needs both optional bulk permission and merchant bulk grant.

## 03-10: History and quality follow-up

**Prerequisites:** Authorized history/monitoring access.

**Pathway:** Filter History → open Data Quality → Refresh/Recheck → inspect run → acknowledge then resolve with permitted reason/evidence.

**Expected result / boundary:** Alert lifecycle is Open → Acknowledged → Resolved. Alert changes do not repair transactions or bypass import validation.

## 03-11: Large or unsupported upload

**Prerequisites:** Synthetic files within a disposable test.

**Pathway:** Select unsupported content or an oversized batch → read extraction/request errors → use valid smaller transaction-level files.

**Expected result / boundary:** UI total limit and approximately 4.1 MB HTTP cap differ; base64 overhead can reject a batch below the displayed total limit.

## 03-12: Refund accounting pathway

**Prerequisites:** Authorized manual/POS entry.

**Pathway:** Record a refund once → check its effect on net sales.

**Expected result / boundary:** Do not double count refund components and refund rows. Accounting refunds do not automatically reverse simulator-wallet settlement.

## Evidence to capture

Record the scenario ID, account role (no password), authorized merchant, relevant dates, expected versus actual result, and any nonsecret record/reference or validation message. For financial comparisons, record metric definition, currency, source and reporting period. Do not label an estimate as a verified outcome.

**Related guide:** See the existing Merchant Transactions guide in the parent `docs/task04` folder. Review actual UI labels and errors on your installed version.
