import math
def fit(train):return {'position':1.}
def allocate(obs,state):
    r=obs[0];p=r['history'];ret=[p[i]/p[i-1]-1 for i in range(len(p)-60,len(p))]
    short=math.sqrt(sum(min(0,x)**2 for x in ret[-5:])/5)
    long=math.sqrt(sum(min(0,x)**2 for x in ret)/60)
    ratio=short/max(long,.001)
    if ratio>2 and p[-1]<sum(p[-20:])/20:state['position']=0.
    elif p[-1]>sum(p[-10:])/10 or ratio<1.4:state['position']=1.
    return {r['symbol']:state['position']}
