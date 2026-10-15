"""Load allowlisted local LLM settings and the optional simulation flag; never execute or log dotenv contents."""
import os
from pathlib import Path

LLM_KEYS = frozenset({'COPILOT_LLM_BASE_URL', 'COPILOT_LLM_API_KEY',
                      'COPILOT_LLM_MODEL', 'COPILOT_AGENT_MODE', 'FINANCIAL_SURVIVAL_SIMULATION_ENABLED'})

def load_llm_env(path=None, environ=None):
    env = os.environ if environ is None else environ
    if env.get('COPILOT_LOAD_LLM_ENV', 'yes').lower() == 'no':
        return ()
    source = Path(path) if path is not None else Path(__file__).resolve().parent.parent / '.env'
    if not source.is_file():
        return ()
    if source.stat().st_size > 65536:
        raise ValueError('Local LLM configuration exceeds 64 KiB')
    entries = {}
    for line in source.read_text(encoding='utf-8-sig').splitlines():
        text = line.strip()
        if not text or text.startswith('#'):
            continue
        if text.startswith('export '):
            text = text[7:].strip()
        key, sep, value = text.partition('=')
        key = key.strip()
        if not sep or key not in LLM_KEYS:
            continue
        value = value.strip()
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError('Malformed quoted local LLM setting')
            value = value[1:-1]
        else:
            value = value.split(' #', 1)[0].rstrip()
        # No variable interpolation, shell execution, escapes or arbitrary env loading.
        entries[key] = value
    loaded = []
    for key, value in entries.items():
        if key not in env:
            env[key] = value
            loaded.append(key)
    return tuple(loaded)

load_llm_env()
