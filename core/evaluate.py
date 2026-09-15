"""Fixed evaluator; minimal long-only open-to-open simulation, not a live broker."""
import argparse
import importlib.util
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from core.prepare import ROOT, digest, dump


def load_module(path):
    # Compile source directly: no stale .pyc after rapid agent edits.
    spec = importlib.util.spec_from_file_location("candidate", path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(Path(path).read_text(), str(path), "exec"), module.__dict__)
    return module


def verify():
    if not (ROOT / "cache/manifest.json").exists():
        raise ValueError("Research workspace is not sealed; researcher must prepare data and finalize policy first")
    manifest = json.loads((ROOT / "cache/manifest.json").read_text())
    for group, base in (("files", ROOT), ("data", ROOT / "cache")):
        for name, expected in manifest[group].items():
            if digest(base / name) != expected:
                raise ValueError(f"Frozen file changed: {name}")
    return manifest


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


def assess(candidate, rows, config):
    train = json.loads((ROOT / "cache/train.json").read_text())
    metrics = simulate(load_module(candidate), train, rows, config)
    policy = load_module(ROOT / "config/reward.py")
    score = float(policy.reward(metrics))
    if not math.isfinite(score) or any(not math.isfinite(v) for v in metrics.values()):
        raise ValueError("Non-finite metrics/reward")
    feasible = bool(policy.constraints(metrics, config))
    return {"metrics": metrics, "reward": score, "feasible": feasible,
            "target_met": feasible and bool(policy.target(metrics, score, config))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--test-dir", type=Path)
    args = p.parse_args()
    manifest = verify()
    config = json.loads((ROOT / "config/research.json").read_text())
    if args.test_dir:
        # Researcher-only endpoint. An exclusive marker prevents accidental repeat
        # testing even on crashes. OS access control is a deployment responsibility.
        frozen = json.loads((ROOT / "runs/frozen.json").read_text())
        if digest(args.candidate) != frozen["strategy_sha256"]:
            raise ValueError("Test candidate is not the frozen champion")
        if digest(ROOT / "cache/manifest.json") != frozen["manifest_sha256"]:
            raise ValueError("Manifest changed after freezing")
        if json.loads((args.test_dir / "manifest.json").read_text()) != manifest:
            raise ValueError("Holdout protocol mismatch")
        if digest(args.test_dir / "test.json") != manifest["test_sha256"]:
            raise ValueError("Holdout changed")
        with (args.test_dir / "TEST_USED.json").open("x") as f:
            json.dump(frozen, f)
        rows = json.loads((args.test_dir / "test.json").read_text())
    else:
        rows = json.loads((ROOT / "cache/validation.json").read_text())
    result = assess(args.candidate, rows, config)
    result["partition"] = "test" if args.test_dir else "validation"
    dump(args.output, result)


if __name__ == "__main__":
    main()
