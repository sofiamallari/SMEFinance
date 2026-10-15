"""Container lifecycle only: scoped ownership, privilege drop, explicit CNY seed."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
from contextlib import closing
from decimal import Decimal

NAME = 'shenzhen_cny_demo'
MERCHANTS = {'M001', 'M002', 'M003', 'M004', 'M005', 'M006'}


class DeploymentError(RuntimeError):
    pass


def configuration():
    from copilot.demo_environment import configure_storage
    root = configure_storage(require_ready=False)
    flag = os.environ.get('COPILOT_INITIALIZE_CNY', 'no').lower()
    if flag not in ('yes', 'no'):
        raise DeploymentError('COPILOT_INITIALIZE_CNY must be yes or no')
    secret = os.environ.get('COPILOT_APPROVAL_SECRET', '')
    if len(secret) < 32 or secret.lower().startswith(('replace', '<', 'example')):
        raise DeploymentError('Configure a private stable COPILOT_APPROVAL_SECRET of at least 32 characters')
    os.environ.setdefault('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8000'))
    if not 1 <= port <= 65535:
        raise DeploymentError('PORT must be between 1 and 65535')
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_ENVIRONMENT_ID'):
        if root != Path('/data') / NAME:
            raise DeploymentError('Railway deployment requires COPILOT_DATA_DIR=/data/shenzhen_cny_demo')
        if os.environ.get('COPILOT_HTTPS') != 'yes' or os.environ['HOST'] != '0.0.0.0':
            raise DeploymentError('Railway requires COPILOT_HTTPS=yes and HOST=0.0.0.0')
    return root, flag == 'yes'


def reject_links(root):
    # Inspect the lexical path before resolving: never chown a symlink target.
    lexical = Path(os.environ.get('COPILOT_DATA_DIR', str(root))).absolute()
    for part in (lexical, *lexical.parents):
        if part.is_symlink():
            raise DeploymentError('Data directory must not traverse symbolic links')
    if root.exists():
        for current, directories, files in os.walk(root, followlinks=False):
            for name in directories + files:
                path = Path(current) / name
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                    raise DeploymentError('Data directory contains a symbolic link or special file; inspect storage')
                if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
                    raise DeploymentError('Data directory contains a hard-linked file; inspect storage')


def prepare_identity(root):
    reject_links(root)
    if os.name == 'posix' and os.geteuid() == 0:
        import pwd
        account = pwd.getpwnam('appuser')
        # Root privileges may touch only this dedicated child of the volume.
        if root != Path('/data') / NAME or Path('/data').is_symlink():
            raise DeploymentError('Privileged ownership preparation is restricted to /data/shenzhen_cny_demo')
        root.mkdir(mode=0o700, parents=False, exist_ok=True)
        for current, directories, files in os.walk(root, followlinks=False):
            for path in [Path(current), *(Path(current) / name for name in files)]:
                os.chown(path, account.pw_uid, account.pw_gid, follow_symlinks=False)
                os.chmod(path, 0o700 if path.is_dir() else 0o600, follow_symlinks=False)
        os.setgroups([])
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
        os.environ['HOME'] = account.pw_dir
    if os.name == 'posix' and os.geteuid() == 0:
        raise DeploymentError('Application must not run as root')
    os.umask(0o077)


def verify_existing(root):
    """Read-only preflight; no AuthStore construction, migrations or recovery."""
    reject_links(root)
    for name in ('dataset.json', 'identity.sqlite3', 'transactions.jsonl', 'audit.jsonl', 'execution.jsonl'):
        if not (root / name).is_file():
            raise DeploymentError('Dataset is incomplete; missing ' + name + '. Inspect or restore matching storage; do not reseed')
    marker = json.loads((root / 'dataset.json').read_text(encoding='utf-8'))
    if marker.get('dataset') != NAME or marker.get('synthetic') is not True or marker.get('version') != 1:
        raise DeploymentError('Unexpected dataset metadata; operator review required')
    with closing(sqlite3.connect((root / 'identity.sqlite3').as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise DeploymentError('SQLite integrity verification failed')
        mids = {r[0] for r in db.execute('SELECT merchant_id FROM merchant_profiles')}
        roles = {r[0] for r in db.execute('SELECT role FROM users')}
        if mids != MERCHANTS or not {'SYSTEM_ADMIN', 'SME_OWNER', 'SME_STAFF', 'BANK'} <= roles:
            raise DeploymentError('Expected six-merchant/four-role dataset is incomplete')
        for table, column in (('applications', 'packet'), ('simulated_payment_state', 'state_json')):
            if any(json.loads(r[0]).get('currency') != 'CNY' for r in db.execute('SELECT ' + column + ' FROM ' + table)):
                raise DeploymentError('Existing financial data is not CNY; refusing startup')
        for row in db.execute('SELECT config_json FROM merchant_transaction_settings'):
            if json.loads(row[0]).get('base_currency') != 'CNY':
                raise DeploymentError('Existing merchant currency configuration is not CNY')
    transactions = {}; batches = {}
    with (root / 'transactions.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            body = {k: v for k, v in event.items() if k != 'checksum'}
            checksum = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
            if event.get('action') != 'canonical_batch' or event.get('checksum') != checksum or event.get('merchant') not in MERCHANTS:
                raise DeploymentError('Canonical transaction ledger verification failed')
            bid = event['batch_id']
            if bid in batches and batches[bid] != checksum:
                raise DeploymentError('Conflicting canonical ledger batches')
            batches[bid] = checksum
            for row in event['transactions']:
                if row.get('currency') != 'CNY' or row.get('merchant_id') != event['merchant'] or not Decimal(row['amount']).is_finite():
                    raise DeploymentError('Invalid canonical CNY transaction')
                tid = row['transaction_id']
                if tid in transactions and transactions[tid] != row:
                    raise DeploymentError('Conflicting canonical transaction identifiers')
                transactions[tid] = row
    if not transactions:
        raise DeploymentError('Expected seeded canonical ledger is empty')


def initialize_or_reuse(root, initialize):
    if (root / 'dataset.json').exists():
        if initialize:
            raise DeploymentError('Dataset already initialized. Set COPILOT_INITIALIZE_CNY=no and remove the seed password; no data was reseeded')
        verify_existing(root)
    else:
        if root.exists() and any(root.iterdir()):
            raise DeploymentError('Partial dataset found. Preserve it for inspection; automatic retry/overwrite is prohibited')
        if not initialize:
            raise DeploymentError('Dataset missing. Explicit first initialization requires COPILOT_INITIALIZE_CNY=yes and a private seed password')
        password = os.environ.get('COPILOT_CNY_DEMO_PASSWORD', '')
        if not (12 <= len(password) <= 256 and any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password)):
            raise DeploymentError('First initialization requires a private 12-256 character seed password with upper/lowercase letters and digits')
        # The existing seeder enforces password policy, permissions and confirmations.
        subprocess.run([sys.executable, '-m', 'copilot.cny_demo', 'seed'], check=True)
        subprocess.run([sys.executable, '-m', 'copilot.cny_demo', 'verify'], check=True)
        verify_existing(root)
        print('CNY initialization verified. Remove the initialization flag and seed-password service variable before the next restart.', flush=True)
    os.environ.pop('COPILOT_CNY_DEMO_PASSWORD', None)


def main():
    try:
        root, initialize = configuration()
        prepare_identity(root)
        initialize_or_reuse(root, initialize)
    except DeploymentError as exc:
        print('Deployment preparation stopped: ' + str(exc), file=sys.stderr, flush=True)
        return 1
    except Exception:
        # Configuration/seed errors can contain sensitive source input: never echo them.
        print('Deployment preparation failed. Check configuration, initialization flag and storage integrity; preserve partial data. See docs/operations/railway.md.', file=sys.stderr, flush=True)
        return 1
    print('Storage preflight passed; starting authenticated server' + (' as non-root.' if os.name == 'posix' else ' for local Windows verification.'), flush=True)
    if os.name == 'nt':
        from copilot.server import main as serve
        serve()
        return 0
    os.execvpe(sys.executable, [sys.executable, '-m', 'copilot.server'], os.environ)


if __name__ == '__main__':
    sys.exit(main())
