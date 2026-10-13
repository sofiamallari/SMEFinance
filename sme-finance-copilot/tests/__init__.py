import os

# Tests never write log files and never call a real LLM unless a test sets it up explicitly.
os.environ["COPILOT_AUDIT_LOG"] = ""
os.environ["COPILOT_EXEC_LOG"] = ""
for _k in ("COPILOT_LLM_BASE_URL", "COPILOT_LLM_API_KEY", "COPILOT_LLM_MODEL", "COPILOT_MCP_API_KEY",
           "COPILOT_MCP_ROLE", "COPILOT_MCP_MERCHANTS", "COPILOT_MCP_CONSENT"):
    os.environ.pop(_k, None)

os.environ["COPILOT_IDENTITY_DB"] = ".test_logs/identity.sqlite3"
