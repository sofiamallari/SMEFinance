import os

# Tests never write log files and never call a real LLM unless a test sets it up explicitly.
os.environ["COPILOT_AUDIT_LOG"] = ""
os.environ["COPILOT_EXEC_LOG"] = ""
for _k in ("COPILOT_LLM_BASE_URL", "COPILOT_LLM_API_KEY", "COPILOT_LLM_MODEL", "COPILOT_MCP_API_KEY",
           "COPILOT_MCP_ROLE", "COPILOT_MCP_MERCHANTS", "COPILOT_MCP_CONSENT"):
    os.environ.pop(_k, None)

# Never open a developer's live identity database or transaction ledger in tests.
import tempfile
from pathlib import Path
_test_runtime = tempfile.TemporaryDirectory(prefix='sme-copilot-tests-')
os.environ['COPILOT_IDENTITY_DB'] = str(Path(_test_runtime.name)/'identity.sqlite3')
os.environ['COPILOT_TRANSACTION_FILE'] = str(Path(_test_runtime.name)/'transactions.jsonl')
