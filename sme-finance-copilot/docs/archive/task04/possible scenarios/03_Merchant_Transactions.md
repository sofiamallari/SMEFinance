> **Historical snapshot — superseded.** Use [current documentation](../../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Merchant Transactions — scenario pathways

Entry: Existing four Merchant Transactions subroutes. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../6%20README_Merchant_Transactions.md); rules: [permissions](../../../technical/security-permissions.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 03-01: Valid entry

**Path:** Owner/delegated Staff enters supported fields → Save → History.

**Expected result / boundary:** Signed type and completed status determine financial effect.

## 03-02: CSV/XLSX import

**Path:** Select → map → validate/reconcile → preview → confirm import.

**Expected result / boundary:** No commit before explicit confirmation; inspect source/error/duplicate evidence.

## 03-03: Duplicate/conflict

**Path:** Reupload receipts or conflicting references → inspect validation.

**Expected result / boundary:** Exact exclusions differ from ambiguity/conflict blocking.

## 03-04: Cancel/stale preview

**Path:** Cancel or change/expire staging state → attempt commit.

**Expected result / boundary:** No unsafe reuse; restage/revalidate when required.

## 03-05: Delegation boundary

**Path:** Staff attempts entry/upload/history/quality without corresponding grants.

**Expected result / boundary:** Reads and writes need separate explicit grants; upload also needs optional permission.

## 03-06: Quality lifecycle

**Path:** Authorized reviewer acknowledges then resolves with evidence/reason.

**Expected result / boundary:** Alert lifecycle does not repair financial records or bypass import validation.

## 03-07: Oversize/unsupported file

**Path:** Upload invalid/oversized synthetic file.

**Expected result / boundary:** Stage HTTP cap is 14.1 MB; extractor limits still apply. Other requests retain 4.1 MB cap.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../implementation-notes/TESTING.md) for recorded evidence.
