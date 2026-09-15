# 固定指标工具库

位置 `core/indicators.py`。Agent 可导入、选择参数、组合因子，也可在策略文件中实现新因子；
不能修改该库。工具库与评估代码一起冻结并复制到每个研究工作区，无第三方依赖。
指标函数不访问磁盘、网络、训练标签或测试数据，只使用传入的历史数组。

| 函数 | 默认参数 | 计算口径 | 最少数据 |
|---|---|---|---|
| sma | period=20 | 简单均线，含当日 | 20条 |
| ema | period=20 | 首20条SMA初始化，alpha=2/(n+1) | 20条 |
| macd | fast=12, slow=26, signal=9 | 独立EMA之差DIF，DIF的EMA为DEA，hist=2×(DIF−DEA) | DIF26条，DEA/hist34条 |
| boll | period=20, width=2 | SMA±2倍总体标准差（ddof=0） | 20条 |
| rsi | period=14 | Wilder平滑，初始14个涨跌幅均值；全平50、无跌100 | 15条 |
| atr | period=14 | TR取日内幅度与相对昨收跳空幅度最大值，Wilder平滑 | 15条OHLC |
| roc | period=1 | n日简单收益率，小数表示，0.01即1% | n+1条 |
| volatility | period=20, annualization=252 | 20个日简单收益的样本标准差×√252 | 21条 |
| donchian | period=20 | 当前日及此前19日的最高/最低价 | 20条high/low |
| volume_ratio | period=20 | 当日量÷前20日均量（不含当日） | 21条量 |

volume_ratio 是日线相对量能，不是行情软件的盘中“量比”。也可传同口径成交额。
暂不添加大量K线形态、重复振荡指标或自动选参；后续按实验需要扩充。

## 一致约定

- 输入按时间升序；输出数组与输入等长，`[-1]` 取当前值。多输出函数返回字典。
- 暖启动不足、缺失值或分母为0时输出 None，不能把它当成有效的0。
- EMA/RSI/ATR遇到缺失后重新积累完整暖启动；NaN/Inf直接拒绝。
- 当日数据只适用于收盘后信号。Donchian突破前高比较应取此前通道（例如 `upper[-2]`）。
- 种子、标准差和MACD柱倍数在不同平台可能不同；本库遵守上表，不承诺与TA-Lib逐值相等。
- EMA等递归指标对起始位置敏感。刚达到最少数据不等于充分稳定，截短窗口与长历史结果可能不同。

## Agent 用法

```python
from core.indicators import sma, boll, rsi

prices = observation['history']
moving_average = sma(prices, 20)[-1]
bands = boll(prices, 20)
strength = rsi(prices, 14)[-1]
# 检查 None 后再组合信号。交易阈值与组合方式由策略决定。
```

开源示例默认120日窗口，支持MACD、MA60等。修改窗口须在准备数据前同步修改
config/research.json和config/time.json；不能让Agent访问工作区外的数据补算。
CSV示例只暴露close历史；ATR和量能指标需要额外的OHLCV适配器。

指标类别参考 [TA-Lib函数目录](https://ta-lib.github.io/ta-lib-python/funcs.html)，实现及具体口径由本库明确规定。
