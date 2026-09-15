"""Researcher runs once. Freeze protocol and materialize disjoint partitions."""
import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXED = ("config/research.json", "config/reward.py", "config/time.json",
         "core/__init__.py", "core/budget.py", "core/indicators.py", "core/prepare.py", "core/evaluate.py", "core/run.py",
         "run.py", "program.md", "AGENTS.md")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def protocol_split(policy):
    if policy.get("method") != "time" or "ratios" in policy or "seed" in policy:
        raise ValueError("Only fixed calendar time periods are supported")
    if policy.get("entry_lag_sessions", 1) != 1 or policy.get("holding_sessions", 1) != 1:
        raise ValueError("This evaluator supports next-open entry and one-session holding only")
    periods = policy["periods"]
    previous_end = None
    for name in ("train", "validation", "test"):
        start, end = (date.fromisoformat(periods[name][k]) for k in ("start", "end"))
        if start > end or (previous_end and start != previous_end + timedelta(days=1)):
            raise ValueError("Time periods must be ordered, non-overlapping and contiguous")
        previous_end = end
    return {"method": "time", "periods": periods}


def split_records(rows, config):
    split = protocol_split(config["split"])
    output = []
    for name in ("train", "validation", "test"):
        period = split["periods"][name]
        part = []
        for row in rows:
            day = date.fromisoformat(row["date"]).isoformat()
            label_end = date.fromisoformat(row["label_end"]).isoformat()
            if label_end < day:
                raise ValueError("Label realization precedes signal")
            if period["start"] <= day <= label_end <= period["end"]:
                part.append(row)
        if not part:
            raise ValueError("Empty " + name + " partition after fixed-date filtering and purging")
        output.append(part)
    return output


def load_panel(path, history_days):
    if history_days < 2:
        raise ValueError("history_days must be >= 2")
    by_symbol = defaultdict(list)
    seen = set()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            day = date.fromisoformat(row["date"]).isoformat()
            symbol = (row.get("symbol") or row.get("index_id") or "").strip()
            key = (day, symbol)
            if not symbol or key in seen:
                raise ValueError("Empty symbol or duplicate date/symbol")
            seen.add(key)
            opening, close = float(row["open"]), float(row["close"])
            if not all(math.isfinite(x) and x > 0 for x in (opening, close)):
                raise ValueError("Prices must be finite and positive")
            by_symbol[symbol].append((day, opening, close))
    # Minimal evaluator requires a balanced panel: never silently treat suspensions
    # as one-session returns. Real A-share calendars need a richer execution adapter.
    calendars = [tuple(x[0] for x in sorted(values)) for values in by_symbol.values()]
    if not calendars or any(c != calendars[0] for c in calendars):
        raise ValueError("Demo evaluator requires a balanced panel; missing sessions need an adapter")
    rows = []
    for symbol, values in sorted(by_symbol.items()):
        values.sort()
        for i in range(history_days - 1, len(values) - 2):
            rows.append({"symbol": symbol, "date": values[i][0],
                         "history": [v[2] for v in values[i-history_days+1:i+1]],
                         "label_end": values[i+2][0],
                         "forward_return": values[i+2][1] / values[i+1][1] - 1})
    return sorted(rows, key=lambda r: (r["date"], r["symbol"]))


def demo(path):
    rng = random.Random(71)
    days, current = [], date(2019, 7, 1)
    while current <= date(2023, 6, 1):
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "symbol", "open", "close"])
        for j in range(4):
            price = 100.0
            for day in days:
                opening = price * math.exp(rng.gauss(0, 0.003))
                price = opening * math.exp(rng.gauss(0.0002, 0.012))
                writer.writerow([day, f"SYNTH{j:03}", opening, price])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--holdout-dir", required=True, type=Path)
    args = parser.parse_args()
    args.holdout_dir = args.holdout_dir.resolve()
    if args.holdout_dir.is_relative_to(ROOT.resolve()):
        parser.error("Keep the final holdout outside the research workspace")
    if (ROOT / "cache").exists() or args.holdout_dir.exists():
        parser.error("Use a fresh workspace and a new holdout directory; never re-split a run")
    if args.demo == bool(args.csv):
        parser.error("Choose exactly one of --demo or --csv")
    config = json.loads((ROOT / "config/research.json").read_text())
    if config.get("protocol") != "config/time.json":
        raise ValueError("Use the single config/time.json contract")
    policy = json.loads((ROOT / config["protocol"]).read_text())
    config["split"] = protocol_split(policy)
    if config["history_days"] != policy["history_days"]:
        raise ValueError("history_days must match the time protocol")
    if args.demo:
        # Keep the full synthetic source with the researcher, outside research/data.
        source = args.holdout_dir.parent / (args.holdout_dir.name + "-synthetic.csv")
        if source.exists():
            parser.error("Synthetic source already exists")
        source.parent.mkdir(parents=True, exist_ok=True)
        demo(source)
    else:
        source = args.csv.resolve()
        if source.is_relative_to(ROOT.resolve()):
            parser.error("Keep the full source CSV outside the research workspace")
    parts = split_records(load_panel(source, config["history_days"]), config)
    data = ROOT / "cache"
    data.mkdir()
    args.holdout_dir.mkdir(parents=True)
    for name, rows in zip(("train", "validation"), parts[:2]):
        dump(data / f"{name}.json", rows)
    dump(args.holdout_dir / "test.json", parts[2])
    manifest = {"source_sha256": digest(source), "synthetic": args.demo,
                "split": config["split"], "counts": list(map(len, parts)),
                "files": {name: digest(ROOT / name) for name in FIXED},
                "data": {name: digest(data / name) for name in ("train.json", "validation.json")},
                "test_sha256": digest(args.holdout_dir / "test.json")}
    dump(data / "manifest.json", manifest)
    dump(args.holdout_dir / "manifest.json", manifest)
    print(json.dumps({"counts": manifest["counts"], "split": config["split"], "synthetic": args.demo}))


if __name__ == "__main__":
    main()
