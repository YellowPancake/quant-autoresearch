from core.indicators import sma, ema, macd, boll, rsi, roc, volatility

def fit(train):
    return {'invested': False, 'age': 0, 'entry': 0.}

def allocate(observations, state):
    row=observations[0]
    p=row['history']
    x=rsi(p,14)[-1]
    if state['invested'] and (x>55 or p[-1]<.92*state['entry']): state['invested']=False
    elif not state['invested'] and x<30:
        state['invested']=True
        state['entry']=p[-1]
    return {row['symbol']: 1.0} if state['invested'] else {}
