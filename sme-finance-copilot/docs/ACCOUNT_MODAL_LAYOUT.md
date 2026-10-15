# Admin account modal layout

Branch: `feature/security-sme-bank-workflow`. UI-only update to System Admin → User Management → Edit account, also used by Create User. Existing working files preserved; no commit, push, merge, reset or discard performed.

## Implemented behavior

The desktop dialog is at most 960px wide and stays inside the viewport. A persistent header and Save/Cancel footer surround one scrollable body. Sections separate Account information, Role and merchant memberships, and Staff delegated permissions. Account fields use two columns where practical; phone fields stack. All existing fields, native requirements/limits and temporary-password creation requirements remain intact.

Staff permissions use readable labels with unchanged underlying IDs (available in label tooltips). Desktop permissions have three columns, tablet two, phone one. Merchant membership selection reveals the corresponding collapsible merchant section; its summary shows business name and ID. The first assigned merchant opens by default. No permissions are checked for a new account automatically.

Permission controls are created once when the dialog opens. Collapsing/expanding, changing role visibility or hiding an unassigned merchant does not erase unsaved checkbox values. Save continues using the existing payload construction: only grants for selected memberships are sent, with existing optional-upload derivation, role rules and password reauthentication. Individual merchant selections remain independent. Non-Staff roles do not display the Staff permission section and use the same existing non-Staff save rules.

Backend validation errors remain reported by the existing page message and are also shown in the persistent modal footer, so they are visible while the dialog remains open. Native invalid fields retain browser validation/focus behavior. Cancel and Escape retain the existing native close-without-save behavior; there was no unsaved-change confirmation, and none was added.

## Modified files

- `web/users.html`: modal section/body/footer markup, compact merchant permission rendering, readable labels, visibility handling and in-modal error feedback.
- `web/common.css`: scoped dialog width, field/permission grids, one scroll body, persistent header/footer and responsive styles.
- `scripts/verify_account_modal.cjs`: repeatable isolated modal verification and screenshots.
- This guide, docs index and User Management quick guide; current evidence below.

No backend, delegation policies, memberships API, suspension/reset/session handlers or permission identifiers were changed. Existing save payload construction, reauthentication and request code were compared against HEAD and are unchanged; only additional visible error feedback was added to the catch handler.

## Actual verification

- **36 focused modal browser checks PASS**: existing account values; saved grants; two selected merchants; first section expansion; collapse/expand unsaved values; independent checkbox state; Cancel; persistence through real Save; native email validation; rejected Admin memberships with visible backend errors; preserved form values; Escape; no JavaScript errors.
- Desktop 1600px, tablet 900px, phone 390px and 320px fit without modal overflow. Permission grid columns 3/2/1 and account columns 2/1 were measured on visible controls. Scrolling the body to the end keeps header/footer visible and the outer dialog does not acquire a second scroll area.
- **47 existing shared Admin workflow checks PASS** on the updated UI: repeated route navigation, profile/layout, Create User, account history/edit/suspend/reset/revoke/filtering, logout and unauthorized-route/financial-access denial.
- Git whitespace checks passed. Browser execution parsed the inline application script. Full backend discovery/live Gemini were not rerun for this UI-only enhancement; earlier backend evidence is historical.

[Modal evidence](../evidence/account-modal/assessment.json) · [Shared workflow evidence](../evidence/shared-admin-layout/assessment.json) · [Desktop fields](../evidence/account-modal/desktop-top.png) · [Desktop permissions](../evidence/account-modal/desktop-permissions.png) · [Tablet](../evidence/account-modal/tablet-permissions.png) · [Phone](../evidence/account-modal/mobile-permissions.png) · [320px](../evidence/account-modal/small-mobile-permissions.png).

All checks use disposable synthetic accounts and stores. No production data or reset-token value is captured in screenshots. Earlier local capture iterations are preserved in timestamped sibling folders.

## Manual check

Sign in as System Admin, open User Management and Edit a Staff account. Compare saved fields/memberships/grants. Change one merchant's checkbox, collapse/reopen it and verify its value persists without changing another merchant. Cancel and reopen to see saved values; then make intended changes and Save with existing reauthentication. Check native/backend validation, scroll header/footer visibility and repeat at tablet/phone width. Create User must still require a temporary password and default to no delegated grants.

Repeatable browser commands from the app directory: `node scripts/verify_account_modal.cjs` and `node scripts/verify_shared_admin_layout.cjs`. Run them sequentially because both use disposable localhost port 8126. Runtime overrides are in [Testing](TESTING.md).

## Limits

Phone permission lists still need vertical scrolling because one readable column is intentional. Section visibility is presentation only; backend authorization remains authoritative. Permission categories beyond existing merchant grouping were not invented. Only headless Microsoft Edge was tested; no broad production browser certification or new unsaved-change protection is claimed.
