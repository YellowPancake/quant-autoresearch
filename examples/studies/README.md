# Completed research examples

[中文](README.zh-CN.md)

Two fixed-protocol studies, including the unsuccessful S&P 500 result. These are
historical research records, not an assertion that automated search reliably beats
buy-and-hold.

## Results

Training: 2010–2019. Validation: 2020–2022. Test: 2023–September 11, 2026.
All figures include 0.05% transaction costs per side.

| Market / strategy | Selection | Validation CAGR | Test CAGR | Test total return | Test max drawdown |
|---|---|---:|---:|---:|---:|
| CSI 300 #178 | Frozen validation champion | 28.58% | 13.21% | 55.27% | 18.15% |
| CSI 300 #84 | Best test milestone, post hoc | 17.40% | 14.58% | 62.07% | 16.06% |
| CSI 300 buy-and-hold | Baseline | −2.49% | 4.28% | 16.04% | 25.98% |
| S&P 500 #215 | Frozen validation champion | 21.93% | 17.67% | 81.60% | 16.16% |
| S&P 500 #15 | Best test milestone, post hoc | 6.08% | 21.81% | 106.16% | 19.25% |
| S&P 500 buy-and-hold | Baseline | 5.86% | 20.59% | 98.66% | 19.25% |

**The frozen champions are #178 and #215.** The strategies shown in the top panels
below (#84 and #15) were selected after comparing test returns among 16 and 14
validation-champion milestones, respectively. That comparison is descriptive;
it did not replace either frozen champion. They are not the best of all attempts
on the test set: non-milestone attempts were not tested.

### CSI 300

![CSI 300 research results](csi300/figures/combined_returns.png)

[Annualized version](csi300/figures/combined_annual.png) · [PDF](csi300/figures/combined_returns.pdf)

### S&P 500

![S&P 500 research results](sp500/figures/combined_returns.png)

[Annualized version](sp500/figures/combined_annual.png) · [PDF](sp500/figures/combined_returns.pdf)

Top panels show daily test-period net asset value. Lower panels show aggregate
return and maximum drawdown for each validation improvement, spaced equally as
stages. Stage numbers are not experiment counts or dates. Each milestone retains
its original attempt ID in `milestones.json`. Total returns cover different
lengths of time across validation and test; use the annualized versions to compare rates.

## Objectives and protocol

| Setting | CSI 300 | S&P 500 |
|---|---|---|
| Reward | Validation cumulative net return | Validation net CAGR |
| Drawdown constraint | Strictly below 50% | At most 50% |
| Validation target | Cumulative return ≥100% | CAGR ≥60% |
| Attempts / failures | 178 / 0 | 316 / 1 |
| Historical champions | 16, including the initial cash strategy | 14, including initial buy-and-hold |
| History available to a strategy | 120 sessions | 252 sessions |
| Features available | OHLC and native volume | OHLC; no volume features |
| Wall-clock budget | Configured 20-hour cap; terminated early | Configured 20-hour cap |

The CSI 300 validation champion reached its cumulative-return target (106.30%).
The S&P 500 validation champion did not reach its 60% CAGR target. S&P 500's
frozen strategy also earned less than buy-and-hold in the test period, although
its drawdown was lower. Note that continued improvements on the validation set may
not consistently translate into better test performance, so monitor for overfitting.

Both studies use long-only index/cash positions with no leverage, zero cash
interest, after-close decisions, next-open entry and following-open valuation.
Labels crossing partition boundaries are removed; earlier prices may supply
warmup history. CAGR uses 252 sessions per year. Drawdown is measured on simulated
daily opening equity, not intraday lows. These are price-index proxies without
dividends, ETF tracking, FX or live execution effects.

The final champion was tested after freezing. Historical validation champions
were then evaluated in a separately authorized audit. Published test outcomes
are now disclosed; replaying or choosing among them is not a new independent test.
Full historical data and possible model pretraining knowledge also preclude a
claim of completely blind future prediction.

## Strategy examples

The four source files below are byte-identical archived strategies. Their hashes
and metrics are recorded in each market's `study.json`. They define `fit(train)`
and `allocate(observations, state)` and refit from training data when replayed.

| Source | Method |
|---|---|
| [CSI 300 frozen #178](csi300/frozen_strategy.py) | Three random forests using 40-, 25- and 15-feature views; majority vote plus an RSI reversal sleeve. |
| [CSI 300 post-hoc #84](csi300/posthoc_strategy.py) | One 20-tree forest plus an RSI reversal sleeve. |
| [S&P 500 frozen #215](sp500/frozen_strategy.py) | Equal blend of monthly ridge and an 8-unit tanh network with feature dropout, plus a volatility-shock exit gate. |
| [S&P 500 post-hoc #15](sp500/posthoc_strategy.py) | Daily ridge-return forecast with symmetric 5-basis-point entry/exit hysteresis. |

CSI 300's forests predict a clipped five-session compounded return. The frozen
strategy enters each forest state above a 0.10% forecast and exits below zero;
a majority controls exposure. Its independent RSI(14) sleeve enters below 30,
exits above 50 or after 20 signal days, and is combined by union with the forest
signal. #84 uses an RSI exit of 55 and a single feature view.

S&P 500 #215 fits 20-session mean-log-return predictors on nine close-derived
features. Ridge strength and neural checkpoints are selected on a chronological
training suffix with a 21-row purge. The neural network uses 10% input dropout
while fitting. The mean forecast controls an all-in/all-out position, filtered
by a five-versus-sixty-session volatility shock and a three-close breakdown.
#15 instead fits a daily-return ridge model using 13 price/OHLC features and holds
its previous position between +0.05% and −0.05% predicted return.

## Reproduce the published metrics

From the repository root, using Python 3.10+ and the standard library:

```sh
python3 -B examples/studies/replay.py --market csi300
python3 -B examples/studies/replay.py --market sp500
```

To replay just one role:

```sh
python3 -B examples/studies/replay.py --market sp500 --strategy frozen
```

The script checks bundled data and strategy hashes, reconstructs the original
history windows and time boundaries, fits on training only, and verifies every
reported validation/test metric against its archived value. Each partition starts
with fresh state. It creates no research workspace or test marker and writes no
results: this is a replay of an already published study, not a route for an Agent
to access a new study's holdout.

These studies used an OHLC-aware observation contract. The main framework's
minimal adapter currently exposes close history only, so the archived files are
**not drop-in replacements for its default strategy**. This separate replay
entry point preserves the original study behavior without changing the minimal
framework. Do not expose this directory or the full bundled histories to an Agent
running a new study.

## Files

Each market directory contains:

- `frozen_strategy.py`, `posthoc_strategy.py`: the two disclosed strategy snapshots.
- `study.json`: original configuration, budget note, data hash and selected metrics.
- `milestones.json`: all evaluated historical champions and the buy-and-hold baseline.
- `attempts.csv`: all attempt descriptions, hashes, statuses and validation metrics.
- `daily_equity.csv`: plotted post-hoc strategy and baseline daily paths.
- `figures/`: cumulative/annualized composites in PNG, SVG and PDF.

`plot.py` redraws the figures from these published records, without fitting or
accessing raw price histories. Only plotting requires Matplotlib:

```sh
python3 -m pip install matplotlib
python3 examples/studies/plot.py --market csi300 --output /tmp/csi300-figures
python3 examples/studies/plot.py --market sp500 --output /tmp/sp500-figures
```

The full Agent conversation, every discarded source file and private workspaces
are not part of this compact example release. The logs and snapshots reproduce
the disclosed strategies and figures, not an identical future Agent search.
