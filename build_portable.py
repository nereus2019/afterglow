"""Build from a verified official Python embeddable download, using an allowlist."""
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).parent.resolve()
DOWNLOAD = ROOT / 'build' / 'python-embed.zip'
EXPECTED = '9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38'
NAME = 'Afterglow-Windows-x64-v1.1'
STAGE = ROOT / 'build' / NAME
OUTPUT = ROOT / 'dist' / (NAME + '.zip')

if hashlib.sha256(DOWNLOAD.read_bytes()).hexdigest() != EXPECTED:
    raise SystemExit('Python download SHA-256 does not match the official release.')
STAGE.mkdir(parents=True, exist_ok=False)
with zipfile.ZipFile(DOWNLOAD) as package:
    package.extractall(STAGE / 'runtime')
pth = STAGE / 'runtime' / 'python313._pth'
pth.write_text(pth.read_text() + '\n..\n', encoding='utf-8')
for name in ['server.py', 'catalog.py', 'start.ps1', 'stop.ps1', '启动余味.cmd', '停止余味.cmd', '便携版使用说明.txt', 'README.md']:
    shutil.copy2(ROOT / name, STAGE / name)
shutil.copytree(ROOT / 'public', STAGE / 'public')
(STAGE / 'RUNTIME-SOURCE.txt').write_text(
    'Python 3.13.17 Windows embeddable x64\n'
    'https://www.python.org/downloads/release/python-31317/\n'
    'https://www.python.org/ftp/python/3.13.17/python-3.13.17-embed-amd64.zip\n'
    'Original archive SHA256: ' + EXPECTED + '\n'
    'Only modification: add parent application folder to python313._pth.\n', encoding='utf-8')
OUTPUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(STAGE.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(STAGE.parent))
digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
OUTPUT.with_suffix('.sha256.txt').write_text(digest + '  ' + OUTPUT.name + '\n')
print(OUTPUT)
print(f'{OUTPUT.stat().st_size / 1024 / 1024:.1f} MB; SHA256 {digest}')
