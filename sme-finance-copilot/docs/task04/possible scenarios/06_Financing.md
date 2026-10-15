# Financing — scenario pathways

Entry: Financing Overview/RBF/Applications. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../9%20README_Financing.md); rules: [permissions](../../SECURITY_PERMISSIONS.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 06-01: Matching/quote

**Path:** Owner/delegated Staff reviews matches, exclusions and calculator.

**Expected result / boundary:** Indicative score/quote is not lender approval or automatic eligibility.

## 06-02: Staff draft

**Path:** Delegate view/create/edit draft actions → Staff saves/edits own draft.

**Expected result / boundary:** No Staff UI/API/AI submission authority.

## 06-03: Owner routes and confirms

**Path:** Owner selects active authorized Bank → reviews draft → proposes → confirms.

**Expected result / boundary:** Recipient is explicit; no first-consent routing or automatic Bank authorization.

## 06-04: Invalid/changed recipient

**Path:** Deactivate selected Bank or change draft/authorization after proposal.

**Expected result / boundary:** Current recipient and exact stored draft are rechecked; unsafe action cannot persist.

## 06-05: Bank packet review

**Path:** Bank selects its routed authorized submitted packet through review view.

**Expected result / boundary:** No unrelated packets or financing decision mutations.

## 06-06: Revocation

**Path:** Owner revokes authorization → Bank attempts new reads/export.

**Expected result / boundary:** Denied; history remains.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../TESTING.md) for recorded evidence.
