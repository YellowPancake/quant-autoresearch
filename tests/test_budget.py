import json
import tempfile
import unittest
from pathlib import Path
from core.budget import attempt_timeout, validate_budget

class BudgetTests(unittest.TestCase):
    def test_time_includes_idle_and_caps_last_attempt(self):
        with tempfile.TemporaryDirectory() as t:
            runs=Path(t); budget={'max_experiments':None, 'total_seconds':86400, 'seconds_per_experiment':120}
            self.assertEqual(attempt_timeout(budget,runs,0,now=1000),120)
            self.assertEqual(attempt_timeout(budget,runs,100000,now=87399),1)
            with self.assertRaisesRegex(ValueError,'time budget exhausted'):
                attempt_timeout(budget,runs,100001,now=87400)
            self.assertEqual(json.loads((runs/'session.json').read_text())['started_at'],1000)
    def test_missing_clock_cannot_restart_budget(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'Missing session'):
                attempt_timeout({'max_experiments':None,'total_seconds':2,'seconds_per_experiment':1},Path(t),1,now=10)
    def test_unbounded_and_invalid_rejected(self):
        for budget in ({'max_experiments':None,'seconds_per_experiment':1},
                       {'max_experiments':0,'seconds_per_experiment':1},
                       {'max_experiments':2,'seconds_per_experiment':float('inf')}):
            with self.assertRaises(ValueError): validate_budget(budget)

if __name__=='__main__': unittest.main()
