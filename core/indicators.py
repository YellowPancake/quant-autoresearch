"""Causal, standard-library indicators. Inputs oldest first; outputs aligned to inputs.

Only the supplied history is used. None resets recursive warmup; insufficient
history and zero denominators produce None, never a fabricated zero. EMA uses
an SMA seed; RSI/ATR use Wilder smoothing. See docs/INDICATORS.md for conventions.
The research agent may import this frozen module, but may not edit it.
"""
import math
import statistics


def _period(value, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'period must be an integer >= {minimum}')
    return value


def _values(values):
    result = [None if x is None else float(x) for x in values]
    if any(x is not None and not math.isfinite(x) for x in result):
        raise ValueError('Use None for missing values; NaN/Inf are invalid')
    return result


def _rolling(values, period, function):
    period = _period(period)
    values = _values(values)
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i-period+1:i+1]
        if all(x is not None for x in window):
            result[i] = function(window)
    return result


def sma(values, period=20):
    """Simple moving average, including the current observation."""
    return _rolling(values, period, statistics.fmean)


def _smooth(values, period, alpha):
    period = _period(period)
    output, seed, current = [], [], None
    for value in _values(values):
        if value is None:
            seed, current = [], None
        elif current is None:
            seed.append(value)
            if len(seed) == period:
                current = statistics.fmean(seed)
        else:
            current += alpha * (value - current)
        output.append(current)
    return output


def ema(values, period=20):
    """SMA-seeded EMA with alpha=2/(period+1); minimum period observations."""
    period = _period(period)
    return _smooth(values, period, 2 / (period + 1))


def macd(close, fast=12, slow=26, signal=9):
    """Return dif, dea, hist; hist=2*(dif-dea). Default DEA needs 34 prices."""
    _period(fast); _period(slow); _period(signal)
    if fast >= slow:
        raise ValueError('MACD fast must be less than slow')
    close = _values(close)
    dif = [None if a is None or b is None else a-b for a, b in zip(ema(close, fast), ema(close, slow))]
    dea = ema(dif, signal)
    hist = [None if a is None or b is None else 2*(a-b) for a, b in zip(dif, dea)]
    return {'dif': dif, 'dea': dea, 'hist': hist}


def boll(close, period=20, width=2.0):
    """Bollinger bands, SMA +/- width * population standard deviation."""
    width = float(width)
    if not math.isfinite(width) or width <= 0:
        raise ValueError('BOLL width must be finite and positive')
    close = _values(close)
    middle = sma(close, period)
    std = _rolling(close, period, statistics.pstdev)
    return {'middle': middle,
            'upper': [None if m is None else m+width*s for m, s in zip(middle, std)],
            'lower': [None if m is None else m-width*s for m, s in zip(middle, std)]}


def rsi(close, period=14):
    """Wilder RSI; needs period+1 prices. Flat window is 50, no losses is 100."""
    period = _period(period)
    close = _values(close)
    changes = [None] + [None if a is None or b is None else b-a for a, b in zip(close, close[1:])] if close else []
    gain = _smooth([None if d is None else max(d, 0) for d in changes], period, 1/period)
    loss = _smooth([None if d is None else max(-d, 0) for d in changes], period, 1/period)
    return [None if g is None else 50.0 if g+l == 0 else 100*g/(g+l) for g, l in zip(gain, loss)]


def _hlc(high, low, close):
    high, low, close = map(_values, (high, low, close))
    if not len(high) == len(low) == len(close):
        raise ValueError('OHLC series lengths must match')
    if any(h is not None and l is not None and h < l for h, l in zip(high, low)):
        raise ValueError('High must not be below low')
    return high, low, close


def atr(high, low, close, period=14):
    """Wilder ATR in price units; needs period+1 bars, including prior close."""
    period = _period(period)
    high, low, close = _hlc(high, low, close)
    tr = [None] * len(close)
    for i in range(1, len(close)):
        h, l, prev = high[i], low[i], close[i-1]
        if h is not None and l is not None and prev is not None and close[i] is not None:
            tr[i] = max(h-l, abs(h-prev), abs(l-prev))
    return _smooth(tr, period, 1/period)


def roc(close, period=1):
    """Fractional simple return: close[t]/close[t-period]-1; .01 means 1%."""
    period = _period(period)
    close = _values(close)
    result = [None] * len(close)
    for i in range(period, len(close)):
        old, new = close[i-period], close[i]
        if old is not None and old != 0 and new is not None:
            result[i] = new/old - 1
    return result


def volatility(close, period=20, annualization=252):
    """Sample stdev of period daily simple returns * sqrt(annualization)."""
    _period(period, 2)
    annualization = float(annualization)
    if not math.isfinite(annualization) or annualization <= 0:
        raise ValueError('annualization must be finite and positive')
    return _rolling(roc(close), period, lambda w: statistics.stdev(w)*math.sqrt(annualization))


def donchian(high, low, period=20):
    """Current-inclusive rolling high/low. Shift by one bar for prior-channel breaks."""
    high, low, _ = _hlc(high, low, high)
    return {'upper': _rolling(high, period, max), 'lower': _rolling(low, period, min)}


def volume_ratio(volume, period=20):
    """Current volume divided by mean of previous period bars, excluding today.

    This is a daily relative-volume feature, not intraday market-software liangbi.
    """
    volume = _values(volume)
    if any(x is not None and x < 0 for x in volume):
        raise ValueError('Volume cannot be negative')
    prior = sma([None] + volume[:-1], period) if volume else sma([], period)
    return [None if v is None or m is None or m == 0 else v/m for v, m in zip(volume, prior)]
