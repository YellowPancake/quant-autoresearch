"""Prepare real datasets without evaluating strategies or inspecting test labels."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.prepare import ROOT


class ExampleTests(unittest.TestCase):
    def test_bundled_and_custom_data_create_separate_studies(self):
        with tempfile.TemporaryDirectory() as temp:
            for example in ('csi300', 'sp500', 'custom'):
                with self.subTest(example=example):
                    workspace = Path(temp) / example
                    source_args = (['--csv', str(ROOT / 'data/sp500/prices.csv')] if example == 'custom'
                                   else ['--example', example])
                    cmd = [sys.executable, '-B', 'prepare.py', *source_args, '--workspace', str(workspace)]
                    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse((workspace / 'data').exists())
                    self.assertFalse((workspace / 'cache/test.json').exists())
                    self.assertTrue((workspace.with_name(workspace.name + '-holdout') / 'test.json').exists())
                    manifest = json.loads((workspace / 'cache/manifest.json').read_text())
                    self.assertFalse(manifest['synthetic'])
                    self.assertTrue(all(n > 0 for n in manifest['counts']))
                    # A repeated command must not overwrite an existing study.
                    repeated = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(repeated.returncode, 0)


if __name__ == '__main__':
    unittest.main()
