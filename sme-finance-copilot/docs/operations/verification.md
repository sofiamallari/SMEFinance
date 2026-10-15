# Focused verification and evidence scope

This documentation task ran static Markdown/link/reference/navigation checks only. It did not rerun application tests, call Gemini, start servers, migrate databases or modify financial records.

For an initialized copy, `python -m copilot.cny_demo verify` is the supported dataset check. It initializes its normal service adapters and therefore belongs on a backed-up/isolated development copy when auditing behavior. Do not run raw test discovery against shared configuration without understanding initialization paths.

Recorded earlier focused checks cover CNY cutover (35 disposable workflow checks and 41 activation checks, plus stated audit limitations), currency audit (59), Survival UI (47), and simplified Validate/Preview UI (24). These are dated targeted observations, not a combined current full-suite pass or live-Gemini result. Public narrative reports link from the [evidence index](../hackathon/evidence.md); private logs/ screenshots may be absent from source ZIPs and must be reviewed/redacted before sharing.

Existing tests and scripts remain in [tests](../../tests) and [scripts](../../scripts). Historical legacy fixtures retain earlier currency/menu assumptions and may require explicit isolated setup; this task does not claim those scripts work unchanged on the current default dataset. New verification should use synthetic disposable data, a new output filename and the selected current CNY configuration. Never overwrite historical evidence or label skipped checks as passing.

Minimal user smoke checklist: sign in by role; confirm merchant scope/CNY; open Dashboard tabs; validate and preview a synthetic POS source without committing unless intended; inspect Cash Flow/RBF; confirm Owner-only routing; verify Bank category consent and permitted review; check optional Survival and explicit action confirmation. Use permitted accounts/fixtures, never weaken policy to complete a demo.

[User journey](../hackathon/demo-journey.md) · [known gaps](../technical/known-limitations.md).
