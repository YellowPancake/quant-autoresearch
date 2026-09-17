import math
import statistics

def features(row):
    p=row['history'];b=row['history_bars']
    ret=[p[i]/p[i-1]-1 for i in range(len(p)-21,len(p))]
    v=max(statistics.stdev(ret[-20:]),.003)
    v5=max(statistics.stdev(ret[-5:]),.001)
    current=b[-1];span=max(current['high']-current['low'],p[-1]*.0001)
    return [
        (p[-1]/p[-2]-1)/v,
        (p[-1]/p[-6]-1)/(v*math.sqrt(5)),
        (p[-1]/p[-22]-1)/(v*math.sqrt(21)),
        (p[-1]/p[-64]-1)/(v*math.sqrt(63)),
        (p[-1]/(sum(p[-200:])/200)-1)/(v*math.sqrt(200)),
        (sum(p[-50:])/50/(sum(p[-200:])/200)-1)/(v*math.sqrt(150)),
        v5/v-1,
        v,
        (current['close']-current['low'])/span-.5,
        (current['close']/current['open']-1)/v,
        (current['open']/b[-2]['close']-1)/v,
        (current['high']-current['low'])/current['close']/v,
        (p[-1]/max(p[-63:])-1)/(v*math.sqrt(63)),
    ]

def solve(matrix,rhs):
    n=len(rhs);a=[list(row)+[rhs[i]] for i,row in enumerate(matrix)]
    for i in range(n):
        pivot=max(range(i,n),key=lambda j:abs(a[j][i]))
        a[i],a[pivot]=a[pivot],a[i]
        if abs(a[i][i])<1e-12:a[i][i]=1e-12
        d=a[i][i];a[i]=[v/d for v in a[i]]
        for j in range(n):
            if j!=i:
                d=a[j][i];a[j]=[x-d*y for x,y in zip(a[j],a[i])]
    return [row[-1] for row in a]

def train_model(xs,ys,ridge):
    n=len(xs);k=len(xs[0])
    means=[sum(x[j] for x in xs)/n for j in range(k)]
    scales=[max(statistics.pstdev(x[j] for x in xs),.00001) for j in range(k)]
    z=[[max(-5,min(5,(x[j]-means[j])/scales[j])) for j in range(k)] for x in xs]
    mu=sum(ys)/n
    matrix=[[sum(x[i]*x[j] for x in z)/n+(ridge if i==j else 0) for j in range(k)] for i in range(k)]
    rhs=[sum(x[j]*(y-mu) for x,y in zip(z,ys))/n for j in range(k)]
    return {'mean':means,'scale':scales,'beta':solve(matrix,rhs),'mu':mu}

def predict(x,m):
    return m['mu']+sum(b*max(-5,min(5,(v-a)/s)) for v,a,s,b in zip(x,m['mean'],m['scale'],m['beta']))

def fit(train):
    xs=[features(r) for r in train];ys=[max(-.1,min(.1,r['forward_return'])) for r in train]
    cut=int(len(train)*.7);best=None
    for ridge in (.01,.1,1.):
        m=train_model(xs[:cut-2],ys[:cut-2],ridge)
        error=sum((predict(x,m)-y)**2 for x,y in zip(xs[cut:],ys[cut:]))
        if best is None or error<best[0]:best=(error,ridge)
    model=train_model(xs,ys,best[1]);model['position']=0.;return model

def allocate(obs,state):
    r=obs[0];p=r['history'];mu=predict(features(r),state)
    if mu>.0005:state['position']=1.
    elif mu<-.0005:state['position']=0.
    ret=[p[i]/p[i-1]-1 for i in range(len(p)-60,len(p))]
    ratio=statistics.stdev(ret[-5:])/max(statistics.stdev(ret),.001)
    risk=state.get('risk',1.)
    if ratio>2 and p[-1]<sum(p[-20:])/20:risk=0.
    elif p[-1]>sum(p[-10:])/10 or ratio<1.4:risk=1.
    state['risk']=risk
    return {r['symbol']:state['position']*risk}
