# Quant-AutoResearch

[中文](README.zh-CN.md)

Give an Agent a strategy, a dataset and a research objective, then let it experiment.
It proposes a change, edits the strategy, runs an evaluation, keeps or discards the
result, and repeats. Each attempt leaves a record you can inspect.

You set the direction, reward, constraints, target and budget. The Agent works within
those settings while the data split and evaluator stay fixed. This project adapts the
research loop of [Karpathy's autoresearch](https://github.com/karpathy/autoresearch)
to quantitative strategy research.

## Research examples

The homepage features broad-market index and CSI 300 studies, each with a
20-hour research budget. Test period: 2023–September 11, 2026;
costs and execution conventions are documented for each study.

### Broad-market indices · Latest study

488 attempts and 18 historical validation champions. Both curves in the top panel
are test results: orange is the frozen validation champion #478; blue is #162,
selected post hoc for the highest test return among the 18 milestones.

![Latest broad-market study: test returns, annualized returns and drawdown](examples/studies/broad_market/figures/combined_annual_return.png)

#162: **+172.52%** test cumulative return, **31.24%** CAGR and **30.05%** maximum drawdown.
Frozen strategy #478: **+116.70%** test cumulative return, **23.33%** CAGR and **31.00%** maximum drawdown.
Costs: 0.03% per side. The post-hoc comparison did not replace the frozen strategy.

[Broad-market study notes and chart data](examples/studies/broad_market/README.md)

### CSI 300

![CSI 300 strategy versus buy-and-hold on the test set](examples/studies/csi300/figures/test_equity.png)

Strategy #84: **+62.07%** cumulative return vs **+16.04%** buy-and-hold;
maximum drawdown **16.06%** vs **25.98%**. Costs: 0.05% per side.
This curve likewise shows the historical validation champion with the highest
test return, selected post hoc.

### Frozen research champions

The strategies selected on validation and frozen before final testing:

| Study | Attempts | Frozen strategy | Test CAGR | Test max drawdown |
|---|---:|---|---:|---:|
| Broad-market indices | 488 | #478 | 23.33% | 31.00% |
| CSI 300 | 178 | #178 | 13.21% | 18.15% |

Note that continued improvements on the validation set may
not consistently translate into better test performance, so monitor for overfitting.

[All studies (including S&P 500), strategy explanations and replay commands](examples/studies/README.md)

## How it works

`prepare.py` creates a study with fixed chronological training, validation and final-test
partitions. The Agent evaluates candidates through `run.py`, which records each attempt
and restores the current best strategy after a discarded or failed change. Validation
drives selection; the researcher evaluates the final test once after freezing a strategy.

## Quick start

Requirements: Python 3.10+, macOS or Linux. The framework uses only the standard library.

The repository includes CSI300 and S&P 500 daily price-index histories from January
2010 through September 11, 2026. Both use the same data format.

Set the objective, dates and budget in `config/`, then run from the repository:

```sh
python3 prepare.py --example csi300 --workspace ../csi300-study
cd ../csi300-study
python3 run.py --description baseline
```

For S&P 500, replace `csi300` with `sp500` in the commands above.

Preparation creates the study and a sibling final-test directory (`../csi300-study-holdout`).
Full histories stay in the original repository. Use new directories for each study.

## Running the Agent

Open your Agent in the prepared **study directory** and give it a prompt like:

> Read AGENTS.md and program.md. Research strategies within the configured direction
> and budget. Edit only strategy/strategy.py and evaluate each idea through run.py.
> Keep feasible improvements. Freeze the best feasible strategy when the target or
> budget is reached.

Use an Agent connected to your preferred model provider. It runs the experiment loop
and may search external sources for ideas when authorized. `run.py` evaluates one attempt.

Restrict the Agent's access to full histories and final-test data; directory separation
and hashes are not a sandbox. See the [research guide](docs/RESEARCH.md) for deployment
boundaries and the researcher's final evaluation.

## Project structure

```text
prepare.py              Create a study from bundled or custom data
run.py                  Evaluate one candidate or freeze the chosen strategy
program.md / AGENTS.md  Agent instructions and edit boundaries
strategy/               Agent edits strategy.py only
config/                 Researcher sets the objective, budget and time protocol
core/                   Fixed preparation, evaluation, budget and indicators
data/                   CSI300 and S&P 500 histories with source manifests
examples/studies/       Completed studies, charts and archived strategy replays
docs/                   Data contract, indicator conventions and research guide
```

Each study generates `cache/` for prepared data and `runs/` for experiment records.

## Design choices

- **Researcher-defined objectives.** Reward, constraints, target and budget are separate settings.
  Defaults are examples; choose your own objective and an attempt or time budget.
- **Fixed evaluation.** Preparation seals the data split, policy and evaluator;
  labels crossing partition boundaries are excluded.
- **A small execution model.** Long-only, unlevered, with cash and proportional costs.
  Decisions after close execute at the next open and hold until the following open.

## Using other data

**Convert other index or stock data to the same format.** The minimum fields are
`date`, `open`, `close`, and either `index_id` or `symbol`.

```sh
python3 prepare.py --csv /path/to/your-prices.csv --workspace ../custom-study
```

Validate dates against the source market's calendar and use separate studies for different
markets. The current adapter uses open/close and exposes close history to the Agent.

[Data contract](docs/DATA.md) · [Examples](examples/README.md) · [Indicators](docs/INDICATORS.md)

## License

Code and documentation: [MIT](LICENSE).

Market data have separate source terms. Data redistribution
rights have not been cleared; see [data sources and terms](data/README.md).
