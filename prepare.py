"""Create a separate study from a bundled real index, then freeze its partitions.

Researcher entry point. Configure config/ before running this command.
The output workspace excludes full histories, examples and researcher-only files.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from core.prepare import ROOT, digest


def prepare_example(example, workspace, holdout, csv_path=None):
    workspace, holdout = Path(workspace).resolve(), Path(holdout).resolve()
    for path in (workspace, holdout):
        if path.exists():
            raise ValueError(f"Use a new directory: {path}")
        if path.is_relative_to(ROOT.resolve()):
            raise ValueError("Study and holdout must be outside the distribution repository")
    if workspace.is_relative_to(holdout) or holdout.is_relative_to(workspace):
        raise ValueError("Study and holdout must be separate directories")
    source = Path(csv_path).resolve() if csv_path else ROOT / 'data' / example / 'prices.csv'
    if csv_path:
        if not source.is_file():
            raise ValueError('CSV source does not exist')
    else:
        manifest = json.loads((source.parent / 'manifest.json').read_text())
        if digest(source) != manifest['sha256']:
            raise ValueError('Bundled data checksum mismatch')
    workspace.mkdir(parents=True)
    for name in ('core', 'config', 'strategy'):
        shutil.copytree(ROOT / name, workspace / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('run.py', 'program.md', 'AGENTS.md', 'README.md', 'README.zh-CN.md', 'LICENSE', '.gitignore'):
        shutil.copy2(ROOT / name, workspace / name)
    subprocess.run([sys.executable, '-B', '-m', 'core.prepare', '--csv', str(source),
                    '--holdout-dir', str(holdout)], cwd=workspace, check=True)
    print(json.dumps({'example': example, 'workspace': str(workspace),
                      'holdout': str(holdout), 'next': 'Run your coding agent in the study workspace.'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--example', choices=('csi300', 'sp500'))
    source.add_argument('--csv', type=Path)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--holdout-dir', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    holdout = args.holdout_dir or workspace.with_name(workspace.name + '-holdout')
    prepare_example(args.example, workspace, holdout, args.csv)


if __name__ == '__main__':
    main()
