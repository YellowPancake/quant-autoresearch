# Research configuration and evaluation

## Define your study

| Researcher-owned file | What it controls |
|---|---|
| `config/research.json` | Direction, history window, costs, constraint/target parameters and budget |
| `config/reward.py` | Executable `reward`, `constraints` and `target` functions |
| `config/time.json` | Fixed chronological train, validation and final-test periods |

There is no universal reward. The runnable default maximizes validation Sharpe, with
example constraints and a stopping target. Replace these functions with your own
objective before preparation. For example, return `metrics["total_return"]` for reward,
require `metrics["max_drawdown"] < 0.5` for feasibility, and set a separate return target.

The default budget allows 20 attempts. For a 24-hour study without an attempt cap,
replace its `budget` object before preparation:

```json
{
  "max_experiments": null,
  "total_seconds": 86400,
  "seconds_per_experiment": 120
}
```

The clock starts at the first attempt and includes thinking, search and pauses.
Failed attempts consume budget. The runner limits evaluation time; API spending
and the agent's own runtime limits belong to the external client.

## Research and final evaluation

The default date ranges are train 2010–2019, validation 2020–2022, and final test
2023–2026-09-11. These are editable study settings, not a prescribed benchmark.
Earlier history can warm up later partitions; labels crossing a partition end are purged.

`fit(train)` receives training labels. `allocate(observations, state)` receives only
the current session's symbols and trailing close histories. Selection uses validation
metrics. Each attempt records its code, hypothesis, metrics, elapsed time and keep/discard/crash
status. Only feasible candidates can become champion; target satisfaction takes precedence
over reward. Discarded or failed changes restore the last champion, when one exists.

After the search stops, freeze a feasible champion:

```sh
python3 run.py --freeze
```

The **researcher** then evaluates that frozen strategy once:

```sh
python3 -m core.evaluate --candidate runs/best.py \
  --test-dir ../csi300-study-holdout --output ../csi300-final.json
```

The final-test marker is written before evaluation, so a failed test also consumes the
one-time check. Do not resume strategy selection using final-test feedback.

## Scope and limitations

The simulator is long-only and unlevered, with residual cash, proportional transaction
costs, next-session-open execution and one-session holding periods. It uses 252 sessions
per year and zero cash/risk-free return. Multiple symbols must share the same session dates;
run different markets as separate studies.

Index levels exclude tradable-fund tracking and execution effects. The simulator does not
model dividends, corporate actions, missing-session fills, suspensions, price limits,
delisting proceeds, liquidity or market impact. It is a research scaffold, not a broker.

Hashes and instructions detect accidental changes; they are **not a security sandbox**.
An untrusted agent needs an isolated evaluator and OS-enforced data access controls.
Public history and an LLM's pretrained knowledge can contaminate historical evaluation;
repeated validation search can overfit. This framework does not guarantee profitability
or eliminate leakage merely by defining a test period.

