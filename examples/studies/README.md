# Research results · Unified total-return accounting

[中文](README.zh-CN.md)

The broad-market, CSI 300 and S&P 500 examples below use one accounting engine:
dividends reinvested, signals after close, execution at the next session's close,
0.03% transaction costs per side and calendar-day CAGR. Each partition starts at NAV 1.
These are **reevaluations of fixed historical strategies**, not a new strategy search.
The original training inputs, signal features and frozen champion IDs are unchanged.

## Results

| Market / approach | Selection | Validation CAGR | Test return | Test CAGR | Test max drawdown |
|---|---|---:|---:|---:|---:|
| Broad-market #478 | Frozen champion | 43.75% | 116.70% | 23.33% | 31.00% |
| Broad-market #162 | Best test milestone, post hoc | 37.14% | 172.52% | 31.24% | 30.05% |
| CSI 300 #178 | Frozen champion | 14.76% | 56.61% | 12.93% | 11.59% |
| CSI 300 #84 | Best test milestone, post hoc | 7.52% | 77.30% | 16.80% | 10.96% |
| CSI 300 TR | Buy-and-hold | -0.25% | 28.13% | 6.95% | 22.41% |
| S&P 500 (SPY proxy) #215 | Frozen champion | 16.26% | 91.39% | 19.25% | 19.05% |
| S&P 500 (SPY proxy) #1 | Best test milestone, post hoc | 7.57% | 108.22% | 22.00% | 18.76% |
| SPY dividend-adjusted | Buy-and-hold | 7.57% | 108.22% | 22.00% | 18.76% |

The broad-market pool contains **24 indices and ETF proxies**. Its frozen champion
remains #478; the post-hoc test selection remains #162. Both Chinese studies share
the exact same CSI 300 benchmark: **28.13%** total return, **6.95%** CAGR and **22.41%**
maximum drawdown. ChiNext ETF buy-and-hold returned **47.32%**, with **11.08%** CAGR
and **40.88%** maximum drawdown.

CSI 300's frozen champion remains #178; #84 is the highest test-return milestone
among the same 16 historical candidates. Under this accounting, #178's validation
cumulative return is **50.99%**, so it does not meet the original 100% target.
The former 106.30% validation result belongs to the original execution protocol.

S&P 500 is evaluated using **SPY dividend-adjusted closes as a total-return proxy**,
for both the strategy and buy-and-hold. This is not the official S&P 500 total-return
index: fund fees and tracking differences are embedded. Complete daily index TR
history could not be downloaded from the checked sources. The pinned public SPY
snapshot covers all 1,682 evaluation sessions; no synthetic pre-inception data is used.
Frozen #215 returns less than buy-and-hold, with slightly greater test drawdown.
The best of the 14 fixed milestones is now initial buy-and-hold #1; former post-hoc
selection #15 returns **107.91%**. #1 and the benchmark have identical daily paths,
so the S&P chart also shows frozen #215 to make that comparison visible.

Note that continued improvements on the validation set may not consistently
translate into better test performance, so monitor for overfitting. Test selection
is retrospective and does not replace the frozen champions or constitute a new
independent blind-test success. Non-milestone attempts were not tested.

## Charts

### Broad-market indices · 20-hour budget

![Broad-market unified results](total_return/broad_market/figures/combined_annual.png)

[Equity chart](total_return/broad_market/figures/test_equity.png) · [PDF](total_return/broad_market/figures/combined_annual.pdf) · [Study details](broad_market/README.md)

### CSI 300

![CSI 300 unified results](total_return/csi300/figures/combined_returns.png)

[Annualized version](total_return/csi300/figures/combined_annual.png) · [PDF](total_return/csi300/figures/combined_returns.pdf)

### S&P 500 · SPY total-return proxy

![S&P 500 unified results using SPY](total_return/sp500/figures/combined_returns.png)

[Annualized version](total_return/sp500/figures/combined_annual.png) · [PDF](total_return/sp500/figures/combined_returns.pdf)

Lower panels reevaluate the original sequence of historical validation champions;
they are not a newly selected sequence under the revised accounting. Attempt IDs
are shown at equally spaced milestones, not proportional elapsed time.

## Objectives and evaluation protocol

| Setting | CSI 300 | S&P 500 | Broad-market |
|---|---|---|---|
| Reward | Validation cumulative net return | Validation net CAGR | Validation net CAGR |
| Drawdown constraint | <50% | ≤50% | `min(50%, 26.34% + (CAGR − 20%) / 2)` |
| Validation target | Cumulative return ≥100% | CAGR ≥60% | CAGR ≥30% |
| Attempts / failures | 178 / 0 | 316 / 1 | 488 / 4 |
| Historical milestones | 16 | 14 | 18 |
| Wall-clock budget | Configured 20-hour cap; terminated early | Configured 20-hour cap | Configured 20-hour cap |

Training remains 2010–2019, validation 2020–2022 and test 2023–September 11, 2026.
Each market uses its own exchange sessions: 728/896 validation/test sessions for
China and 756/926 for the US. Both start each test at the January 3 close and buy
at the January 4 close. All portfolio rules are long-only and fully funded, with
zero cash interest and no forced terminal sale. Buy-and-hold buys once and retains
units. Fees are charged on actual executed amounts; the chart origin does not
remove entry costs. Drawdown uses daily closing NAV. CAGR uses actual elapsed
days divided by 365.2425. Index TR and adjusted ETF series already incorporate
dividends; they are never added a second time.

Only returns and accounting are changed. Single-index models still fit the
original price-index training labels and generate decisions from original OHLC
history. The shared accounting audit replays broad-market archived orders; the source
replay below independently regenerates #478 and #162 from training prices. No test-driven
retuning, signal reconstruction from future prices or changes to frozen runs occur.
Execution, fees, valuation, annualization and the SPY proxy all differ from parts
of the original reports; differences must not be attributed solely to dividends.

## Strategies and reproduction

Broad-market sources and complete data are now included: [frozen #478](broad_market/frozen_strategy.py)
and [post-hoc #162](broad_market/posthoc_strategy.py). Refit and regenerate both from
prices (Python 3.12+, NumPy and pandas):

```sh
python3 -m pip install -r examples/studies/broad_market/requirements.txt
python3 examples/studies/broad_market/replay.py
```

The command prints results and writes a readable summary, daily NAV and orders to
`results/broad-market/`. [Source replay guide](broad_market/README.md#reproduce-the-strategies)
and [verified results](broad_market/reproduction.json) document all 188 orders and 3,248 daily NAV checks.

Archived code: [CSI 300 #178](csi300/frozen_strategy.py), [CSI 300 #84](csi300/posthoc_strategy.py),
[S&P 500 #215](sp500/frozen_strategy.py), [former S&P 500 selection #15](sp500/posthoc_strategy.py).
[Original strategy explanations](ARCHIVE.md#strategy-examples) preserve the methods;
the original metrics on that archive page use the former accounting.

From the repository root, Python 3.10+ and the standard library are sufficient:

```sh
python3 examples/studies/total_return/evaluate.py --market csi300
python3 examples/studies/total_return/evaluate.py --market broad_market
python3 examples/studies/total_return/evaluate.py --market sp500
python3 -m unittest discover -s examples/studies/total_return -p 'test_*.py'
python3 examples/studies/total_return/report.py
```

`extract_signals.py --market csi300` (or `sp500`) optionally reconstructs the
bundled decisions from the unchanged strategy snapshots and original training data.
`fetch_spy.py` optionally reproduces the pinned proxy download and verifies its hash.
`plot.py --market MARKET` in the same directory redraws the charts and requires
Matplotlib. The common evaluator verifies hashes before running; it also checks
all 29,232 broad-market daily NAVs against the archived paths. A regression check
requires the two CSI 300 benchmark paths to match on every date.

[Data provenance and hashes](total_return/manifest.json) · [Chinese return data](total_return/data/china_total_return.csv) · [SPY return data](total_return/data/spy_total_return.csv)

Each market's `total_return/` directory contains `results.json`, `stages.csv`,
`equity.csv` and `figures/`, plus fixed signals or orders. Original price-protocol
logs, snapshots and replay commands remain in the [original archive](ARCHIVE.md).
The minimal new-study runner is unchanged and still uses its original price-index
adapter; these total-return reports are reproduced through the explicit commands
above. Do not expose published test data or this researcher's report directory
to an Agent conducting a new experiment.
