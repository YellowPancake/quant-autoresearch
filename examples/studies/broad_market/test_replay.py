"""Guard source-level replay against stale inputs, bad orders and future leakage."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import replay
from engine import features


class ReplayTests(unittest.TestCase):
    def test_modified_source_is_rejected_before_fitting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'strategy.py').write_text('changed')
            (root / 'manifest.json').write_text(json.dumps({'files': {
                'strategy.py': hashlib.sha256(b'original').hexdigest()}}))
            with patch.object(replay, 'HERE', root):
                with self.assertRaisesRegex(ValueError, 'Published input changed'):
                    replay.verify_inputs()

    def test_wrong_execution_date_fails_even_with_matching_nav(self):
        attempt, partition = '0162', 'test'
        metrics = json.loads((replay.REFERENCE / 'results.json').read_text())['results'][attempt][partition]
        curve = [{'date': r['date'], 'equity': float(r['equity'])}
                 for r in replay.read_csv(replay.REFERENCE / 'archived_equity.csv')
                 if r['attempt'] == attempt and r['partition'] == partition]
        orders = [r for r in json.loads((replay.REFERENCE / 'orders.json').read_text())
                  if r['attempt'] == attempt and r['partition'] == partition]
        orders[0]['execution_date'] = orders[0]['signal_date']
        with self.assertRaisesRegex(ValueError, 'execution_date differs'):
            replay.check_replay(attempt, partition, metrics, curve, orders)

    def test_future_quotes_do_not_change_past_features(self):
        n = 320
        prices = pd.DataFrame({'a': 100 + np.arange(n) * .1 + np.sin(np.arange(n)),
                               'b': 90 + np.arange(n) * .2},
                              index=pd.bdate_range('2018-01-01', periods=n))
        prices.iloc[12, 0] = np.nan
        prefix = features(prices.iloc[:280])
        prices.iloc[280:] *= 100
        extended = features(prices)
        for key in prefix:
            np.testing.assert_allclose(prefix[key], extended[key][:280], equal_nan=True, rtol=0, atol=1e-12)

    def test_output_cannot_overwrite_published_sources(self):
        with self.assertRaisesRegex(ValueError, 'write replay outputs under results'):
            replay.replay(['frozen'], ['test'], replay.HERE)


if __name__ == '__main__':
    unittest.main()
