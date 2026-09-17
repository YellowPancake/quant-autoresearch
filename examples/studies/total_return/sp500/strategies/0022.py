import statistics
def fit(train):return {'position':1.}
def allocate(obs,state):
    r=obs[0];p=r['history'];ret=[p[i]/p[i-1]-1 for i in range(len(p)-60,len(p))]
    ratio=statistics.stdev(ret[-5:])/max(statistics.stdev(ret),.001)
    if ratio>2 and p[-1]<sum(p[-20:])/20:state['position']=0.
    elif p[-1]>sum(p[-10:])/10:state['position']=1.
    return {r['symbol']:state['position']}
