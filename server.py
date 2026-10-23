from catalog import search_catalog, search_source, fetch
from contextlib import contextmanager
import datetime as dt
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import urllib.parse as up
import urllib.request as ur
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).parent
DB = Path(os.environ.get('AFTERGLOW_DB', str(ROOT / 'data' / 'library.sqlite3')))
TYPES = ['movie', 'tv', 'variety', 'book', 'game', 'album']
TOKEN = secrets.token_urlsafe(24)

@contextmanager
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=15)
    try:
        c.execute('CREATE TABLE IF NOT EXISTS works (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
        with c:
            yield c
    finally:
        c.close()

def records():
    with connect() as c:
        return [json.loads(r[0]) for r in c.execute('SELECT body FROM works')]

def validate(item):
    if not isinstance(item, dict):
        raise ValueError('记录格式不正确')
    result = {k: str(item.get(k, '')).strip() for k in ['id', 'title', 'category', 'date', 'year', 'creator', 'cover', 'source', 'sourceId', 'url', 'note', 'edition', 'language', 'isbn']}
    if not result['title'] or len(result['title']) > 300 or result['category'] not in TYPES:
        raise ValueError('请填写作品名称并选择正确分类')
    try:
        result['date'] = dt.date.fromisoformat(result['date']).isoformat()
    except ValueError:
        raise ValueError('标记日期不正确')
    if any(len(v) > 10000 for v in result.values()):
        raise ValueError('记录内容过长')
    for k in ['url', 'cover']:
        if result[k] and up.urlparse(result[k]).scheme not in ['http', 'https']:
            raise ValueError('链接必须以 http 或 https 开头')
    result['id'] = result['id'] or str(uuid.uuid4())
    return result

def save(items, merge=False):
    clean = [validate(i) for i in items]
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        existing = [json.loads(r[0]) for r in c.execute('SELECT body FROM works')]
        count = 0
        for item in clean:
            duplicate = next((x for x in existing if x['category'] == item['category'] and ((item['sourceId'] and x['source'] == item['source'] and x['sourceId'] == item['sourceId']) or (not item['sourceId'] and x['title'].casefold() == item['title'].casefold()))), None)
            if merge and (duplicate or any(x['id'] == item['id'] for x in existing)):
                continue
            if duplicate and duplicate['id'] != item['id']:
                raise ValueError('这部作品已在书架中，请打开原记录编辑')
            c.execute('INSERT OR REPLACE INTO works VALUES (?, ?)', (item['id'], json.dumps(item, ensure_ascii=False)))
            existing = [x for x in existing if x['id'] != item['id']] + [item]
            count += 1
    return count

class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, mime='application/json; charset=utf-8'):
        payload = json.dumps(data, ensure_ascii=False).encode() if not isinstance(data, bytes) else data
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        url = up.urlparse(self.path)
        try:
            if url.path == '/api/records':
                return self.send(200, {'records': records(), 'token': TOKEN})
            if url.path == '/api/info':
                addresses = sorted({x[4][0] for x in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET) if not x[4][0].startswith('127.')})
                return self.send(200, {'urls': [f'http://{ip}:{self.server.server_port}' for ip in addresses]})
            if url.path == '/api/export':
                return self.send(200, {'app': 'afterglow', 'version': 1, 'exportedAt': dt.datetime.now().isoformat(), 'records': records()})
            if url.path == '/api/search':
                p = up.parse_qs(url.query)
                q, category = p.get('q', [''])[0].strip(), p.get('category', ['movie'])[0]
                if not q or len(q) > 150 or category not in TYPES:
                    raise ValueError('请输入 1–150 字的关键词')
                alternate = p.get('alternate', [''])[0].strip()
                if len(alternate) > 150:
                    raise ValueError('其他译名最多 150 字')
                return self.send(200, search_catalog(q, category, alternate))
            files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/stats.js': 'stats.js'}
            if url.path in files:
                mime = {'/': 'text/html', '/app.js': 'text/javascript', '/style.css': 'text/css', '/stats.js': 'text/javascript'}[url.path]
                return self.send(200, (ROOT / 'public' / files[url.path]).read_bytes(), mime+'; charset=utf-8')
            self.send(404, {'error': '未找到页面'})
        except ValueError as e:
            self.send(400, {'error': str(e)})
        except Exception:
            self.send(500, {'error': '读取失败，请检查本地数据文件或稍后重试'})

    def do_POST(self):
        if self.headers.get('X-App-Token') != TOKEN:
            return self.send(403, {'error': '请刷新页面后重试'})
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 10_000_000:
                raise ValueError('文件为空或超过 10 MB')
            body = json.loads(self.rfile.read(size))
            if self.path == '/api/records':
                count = save([body])
            elif self.path == '/api/import':
                if not isinstance(body, dict) or body.get('app') != 'afterglow' or body.get('version') != 1 or not isinstance(body.get('records'), list):
                    raise ValueError('请选择由余味导出的 JSON 备份')
                count = save(body['records'], merge=True)
            elif self.path == '/api/delete':
                with connect() as c:
                    c.execute('DELETE FROM works WHERE id=?', (body['id'],))
                count = 1
            else:
                return self.send(404, {'error': '接口不存在'})
            self.send(200, {'count': count})
        except (ValueError, KeyError, TypeError) as e:
            self.send(400, {'error': str(e)})
        except Exception:
            self.send(500, {'error': '保存失败，原有记录未被清空，请检查磁盘空间'})

if __name__ == '__main__':
    with connect():
        pass
    port = int(os.environ.get('PORT', '8765'))
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'Afterglow: http://localhost:{port}', flush=True)
    server.serve_forever()
