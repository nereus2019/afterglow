"""Verify the distributable from a fresh extraction, on a separate port."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import zipfile

root = Path(__file__).resolve().parents[1]
archive_path = root / 'dist' / 'Afterglow-Windows-x64-v1.1.zip'
with zipfile.ZipFile(archive_path) as archive:
    assert not any('/data/' in n or n.endswith('.log') or '/.git/' in n for n in archive.namelist())
    with tempfile.TemporaryDirectory(prefix='portable-test-', dir=root / 'build') as folder:
        archive.extractall(folder)
        app = Path(folder) / 'Afterglow-Windows-x64-v1.1'
        runtime = app / 'runtime' / 'python.exe'
        subprocess.run([str(runtime), '-X', 'utf8', '-c', 'import sqlite3, ssl, server; print("Bundled runtime, SQLite, SSL and app imports: OK")'], cwd=app, check=True)
        env = dict(os.environ, PORT='18765')
        env.pop('AFTERGLOW_DB', None)
        launch = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(app / 'start.ps1'), '-NoBrowser']
        base = 'http://127.0.0.1:18765'
        def api(path, body=None, token=''):
            req = urllib.request.Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                headers={'Content-Type': 'application/json', 'X-App-Token': token})
            with urllib.request.urlopen(req, timeout=35) as r:
                return json.load(r)
        try:
            subprocess.run(launch, env=env, cwd=app, check=True, timeout=35)
            initial = api('/api/records')
            assert initial['records'] == []
            token = initial['token']
            api('/api/records', {'title': '便携版测试', 'category': 'game', 'date': '2026-10-23'}, token)
            backup = api('/api/export')
            assert len(backup['records']) == 1
            api('/api/delete', {'id': backup['records'][0]['id']}, token)
            assert api('/api/import', backup, token)['count'] == 1
            subprocess.run(launch, env=env, cwd=app, check=True, timeout=35)
            assert len(api('/api/records')['records']) == 1
            with urllib.request.urlopen(base) as page:
                assert page.status == 200 and '余味' in page.read().decode()
            print('Portable launcher, empty initial library, save/export/restore and repeated launch: PASS')
        finally:
            subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(app / 'stop.ps1')], cwd=app, check=True)
        try:
            urllib.request.urlopen(base, timeout=2)
        except OSError:
            print('Portable stop launcher: PASS')
        else:
            raise AssertionError('Test server is still running')
print('Distribution contains no personal data or logs: PASS')
