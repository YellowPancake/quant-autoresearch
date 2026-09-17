# 宽基指数实验

[English](README.md) · [全部实验](../README.zh-CN.md)

20小时研究预算，共488次尝试，其中484次完成回测、4次失败，产生18个历史验证冠军节点。
在24个指数及ETF代理构成的候选池中筛选标的、研究组合配置。
现已包含两份策略源码、完整训练与评测行情，以及从源码重新生成订单的复现入口。

![宽基策略与两种买入持有基准的净值对比](../total_return/broad_market/figures/test_equity.png)

[净值图PDF](../total_return/broad_market/figures/test_equity.pdf) · [研究过程合并图](../total_return/broad_market/figures/combined_annual.png) · [合并图PDF](../total_return/broad_market/figures/combined_annual.pdf)

## 复现策略

[冻结冠军 #478 源码](frozen_strategy.py) · [事后比较方案 #162 源码](posthoc_strategy.py) · [已验证的运行结果](reproduction.json)

在仓库根目录执行，使用Python 3.12+，建议在虚拟环境中安装依赖：

```sh
python3 -m pip install -r examples/studies/broad_market/requirements.txt
python3 examples/studies/broad_market/replay.py
```

默认复现两份策略的验证集与测试集，直接打印累计收益、年化收益及最大回撤。
脚本重新使用2010—2019年的训练数据拟合策略，从历史行情生成订单，再与归档核对；
不会使用归档订单决定交易。188笔订单与3,248条日净值均已验证一致。

结果写入 `results/broad-market/`：`README.md` 可直接查看摘要，`summary.json` 包含指标与核对误差，
`equity.csv` 为每日净值，`orders.json` 为重新生成的订单。复现不需要网络或API密钥。
若只想运行首页方案的测试期：

```sh
python3 examples/studies/broad_market/replay.py --strategy posthoc --partition test --output results/broad-market-162
```

`--strategy frozen` 对应 #478，`posthoc` 对应 #162；后者是事后测试比较方案，不是冻结冠军。
默认容许的数值误差为 `1e-8`；任何订单日期、标的、权重或日净值不匹配都会报错。

```text
examples/studies/broad_market/
├── frozen_strategy.py / posthoc_strategy.py  # 两份原始策略快照
├── engine.py                               # 原始评估器
├── replay.py / requirements.txt             # 复现入口与固定依赖
├── data/prices.csv                          # 2010—2026完整行情
├── data/universe.json                       # 标的与来源说明
├── manifest.json                           # 文件哈希和评估协议
└── reproduction.json                        # 已核对的复现结果
```

源码、评估器和完整行情均与冻结归档逐字节一致。行情包含4,055个交易日、24个可选标的及1个仅供参考的序列，
保留上市前和缺失报价的空值。验证与测试使用的行情与统一全收益报告完全相同；信号只使用当日及此前信息，
各分区从独立策略状态和现金净值1开始。该独立入口复现已公开实验，不重新启动20小时搜索，
也不修改历史冻结记录；这两份多标的策略不能直接替换最简运行器的默认单指数策略。

## 结果

| 策略 | 选择方式 | 验证年化收益 | 测试累计收益 | 测试年化收益 | 测试最大回撤 |
|---|---|---:|---:|---:|---:|
| #478 | 验证集选出并冻结 | 43.75% | 116.70% | 23.33% | 31.00% |
| #162 | 事后比较的测试收益最高节点 | 37.14% | 172.52% | 31.24% | 30.05% |

净值图比较 #162、创业板买入持有和沪深300买入持有，三条曲线起点均为1。
研究过程合并图使用相同的净值对比，下方展示18个节点的验证、测试年化收益和最大回撤；
横轴显示原尝试编号，各节点等间距排列，不代表相等的研究耗时。

| 测试期方案 | 累计收益 | 年化收益 | 最大回撤 |
|---|---:|---:|---:|
| #162（事后比较） | 172.52% | 31.24% | 30.05% |
| 创业板买入持有 | 47.32% | 11.08% | 40.88% |
| 沪深300买入持有 | 28.13% | 6.95% | 22.41% |

创业板使用159915 ETF后复权行情，沪深300使用H00300全收益指数，均取自本次实验的数据。
两条基准在2023年1月3日收盘发出买入指令，1月4日收盘全仓买入，扣除0.03%买入费用，
之后保持份额不变，期末不卖出。费用已保留在净值中，没有在买入后重新归一化。
沪深300单指数实验现已使用相同的全收益行情，基准净值逐日完全一致。

#162从18个已评估的历史验证冠军中事后选出，不代表全部488次尝试均接受测试，
也没有替换最终冻结策略 #478。#478测试年化未达到30%目标，回撤也超过其对应约28.00%的上限。
#162达到本次事后比较的数值门槛，但这不构成一次新的独立盲测成功。

需要注意，验证集上的持续改进不一定会稳定转化为测试集提升，因此需要观察过拟合情况。

## 评估口径

| 设置 | 内容 |
|---|---|
| 实际经过时间预算 | 配置上限为20小时 |
| 训练集 | 2010—2019年 |
| 验证集 | 2020—2022年 |
| 测试交易日期 | 2023年1月3日至2026年9月11日，共896日 |
| Reward | 满足约束时最大化净年化收益 |
| 年化收益目标 | ≥30% |
| 回撤上限 | `min(50%, 26.34% + (CAGR − 20%) / 2)` |
| 交易费用 | 每边0.03%，按实际成交金额扣除 |
| 执行 | 收盘形成信号，下一交易日收盘成交 |
| 年化口径 | 实际日历天数 / 365.2425 |
| 仓位 | 只做多、无杠杆，现金利息为零，期末不强制清仓 |

各分区从现金净值1开始，执行、费用和年化均与单指数实验的统一复评一致。
公共评估器复核了宽基全部29,232条归档日净值，结果完全相同。
本测试时间段在此前研究中已经出现，现有结果也已公开，
后续验证需要新的、未参与选择的数据。

## 图表数据

- [figures/test_equity.csv](figures/test_equity.csv)：图中的三条每日净值曲线。
- [figures/comparison_metrics.json](figures/comparison_metrics.json)：三种方案的累计收益、年化收益与最大回撤。
- [benchmark_closes.csv](benchmark_closes.csv)、[benchmark_sources.json](benchmark_sources.json)：基准价格与来源、哈希、计算口径。
- [best_methods_test_curves.csv](best_methods_test_curves.csv)：原始策略曲线归档，保留 #162及 #478；当前图不展示 #478。
- [stage_metrics.csv](stage_metrics.csv)：18个历史验证冠军节点的指标与约束判定。
- [presentation_selection.json](presentation_selection.json)：图中策略的选择方式与角色。

策略曲线来自已完成的归档。固定订单通过公共评估器重放，没有重新搜索策略或修改冻结测试记录。
重新计算报告并绘图（仅绘图需要Matplotlib）：

```sh
python3 examples/studies/total_return/evaluate.py --market broad_market
python3 examples/studies/total_return/plot.py --market broad_market
```

[统一日净值与指标](../total_return/broad_market/)包含全部18个节点。
上面列出的原文件保留为历史归档；当前图由 `total_return/` 的公共绘图代码生成。
