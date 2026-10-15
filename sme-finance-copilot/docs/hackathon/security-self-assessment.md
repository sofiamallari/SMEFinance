# Security self-assessment

This is an implementation summary, not a penetration-test certificate or production certification. [Canonical permission rules](../technical/security-permissions.md) are maintained once.

Implemented: server-derived session identity, bounded four-role policy, merchant memberships, explicit Staff delegation, Owner-controlled category/expiry/revocation, receiving-Bank routing checks, separate simulated review permission, cookie CSRF/origin checks, password hashing, token-based recovery, exact sensitive-action confirmation, permanent T4 denial, authenticated MCP and typed financial evidence checks.

Remaining gaps: no MFA or emailed self-service recovery; secrets/HTTPS/hosting depend on correct deployment configuration; no automated operations/incident-response service; SQLite+JSONL assumes one application writer topology; no distributed atomic snapshot; JSONL audit chaining restarts per process; consent cannot recall prior exports; no externally verified accounting/cash or production underwriting. Shared seed passwords must be privately handled and rotated before public hosting.

Undefined permissions deny. Admin does not gain merchant finance access. Bank cannot approve, reject or disburse loans through this POC. Provider output cannot override backend authorization. Historical assessments belong to the inspected code/fixtures, not automatically to this working tree. [Evidence](evidence.md) · [limitations](../technical/known-limitations.md) · [deployment preparation](../operations/railway.md).
