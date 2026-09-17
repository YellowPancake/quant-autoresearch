# Broad-market index study

[中文](README.zh-CN.md) · [All studies](../README.md)

A 20-hour research budget produced 488 attempts: 484 completed backtests,
4 failures and 18 historical validation champions. This release includes only
the latest figure and its supporting data.

![Latest broad-market study results](figures/combined_annual_return.png)

[Download PDF](figures/combined_annual_return.pdf)

## Results

| Strategy | Selection | Validation CAGR | Test total return | Test CAGR | Test max drawdown |
|---|---|---:|---:|---:|---:|
| #478 | Frozen validation champion | 43.75% | 116.70% | 23.33% | 31.00% |
| #162 | Highest test-return milestone, post hoc | 37.14% | 172.52% | 31.24% | 30.05% |

Both top-panel curves show cumulative net returns over the same test period.
The lower panels show validation/test CAGR and maximum drawdown across 18 milestones.
Stages indicate milestone order, not equal numbers of attempts or elapsed research time.

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
differ from the single-index CSI 300 study; read each result with its own protocol.
This historical test period had already appeared in prior research and the results
are now public. Further validation requires new data that did not inform selection.

## Chart data

- [best_methods_test_curves.csv](best_methods_test_curves.csv): both test paths; `strategy_return` is #162's cumulative return and `validation_best_test_return` is #478's.
- [stage_metrics.csv](stage_metrics.csv): metrics and constraint checks for all 18 historical validation champions.
- [presentation_selection.json](presentation_selection.json): plotted strategy roles and selection method.

The figure was copied directly from the completed study archive, without searching
for new strategies or rerunning final tests. This directory publishes charts and
summary data only; the parent directory's `replay.py` still supports only CSI 300
and S&P 500, not this broad-market study.
