"""The ONLY file the research agent edits. Standard library, CPU-only baseline.

fit receives training records including forward_return.
allocate receives a single signal date's records WITHOUT forward labels.
Each record contains symbol, date, history (oldest -> newest closes).
The minimal CSV adapter exposes close history; it does not provide OHLCV bars.
Decide after today's close; execute at next session's open, hold to following open.
Return {symbol: portfolio_weight}; long-only, sum <= 1, remainder cash.
"""


def fit(train):
    # Replace with learned factors/models if useful. Only train has labels.
    return {"lookback": 10, "top_k": 5}


def allocate(observations, state):
    def score(row):
        prices = row["history"]
        return prices[-1] / prices[-state["lookback"]] - 1
    ranked = sorted(observations, key=score, reverse=True)
    selected = ranked[:state["top_k"]]
    return {row["symbol"]: 1 / len(selected) for row in selected}
