# Input data contract

The distribution bundle includes CSI300 and S&P 500 histories under data/.
Use prepare.py to create separate study workspaces. For another instrument, convert
its data to the same schema. There is no market-data downloader or Hugging Face dependency.

| Column | Type | Meaning |
|---|---|---|
| date | `YYYY-MM-DD` | Local market session date |
| index_id or symbol | nonempty string | Stable instrument identifier; symbol takes precedence if both are supplied |
| open | finite positive number | Opening price or index level |
| close | finite positive number | Closing price or index level |

One row per `(date, instrument identifier)`. Order may vary; preparation sorts the input. Multiple
symbols must have exactly the same dates. All four fields are required. Extra columns
are ignored; they do not automatically become features visible to the strategy.

The source owner must validate actual sessions, missing observations, time zones, price
adjustments and units before preparation. The adapter checks duplicates, positive finite
prices and panel balance; it cannot detect an omitted session shared by every symbol.
Do not fill missing trading sessions with invented prices. Do not combine different
market calendars into one balanced panel by forward-filling prices.

## What a candidate sees

For signal session `t`, `history` contains the configured number of trailing closes
through `t`. `fit(train)` gets training records with `forward_return` labels.
`allocate(observations, state)` receives `symbol`, `date`, `history`, without labels.
It returns nonnegative portfolio weights totaling at most one; the balance is cash.

The label is `open[t+2] / open[t+1] - 1`: act after close `t`, execute at open `t+1`,
then hold to open `t+2`. End labels and signal dates must lie in the same partition.
The adapter uses session order, not UTC timestamps. `signal_time` in the example policy
describes this convention; it is not an intraday timestamp execution engine.

The CSV adapter does not expose volume, high, low, fundamental data or publication
timestamps. Rich bars require an explicit adapter and availability policy. Auxiliary
indicator functions alone do not make those fields available to an agent.

## Reproducibility and ownership

Keep the raw source, download timestamp, source identifiers, calendar/adjustment
conventions, repair log and checksum with the researcher's data snapshot.
Preparation records the CSV hash, actual sample counts, protocol, evaluator/policy
hashes and partition hashes in `cache/manifest.json`. Re-downloading later may yield
revised data; reproduce a study using the same source snapshot.

Use market-specific data and costs for each study. For indices, state whether the input
is a price index or a total-return index. For tradable funds, document distributions,
splits and the consistent price basis used by both open and close.

Raw source CSVs and final holdout directories must be outside each study workspace. This
prevents accidental bundling; it does not restrict a process that can read parent
directories. Strong isolation needs a separate evaluator and OS permissions. Public
historical data remain reconstructible even if a local test file is inaccessible.
