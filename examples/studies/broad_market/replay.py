"""Refit the two published broad-market strategies and verify their original results.

No network, strategy search, or archived-order input is used to generate decisions.
The archived orders and curves are read only after simulation, as verification data.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from engine import load_strategy, simulate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REFERENCE = HERE.parent / 'total_return' / 'broad_market'
TOLERANCE = 1e-8


def read_csv(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def verify_inputs():
    manifest = json.loads((HERE / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        actual = hashlib.sha256((HERE / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Published input changed: {name}')
    prices = pd.read_csv(HERE / 'data/prices.csv', index_col='date', parse_dates=True)
    meta = json.loads((HERE / 'data/universe.json').read_text())
    if not prices.index.is_unique or not prices.index.is_monotonic_increasing:
        raise ValueError('Invalid session ordering')
    if set(prices.columns) != set(meta) or sum(m['selectable'] for m in meta.values()) != 24:
        raise ValueError('Universe differs from the published 24-asset pool')
    # Prove that the newly supplied training/warmup panel uses the same evaluation prices.
    published = pd.read_csv(REFERENCE.parent / 'data/china_total_return.csv', index_col='date', parse_dates=True)
    pd.testing.assert_frame_equal(prices.loc[published.index], published, check_exact=True)
    return manifest, prices, meta


def check_replay(attempt, partition, metrics, curve, trades):
    expected_metrics = json.loads((REFERENCE / 'results.json').read_text())['results'][attempt][partition]
    for key, expected in expected_metrics.items():
        if not math.isclose(metrics[key], expected, rel_tol=0, abs_tol=TOLERANCE):
            raise ValueError(f'{attempt}/{partition}: {key} differs: {metrics[key]} != {expected}')
    expected_curve = [r for r in read_csv(REFERENCE / 'archived_equity.csv')
                      if r['attempt'] == attempt and r['partition'] == partition]
    if [r['date'] for r in curve] != [r['date'] for r in expected_curve]:
        raise ValueError(f'{attempt}/{partition}: daily calendar differs')
    max_nav_error = max(abs(r['equity'] - float(e['equity'])) for r, e in zip(curve, expected_curve))
    if max_nav_error > TOLERANCE:
        raise ValueError(f'{attempt}/{partition}: daily NAV differs by {max_nav_error}')
    expected_orders = [r for r in json.loads((REFERENCE / 'orders.json').read_text())
                       if r['attempt'] == attempt and r['partition'] == partition]
    if len(trades) != len(expected_orders):
        raise ValueError(f'{attempt}/{partition}: order count differs')
    max_weight_error = 0.0
    for order, expected in zip(trades, expected_orders):
        for key in ('signal_date', 'execution_date'):
            if order[key] != expected[key]:
                raise ValueError(f'{attempt}/{partition}: {key} differs')
        if set(order['weights']) != set(expected['weights']):
            raise ValueError(f'{attempt}/{partition}: selected assets differ')
        for symbol, weight in order['weights'].items():
            error = abs(weight - expected['weights'][symbol])
            max_weight_error = max(error, max_weight_error)
            if error > TOLERANCE:
                raise ValueError(f'{attempt}/{partition}: {symbol} weight differs by {error}')
    return dict(verified=True, daily_nav_rows=len(curve), orders=len(trades),
                max_nav_error=max_nav_error, max_weight_error=max_weight_error)


def replay(roles, partitions, output):
    output = output.resolve()
    if output == ROOT or (ROOT in output.parents and ROOT / 'results' not in output.parents):
        raise ValueError('Inside this repository, write replay outputs under results/ only.')
    manifest, prices, meta = verify_inputs()
    reports, curves, orders = [], [], []
    for role in roles:
        selection = manifest['roles'][role]
        attempt = selection['attempt']
        for partition in partitions:
            start, end = manifest['periods'][partition]
            # Fresh module/state per partition; engine.fit sees only 2010–2019.
            metrics, curve, trades = simulate(load_strategy(HERE / selection['file']), prices,
                                             meta, start, end, fee=manifest['fee_per_side'])
            verification = check_replay(attempt, partition, metrics, curve, trades)
            reports.append(dict(role=role, attempt=attempt, partition=partition,
                                metrics=metrics, verification=verification))
            curves.extend(dict(attempt=attempt, partition=partition, **r) for r in curve)
            orders.extend(dict(attempt=attempt, partition=partition, **r) for r in trades)
            print(f'#{int(attempt)} {role:7s} {partition:10s}: return {metrics["total_return"]:.2%}, '
                  f'CAGR {metrics["annual_return"]:.2%}, max drawdown {metrics["max_drawdown"]:.2%}; '
                  f'{len(trades)} orders / {len(curve)} daily NAVs verified', flush=True)
    # No output is labeled successful until every requested simulation has passed.
    output.mkdir(parents=True, exist_ok=True)
    summary = {'verified': True, 'tolerance': TOLERANCE,
               'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__},
               'manifest_sha256': hashlib.sha256((HERE / 'manifest.json').read_bytes()).hexdigest(),
               'results': reports}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    write_csv(output / 'equity.csv', curves)
    (output / 'orders.json').write_text(json.dumps(orders, indent=2, allow_nan=False) + '\n')
    lines = ['# Verified broad-market strategy replay', '',
             'Strategies refitted from training prices; orders and daily NAV independently regenerated.', '',
             '#478 is the frozen champion; #162 is the post-hoc test comparison.', '']
    for r in reports:
        m = r['metrics']
        lines += [f'- #{int(r["attempt"])} / {r["partition"]}: return **{m["total_return"]:.2%}**, '
                  f'CAGR **{m["annual_return"]:.2%}**, maximum drawdown **{m["max_drawdown"]:.2%}**.']
    lines += ['', '[Full metrics and verification](summary.json) · [Daily NAV](equity.csv) · [Orders](orders.json)', '']
    (output / 'README.md').write_text('\n'.join(lines))
    print(f'All requested results verified. Files: {output}', flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strategy', choices=['all', 'frozen', 'posthoc'], default='all')
    parser.add_argument('--partition', choices=['all', 'validation', 'test'], default='all')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/broad-market')
    args = parser.parse_args()
    replay(['frozen', 'posthoc'] if args.strategy == 'all' else [args.strategy],
           ['validation', 'test'] if args.partition == 'all' else [args.partition], args.output)
