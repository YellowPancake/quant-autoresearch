from core.indicators import sma, ema, macd, boll, rsi, roc, volatility

def fit(train):
    return {'invested': False, 'age': 0, 'entry': 0.}

def allocate(observations, state):
    row=observations[0]
    p=row['history']
    x=rsi(p,14)[-1]
    if x<30: state['invested']=True
    elif x>70: state['invested']=False
    return {row['symbol']: 1.0} if state['invested'] else {}
