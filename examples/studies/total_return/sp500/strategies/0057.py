import math
import statistics

def base_features(row):
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

def features(row):
    x=base_features(row)
    return x[:8]+x[12:]

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

def risk_ratio(row):
    p=row['history'];r=[p[i]/p[i-1]-1 for i in range(len(p)-60,len(p))]
    return statistics.stdev(r[-5:])/max(statistics.stdev(r),.001)
def add_risk(model,train):
    v=sorted(risk_ratio(r) for r in train);n=len(v)
    model.update({'gate':1.,'exit':v[int(.95*(n-1))],'recover':v[int(.70*(n-1))]})
    return model
def gate(row,state):
    p=row['history'];v=risk_ratio(row)
    if v>state['exit'] and p[-1]<min(p[-4:-1]):state['gate']=0.
    elif p[-1]>sum(p[-10:])/10 or v<state['recover']:state['gate']=1.
    return state['gate']

def fit(train):
    horizon=20
    xs=[features(r) for r in train[:-horizon+1]]
    log_returns=[math.log1p(r['forward_return']) for r in train]
    ys=[sum(log_returns[i:i+horizon])/horizon for i in range(len(xs))]
    cut=int(len(xs)*.7);best=None
    for ridge in (.01,.1,1.):
        m=train_model(xs[:cut-horizon-1],ys[:cut-horizon-1],ridge)
        error=sum((predict(x,m)-y)**2 for x,y in zip(xs[cut:],ys[cut:]))
        if best is None or error<best[0]:best=(error,ridge)
    model=train_model(xs,ys,best[1]);model['position']=1.
    return add_risk(model,train)

def allocate(obs,state):
    row=obs[0];mu=predict(features(row),state)
    threshold=.001/20
    if mu>threshold:state['position']=1.
    elif mu<-threshold:state['position']=0.
    return {row['symbol']:state['position']*gate(row,state)}
