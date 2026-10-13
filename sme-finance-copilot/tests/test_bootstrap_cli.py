"""Scripted bootstrap uses a secret environment value, never a password argument."""
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from copilot.auth import AuthStore, main

class BootstrapCLI(unittest.TestCase):
    def test_environment_password_bootstrap_and_no_secret_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'identity.sqlite3')
            secret='Scripted-Test-Password-123'
            args=['auth','bootstrap','--database',path,'--username','admin','--email','admin@example.test','--password-env','TEST_BOOTSTRAP_SECRET']
            output=io.StringIO()
            with patch('sys.argv',args),patch.dict(os.environ,{'TEST_BOOTSTRAP_SECRET':secret}),contextlib.redirect_stdout(output):
                main()
                self.assertNotIn('TEST_BOOTSTRAP_SECRET',os.environ)
            self.assertNotIn(secret,output.getvalue())
            store=AuthStore(path,{'M002'})
            token=store.login('admin',secret)[0]
            self.assertEqual(store.principal(token).role,'security_admin')
            self.assertEqual(store.principal(token).merchant_ids,set())

    def test_missing_environment_password_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'identity.sqlite3')
            args=['auth','bootstrap','--database',path,'--username','admin','--email','admin@example.test','--password-env','TEST_ABSENT_SECRET']
            with patch('sys.argv',args),patch.dict(os.environ,{},clear=True),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):main()
            store=AuthStore(path,{'M002'})
            with store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)
