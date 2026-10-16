# Local Gemini connectivity diagnosis

Branch: `feature/ai-governance-chatbot-v2`. Local investigation only; no commit, push, merge or deployment.

## Configuration observed

- Model: `gemini-3.1-flash-lite`.
- Live flag: `COPILOT_GOVERNED_LIVE=yes`.
- Agent mode: `COPILOT_AGENT_MODE=auto`.
- API key: present in the inspected configured Python runtime; its value was never printed.
- Configured base: `https://generativelanguage.googleapis.com/v1beta/openai/`.
- Request endpoint: base plus `chat/completions`.
- Client: existing standard-library `urllib.request` adapter; no Gemini SDK.
- Local `.env` exists and loads through the existing `llm_config`/`ai_agent` startup. No `.env` changes.
- Running localhost backend health returned HTTP 200, `agent_mode=ai_agent`, authenticated mode. This corroborates configured backend operation; no direct extraction of the other process's environment or credentials occurred. No mock provider is installed in ordinary server startup.

## Actual external probes

The existing authenticated adapter sent only: “Reply with exactly: GEMINI_CONNECTION_OK”. Financial orchestration and claim verification were bypassed, provider transport/authentication were preserved. Three real HTTP probes returned 503, in approximately 1.89, 2.83 and 3.94 seconds. The final structured error was a JSON list containing provider code `503`, status `UNAVAILABLE`, and a high-demand indication. Only standardized codes/categories were output; raw bodies, prompts, authorization headers and credentials were not logged.

There was an HTTP error response, but **no successful Gemini completion** and no expected-text success. API-key validity and selected-model availability cannot be conclusively confirmed from a 503. It was not a 401/403 authentication response. One metadata-only invocation omitted configuration bootstrap and stopped locally before making a request; it was corrected in the diagnostic harness, not by changing the application's loader.

## Failure location and time budget

The minimal request was 159 bytes and failed at the external provider-call stage, before completion parsing or financial claim verification. It did not approach the 30-second request or 60-second chat limits. Independent failure proves financial tools and oversized financial context are not necessary to reproduce this outage.

Because the independent request did not succeed, the conditional full live browser/chatbot trace was **not run**. No browser-to-Gemini success is claimed. A separate synthetic sizing/routing check measured approximately 0.094 seconds for an authorized summary read and 3,763 bytes for the oven messages/tools footprint. These are fixture measurements, not a successful live pipeline or the full serialized HTTP payload. A provider double confirmed exactly one request on 503 and no format-correction retry. Current format correction is restricted to claim-format failures; provider exceptions do not enter it.

## Minimal correction

Only provider-error handling/presentation changed:

- HTTP 503 becomes a sanitized `ProviderUnavailable` exception.
- Failure remains `provider_error`, not `response_validation`.
- Existing audit reason records `provider_http_503` without raw provider text or credentials.
- Browser note: “AI service temporarily busy · deterministic guidance”.
- User-initiated retry remains available. No automatic provider retry, fallback model, endpoint change or timeout increase was added.

Financial reasoning, purchase extraction, calculations, roles, governance JSON, merchant isolation, tool permissions and source data were not modified. The correction explains the outage; it cannot remove provider capacity limits or guarantee a later request succeeds.

## Verification

Seven focused provider-adapter/routing tests passed: authenticated endpoint construction, 503 sanitization/no retry, distinct auth/rate-limit errors, unchanged timeout, provider-versus-claim failure routing, synthetic timing/sizing. Python/JavaScript syntax and `git diff --check` passed. These automated tests use explicit doubles. Real Gemini probes received only the unsuccessful provider responses described above. Full regression and full live browser pipeline were not run.

Changed files for this task: `copilot/governed_partner.py`, `web/financial-partner.js`, `tests/test_provider_connectivity.py`, and this report. Existing uncommitted work is preserved.

Restart the local server and refresh the browser to load the new label. Try the same minimal test later; do not infer live success from a deterministic response. No model switch or financial/security bypass is recommended on the basis of this outage.
