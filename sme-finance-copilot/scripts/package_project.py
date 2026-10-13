"""Package source and verification evidence; exclude credentials and runtime stores."""
from pathlib import Path
import hashlib
import zipfile

def package():
    root=Path(__file__).resolve().parents[1]
    destination=root.parent/'downloads' if (root.parent/'downloads').is_dir() else root.parent
    output=destination/'SME-Finance-Copilot-v1.2-FinTechathon.zip'
    excluded={'__pycache__','logs','.test_logs','.pytest_cache','.git','.venv','.publish'}
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if not path.is_file() or any(p in excluded for p in path.relative_to(root).parts):continue
            if path.name.startswith('ui-ledger') or path.name=='.env' or (path.name.startswith('.env.') and path.name!='.env.example'):continue
            if path.suffix in {'.zip','.pyc','.sqlite','.sqlite3','.db'} or path.name.endswith(('-wal','-shm')):continue
            archive.write(path,Path(root.name)/path.relative_to(root))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise RuntimeError('ZIP integrity check failed')
        names=archive.namelist()
        for required in ['copilot/auth.py','copilot/migrations/001_identity.sql','web/login.html','web/users.html','web/security.html','tests/test_authentication.py']:
            assert f'{root.name}/{required}' in names,required
    print(f'ZIP: {output}\nFiles: {len(names)}\nSHA-256: {hashlib.sha256(output.read_bytes()).hexdigest()}\nIntegrity: verified')

if __name__=='__main__':package()
