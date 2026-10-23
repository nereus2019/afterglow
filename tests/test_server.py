import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
import server

class LibraryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = server.DB
        server.DB = Path(self.temp.name) / 'library.sqlite3'
        self.item = dict(title='空之轨迹 FC', category='game', date='2026-10-23', source='Bangumi', sourceId='123')

    def tearDown(self):
        server.DB = self.old
        self.temp.cleanup()

    def test_save_edit_and_duplicate(self):
        server.save([self.item])
        saved = server.records()[0]
        self.assertEqual(saved['title'], self.item['title'])
        with self.assertRaises(ValueError):
            server.save([self.item])
        saved['note'] = '非常喜欢'
        server.save([saved])
        self.assertEqual(len(server.records()), 1)
        self.assertEqual(server.records()[0]['note'], '非常喜欢')

    def test_merge_and_atomic_validation(self):
        server.save([self.item])
        self.assertEqual(server.save([self.item], merge=True), 0)
        second = dict(self.item, title='SC', sourceId='456')
        with self.assertRaises(ValueError):
            server.save([second, dict(second, date='bad')], merge=True)
        self.assertEqual(len(server.records()), 1)
        self.assertEqual(server.save([second], merge=True), 1)

    def test_url_validation(self):
        with self.assertRaises(ValueError):
            server.save([dict(self.item, cover='javascript:alert(1)')])

    def test_http_roundtrip(self):
        http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{http.server_port}'
        def request(path, data=None, authorized=True):
            headers = {'Content-Type': 'application/json'}
            if authorized:
                headers['X-App-Token'] = server.TOKEN
            req = urllib.request.Request(base+path, data=json.dumps(data).encode() if data else None, headers=headers)
            with urllib.request.urlopen(req) as r:
                return json.load(r)
        try:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                request('/api/records', self.item, False)
            self.assertEqual(caught.exception.code, 403)
            request('/api/records', self.item)
            backup = request('/api/export')
            saved = backup['records'][0]
            request('/api/delete', {'id': saved['id']})
            self.assertEqual(request('/api/records')['records'], [])
            self.assertEqual(request('/api/import', backup)['count'], 1)
            self.assertEqual(request('/api/records')['records'][0], saved)
        finally:
            http.shutdown()
            http.server_close()

if __name__ == '__main__':
    unittest.main()
