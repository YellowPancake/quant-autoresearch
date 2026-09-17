"""Build bilingual study reports from the shared accounting results."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def table(zh=False):
    header = ('| 市场 / 方案 | 选择方式 | 验证年化 | 测试累计收益 | 测试年化 | 测试最大回撤 |' if zh else
              '| Market / approach | Selection | Validation CAGR | Test return | Test CAGR | Test max drawdown |')
    rows = [header, '|---|---|---:|---:|---:|---:|']
    for market, en, cn in [('broad_market', 'Broad-market', '宽基'), ('csi300', 'CSI 300', '沪深300'), ('sp500', 'S&P 500 (SPY proxy)', '标普500（SPY代理）')]:
        r = json.loads((HERE / market / 'results.json').read_text())
        choices = [(r['frozen_attempt'], '冻结冠军' if zh else 'Frozen champion'),
                   (r['posthoc_attempt'], '事后测试最佳节点' if zh else 'Best test milestone, post hoc')]
        for a, role in choices:
            m = r['results'][a]
            vals = [m['validation']['annual_return']] + [m['test'][k] for k in ['total_return', 'annual_return', 'max_drawdown']]
            rows.append(f'| {cn if zh else en} #{int(a)} | {role} | ' + ' | '.join(f'{v:.2%}' for v in vals) + ' |')
        for symbol, m in r['baselines'].items():
            if market == 'broad_market':
                continue  # CSI baseline is literally identical to the row below.
            vals = [m['validation']['annual_return']] + [m['test'][k] for k in ['total_return', 'annual_return', 'max_drawdown']]
            name = ('沪深300全收益' if symbol == 'csi300' else 'SPY含分红') if zh else ('CSI 300 TR' if symbol == 'csi300' else 'SPY dividend-adjusted')
            rows.append(f'| {name} | {"买入持有" if zh else "Buy-and-hold"} | ' + ' | '.join(f'{v:.2%}' for v in vals) + ' |')
    return '\n'.join(rows)


EN = '''# Research results · Unified total-return accounting

[中文](README.zh-CN.md)

The broad-market, CSI 300 and S&P 500 examples below use one accounting engine:
dividends reinvested, signals after close, execution at the next session's close,
0.03% transaction costs per side and calendar-day CAGR. Each partition starts at NAV 1.
These are **reevaluations of fixed historical strategies**, not a new strategy search.
The original training inputs, signal features and frozen champion IDs are unchanged.

## Results

{table}

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
'''

ZH = '''# 研究结果 · 统一全收益口径

[English](README.md)

下方宽基、沪深300和标普500实验统一使用同一个收益评估器：分红再投资、收盘后产生信号、
下一交易日收盘成交、买卖各0.03%费用、按实际日历天数年化，各分区净值均从1开始。
这是**固定历史策略的统一口径复评**，没有重新搜索策略；原训练输入、信号特征和冻结冠军编号保持不变。

## 结果

{table}

宽基候选池包含 **24个指数及ETF代理**。冻结冠军仍为 #478，事后比较方案仍为 #162。
两组国内实验共用完全相同的沪深300基准：累计收益 **28.13%**、年化 **6.95%**、
最大回撤 **22.41%**。创业板ETF买入持有累计收益 **47.32%**、年化 **11.08%**、最大回撤 **40.88%**。

沪深300冻结冠军仍为 #178；在原有16个历史节点中，#84的测试收益最高。
新口径下 #178验证集累计收益为 **50.99%**，未达到原先100%的目标。
此前106.30%的验证收益属于原执行协议，不能沿用到此次复评。

标普实验的策略与基准均采用 **SPY含分红复权收盘价作为全收益代理**，并非标普500官方全收益指数；
基金费用与跟踪差异已经包含在行情中。已检查的数据源暂未能下载完整的指数全收益日线，
因此采用已固定版本的公开SPY数据，覆盖全部1,682个评测交易日，不使用基金成立前的合成数据。
冻结策略 #215收益低于买入持有，测试回撤也略高。14个固定节点中收益最高的变为初始买入持有 #1；
原事后比较方案 #15累计收益为 **107.91%**。#1与基准的每日净值完全相同，因此标普图中同时展示
冻结策略 #215，便于观察差异。

需要注意，验证集上的持续改进不一定会稳定转化为测试集提升，因此需要观察过拟合情况。
测试集最佳节点属于事后比较，没有替换冻结冠军，也不构成新的独立盲测成功。
未成为历史冠军的尝试没有接受测试集评估。

## 图表

### 宽基指数 · 20小时预算

![宽基统一口径结果](total_return/broad_market/figures/combined_annual.png)

[净值图](total_return/broad_market/figures/test_equity.png) · [PDF](total_return/broad_market/figures/combined_annual.pdf) · [实验说明](broad_market/README.zh-CN.md)

### 沪深300

![沪深300统一口径结果](total_return/csi300/figures/combined_returns.png)

[年化版本](total_return/csi300/figures/combined_annual.png) · [PDF](total_return/csi300/figures/combined_returns.pdf)

### 标普500 · SPY全收益代理

![标普500策略使用SPY代理复评](total_return/sp500/figures/combined_returns.png)

[年化版本](total_return/sp500/figures/combined_annual.png) · [PDF](total_return/sp500/figures/combined_returns.pdf)

下方子图按原历史验证冠军的顺序重新计算指标，不是在新口径下重新挑选的冠军序列。
横轴显示原尝试编号，各节点等间距排列，不代表等长研究时间。

## 目标与评估协议

| 设置 | 沪深300 | 标普500 | 宽基 |
|---|---|---|---|
| Reward | 验证集累计净收益 | 验证集年化净收益 | 验证集年化净收益 |
| 回撤约束 | <50% | ≤50% | `min(50%, 26.34% + (CAGR − 20%) / 2)` |
| 验证集目标 | 累计收益 ≥100% | 年化收益 ≥60% | 年化收益 ≥30% |
| 尝试 / 失败次数 | 178 / 0 | 316 / 1 | 488 / 4 |
| 历史节点 | 16 | 14 | 18 |
| 实际经过时间预算 | 配置上限为20小时，提前终止 | 配置上限为20小时 | 配置上限为20小时 |

训练集仍为2010—2019年，验证集2020—2022年，测试集2023年至2026年9月11日。
按各自交易所日历：国内验证/测试分别728/896个交易日，美国为756/926个交易日。
两地测试均从1月3日收盘开始，买入持有基准于1月4日收盘买入。
所有组合只做多、无杠杆，现金利息为零，期末不强制平仓；买入持有仅买入一次，之后保持份额。
按实际成交金额扣费，净值起点为1不会消除建仓费用。回撤基于每日收盘净值；
年化按实际经过天数除以365.2425计算。全收益指数和含分红复权ETF行情已包含分红，不能重复添加。

此次只统一收益与记账：单指数策略仍使用原价格指数训练标签拟合，从原OHLC历史生成决策；
公共记账审计按宽基归档订单重放；下方源码复现入口则从训练行情独立重建 #478 和 #162。
没有根据测试结果调参、用未来价格生成信号或修改冻结实验。
成交时点、费用、估值、年化和SPY代理均与部分旧报告不同，结果变化不能全部归因于分红。

## 策略与复现

宽基已补齐完整行情及源码：[冻结冠军 #478](broad_market/frozen_strategy.py)、
[事后比较方案 #162](broad_market/posthoc_strategy.py)。从行情重新拟合并生成两份策略的订单：

```sh
python3 -m pip install -r examples/studies/broad_market/requirements.txt
python3 examples/studies/broad_market/replay.py
```

此入口要求Python 3.12+、NumPy和pandas，直接打印结果，并将可读摘要、每日净值与订单写入
`results/broad-market/`。[源码复现说明](broad_market/README.zh-CN.md#复现策略)与
[已验证结果](broad_market/reproduction.json)记录了188笔订单、3,248条日净值的核对情况。

归档源码：[沪深300 #178](csi300/frozen_strategy.py)、[沪深300 #84](csi300/posthoc_strategy.py)、
[标普500 #215](sp500/frozen_strategy.py)、[原标普事后方案 #15](sp500/posthoc_strategy.py)。
[原策略说明](ARCHIVE.zh-CN.md#策略示例)保留算法细节；该归档页的旧指标采用原口径。

在仓库根目录执行，Python 3.10+，只依赖标准库：

```sh
python3 examples/studies/total_return/evaluate.py --market csi300
python3 examples/studies/total_return/evaluate.py --market broad_market
python3 examples/studies/total_return/evaluate.py --market sp500
python3 -m unittest discover -s examples/studies/total_return -p 'test_*.py'
python3 examples/studies/total_return/report.py
```

如需从不变的策略源码和原训练数据重建决策，运行同目录下的
`extract_signals.py --market csi300`，或将市场替换为 `sp500`。
`fetch_spy.py` 可重新下载固定版本的代理数据并检查哈希。
`plot.py --market MARKET` 用于重新绘图，仅此步骤依赖Matplotlib。
评估器先检查输入哈希，再复核宽基全部29,232条日净值；回归检查要求两组沪深300基准逐日一致。

[数据来源与哈希](total_return/manifest.json) · [国内收益行情](total_return/data/china_total_return.csv) · [SPY收益行情](total_return/data/spy_total_return.csv)

`total_return/` 的每个市场目录包含 `results.json`、`stages.csv`、`equity.csv`、`figures/`，
以及固定信号或订单。原价格口径日志、快照与复现命令保留在[原协议归档](ARCHIVE.zh-CN.md)。
最简新实验运行器本轮未改动，仍使用原价格指数适配器；复现本页全收益结果请使用上面的明确入口。
开展新实验时，不要向研究Agent开放这些已公开的测试数据与研究者报告目录。
'''


if __name__ == '__main__':
    for name, text, zh in [('README.md', EN, False), ('README.zh-CN.md', ZH, True)]:
        (HERE.parent / name).write_text(text.replace('{table}', table(zh)))
