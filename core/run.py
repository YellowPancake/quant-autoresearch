"""One measured attempt per call. The external coding agent owns the idea loop."""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from core.evaluate import verify
from core.budget import attempt_timeout
from core.prepare import ROOT, digest, dump


def run(description, freeze=False):
    verify()
    config = json.loads((ROOT / "config/research.json").read_text())
    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    lock = runs / ".lock"
    # One process at a time, including budget checks and frozen state changes.
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        if (runs / "frozen.json").exists():
            raise ValueError("Research ended: strategy already frozen")
        history = sorted(runs.glob("[0-9]*"))
        completed = [json.loads((p / "result.json").read_text()) for p in history if (p / "result.json").exists()]
        champion_path = runs / "champion.json"
        champion = json.loads(champion_path.read_text()) if champion_path.exists() else None
        if freeze:
            if not champion:
                raise ValueError("No feasible champion to freeze")
            dump(runs / "frozen.json", {"strategy_sha256": digest(runs / "best.py"),
                 "manifest_sha256": digest(ROOT / "cache/manifest.json"), "champion": champion})
            print("Frozen. Researcher may now run the independent test once.")
            return
        timeout = attempt_timeout(config["budget"], runs, len(history))
        if any(r.get("target_met") for r in completed):
            raise ValueError("Validation target reached; freeze the champion")
        attempt = runs / f"{len(history)+1:04d}"
        attempt.mkdir()
        source = (ROOT / "strategy/strategy.py").read_bytes()
        (attempt / "strategy.py").write_bytes(source)
        started = time.monotonic()
        result = {"description": description, "strategy_sha256": digest(attempt / "strategy.py")}
        with (attempt / "log.txt").open("w") as log:
            process = subprocess.Popen([sys.executable, "-B", "-m", "core.evaluate",
                         "--candidate", str(attempt / "strategy.py"),
                         "--output", str(attempt / "metrics.json")],
                        stdout=log, stderr=log, start_new_session=True, cwd=ROOT)
            try:
                code = process.wait(timeout=timeout)
                if code:
                    raise RuntimeError(f"Evaluator exited {code}; see log.txt")
                measured = json.loads((attempt / "metrics.json").read_text())
                verify()
                if digest(attempt / "strategy.py") != result["strategy_sha256"]:
                    raise ValueError("Candidate changed during execution")
                result.update(measured)
                better = measured["feasible"] and (champion is None or
                         (measured["target_met"], measured["reward"]) >
                         (champion["target_met"], champion["reward"]))
                result["status"] = "keep" if better else "discard"
                if better:
                    (runs / "best.py").write_bytes(source)
                    dump(champion_path, result)
            except Exception as exc:
                result.update(status="crash", error=str(exc))
            finally:
                # Also terminate any descendants left behind by a candidate.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
        result["seconds"] = time.monotonic() - started
        dump(attempt / "result.json", result)
        # Restore champion without git reset; never touch unrelated working changes.
        if result["status"] != "keep" and (runs / "best.py").exists():
            (ROOT / "strategy/strategy.py").write_bytes((runs / "best.py").read_bytes())
        print(json.dumps(result, allow_nan=False))
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--description", default="baseline")
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    run(args.description, args.freeze)


if __name__ == "__main__":
    main()
