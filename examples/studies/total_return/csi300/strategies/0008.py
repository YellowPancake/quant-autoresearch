from core.indicators import sma, ema, macd, rsi, roc, volatility

def fit(train):
    return {'invested': False}

def allocate(observations, state):
    row = observations[0]
    p = row['history']
    m = macd(p)
    weight = float(m['dif'][-1] > 0 and m['hist'][-1] > 0)
    return {row['symbol']: weight} if weight else {}
