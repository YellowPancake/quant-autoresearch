from core.indicators import sma, ema, macd, rsi, roc, volatility

def fit(train):
    return {'invested': False}

def allocate(observations, state):
    row = observations[0]
    p = row['history']
    strength = rsi(p,14)[-1]
    if strength < 30: state['invested'] = True
    elif strength > 55: state['invested'] = False
    weight = float(state['invested'])
    return {row['symbol']: weight} if weight else {}
