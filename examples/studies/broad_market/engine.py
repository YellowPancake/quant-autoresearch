"""Fixed causal multi-asset, next-close evaluator for the broad-market study."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PERIODS = (5, 10, 20, 40, 60, 120, 200, 252)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))

def load_strategy(path):
    spec=importlib.util.spec_from_file_location('candidate',path)
    m=importlib.util.module_from_spec(spec)
    exec(compile(Path(path).read_text(),str(path),'exec'),m.__dict__)
    return m

def rsi(p, n=14):
    d=p.diff(); g=d.clip(lower=0).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    l=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    r=100-100/(1+g/l.replace(0,np.nan))
    return r.where(l.ne(0),100.).where(g.ne(0)|l.ne(0),50.)

def features(p):
    """Every rolling operation is trailing; no fill of unavailable quotes."""
    f={}
    ret=p.pct_change(fill_method=None)
    for n in PERIODS:
        f[f'mom{n}']=p.pct_change(n,fill_method=None).to_numpy()
        f[f'trend{n}']=(p/p.rolling(n,min_periods=n).mean()-1).to_numpy()
        f[f'vol{n}']=(ret.rolling(n,min_periods=n).std()*np.sqrt(242)).to_numpy()
        f[f'dd{n}']=(p/p.rolling(n,min_periods=n).max()-1).to_numpy()
    for n in (6,14,28): f[f'rsi{n}']=rsi(p,n).to_numpy()
    f['daily_return']=ret.to_numpy()
    return f

def allowed_drawdown(annual):
    return min(.50,.2634+(annual-.20)/2)

def metrics(curve):
    nav=np.asarray([r['equity'] for r in curve],float)
    dates=pd.to_datetime([r['date'] for r in curve])
    years=(dates[-1]-dates[0]).days/365.2425
    annual=(nav[-1]/nav[0])**(1/years)-1 if years>0 else 0.
    # Initial NAV belongs to the initial signal date; no same-day execution.
    dd=float(np.max(1-nav/np.maximum.accumulate(nav)))
    daily=nav[1:]/nav[:-1]-1
    vol=np.std(daily,ddof=1) if len(daily)>1 else 0
    return dict(days=len(nav),start=str(dates[0].date()),end=str(dates[-1].date()),
        total_return=float(nav[-1]/nav[0]-1),annual_return=float(annual),max_drawdown=dd,
        sharpe=float(np.mean(daily)/vol*np.sqrt(242)) if vol>1e-12 else 0.,
        turnover=float(sum(r['turnover'] for r in curve)),cost_paid=float(sum(r['cost'] for r in curve)),
        drawdown_limit=allowed_drawdown(annual),
        feasible=bool(dd<=allowed_drawdown(annual)+1e-12 and dd<=.50),
        target_met=bool(annual>=.30 and dd<=allowed_drawdown(annual)+1e-12 and dd<=.50))

def rebalance(before, cash, w, fee):
    gross=float(before.sum()+cash)
    # Solve cash self-financing exactly, with fees charged on actual notionals.
    net=gross
    for _ in range(12):
        net=gross-fee*float(np.abs(net*w-before).sum())
    after=net*w
    cost=fee*float(np.abs(after-before).sum())
    newcash=gross-float(after.sum())-cost
    if newcash < -1e-9: raise ValueError('Unfunded rebalance')
    return after,max(newcash,0.),cost,float(np.abs(after-before).sum()/gross)

def simulate(strategy, prices, meta, start, end, fee=.0003, baseline=False, prepared=None):
    """Candidate sees only train + trailing observations; holdings drift between orders.

    None means hold existing units; an empty weight dict means liquidate to cash.
    A signal at close t is executed at close t+1, after that day's market move.
    Missing quotes postpone the entire pending basket. Marks carry only for NAV,
    never for indicators or synthetic trade fills. No terminal forced liquidation.
    """
    prices=prices.loc[:end]
    cols=list(prices.columns); n=len(cols); idx={s:i for i,s in enumerate(cols)}
    train=prices.loc[:'2019-12-31'].copy()
    state=strategy.fit(train)
    if state is None: state={}
    f=features(prices) if prepared is None else prepared
    raw=prices.to_numpy(); marked=prices.ffill().to_numpy()
    # Eligible only after sufficient real observations, plus launch-date masking.
    eligible=prices.rolling(21,min_periods=21).count().eq(21).to_numpy()
    selectable=np.array([meta[s]['selectable'] or baseline for s in cols])
    dates=prices.index
    weekly=np.array([i==len(dates)-1 or dates[i].to_period('W-FRI')!=dates[i+1].to_period('W-FRI') for i in range(len(dates))])
    monthly=np.array([i==len(dates)-1 or dates[i].month!=dates[i+1].month for i in range(len(dates))])
    # Exchange calendar, including future holidays, is known metadata, not prices.
    before=np.zeros(n); cash=1.; pending=None; curve=[]; trades=[]; peak=1.
    positions=np.flatnonzero((dates>=pd.Timestamp(start)) & (dates<=pd.Timestamp(end)))
    for step,i in enumerate(positions):
        cost=turnover=0.
        if step:
            held=before>0
            if np.any(~np.isfinite(marked[i,held])): raise ValueError('Unmarkable holding')
            before[held]*=marked[i,held]/marked[i-1,held]
        if pending is not None:
            w,sd=pending
            needed=(before>1e-15)|(w>0)
            if np.isfinite(raw[i,needed]).all():
                before,cash,cost,turnover=rebalance(before,cash,w,fee)
                trades.append(dict(signal_date=sd,execution_date=str(dates[i].date()),
                    weights={s:float(w[j]) for j,s in enumerate(cols) if w[j]>0},cost=cost,turnover=turnover))
                pending=None
        nav=float(before.sum()+cash);peak=max(peak,nav)
        curve.append(dict(date=str(dates[i].date()),equity=nav,drawdown=1-nav/peak,cost=cost,turnover=turnover,exposure=float(before.sum()/nav)))
        observation=dict(symbols=cols,features={k:v[i].copy() for k,v in f.items()},
            history=raw[max(0,i-503):i+1].copy(),eligible=eligible[i]&selectable,
            weights=before/nav,equity=nav,drawdown=1-nav/peak,
            weekly=bool(weekly[i]),monthly=bool(monthly[i]),step=step)
        choice=strategy.allocate(observation,state)
        if choice is not None:
            if not isinstance(choice,dict) or set(choice)-set(cols):raise ValueError('Invalid weight symbols')
            w=np.zeros(n)
            for s,x in choice.items():w[idx[s]]=float(x)
            if not np.isfinite(w).all() or np.any(w<0) or w.sum()>1+1e-10:raise ValueError('Weights outside fully funded long-only budget')
            if np.any((w>0)&~(eligible[i]&selectable)):raise ValueError('Not eligible at signal time')
            pending=(w,str(dates[i].date()))
    return metrics(curve),curve,trades

def verify(root):
    m=json.loads((root/'manifest.json').read_text())
    for name,h in m['files'].items():
        if digest(root/name)!=h:raise ValueError('Frozen file changed: '+name)
    return m

def load_inputs(root, test=False):
    verify(root)
    if test: raise ValueError('Holdout access is researcher-only')
    p=pd.read_csv(root/'data/prices.csv',index_col='date',parse_dates=True)
    meta=json.loads((root/'config/universe.json').read_text())
    return p,meta
