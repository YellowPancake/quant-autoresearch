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
    for n in (10,20,60):
        changes=[p[i]-p[i-1] for i in range(len(p)-n,len(p))]
        path=sum(abs(v) for v in changes)
        x += [(p[-1]-p[-n-1])/path if path else 0.,sum(v>0 for v in changes)/n]
    all_rets=[p[i]/p[i-1]-1 for i in range(1,len(p))]
    v5=statistics.stdev(all_rets[-5:]);v20=statistics.stdev(all_rets[-20:]);v60=statistics.stdev(all_rets[-60:])
    downside=math.sqrt(statistics.fmean(min(v,0.)**2 for v in all_rets[-20:]))
    x += [v5/max(v20,1e-8),v20/max(v60,1e-8),downside/max(v20,1e-8),max(abs(v) for v in all_rets[-20:])/max(v20,1e-8)]
    for n in (5,20):
        ibs=[];bodies=[];wicks=[]
        for bar in b[-n:]:
            width=bar['high']-bar['low']
            ibs.append((bar['close']-bar['low'])/width if width else .5)
            bodies.append((bar['close']-bar['open'])/width if width else 0.)
            wicks.append((bar['high']-max(bar['close'],bar['open'])-min(bar['close'],bar['open'])+bar['low'])/width if width else 0.)
        x += [statistics.fmean(ibs),statistics.fmean(bodies),statistics.fmean(wicks)]
    for n in (5,20,60):
        volume_pairs=[((1 if p[i]>p[i-1] else -1 if p[i]<p[i-1] else 0),b[i]['volume_native']) for i in range(len(p)-n,len(p)) if b[i]['volume_native'] is not None]
        total=sum(v for _,v in volume_pairs)
        x.append(sum(sign*v for sign,v in volume_pairs)/total if total>0 else 0.)
    for n in (5,20,60):
        overnight=sum(math.log(b[i]['open']/p[i-1]) for i in range(len(p)-n,len(p)))
        intraday=sum(math.log(b[i]['close']/b[i]['open']) for i in range(len(p)-n,len(p)))
        x += [overnight,intraday]
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

GROUPS=[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]]
MODE='majority'

def fit(train):
    n=len(train)-HORIZON+1
    y=[max(-.15,min(.15,math.prod(1+r['forward_return'] for r in train[i:i+HORIZON])-1)) for i in range(n)]
    full=[features(r) for r in train[:n]]
    models=[]
    for indices in GROUPS:
        x=[[row[j] for j in indices] for row in full]
        rng=random.Random(711)
        trees=[build(x,y,[rng.randrange(n) for _ in range(n)],DEPTH,rng) for _ in range(20)]
        models.append({'trees':trees,'indices':indices,'invested':False})
    return {'models':models,'invested':False}

def allocate(observations,state):
    row=observations[0];full=features(row)
    means=[];signals=[]
    for model in state['models']:
        x=[full[j] for j in model['indices']]
        mean=statistics.fmean(predict(t,x) for t in model['trees'])
        if mean>.0002*HORIZON:model['invested']=True
        elif mean<0:model['invested']=False
        means.append(mean);signals.append(model['invested'])
    if MODE=='prediction':
        mean=statistics.fmean(means)
        if mean>.0002*HORIZON:state['invested']=True
        elif mean<0:state['invested']=False
    elif MODE=='union':state['invested']=any(signals)
    elif MODE=='intersection':state['invested']=all(signals)
    else:state['invested']=sum(signals)>len(signals)/2
    strength=rsi(row['history'],14)[-1]
    if state.get('reversal',False):
        state['reversal_age']+=1
        if strength>50 or state['reversal_age']>=20:state['reversal']=False
    elif strength<30:
        state['reversal']=True;state['reversal_age']=0
    weight=float(state['invested'] or state.get('reversal',False))
    return {row['symbol']:weight} if weight else {}
