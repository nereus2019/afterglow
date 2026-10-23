import unittest
from unittest.mock import patch
import catalog

class CatalogTest(unittest.TestCase):
    def test_traditional_and_alias_correction(self):
        result = catalog.variants('全能读者视角', 'Omniscient Reader')
        self.assertIn('全知读者视角', result)
        self.assertIn('Omniscient Reader', result)
        if catalog.os.name == 'nt':
            self.assertIn('全知讀者視角', result)
            self.assertEqual(catalog.chinese('垃圾場'), '垃圾场')

    def test_only_exact_match_expands_aliases(self):
        with patch.object(catalog, 'search_source', return_value=[{'title': '不相关的书', 'sourceId': '1'}]), patch.object(catalog, 'fetch') as fetch:
            self.assertEqual(catalog.book_aliases('全知读者视角'), [])
            fetch.assert_not_called()
        with patch.object(catalog, 'search_source', return_value=[{'title': '全知读者视角', 'sourceId': '1'}]), patch.object(catalog, 'fetch', return_value={'name':'전지적 독자 시점','infobox':[{'key':'别名','value':[{'v':'Omniscient Reader'}]}]}):
            self.assertIn('Omniscient Reader', catalog.book_aliases('全知读者视角'))

    def test_publisher_preserves_volumes_and_excludes_merchandise(self):
        base = {'images':[], 'permalink':'https://example.com/book', 'attributes':[{'name':'語言','terms':[{'name':'繁體中文'}]}]}
        products = [dict(base,id=i,name=n) for i,n in enumerate(['全知讀者視角01','全知讀者視角02','全知讀者視角01+02套書','全知讀者視角徽章','【預購】全知讀者視角03（已截止）'])]
        with patch.object(catalog, 'fetch', return_value=products):
            rows = catalog.search_source('深空出版','全知读者视角','book')
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[2]['edition'],'套书（多册合一）')
        self.assertNotEqual(rows[0]['sourceId'],rows[1]['sourceId'])

    def test_partial_failure_and_cross_variant_dedup(self):
        def source(name, q, category):
            if name == 'Open Library':
                raise OSError('offline')
            return [dict(title='全知讀者視角'+v,sourceId=v,year='',creator='',cover='',url='https://example.com',edition='单册') for v in ['02','01']]
        with patch.object(catalog,'book_aliases',return_value=['English title']), patch.object(catalog,'search_source',side_effect=source):
            d = catalog.search_catalog('全能读者视角','book')
        self.assertEqual(len(d['results']),4)  # Two distinct volumes per source; variants merge.
        self.assertEqual(d['results'][0]['title'],'全知讀者視角01')
        self.assertEqual(d['results'][0]['source'],'深空出版')
        self.assertTrue(d['warnings'])
        self.assertIn('English title',d['queries'])

    def test_same_album_title_keeps_different_artists(self):
        entries = [{'id':'a','title':'垃圾场','first-release-date':'1994','score':100,'artist-credit':[{'name':'何勇'}]},
                   {'id':'b','title':'垃圾场','first-release-date':'2026-05-20','score':100,'artist-credit':[{'name':'劣'}]},
                   {'id':'c','title':'不相关','score':20}]
        with patch.object(catalog,'fetch',return_value={'release-groups':entries}):
            rows=catalog.search_source('MusicBrainz','垃圾场','album')
        self.assertEqual([(x['year'],x['creator']) for x in rows],[('1994','何勇'),('2026','劣')])
        self.assertEqual(len(catalog.merge_results([dict(x,source='MusicBrainz') for x in rows])),2)
