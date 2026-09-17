"""Rebuild decisions from fixed historical single-index strategies, without retuning."""
import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent))
from core.evaluate import load_module
from replay import records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', choices=['csi300', 'sp500'], required=True)
    args = parser.parse_args()
    folder = HERE / args.market
    old = HERE.parent / args.market
    study = json.loads((old / 'study.json').read_text())
    source = ROOT / study['data_file']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == study['data_sha256']
    original_rows = records(source, study['history_days'])
    train_period = study['time_protocol']['periods']['train']
    train = [r for r in original_rows if train_period['start'] <= r['date'] <= r['label_end'] <= train_period['end']]
    # Signals use the original OHLC/volume data, including the last two sessions.
    with source.open() as f:
        bars = list(csv.DictReader(f))
    for b in bars:
        for key in ('open', 'high', 'low', 'close'):
            b[key] = float(b[key])
        for key in ('volume_native', 'amount_native'):
            b[key] = float(b[key]) if b[key] else None
    histories = {}
    for i in range(study['history_days'] - 1, len(bars)):
        history = bars[i - study['history_days'] + 1:i + 1]
        histories[bars[i]['date']] = dict(date=bars[i]['date'], symbol=bars[i]['index_id'],
            history=[r['close'] for r in history], history_bars=history)
    old_milestones = json.loads((old / 'milestones.json').read_text())['results']
    candidates = [r for r in old_milestones if r['role'] == 'validation_champion']
    with (folder / 'signals.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=['attempt', 'partition', 'date', 'weight'], lineterminator='\n')
        writer.writeheader()
        for candidate in candidates:
            attempt = candidate['attempt']
            path = folder / 'strategies' / f'{attempt}.py'
            assert hashlib.sha256(path.read_bytes()).hexdigest() == candidate['strategy_sha256']
            for partition in ('validation', 'test'):
                strategy = load_module(path)
                state = strategy.fit(train)
                period = study['time_protocol']['periods'][partition]
                for day, observation in histories.items():
                    if not period['start'] <= day <= period['end']:
                        continue
                    weights = strategy.allocate([observation], state)
                    assert isinstance(weights, dict) and not set(weights) - {observation['symbol']}
                    weight = float(weights.get(observation['symbol'], 0))
                    assert 0 <= weight <= 1
                    writer.writerow(dict(attempt=attempt, partition=partition, date=day, weight=weight))
                f.flush()
            print(args.market, attempt, 'signals reconstructed', flush=True)


if __name__ == '__main__':
    main()
