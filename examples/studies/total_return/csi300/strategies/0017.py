from core.indicators import sma, ema, macd, boll, rsi, roc, volatility

def fit(train):
    return {'invested': False, 'age': 0, 'entry': 0.}

def allocate(observations, state):
    row=observations[0]
    p=row['history']
    m=sma(p,20)[-1]
    if p[-1]<.95*m: state['invested']=True
    elif p[-1]>m: state['invested']=False
    return {row['symbol']: 1.0} if state['invested'] else {}
