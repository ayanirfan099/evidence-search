import json,tempfile,unittest
from pathlib import Path
from engine import EvidenceSearch,ROOT,chunk_file

class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=EvidenceSearch()
    def test_specific_retrieval(self):
        results=self.engine.search('HTTP 429 Retry-After')['results']
        self.assertEqual(results[0]['source'],'api-limits.md')
    def test_citations_are_exact(self):
        for result in self.engine.search('invoice refund',10)['results']:
            lines=(ROOT/'data/docs'/result['source']).read_text().splitlines()
            self.assertEqual(result['excerpt'],'\n'.join(lines[result['start_line']-1:result['end_line']]))
    def test_unknown_query_returns_nothing(self):
        self.assertFalse(self.engine.search('zxqv zxqv')['has_matches'])
    def test_stopwords_return_nothing(self):
        self.assertFalse(self.engine.search('the and of')['has_matches'])
    def test_invalid_requests(self):
        for query in ['',None,'a'*513]:
            with self.assertRaises(ValueError):self.engine.search(query)
        for k in [0,11,True,1.5]:
            with self.assertRaises(ValueError):self.engine.search('invoice',k)
    def test_empty_corpus(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):EvidenceSearch(folder)
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'linked.md').symlink_to(ROOT/'data/docs/billing.md')
            with self.assertRaises(ValueError):EvidenceSearch(path)
    def test_deterministic_ranking(self):
        self.assertEqual(self.engine.search('refund invoice'),self.engine.search('refund invoice'))
    def test_retrieval_evaluation(self):
        report=self.engine.evaluate(json.loads((ROOT/'data/queries.json').read_text()))
        self.assertEqual(report['queries'],12);self.assertGreaterEqual(report['hit_rate_at_3'],0.5)

if __name__=='__main__':unittest.main()
