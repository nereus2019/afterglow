"""Public catalog adapters. Search results always come from remote records."""
import concurrent.futures
import ctypes
from functools import lru_cache
import html
import json
import os
import re
import threading
import time
import urllib.parse as up
import urllib.request as ur

_cache = {}
_lock = threading.Lock()
_host_locks = {}
_last_request = {}
SOURCES = {'book': ['Bangumi', '深空出版', 'Open Library'],
           'album': ['MusicBrainz', 'iTunes', 'Bangumi']}

@lru_cache(maxsize=2048)
def chinese(text, traditional=False):
    if os.name != 'nt':
        return text
    mapper = ctypes.windll.kernel32.LCMapStringEx
    mapper.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_wchar_p, ctypes.c_int,
                       ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ssize_t]
    mapper.restype = ctypes.c_int
    flag = 0x04000000 if traditional else 0x02000000
    size = mapper('zh-CN', flag, text, -1, None, 0, None, None, 0)
    if not size:
        return text
    buffer = ctypes.create_unicode_buffer(size)
    mapper('zh-CN', flag, text, -1, buffer, size, None, None, 0)
    return buffer.value

def normalize(text):
    return re.sub(r'\s+', '', chinese(text).casefold())

def unique(values):
    return list(dict.fromkeys(x.strip() for x in values if x and x.strip()))

def variants(query, alternate=''):
    # A documented correction, not generated catalog data. Other aliases are read
    # from Bangumi's infobox or supplied explicitly by the user.
    corrected = chinese(query).replace('全能读者视角', '全知读者视角')
    return unique([corrected, chinese(corrected, True), query, alternate])[:4]

def fetch(url, data=None):
    key = (url, json.dumps(data, sort_keys=True))
    host = up.urlparse(url).hostname
    with _lock:
        host_lock = _host_locks.setdefault(host, threading.Lock())
    # Serialize each service, including repeated requests from multiple devices.
    with host_lock:
        now = time.monotonic()
        cached = _cache.get(key)
        if cached and now - cached[0] < 600:
            return cached[1]
        delay = 1.05 - (now - _last_request.get(host, 0))
        if delay > 0:
            time.sleep(delay)
        _last_request[host] = time.monotonic()
        req = ur.Request(url, data=json.dumps(data).encode() if data else None,
                         headers={'User-Agent': 'AfterglowLocal/1.1 (personal local media catalog)',
                                  'Content-Type': 'application/json'})
        with ur.urlopen(req, timeout=9) as r:
            result = json.load(r)
        with _lock:
            if len(_cache) >= 256:
                _cache.pop(next(iter(_cache)))
            _cache[key] = (time.monotonic(), result)
        return result

def bangumi_item(x):
    return dict(title=x.get('name_cn') or x['name'], year=(x.get('date') or '')[:4],
                creator=x.get('name', ''), cover=(x.get('images') or {}).get('large', ''),
                sourceId=str(x['id']), url=f"https://bgm.tv/subject/{x['id']}",
                edition=x.get('platform', ''), language='', isbn='')

def search_source(source, q, category):
    if source == 'Bangumi':
        types = {'movie': [2, 6], 'tv': [2, 6], 'variety': [6], 'book': [1], 'game': [4], 'album': [3]}
        d = fetch('https://api.bgm.tv/v0/search/subjects?limit=50',
                  {'keyword': q, 'sort': 'match', 'filter': {'type': types[category]}})
        return [bangumi_item(x) for x in d.get('data', [])]
    if source == 'Open Library':
        query = 'title:' + q if len(q) < 3 else q
        d = fetch('https://openlibrary.org/search.json?' + up.urlencode(
            {'q': query, 'limit': 50, 'fields': 'key,title,author_name,first_publish_year,cover_i,language'}))
        return [dict(title=x['title'], year=str(x.get('first_publish_year', '')),
                     creator=', '.join(x.get('author_name', [])),
                     cover=f"https://covers.openlibrary.org/b/id/{x['cover_i']}-M.jpg" if x.get('cover_i') else '',
                     sourceId=x['key'], url='https://openlibrary.org'+x['key'],
                     language=', '.join(x.get('language', [])[:4]), edition='书目 / 请核对小说或漫画') for x in d.get('docs', [])]
    if source == '深空出版':
        d = fetch('https://www.starwatcher.com.tw/wp-json/wc/store/v1/products?' + up.urlencode(
            {'search': chinese(q, True), 'per_page': 100, 'orderby': 'title', 'order': 'asc'}))
        items = []
        for x in d:
            title = html.unescape(x['name'])
            attrs = {a['name']: ' / '.join(t['name'] for t in a.get('terms', [])) for a in x.get('attributes', [])}
            if '語言' not in attrs or any(k in title for k in ['已截止', '預購', '吊飾', '壓克力', '明信片', '立牌', '徽章', '掛軸']):
                continue
            bundle = any(k in title for k in ['套書', '+', '＋'])
            edition = '套书（多册合一）' if bundle else '特装 / 珍藏版' if any(k in title for k in ['特裝', '珍藏']) else '单册'
            images = x.get('images') or []
            items.append(dict(title=title, year='', creator=attrs.get('作者', '深空出版'),
                              cover=images[0]['src'] if images else '', sourceId=str(x['id']), url=x['permalink'],
                              language=attrs.get('語言', ''), edition=edition,
                              isbn=attrs.get('ISBN', '')))
        return items
    if source.startswith('iTunes'):
        country = 'US' if source == 'iTunes US' else 'TW'
        d = fetch('https://itunes.apple.com/search?' + up.urlencode(
            {'term': q, 'entity': 'album', 'country': country, 'limit': 50}))
        return [dict(title=x['collectionName'], year=x.get('releaseDate', '')[:4],
                     creator=x.get('artistName', ''), cover=x.get('artworkUrl100', '').replace('100x100', '600x600'),
                     sourceId=str(x['collectionId']), url=x.get('collectionViewUrl', ''), edition='iTunes '+country)
                for x in d.get('results', [])]
    if source == 'MusicBrainz':
        # Plain search supports artist + title; dismax escapes query operators.
        d = fetch('https://musicbrainz.org/ws/2/release-group/?' + up.urlencode(
            {'query': q, 'dismax': 'true', 'fmt': 'json', 'limit': 50}))
        return [dict(title=x['title'], year=x.get('first-release-date', '')[:4],
                     creator=''.join(a.get('name', '') + a.get('joinphrase', '') for a in x.get('artist-credit', [])),
                     cover=f"https://coverartarchive.org/release-group/{x['id']}/front-250",
                     sourceId=x['id'], url=f"https://musicbrainz.org/release-group/{x['id']}",
                     edition=x.get('primary-type', '音乐发行')) for x in d.get('release-groups', []) if int(x.get('score', 100)) >= 60]
    if source != 'Wikipedia':
        raise ValueError('未知搜索来源')
    d = fetch('https://zh.wikipedia.org/w/api.php?' + up.urlencode(
        {'action': 'query', 'generator': 'search', 'gsrsearch': q, 'gsrlimit': 20,
         'prop': 'pageimages|description', 'piprop': 'thumbnail', 'pithumbsize': 400, 'format': 'json'}))
    return [dict(title=x['title'], year='', creator=x.get('description', ''),
                 cover=x.get('thumbnail', {}).get('source', ''), sourceId=str(x['pageid']),
                 url='https://zh.wikipedia.org/?curid='+str(x['pageid']))
            for x in sorted(d.get('query', {}).get('pages', {}).values(), key=lambda x: x.get('index', 0))]

def book_aliases(query):
    """Only expand aliases from an exact title match, never an unrelated hit."""
    matches = search_source('Bangumi', query, 'book')
    exact = next((x for x in matches if normalize(x['title']) == normalize(query)), None)
    if not exact:
        return []
    d = fetch('https://api.bgm.tv/v0/subjects/' + exact['sourceId'])
    names = [d.get('name', '')]
    for field in d.get('infobox', []):
        if field['key'] == '别名':
            values = field.get('value', [])
            names.extend([x.get('v', '') for x in values if isinstance(x, dict)] if isinstance(values, list) else [values])
    # Prefer an English catalog title, then the original language.
    return sorted(unique(names), key=lambda s: not bool(re.search(r'[A-Za-z]{3}', s)))[:2]

def result_key(item):
    return (item['source'], item['sourceId'])

def merge_results(items):
    merged = {}
    for item in items:
        merged.setdefault(result_key(item), item)
    return list(merged.values())

def search_catalog(q, category, alternate=''):
    queries = variants(q, alternate)
    notes = []
    if chinese(q) != queries[0]:
        notes.append('已同时检索常用名称：' + queries[0])
    aliases = []
    if category == 'book':
        try:
            aliases = book_aliases(queries[0])
        except Exception:
            notes.append('暂未取得原名 / 英文别名；可在“其他译名”中补充')
    sources = SOURCES.get(category, ['Bangumi', 'Wikipedia'])
    jobs = {}
    for source in sources:
        terms = queries[:2]
        if alternate:
            terms = unique(terms + [alternate])
        if source == 'Open Library':
            terms = unique(terms + aliases)
        if source == '深空出版':
            terms = unique([chinese(queries[0], True), chinese(alternate, True) if alternate else ''])
        if source == 'MusicBrainz':
            terms = unique([queries[0], alternate])
        jobs[source] = terms
    if category == 'album':
        jobs['iTunes US'] = unique([queries[0], alternate])

    def run_source(source, terms):
        found, failures, successes = [], [], 0
        for term in terms:
            try:
                rows = search_source(source, term, category)
                successes += 1
                found.extend(dict(x, source='iTunes' if source.startswith('iTunes') else source,
                                  category=category) for x in rows)
            except Exception:
                failures.append(term)
        return found, failures, successes

    results, warnings, status = [], [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {pool.submit(run_source, s, terms): s for s, terms in jobs.items()}
        for task in concurrent.futures.as_completed(tasks):
            source = tasks[task]
            found, failures, successes = task.result()
            results.extend(found)
            status.append({'source': source, 'count': len(merge_results(found)),
                           'state': 'partial' if failures and successes else 'error' if failures else 'ok'})
            if failures:
                warnings.append(source + (' 部分查询失败' if successes else ' 暂时无法连接'))
    results = merge_results(results)
    needles = [normalize(x) for x in unique(queries+aliases)]
    def rank(x):
        title = normalize(x['title'])
        relevant = any(n in title for n in needles)
        volume = re.search(r'\d+', x['title'])
        return (not relevant, 0 if x['source'] == '深空出版' and x.get('edition') == '单册' else 1,
                x['source'] == 'Wikipedia', int(volume[0]) if volume and category == 'book' else 0,
                x['title'], x['source'], x['sourceId'])
    results.sort(key=rank)
    return {'results': results, 'warnings': warnings, 'notes': notes,
            'queries': unique([term for terms in jobs.values() for term in terms]),
            'sources': sorted(status, key=lambda x: x['source'])}
