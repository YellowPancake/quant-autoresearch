import statistics
def ratio(row):
    p=row['history'];ret=[p[i]/p[i-1]-1 for i in range(len(p)-60,len(p))]
    return statistics.stdev(ret[-5:])/max(statistics.stdev(ret),.001)
def fit(train):
    values=sorted(ratio(r) for r in train);n=len(values)
    return {'position':1.,'exit':values[int(.95*(n-1))],'recover':values[int(.70*(n-1))]}

def allocate(obs,state):
    r=obs[0];p=r['history'];v=ratio(r)
    if v>state['exit'] and p[-1]<min(p[-4:-1]):state['position']=0.
    elif p[-1]>sum(p[-10:])/10 or v<state['recover']:state['position']=1.
    return {r['symbol']:state['position']}
