# AI Financial Partner drawer polish

Branch: `feature/security-sme-bank-workflow`. Existing working changes retained.

Implemented in `web/index.html` and `web/financial-partner.js`:

- Viewport-fixed right drawer: 420px desktop, full available width on phones;
  dynamic viewport/visual viewport sizing and safe-area padding. Existing desktop
  content reserves drawer width. Native modal dialogs remain above it.
- Fixed header and bottom composer, independently scrolling messages, readable
  dark user bubbles/light text, wrapped long content and accessible close control.
- Suggested Questions stays above the composer as a reusable collapsible section.
  New conversations show it; sending collapses it; users can reopen it. The list
  has a bounded scroll region when needed, matching the reference arrangement.
  Existing prompts remain, with import/staff-help prompts added. Clicking a chip
  uses the real existing `partnerSend` explain/read path and `/api/chat`, with no
  fake replies or automatic action confirmation.
- Empty/whitespace Send is disabled; existing loading, retry, Enter/Shift+Enter,
  merchant-scoped history and error handling remain. Incoming messages preserve
  the reader's position when scrolled up; an explicitly sent question scrolls down.

`copilot/partner_help.py` wording now points to + New Application, + Authorize
Bank and Staff Access → Manage Permissions, matching the consolidated UI. Existing
registry authorization checks remain; no financial formula, tool permission,
consent rule, audit or write operation changed. Existing application colors were
retained rather than adding a separate dark theme.

Verification actually run:

- PASS: Python compilation of help module; JavaScript syntax for drawer and extracted
  Owner inline script; whitespace/diff checks.
- PASS: brief headless Edge smoke using the existing disposable synthetic fixture:
  fixed drawer while document scrolls, desktop/tablet/mobile fit, visible header/
  composer, independent message scrolling and retained reading position, reusable
  suggestions, actual guidance API request, empty Send disabled; no JS errors.
- Visual inspection: mobile screenshot confirms user-message contrast and layout.
- Frontend build: NOT RUN — static application has no frontend build script.
- Full regression/extensive automated/cross-browser tests: NOT RUN, deferred per
  hackathon time constraint. No new repository test suite was added.
- Live Gemini connectivity and physical-device keyboard behavior: NOT RUN. Provider
  availability is unchanged; desktop mobile emulation is not a physical-device test.

Evidence screenshots: `evidence/partner-drawer-polish/desktop.png`, `tablet.png`,
`mobile.png`. Existing older UI scripts may assert the previous chip count or
populate-only behavior and were not modified to hide their outdated assumptions.

Files changed: `web/index.html`, `web/financial-partner.js`,
`copilot/partner_help.py`, this report. No commit, push, merge, reset or persistent
merchant-data change.
