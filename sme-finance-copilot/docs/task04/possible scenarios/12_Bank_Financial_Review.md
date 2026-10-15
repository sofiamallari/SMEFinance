# Bank Financial Review — scenario pathways

Entry: /bank. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../12%20README_Bank_Financial_Review.md); rules: [permissions](../../SECURITY_PERMISSIONS.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 12-01: Read authorized evidence

**Path:** Select authorized merchant → Overview → Financial Review → expand the permitted evidence; select routed packet under Financing Applications.

**Expected result / boundary:** No SME operational menus, missing data invented or new risk engine.

## 12-02: CSV export

**Path:** Reports & Exports → Download CSV → inspect simulated label/classification.

**Expected result / boundary:** Authorization/categories rechecked and export audited.

## 12-03: Unrelated packet/category

**Path:** Request another Bank packet or withheld assessment.

**Expected result / boundary:** Resource/category denied or withheld; authorization is not blanket packet visibility.

## 12-04: Revoked access

**Path:** Owner revokes → Bank refreshes or next live check detects revocation → protected sections and conversation clear → new report/AI/export denied.

**Expected result / boundary:** New protected reads/exports denied; historical records remain.

## 12-05: Bank decisions

**Path:** Attempt approve/reject/payment/submission action.

**Expected result / boundary:** Always outside Bank POC authority.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../TESTING.md) for recorded evidence.

## 12-06: Persistent AI and module navigation

Ask a permitted financial question → navigate all six sidebar modules → transcript remains for the same merchant. Switch to another authorized merchant → original transcript is not shown there. Return → its separate in-memory thread is restored. Reload/logout → page-memory history is cleared.

## 12-07: Mobile and missing evidence

Resize to mobile → collapse navigation → open AI overlay → use Escape/backdrop to close. Withhold forecasts while permitting reports → forecast section says unavailable, and response data contains no forecast. Details remain collapsed until requested.
