# Bundled index histories / 内置指数行情

This repository contains real CSI300 and S&P 500 daily price-index histories.
Market-data redistribution has **not** been cleared;
the repository's MIT license applies only to code and documentation.

| Dataset | Path | Coverage | Rows | Local session timezone |
|---|---|---|---|---|
| CSI300 / 沪深300 | `csi300/prices.csv` | 2010-01-04–2026-09-11 | 4055 | Asia/Shanghai |
| S&P 500 / 标普500 | `sp500/prices.csv` | 2010-01-04–2026-09-11 | 4198 | America/New_York |

Both files preserve the same 13-column archive schema. SHA-256, coverage and source
identifiers are recorded in the adjacent manifests. Neither dataset contains strategy
outputs or experiment results. Prices are index points, excluding dividends.

| Column | Meaning |
|---|---|
| index_id | Stable index identifier |
| date | Local trading-session date |
| open, high, low, close | Daily price-index levels |
| volume_native | Upstream volume in the source's native convention; nullable |
| amount_native | Upstream amount in the source's native convention; nullable |
| available_at | Assumed conservative end-of-day availability, with timezone |
| availability_basis | Basis for that availability assumption |
| ingested_at | Source download timestamp |
| source_id | Source identifiers, including any repair source |
| data_quality | Missingness, source limitations and repair flags |

The minimal evaluator consumes `index_id,date,open,close` only. Other fields remain
available for a future adapter; their presence in the file does not make them visible
to the current strategy. Custom files can use `symbol` instead of `index_id`.
For another index or stock, convert it to this format; the unused extra columns can
be omitted. See [the data contract](../docs/DATA.md).

Full data include final-test dates. The researcher runs `prepare.py` from the
distribution repository, then runs the agent in the new study workspace. Do not
grant the research agent access to these full histories or the external final holdout.
This directory layout is not an OS security sandbox.

## Sources and limitations

- CSI300: BaoStock index API, recorded as `baostock_index`. See the provider's
  [disclaimer](https://baostock.com/disclaimer). API accessibility does not establish
  permission to redistribute the complete history; no affirmative data redistribution
  license has been recorded for this snapshot.
- S&P 500: [Sina history](https://finance.sina.com.cn/staticdata/us/.INX), with nine
  close corrections from [FRED SP500](https://fred.stlouisfed.org/series/SP500), one
  high correction from [September 2017 daily history](https://www.statmuse.com/money/ask/s-and-p-close-september-2017)
  and one open correction from [July 3, 2023 intraday history](https://www.statmuse.com/money/ask/sandp-500-chart-jul-3-2023).
  FRED's SP500 series notes explicitly require prior written permission from S&P
  Dow Jones Indices for reproduction. No such permission is recorded here.
- The S&P snapshot excludes three non-session source rows. Its 4198 dates match
  the XNYS calendar used during collection; 2511 closes were cross-checked with FRED.
  S&P volume has two missing values and amount has 1305. Native volume/amount units
  and aggregation are unverified and should not be assumed comparable across markets.
- Current revised historical snapshots are not point-in-time publication archives.
  `available_at` is a research assumption, not proof of historical availability.

**公开前需解决实际来源的再分发许可。** 本地审阅包加入数据不表示已有公开分发授权；
注明来源或“仅供研究”不能代替许可。这一条件来自实际数据源条款，而非框架的代码许可证。
