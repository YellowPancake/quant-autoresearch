import math,statistics
from core.indicators import rsi

RIDGE=1.0
ENTRY=0.0005
RECENT=False
NONLINEAR=False

def features(row):
    p=row['history'];b=row['history_bars'];last=b[-1]
    rets=[p[i]/p[i-1]-1 for i in range(len(p)-20,len(p))]
    spread=last['high']-last['low']
    vols=[x['volume_native'] for x in b[-21:-1] if x['volume_native'] is not None]
    v=last['volume_native']
    x=[p[-1]/p[-1-n]-1 for n in (1,5,20,60)]
    x += [p[-1]/statistics.fmean(p[-n:])-1 for n in (5,20,60)]
    x += [rsi(p,14)[-1]/100,rsi(p,2)[-1]/100,statistics.stdev(rets),
          (last['close']-last['low'])/spread if spread else .5,
          spread/p[-2],last['close']/last['open']-1,last['open']/p[-2]-1,
          v/statistics.fmean(vols)-1 if v is not None and vols and statistics.fmean(vols)>0 else 0.]
    if NONLINEAR:
        x += [max(-x[5],0),max(x[5],0),x[0]*x[0],x[4]*x[4],x[7]*x[9],x[10]*x[0]]
    return x


import random
HORIZON=5
DEPTH=3
MIN_LEAF=120
AGREEMENT=False

def build(x,y,ids,depth,rng):
    total=sum(y[i] for i in ids);n=len(ids)
    prediction=total/(n+50)
    if depth==0 or n<MIN_LEAF*2:return (prediction,)
    best_gain=0.;best=None
    for j in rng.sample(range(len(x[0])),5):
        values=sorted(x[i][j] for i in ids)
        for q in (.2,.4,.6,.8):
            cut=values[int((n-1)*q)]
            left=[i for i in ids if x[i][j]<=cut];right=[i for i in ids if x[i][j]>cut]
            if min(len(left),len(right))<MIN_LEAF:continue
            sl=sum(y[i] for i in left);sr=total-sl
            gain=sl*sl/len(left)+sr*sr/len(right)-total*total/n
            if gain>best_gain:
                best_gain=gain;best=(j,cut,left,right)
    if best is None:return (prediction,)
    j,cut,left,right=best
    return (j,cut,build(x,y,left,depth-1,rng),build(x,y,right,depth-1,rng))

def predict(tree,x):
    while len(tree)>1:
        j,cut,left,right=tree;tree=left if x[j]<=cut else right
    return tree[0]

def fit(train):
    n=len(train)-HORIZON+1
    y=[max(-.15,min(.15,math.prod(1+r['forward_return'] for r in train[i:i+HORIZON])-1)) for i in range(n)]
    x=[features(r) for r in train[:n]]
    rng=random.Random(711)
    trees=[build(x,y,[rng.randrange(n) for _ in range(n)],DEPTH,rng) for _ in range(20)]
    return {'trees':trees,'invested':False}

def allocate(observations,state):
    row=observations[0];x=features(row)
    estimates=[predict(t,x) for t in state['trees']]
    mean=statistics.fmean(estimates);votes=sum(v>0 for v in estimates)/len(estimates)
    if mean>.0002*HORIZON and (not AGREEMENT or votes>=.6):state['invested']=True
    elif mean<0 or (AGREEMENT and votes<.4):state['invested']=False
    strength=rsi(row['history'],14)[-1]
    if state.get('reversal',False):
        state['reversal_age']+=1
        if strength>55 or state['reversal_age']>=20:state['reversal']=False
    elif strength<30:
        state['reversal']=True;state['reversal_age']=0
    weight=float(state['invested'] or state.get('reversal',False))
    return {row['symbol']:weight} if weight else {}
