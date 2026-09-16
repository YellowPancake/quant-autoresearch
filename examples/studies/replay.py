"""Offline replay of published, already disclosed research examples (not a new test)."""
import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.evaluate import load_module


# Execution math preserved from the frozen study evaluator.
def simulate(strategy, train, rows, config):
    state = strategy.fit(train)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["date"]].append(row)
    prior, equity, peak, drawdown = {}, 1.0, 1.0, 0.0
    returns, turnovers = [], []
    for day in sorted(grouped):
        batch = grouped[day]
        labels = {r["symbol"]: r["forward_return"] for r in batch}
        observations = [{k: r[k] for k in ("date", "symbol", "history")} for r in batch]
        for observation, row in zip(observations, batch):
            if "history_bars" in row:
                observation["history_bars"] = row["history_bars"]
        weights = strategy.allocate(observations, state)
        if not isinstance(weights, dict) or set(weights) - set(labels):
            raise ValueError("allocate must return weights for observable symbols only")
        weights = {s: float(w) for s, w in weights.items()}
        if any(not math.isfinite(w) or w < 0 for w in weights.values()) or sum(weights.values()) > 1 + 1e-9:
            raise ValueError("Weights must be finite, long-only, and sum <= 1")
        symbols = set(prior) | set(weights)
        buys = sum(max(weights.get(s, 0) - prior.get(s, 0), 0) for s in symbols)
        sells = sum(max(prior.get(s, 0) - weights.get(s, 0), 0) for s in symbols)
        cost = buys * config["execution"]["buy_cost"] + sells * config["execution"]["sell_cost"]
        gross = sum(w * labels[s] for s, w in weights.items())
        # Proportional transaction-cost convention, then market move.
        net = (1 - cost) * (1 + gross) - 1
        if not math.isfinite(net) or net <= -1:
            raise ValueError("Invalid portfolio return")
        returns.append(net)
        turnovers.append(buys + sells)
        equity *= 1 + net
        peak = max(peak, equity)
        drawdown = max(drawdown, 1 - equity / peak)
        # Drift weights to next opening before computing the next rebalance.
        prior = {s: w * (1 + labels[s]) / (1 + gross) for s, w in weights.items()}
    if not returns:
        raise ValueError("No evaluation dates")
    # Liquidate terminal holdings; costs included in the final daily return.
    liquidation = sum(prior.values()) * config["execution"]["sell_cost"]
    equity *= 1 - liquidation
    returns[-1] = (1 + returns[-1]) * (1 - liquidation) - 1
    turnovers[-1] += sum(prior.values())
    drawdown = max(drawdown, 1 - equity / peak)
    sd = statistics.stdev(returns) if len(returns) > 1 else 0
    return {"days": len(returns), "total_return": equity - 1,
            "annual_return": equity ** (252 / len(returns)) - 1,
            "sharpe": statistics.mean(returns) / sd * math.sqrt(252) if sd > 1e-12 else 0.0,
            "max_drawdown": drawdown, "mean_turnover": statistics.mean(turnovers)}

class BuyAndHold:
    @staticmethod
    def fit(train):
        return None

    @staticmethod
    def allocate(observations, state):
        return {observations[0]["symbol"]: 1.0}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path, history_days):
    with path.open(newline="") as f:
        bars = list(csv.DictReader(f))
    bars.sort(key=lambda r: r['date'])
    assert len({r['date'] for r in bars}) == len(bars)
    assert len({r['index_id'] for r in bars}) == 1
    for row in bars:
        for key in ('open', 'high', 'low', 'close'):
            row[key] = float(row[key])
        for key in ('volume_native', 'amount_native'):
            row[key] = float(row[key]) if row[key] else None
    result = []
    for i in range(history_days-1, len(bars)-2):
        history = bars[i-history_days+1:i+1]
        result.append({'symbol':bars[i]['index_id'], 'date':bars[i]['date'],
                       'history':[r['close'] for r in history], 'history_bars':history,
                       'forward_return':bars[i+2]['open']/bars[i+1]['open']-1,
                       'label_end':bars[i+2]['date']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', choices=['csi300','sp500'], required=True)
    parser.add_argument('--strategy', choices=['frozen','posthoc','baseline','all'], default='all')
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent/args.market
    study = json.loads((folder/'study.json').read_text())
    source = ROOT/study['data_file']
    if sha(source) != study['data_sha256']:
        raise ValueError('Bundled source differs from the published study snapshot')
    rows = records(source, study['history_days'])
    parts = {}
    for name, period in study['time_protocol']['periods'].items():
        parts[name] = [r for r in rows if period['start'] <= r['date'] <= r['label_end'] <= period['end']]
    config = study['original_research_config']
    roles = ['frozen','posthoc','baseline'] if args.strategy=='all' else [args.strategy]
    for role in roles:
        expected = study['strategies'][role]
        if role=='baseline':
            strategy = BuyAndHold
        else:
            source = folder/expected['file']
            if sha(source) != expected['strategy_sha256']:
                raise ValueError('Published strategy source changed: '+role)
            strategy = load_module(source)
        for partition in ['validation','test']:
            actual = simulate(strategy, parts['train'], parts[partition], config)
            for key,value in expected[partition].items():
                if not math.isclose(actual[key],value,rel_tol=1e-9,abs_tol=1e-11):
                    raise AssertionError((role,partition,key,actual[key],value))
            print(json.dumps({'market':args.market,'strategy':role,'attempt':expected['attempt'],
                              'partition':partition,'matches_published_metrics':True,'metrics':actual}),flush=True)


if __name__=='__main__':
    main()
