# AI orchestration and safeguards

Existing OpenAI-compatible Gemini integration is in [ai_agent.py](../../copilot/ai_agent.py), configuration loading in [llm_config.py](../../copilot/llm_config.py), and rule narrator in [llm.py](../../copilot/llm.py). Current provisional model documented in prior verification is gemini-3.1-flash-lite; provider availability must be verified separately with the owner’s local key. No live provider check ran for this documentation task.

Authenticated session/selected merchant → allowed tool exposure → finance-domain/application-help routing → domain service execution through Principal/PolicyGuard → typed facts/claims, provenance, currency/period/merchant checks → backend-rendered or verified answer → scoped context and audit. Tools retrieve authoritative data; free-text user figures or arbitrary Gemini arithmetic do not become authoritative totals. Unsupported metrics and foreign conversion requests are refused or reported unavailable. Read permissions are independent of use_copilot.

Owner help registry is [partner_help.py](../../copilot/partner_help.py). Additional Owner read adapters in owner_partner.py reuse existing settings, delegation, consent and application services; they do not imply every module has unrestricted write support. Financial evidence is in reliability.py and verified_agent.py. Sensitive supported sandbox actions are separate proposals with explicit confirmation, live reauthorization, session/merchant binding and freshness; chips alone do not authorize action. T4 stays prohibited.

UI conversation state survives ordinary module navigation but merchant scope is cleared/partitioned through the existing mechanism. Cross-session transcript restoration is not promised. Bank has no AI UI in the current portal; retained backend read capabilities remain separately guarded.

Survival uses backend Decimal calculations. Gemini may only select allowed server-authored statement IDs for five explanation sections; invalid/unavailable output falls back to labeled rule-based guidance. Frontend lays out the actual returned projection and does not change formulas, persist scenarios as transactions, or fabricate cash runway.

Fallback success is not connectivity evidence. [API source](../../copilot/server.py) · [permissions](security-permissions.md) · [limitations](known-limitations.md).
