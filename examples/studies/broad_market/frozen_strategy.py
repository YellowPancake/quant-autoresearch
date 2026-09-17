SUPPORT='exposure'
TRANSFER='index'
KIND='concentration'
EDGE=0.0012
import numpy as np
import pandas as pd
from engine import features
PARAMS={'horizon': 20, 'mode': 'hierarchy', 'top': 1, 'gate': False, 'nonlinear': False}
KEYS=['mom5', 'mom20', 'mom60', 'mom120', 'trend20', 'trend120', 'vol20', 'vol60', 'dd60']


def concentration_features(windows):
    valid=np.isfinite(windows).all(-1)
    r=np.where(np.isfinite(windows),windows,0.);absolute=np.abs(r)
    cutoff=np.partition(absolute,-3,axis=-1)[...,-3]
    above=absolute>cutoff[...,None];equal=absolute==cutoff[...,None]
    fraction=(3-above.sum(-1))/np.maximum(equal.sum(-1),1)
    tail_weights=above.astype(float)+equal*fraction[...,None]
    total=absolute.sum(-1);den=np.maximum(total,1e-12)
    trimmed=((1-tail_weights)*r).sum(-1);tail=(tail_weights*r).sum(-1)
    hhi=(absolute*absolute).sum(-1)/(den*den);largest=absolute.max(-1)/den;tail_share=(tail_weights*absolute).sum(-1)/den
    if KIND=='decomposition':parts=[trimmed,tail]
    elif KIND=='concentration':parts=[hhi,largest,tail_share]
    else:parts=[trimmed,tail,hhi,largest,tail_share]
    out=np.stack(parts,axis=-1)
    return np.where(valid[...,None],out,np.nan)

def indicator_features(prices):
    raw=np.asarray(prices,dtype=float);ret=np.diff(np.log(np.where(raw>0,raw,np.nan)),axis=0)
    nfeatures=2 if KIND=='decomposition' else 3 if KIND=='concentration' else 5
    out=np.full((*raw.shape,nfeatures),np.nan)
    if len(ret)>=60:
        windows=np.lib.stride_tricks.sliding_window_view(ret,60,axis=0)
        out[60:]=concentration_features(windows)
    return out


COHORTS=[
 ['csi300','csi100','sse50','sse180','sz100','csi_a50'],
 ['csi500','csi1000','cni2000','csi2000','sme100','bse50'],
 ['growth','chinext50','star50','star100'],
 ['dividend','value300','lowvol'],
 ['csi800','csi_all','ssecomp','szcomponent','csi_a500']]

def source_mask(good,excluded):
    mask=good.copy();mask[:,excluded]=False
    return mask

def ridge_model(x,y,mask,penalty):
    xx=x[mask];yy=y[mask]
    mu=xx.mean(0);sd=np.maximum(xx.std(0),1e-5)
    z=np.clip((xx-mu)/sd,-6,6);mean=yy.mean()
    beta=np.linalg.solve(z.T@z+len(z)*penalty*np.eye(z.shape[1]),z.T@(yy-mean))
    precision=np.linalg.solve(z.T@z/len(z)+penalty*np.eye(z.shape[1]),np.eye(z.shape[1]))
    distance=np.einsum('ni,ij,nj->n',z,precision,z)
    radius=max(float(np.quantile(distance,.95)),1e-12)
    return dict(mu=mu,sd=sd,beta=beta,mean=mean,precision=precision,radius=radius)


def support_factor(z,precision,radius):
    distance=np.einsum('...i,...ij,...j->...',z,precision,z)
    return np.sqrt(np.minimum(1.,radius/np.maximum(distance,1e-12)))

def predict_single(x,m):
    z=np.clip((x-m['mu'])/m['sd'],-6,6)
    factor=support_factor(z,m['precision'],m['radius'])
    if SUPPORT=='projection':z=z*factor[...,None]
    return z@m['beta']+m['mean']

def fit(train):
    f=features(train);x=np.stack([f[k] for k in KEYS],axis=2)
    extra=indicator_features(train)
    for end in [min(600,len(train)),len(train)]:
        assert np.allclose(extra[end-1],indicator_features(train.iloc[max(0,end-504):end])[-1],equal_nan=True,atol=1e-10)
    assert np.isfinite(extra[np.isfinite(x).all(2)]).all()
    x=np.concatenate([x,extra],axis=2)
    y=(train.shift(-21)/train.shift(-1)-1).to_numpy()
    good=np.isfinite(x).all(2)&np.isfinite(y)
    names=list(train.columns);n=len(names);d=x.shape[-1]
    if 'bank' in names:good[:,names.index('bank')]=False
    enddate=pd.Series(train.index,index=train.index).shift(-21)
    if TRANSFER=='index':groups=[[j] for j,k in enumerate(names) if k!='bank']
    else:groups=[[names.index(k) for k in group if k in names] for group in COHORTS]
    assert sorted(j for group in groups for j in group)==[j for j,k in enumerate(names) if k!='bank']
    out=dict(mu=np.zeros((n,d)),sd=np.ones((n,d)),beta=np.zeros((n,d)),mean=np.zeros(n),precision=np.zeros((n,d,d)),radius=np.ones(n))
    early_grid=np.full(y.shape,np.nan);penalties={}
    for ids in groups:
        source=source_mask(good,ids)
        assert not source[:,ids].any()
        best=None
        for penalty in [.01,.1,1.]:
            losses=[]
            for cut,end in [('2015-12-31','2017-12-31'),('2017-12-31','2019-12-31')]:
                tr=source&enddate.le(pd.Timestamp(cut)).to_numpy()[:,None]
                va=source&((train.index>pd.Timestamp(cut))&(train.index<=pd.Timestamp(end)))[:,None]
                if tr.sum()<500 or va.sum()<100:continue
                model=ridge_model(x,y,tr,penalty)
                losses.append(float(np.mean((predict_single(x[va],model)-y[va])**2)))
            loss=float(np.mean(losses)) if losses else np.inf
            if best is None or loss<best[0]:best=(loss,penalty)
        penalty=best[1] if np.isfinite(best[0]) else 1.
        assert source.sum()>=500
        model=ridge_model(x,y,source,penalty)
        early=source&enddate.le(pd.Timestamp('2017-12-31')).to_numpy()[:,None]
        assert early.sum()>=500
        old=ridge_model(x,y,early,penalty)
        for j in ids:
            for key in ['mu','sd','beta','mean','precision','radius']:out[key][j]=model[key]
            early_grid[:,j]=predict_single(x[:,j],old)
            penalties[names[j]]=penalty
    gaps=[]
    for i,day in enumerate(train.index):
        if day<=pd.Timestamp('2017-12-31'):continue
        for group in [['dividend','value300','lowvol'],['growth','chinext50','star50']]:
            ids=[names.index(k) for k in group]
            values=sorted([early_grid[i,j] for j in ids if good[i,j]],reverse=True)
            if len(values)>1:gaps.append(values[0]-values[1])
    out.update(edge=max(.0006,float(np.median(gaps))*.25) if gaps else .0006,
               style=None,held=0,weights=None,member=None,selected_penalties=penalties)
    return out

def allocate(o,s):
    if not o['weekly']:return None
    f=o['features'];names=o['symbols'];good=o['eligible'].copy()
    x=np.stack([f[k] for k in KEYS],axis=1)
    extra=indicator_features(pd.DataFrame(o['history'],columns=names))[-1]
    x=np.concatenate([x,extra],axis=1)
    if PARAMS['nonlinear']:x=np.concatenate([x,np.tanh(x[:,:4]*5),x[:,8:9]*x[:,:2]/100],axis=1)
    good &= np.isfinite(x).all(1)
    z=np.clip((x-s['mu'])/s['sd'],-6,6)
    support=support_factor(z,s['precision'],s['radius'])
    if SUPPORT=='projection':z=z*support[:,None]
    pred=(z*s['beta']).sum(-1)+s['mean']
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
    if group and current is not None and good[current] and pred[group[0]]-pred[current]<s['edge']:group=[current]
    s['member']=group[0] if group else None
    exposure=1.
    if group and pred[group[0]]<0:exposure=.5
    if group and SUPPORT=='exposure':exposure*=float(support[group[0]])
    w={names[j]:exposure/len(group) for j in group}
    if w==s['weights']:return None
    s['weights']=w
    return w
