"""Disposable, synthetic authenticated fixture for the optional browser smoke test."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import os
os.environ['COPILOT_AUTH_MODE']='authenticated'
from tests.auth_support import setup_identity,attach_server
from http.server import ThreadingHTTPServer

class Fixture:
    def __init__(self):self.cleanups=[]
    def addCleanup(self,fn):self.cleanups.append(fn)

if __name__=='__main__':
    fixture=Fixture();setup_identity(fixture);attach_server(fixture)
    from copilot.server import Handler
    print('Disposable authenticated UI fixture ready',flush=True)
    try:ThreadingHTTPServer(('127.0.0.1',8124),Handler).serve_forever()
    finally:
        for fn in reversed(fixture.cleanups):fn()
