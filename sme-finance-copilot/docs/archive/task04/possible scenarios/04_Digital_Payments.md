> **Historical snapshot — superseded.** Use [current documentation](../../../README.md). Original evidence/scope is retained; old roles, menus, currency and setup instructions are not current policy.

# Digital Payments — scenario pathways

Entry: /payment-sandbox. Use synthetic data and separately signed-in authorized role accounts. Detailed UI steps: [module guide](../7%20README_Digital_Payments.md); rules: [permissions](../../../technical/security-permissions.md). These pathways are instructions, not new test-execution evidence or an exhaustive input enumeration.

## 04-01: QR/Tap/Link lifecycle

**Path:** Authorized user proposes → reviews → confirms → simulates customer completion.

**Expected result / boundary:** Pending is not revenue; no real money moves.

## 04-02: POS cart

**Path:** Select items → review computed total → confirm QR/Tap.

**Expected result / boundary:** Clear resets cart, not persisted activity.

## 04-03: External wallet

**Path:** Complete offered external Link channel.

**Expected result / boundary:** Recorded sale does not credit the internal wallet.

## 04-04: Cash/refund boundary

**Path:** Use POS Cash notice or ask for linked refund UI.

**Expected result / boundary:** Cash button is not a saved entry; no end-user linked-refund endpoint exists.

## 04-05: Expiry/repeat/denial

**Path:** Try expired request or repeated/foreign action, or Bank/admin payment request.

**Expected result / boundary:** Existing confirmation/status and role checks reject unsafe writes.

Capture role, authorized merchant, dates/currency, nonsecret reference, and expected versus actual outcome. Never capture passwords/tokens/provider keys. See [testing](../../implementation-notes/TESTING.md) for recorded evidence.
