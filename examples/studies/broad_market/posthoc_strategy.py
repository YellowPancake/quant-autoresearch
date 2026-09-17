EDGE=0.0012
import numpy as np
import pandas as pd
from engine import features
PARAMS={'horizon': 20, 'mode': 'hierarchy', 'top': 1, 'gate': True, 'nonlinear': False}
KEYS=['mom5', 'mom20', 'mom60', 'mom120', 'trend20', 'trend120', 'vol20', 'vol60', 'dd60']

def fit(train):
    h=PARAMS['horizon']; f=features(train)
    x=np.stack([f[k] for k in KEYS],axis=2)
    y=(train.shift(-h-1)/train.shift(-1)-1).to_numpy()
    if PARAMS['nonlinear']:
        # Fixed nonlinear expansion, not data-derived future regimes.
        x=np.concatenate([x,np.tanh(x[:,:,:4]*5),x[:,:,8:9]*x[:,:,:2]/100],axis=2)
    good=np.isfinite(x).all(2)&np.isfinite(y)
    for j,k in enumerate(train.columns):
        if k=='bank':good[:,j]=False
    enddate=pd.Series(train.index,index=train.index).shift(-h-1)
    best=None
    for penalty in [.01,.1,1.]:
        losses=[]
        for cut,nextend in [('2015-12-31','2017-12-31'),('2017-12-31','2019-12-31')]:
            tr=good & (enddate.le(pd.Timestamp(cut)).to_numpy()[:,None])
            va=good & ((train.index>pd.Timestamp(cut))&(train.index<=pd.Timestamp(nextend)))[:,None]
            if tr.sum()<500 or va.sum()<100:continue
            xx=x[tr];yy=y[tr];mu=xx.mean(0);sd=np.maximum(xx.std(0),1e-5)
            z=np.clip((xx-mu)/sd,-6,6);ym=yy.mean()
            beta=np.linalg.solve(z.T@z+np.eye(z.shape[1])*len(z)*penalty,z.T@(yy-ym))
            pred=np.clip((x[va]-mu)/sd,-6,6)@beta+ym
            losses.append(np.mean((pred-y[va])**2))
        loss=float(np.mean(losses)) if losses else np.inf
        if best is None or loss<best[0]:best=(loss,penalty)
    xx=x[good];yy=y[good];mu=xx.mean(0);sd=np.maximum(xx.std(0),1e-5)
    z=np.clip((xx-mu)/sd,-6,6);ym=yy.mean()
    beta=np.linalg.solve(z.T@z+np.eye(z.shape[1])*len(z)*best[1],z.T@(yy-ym))
    return dict(mu=mu,sd=sd,beta=beta,mean=ym,style=None,held=0,weights=None,member=None,selected_penalty=best[1],training_cv_mse=best[0])

def allocate(o,s):
    if not o['weekly']:return None
    f=o['features'];names=o['symbols'];good=o['eligible'].copy()
    x=np.stack([f[k] for k in KEYS],axis=1)
    if PARAMS['nonlinear']:x=np.concatenate([x,np.tanh(x[:,:4]*5),x[:,8:9]*x[:,:2]/100],axis=1)
    good &= np.isfinite(x).all(1)
    pred=np.clip((x-s['mu'])/s['sd'],-6,6)@s['beta']+s['mean']
    if PARAMS['mode']=='hierarchy':
        value=[names.index(k) for k in ['dividend','value300','lowvol'] if good[names.index(k)]]
        growth=[names.index(k) for k in ['growth','chinext50','star50'] if good[names.index(k)]]
        if not value or not growth:return None
        a=np.mean(f['rsi14'][value]);b=np.mean(f['rsi14'][growth]);proposed='value' if a>b else 'growth'
        if s['style'] is None or (proposed!=s['style'] and s['held']>=2 and abs(a-b)>=3):s['style']=proposed;s['held']=0
        s['held']+=1
        group=value if s['style']=='value' else growth
        good &= np.array([j in group for j in range(len(names))])
    elif PARAMS['mode']=='styles':
        good &= np.array([k in ['dividend','value300','lowvol','growth','chinext50','star50'] for k in names])
    if PARAMS.get('gate'):good &= pred>.0006
    pred[~good]=-np.inf
    order=np.argsort(-pred,kind='stable')[:PARAMS['top']]
    group=[j for j in order if good[j]]
    current=s['member']
    if group and current is not None and good[current] and pred[group[0]]-pred[current]<EDGE:group=[current]
    s['member']=group[0] if group else None
    w={names[j]:1/len(group) for j in group}
    if w==s['weights']:return None
    s['weights']=w
    return w
