# Broad-market replay data / 宽基复现数据

`prices.csv` is the unchanged frozen input panel: 4,055 Chinese exchange sessions
from 2010-01-04 through 2026-09-11. `date` is the session date; the other 25 columns
are instrument keys defined in `universe.json` (24 selectable, one reference-only).
Values are total-return index levels or dividend-adjusted ETF closes. Their absolute
scales differ; returns are calculated within each series. Dividends must not be added again.

Empty cells mean pre-launch or unavailable quotes, not zero prices. Not every asset
exists throughout the full history. The supplied panel already masks pre-launch
index history; the evaluator requires 21 valid observations for eligibility.
Missing prices are carried only to value existing holdings, never to execute trades
or fill indicator inputs. Instrument sources, types, launch dates where recorded,
and original source hashes are in `universe.json`; the whole-panel hash is in
[`../manifest.json`](../manifest.json).

Training uses 2010–2019. Validation uses 2020–2022; test uses 2023–2026-09-11.
Earlier observations supply trailing history. The validation/test slice exactly
matches the data used in the published unified total-return report.

`prices.csv` 与冻结输入逐字节一致，包含4,055个中国交易所交易日。
`date` 为交易日期，其余25列对应 `universe.json` 中的标的：24个可选，1个仅供参考。
数值为全收益指数点位或含分红复权ETF收盘价，不能重复添加分红，也不能直接比较不同序列的绝对数值。
空值表示尚未上市或缺失报价；并非所有标的都有完整的2010年以来历史。
缺失报价只允许用于已有持仓估值时沿用前值，不用于补造指标或成交价。
本目录同时包含已公开的训练、验证与测试行情，供研究者复现结果；新实验的研究Agent不应访问它。
