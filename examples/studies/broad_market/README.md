# Broad-market index study

[中文](README.zh-CN.md) · [All studies](../README.md)

A 20-hour research budget produced 488 attempts: 484 completed backtests,
4 failures and 18 historical validation champions. The Agent researches asset
selection and portfolio allocation across 24 indices and ETF proxies. This release includes
both strategy sources, complete training/evaluation prices and a source-level replay entry point.

![Broad-market strategy versus two buy-and-hold benchmarks](../total_return/broad_market/figures/test_equity.png)

[Equity chart PDF](../total_return/broad_market/figures/test_equity.pdf) · [Research progress composite](../total_return/broad_market/figures/combined_annual.png) · [Composite PDF](../total_return/broad_market/figures/combined_annual.pdf)

## Reproduce the strategies

[Frozen champion #478 source](frozen_strategy.py) · [Post-hoc selection #162 source](posthoc_strategy.py) · [Verified run results](reproduction.json)

From the repository root, using Python 3.12+; a virtual environment is recommended:

```sh
python3 -m pip install -r examples/studies/broad_market/requirements.txt
python3 examples/studies/broad_market/replay.py
```

By default, both strategies are refitted on 2010–2019 training prices and run on
validation and test. Cumulative return, CAGR and maximum drawdown are printed directly.
Orders are generated from the strategy and price history; archived orders are used
only for verification afterward. All 188 orders and 3,248 daily NAVs were reproduced.

Outputs go to `results/broad-market/`: `README.md` provides the summary,
`summary.json` includes metrics and verification errors, `equity.csv` contains daily
NAV, and `orders.json` contains regenerated orders. Replay needs no network or API key.
To run only the homepage selection on the test period:

```sh
python3 examples/studies/broad_market/replay.py --strategy posthoc --partition test --output results/broad-market-162
```

`--strategy frozen` selects #478; `posthoc` selects #162, which remains a retrospective
test comparison, not the frozen champion. The numerical tolerance is `1e-8`;
any mismatch in order dates, assets, weights or daily NAV raises an error.

```text
examples/studies/broad_market/
├── frozen_strategy.py / posthoc_strategy.py  # original strategy snapshots
├── engine.py                               # original evaluator
├── replay.py / requirements.txt             # entry point and pinned dependencies
├── data/prices.csv                          # full 2010–2026 history
├── data/universe.json                       # instruments and provenance
├── manifest.json                           # hashes and evaluation protocol
└── reproduction.json                        # verified reproduction results
```

Strategies, evaluator and full price panel are byte-identical to the frozen archives.
The panel contains 4,055 sessions, 24 selectable assets and one reference-only series,
preserving pre-launch and missing quotes. Evaluation prices exactly match the unified
total-return report. Decisions use only current/past observations; each partition
starts with fresh strategy state and cash NAV 1. This separate entry point replays
published research, without restarting the 20-hour search or modifying frozen records.
These multi-asset strategies are not drop-in replacements for the minimal runner's
default single-index strategy.

## Results

| Strategy | Selection | Validation CAGR | Test total return | Test CAGR | Test max drawdown |
|---|---|---:|---:|---:|---:|
| #478 | Frozen validation champion | 43.75% | 116.70% | 23.33% | 31.00% |
| #162 | Highest test-return milestone, post hoc | 37.14% | 172.52% | 31.24% | 30.05% |

The equity chart compares #162 with ChiNext and CSI 300 buy-and-hold, all starting
from 1. The research progress composite uses the same equity comparison; its lower
panels show validation/test CAGR and maximum drawdown across 18 milestones.
The horizontal axis shows historical attempt IDs at equally spaced milestones, not elapsed research time.

| Test-period approach | Total return | CAGR | Max drawdown |
|---|---:|---:|---:|
| #162 (post hoc) | 172.52% | 31.24% | 30.05% |
| ChiNext buy-and-hold | 47.32% | 11.08% | 40.88% |
| CSI 300 buy-and-hold | 28.13% | 6.95% | 22.41% |

ChiNext uses backward-adjusted ETF 159915 prices; CSI 300 uses the H00300 total-return
index. Both series come from this study's data. The benchmarks signal at the close
on January 3, 2023 and buy at the January 4 close, paying a 0.03% purchase fee.
They retain the same units thereafter, without a terminal sale. Fees remain in the
equity paths; no normalization after entry removes them. The single-index example
now uses the exact same CSI 300 total-return series and daily benchmark path.

#162 was selected retrospectively from 18 evaluated validation champions; not all
488 attempts were tested. It did not replace frozen strategy #478, whose test CAGR
fell below the 30% target and whose drawdown exceeded its corresponding limit of
about 28.00%. #162 met the numerical thresholds in this retrospective comparison;
that does not constitute a new independent blind-test success.

Note that continued improvements on the validation set may not consistently
translate into better test performance, so monitor for overfitting.

## Evaluation conventions

| Setting | Detail |
|---|---|
| Wall-clock budget | Configured 20-hour cap |
| Training | 2010–2019 |
| Validation | 2020–2022 |
| Test trading dates | January 3, 2023–September 11, 2026; 896 sessions |
| Reward | Maximize net CAGR among feasible candidates |
| CAGR target | ≥30% |
| Drawdown limit | `min(50%, 26.34% + (CAGR − 20%) / 2)` |
| Transaction costs | 0.03% per side, charged on executed amounts |
| Execution | Signal at close; execute at the next session's close |
| Annualization | Actual calendar days / 365.2425 |
| Positions | Long-only, no leverage, zero cash interest, no forced terminal liquidation |

Each partition starts with cash equity of 1. Execution timing, costs and annualization
match the unified reevaluation of the single-index studies. All 29,232 archived
broad-market daily NAVs were reproduced exactly by the common accounting engine.
This historical test period had already appeared in prior research and the results
are now public. Further validation requires new data that did not inform selection.

## Chart data

- [figures/test_equity.csv](figures/test_equity.csv): all three daily equity paths shown in the chart.
- [figures/comparison_metrics.json](figures/comparison_metrics.json): total return, CAGR and maximum drawdown for the three approaches.
- [benchmark_closes.csv](benchmark_closes.csv), [benchmark_sources.json](benchmark_sources.json): benchmark prices, provenance, hashes and calculation conventions.
- [best_methods_test_curves.csv](best_methods_test_curves.csv): original #162 and #478 archives; #478 is no longer plotted.
- [stage_metrics.csv](stage_metrics.csv): metrics and constraint checks for all 18 historical validation champions.
- [presentation_selection.json](presentation_selection.json): plotted strategy roles and selection method.

The strategy paths come from completed archives. Fixed orders were replayed through
the common accounting engine without strategy search or changing frozen test records.
Recalculate the report and redraw the figures (plotting requires Matplotlib):

```sh
python3 examples/studies/total_return/evaluate.py --market broad_market
python3 examples/studies/total_return/plot.py --market broad_market
```

[Unified daily paths and metrics](../total_return/broad_market/) contain all 18
milestones. The original files above remain archival records; the current chart
uses the shared plotting code in `total_return/`.
