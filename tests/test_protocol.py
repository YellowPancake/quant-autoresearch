import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.evaluate import simulate
from core.prepare import ROOT, demo, load_panel, split_records, protocol_split


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = json.loads((ROOT / "config/research.json").read_text())

    def test_fixed_time_boundaries(self):
        self.config['split'] = protocol_split(json.loads((ROOT / 'config/time.json').read_text()))
        demo(self.base / 'prices.csv')
        rows = load_panel(self.base / 'prices.csv', 30)
        parts = split_records(rows, self.config)
        for name, part in zip(('train', 'validation', 'test'), parts):
            period = self.config['split']['periods'][name]
            for row in part:
                self.assertLessEqual(period['start'], row['date'])
                self.assertLessEqual(row['label_end'], period['end'])
        self.assertEqual([{r['symbol'] for r in part} for part in parts],
                         [{r['symbol'] for r in rows}] * 3)
        extra = [{'date': d, 'label_end': e} for d, e in [
            ('2019-12-31', '2020-01-02'), ('2022-12-30', '2023-01-03'),
            ('2026-09-11', '2026-09-14'), ('2009-12-30', '2010-01-04')]]
        self.assertEqual(parts, split_records(rows + extra, self.config))
        for method in ('symbol', 'stock'):
            with self.assertRaises(ValueError):
                protocol_split({'method': method})
        bad = copy.deepcopy(self.config['split'])
        bad['periods']['validation']['start'] = '2019-12-31'
        with self.assertRaises(ValueError):
            protocol_split(bad)
        with self.assertRaises(ValueError):
            protocol_split(dict(self.config['split'], ratios=[.7, .1, .2]))
        for field in ('entry_lag_sessions', 'holding_sessions'):
            with self.assertRaisesRegex(ValueError, 'next-open'):
                protocol_split(dict(self.config['split'], **{field: 2}))

    def test_open_execution_and_costs(self):
        path = self.base / "tiny.csv"
        path.write_text("date,symbol,open,close\n2020-01-01,A,10,11\n2020-01-02,A,20,21\n2020-01-03,A,30,31\n2020-01-04,A,60,61\n")
        rows = load_panel(path, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["history"], [11, 21])
        self.assertEqual(rows[0]["forward_return"], 1.0)  # 60/30, not 30/20
        path.write_text(path.read_text().replace('date,symbol,open,close', 'date,index_id,open,close'))
        self.assertEqual(load_panel(path, 2), rows)
        self.config["execution"] = {"buy_cost": 0.01, "sell_cost": 0.02}
        def allocate(obs, state):
            self.assertNotIn("forward_return", obs[0])
            return {"A": 1}
        m = simulate(SimpleNamespace(fit=lambda train: None, allocate=allocate), [], rows, self.config)
        self.assertAlmostEqual(m["total_return"], 0.99 * 2 * 0.98 - 1)

    def test_end_to_end_budget_freeze_and_holdout(self):
        repo = self.base / "repo"
        shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns("cache", "runs", "store", "experiments", "artifacts", "__pycache__", ".git"))
        config = copy.deepcopy(self.config)
        config["constraints"]["max_drawdown"] = 1
        config["target"]["reward_at_least"] = 1e9
        config["budget"]["max_experiments"] = 2
        (repo / "config/research.json").write_text(json.dumps(config))
        # Deterministic feasible all-cash strategy for protocol assertions.
        (repo / "strategy/strategy.py").write_text("from core.indicators import sma\ndef fit(train): return None\ndef allocate(obs, state):\n    assert sma(obs[0]['history'], 5)[-1] is not None\n    return {}\n")
        holdout = self.base / "heldout"
        def command(*args, ok=True):
            p = subprocess.run([sys.executable, "-B", *args], cwd=repo, capture_output=True, text=True, timeout=30)
            self.assertEqual(p.returncode == 0, ok, p.stdout + p.stderr)
            return p
        rejected = command('-m', 'core.prepare', '--demo', '--holdout-dir', str(repo / 'holdout'), ok=False)
        self.assertIn('outside the research workspace', rejected.stderr)
        self.assertFalse((repo / 'cache').exists())
        demo(repo / 'source.csv')
        rejected = command('-m', 'core.prepare', '--csv', str(repo / 'source.csv'),
                           '--holdout-dir', str(holdout), ok=False)
        self.assertIn('outside the research workspace', rejected.stderr)
        (repo / 'source.csv').unlink()
        self.assertFalse((repo / 'cache').exists())
        command("-m", "core.prepare", "--demo", "--holdout-dir", str(holdout))
        self.assertFalse((repo / "cache/test.json").exists())
        # Directory moves must not weaken the frozen evaluation boundary.
        for name in ('config/time.json', 'config/reward.py', 'config/research.json',
                     'core/evaluate.py', 'core/indicators.py', 'core/__init__.py', 'AGENTS.md', 'run.py'):
            path = repo / name
            original = path.read_bytes()
            path.write_bytes(original + b'\n')
            result = command('run.py', ok=False)
            self.assertIn('Frozen file changed', result.stderr)
            path.write_bytes(original)
        command("run.py")
        self.assertEqual(json.loads((repo / "runs/0001/result.json").read_text())["status"], "keep")
        (repo / "strategy/strategy.py").write_text("raise RuntimeError('intentional crash')\n")
        command("run.py")
        self.assertEqual(json.loads((repo / "runs/0002/result.json").read_text())["status"], "crash")
        self.assertEqual((repo / "strategy/strategy.py").read_bytes(), (repo / "runs/best.py").read_bytes())
        command("run.py", ok=False)  # Failed attempts consume the budget.
        command("run.py", "--freeze")
        command("run.py", ok=False)
        args = ("-m", "core.evaluate", "--candidate", "runs/best.py", "--test-dir", str(holdout), "--output", str(self.base / "result.json"))
        command(*args)
        self.assertEqual(json.loads((self.base / "result.json").read_text())["partition"], "test")
        command(*args, ok=False)
        (repo / "config/reward.py").write_text("def reward(m): return 100000\n")
        command("run.py", ok=False)


if __name__ == "__main__":
    unittest.main()
