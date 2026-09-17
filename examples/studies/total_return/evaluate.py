"""Revalue fixed historical decisions under one total-return accounting convention."""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEE = 0.0003
PERIODS = {'validation': ('2020-01-01', '2022-12-31'),
           'test': ('2023-01-01', '2026-09-11')}
FROZEN = {'csi300': '0178', 'sp500': '0215', 'broad_market': '0478'}


def read_csv(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with path.open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def simulate(prices, orders, fee=FEE):
    """Orders are target weights keyed by execution date, after that day's return.

    Prices must be dividend-reinvested closes. Missing marks carry for valuation
    only; an archived execution without a real quote is rejected. No final sale.
    """
    cash, holdings, marks, curve = 1.0, {}, {}, []
    assert set(orders) <= {r['date'] for r in prices}
    for row in prices:
        day = row['date']
        current = {k: float(v) for k, v in row.items() if k != 'date' and v != ''}
        assert all(math.isfinite(v) and v > 0 for v in current.values())
        for symbol in holdings:
            if symbol in current:
                holdings[symbol] *= current[symbol] / marks[symbol]
        marks.update(current)
        if day in orders:
            weights = orders[day]
            assert all(math.isfinite(w) and w >= 0 for w in weights.values())
            assert sum(weights.values()) <= 1 + 1e-10
            needed = {s for s, v in holdings.items() if v > 1e-15} | {s for s, w in weights.items() if w > 0}
            assert needed <= current.keys(), (day, needed - current.keys())
            symbols = sorted(holdings.keys() | weights.keys())
            gross = cash + sum(holdings.values())
            net = gross
            for _ in range(12):
                net = gross - fee * sum(abs(net * weights.get(s, 0) - holdings.get(s, 0)) for s in symbols)
            after = {s: net * weights.get(s, 0) for s in symbols}
            cost = fee * sum(abs(after[s] - holdings.get(s, 0)) for s in symbols)
            cash = gross - sum(after.values()) - cost
            assert cash >= -1e-9
            cash = max(0.0, cash)
            holdings = {s: v for s, v in after.items() if v > 0}
        curve.append({'date': day, 'equity': cash + sum(holdings.values())})
    assert curve[0]['equity'] == 1.0
    return curve


def metrics(curve):
    values = [r['equity'] for r in curve]
    peak, dd = 1.0, 0.0
    for value in values:
        peak = max(peak, value)
        dd = max(dd, 1 - value / peak)
    years = (date.fromisoformat(curve[-1]['date']) - date.fromisoformat(curve[0]['date'])).days / 365.2425
    return {'days': len(curve), 'total_return': values[-1] - 1,
            'annual_return': values[-1] ** (1 / years) - 1, 'max_drawdown': dd}


def assess(market, result):
    annual, dd = result['annual_return'], result['max_drawdown']
    if market == 'csi300':
        feasible, reached, reward, limit = dd < .5, result['total_return'] >= 1, result['total_return'], .5
    elif market == 'sp500':
        feasible, reached, reward, limit = dd <= .5, annual >= .6, annual, .5
    else:
        limit = min(.5, .2634 + (annual - .2) / 2)
        feasible, reached, reward = dd <= limit + 1e-12 and dd <= .5, annual >= .3, annual
    return {'reward': reward, 'feasible': feasible, 'target_met': feasible and reached, 'drawdown_limit': limit}


def evaluate(market):
    folder = HERE / market
    manifest = json.loads((HERE / 'manifest.json').read_text())
    for name, expected in manifest['inputs'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    data = HERE / 'data' / ('spy_total_return.csv' if market == 'sp500' else 'china_total_return.csv')
    assert hashlib.sha256(data.read_bytes()).hexdigest() == manifest['data'][data.name]['sha256']
    prices = read_csv(data)
    assert [r['date'] for r in prices] == sorted({r['date'] for r in prices})
    by_partition = {p: [r for r in prices if start <= r['date'] <= end] for p, (start, end) in PERIODS.items()}
    all_orders = defaultdict(dict)
    if market == 'broad_market':
        for order in json.loads((folder / 'orders.json').read_text()):
            assert order['signal_date'] < order['execution_date']
            key = order['attempt'], order['partition']
            assert order['execution_date'] not in all_orders[key]
            all_orders[key][order['execution_date']] = order['weights']
    else:
        grouped = defaultdict(list)
        for row in read_csv(folder / 'signals.csv'):
            grouped[row['attempt'], row['partition']].append(row)
        for key, signals in grouped.items():
            panel = by_partition[key[1]]
            assert [r['date'] for r in signals] == [r['date'] for r in panel]
            all_orders[key] = {panel[i + 1]['date']: {market: float(r['weight'])}
                               for i, r in enumerate(signals[:-1])}
    attempts = sorted({key[0] for key in all_orders})
    results, curves = {}, {}
    for attempt in attempts:
        results[attempt] = {}
        for partition in PERIODS:
            curve = simulate(by_partition[partition], all_orders[attempt, partition])
            curves[attempt, partition] = curve
            results[attempt][partition] = metrics(curve)
    if market == 'broad_market':
        # A second implementation must reproduce all 18 archived paths, not just endpoints.
        expected = read_csv(folder / 'archived_equity.csv')
        actual = {(a, p, r['date']): r['equity'] for (a, p), curve in curves.items() for r in curve}
        assert len(expected) == len(actual)
        delta = max(abs(actual[r['attempt'], r['partition'], r['date']] - float(r['equity'])) for r in expected)
        assert delta < 1e-11, delta
        print('All broad-market archived daily NAVs reproduced; max error', delta)
    baselines = ('csi300', 'growth') if market == 'broad_market' else (market,)
    baseline_metrics = {}
    for symbol in baselines:
        baseline_metrics[symbol] = {}
        for partition, panel in by_partition.items():
            curve = simulate(panel, {panel[1]['date']: {symbol: 1.0}})
            curves['baseline_' + symbol, partition] = curve
            baseline_metrics[symbol][partition] = metrics(curve)
    posthoc = max(attempts, key=lambda a: results[a]['test']['total_return'])
    summary = {'market': market, 'accounting': 'total_return_next_close_v1',
        'return_instrument': 'SPY dividend-adjusted ETF proxy' if market == 'sp500' else 'CSI total-return indices / dividend-adjusted ETF proxies',
        'data_file': str(data.relative_to(HERE)), 'data_sha256': hashlib.sha256(data.read_bytes()).hexdigest(),
        'fee_per_side': FEE, 'periods': PERIODS, 'milestone_count': len(attempts),
        'frozen_attempt': FROZEN[market], 'posthoc_attempt': posthoc,
        'results': results, 'baselines': baseline_metrics,
        'assessments': {a: {p: assess(market, m) for p, m in parts.items()} for a, parts in results.items()}}
    (folder / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    write_csv(folder / 'equity.csv', [{'attempt': a, 'partition': p, **r} for (a, p), curve in curves.items() for r in curve])
    write_csv(folder / 'stages.csv', [{'attempt': a, **{p + '_' + k: v for p in PERIODS for k, v in results[a][p].items()}} for a in attempts])
    print(market, 'post hoc', posthoc, results[posthoc]['test'], 'frozen', results[FROZEN[market]]['test'], 'baselines', baseline_metrics)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', choices=list(FROZEN), required=True)
    evaluate(parser.parse_args().market)
