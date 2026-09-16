"""Combine archived daily equity and milestone aggregates; never rerun strategies."""
import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter, MultipleLocator


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market',choices=['csi300','sp500'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    folder=Path(__file__).resolve().parent/args.market
    study=json.loads((folder/'study.json').read_text())
    with (folder/'daily_equity.csv').open() as f: daily=list(csv.DictReader(f))
    milestones=json.loads((folder/'milestones.json').read_text())['results']
    rows=[r for r in milestones if r['role']=='validation_champion']
    baseline=study['strategies']['baseline']['test']
    selected=study['strategies']['posthoc']
    assert len(rows)==study['milestones'] and len(daily)==selected['test']['days']+1
    assert math.isclose(float(daily[-1]['strategy_equity'])-1,selected['test']['total_return'],abs_tol=1e-12)
    assert math.isclose(float(daily[-1]['buy_and_hold_equity'])-1,baseline['total_return'],abs_tol=1e-12)
    dates=[date.fromisoformat(r['date']) for r in daily]
    stages=list(range(1,len(rows)+1))
    title=study['title'];frozen=int(study['strategies']['frozen']['attempt'])
    plt.rcParams.update({'font.family':'DejaVu Serif','font.size':10,'axes.labelsize':10,
        'xtick.labelsize':9,'ytick.labelsize':9,'axes.linewidth':.8,'axes.edgecolor':'#222222',
        'text.color':'#222222','axes.labelcolor':'#222222','xtick.color':'#222222','ytick.color':'#222222',
        'xtick.direction':'in','ytick.direction':'in','svg.fonttype':'none','pdf.fonttype':42,
        'savefig.facecolor':'white','axes.unicode_minus':False})
    args.output.mkdir(parents=True,exist_ok=True)
    for metric,label,stem,step in [
        ('total_return','Cumulative net return','combined_returns',.2),
        ('annual_return','Annualized net return','combined_annual',.05)]:
        fig=plt.figure(figsize=(10.8,11.8))
        eq=fig.add_axes([.09,.655,.885,.27])
        ret=fig.add_axes([.09,.365,.885,.195])
        dd=fig.add_axes([.09,.14,.885,.195],sharex=ret)
        fig.suptitle(f'{title}: Test Equity and Research Progress',y=.972,fontsize=15)
        for ax in (eq,ret,dd):
            ax.grid(True,color='#DADADA',linestyle=':',linewidth=.55)
            ax.set_axisbelow(True);ax.tick_params(top=True,right=True)
        eq.plot(dates,[float(r['strategy_equity']) for r in daily],color='#D95F02',lw=1.45,
                label=f"Strategy #{int(selected['attempt'])} (best test milestone; post hoc)")
        eq.plot(dates,[float(r['buy_and_hold_equity']) for r in daily],color='#1F77B4',lw=1.35,
                label=f'{title} buy-and-hold')
        eq.set_xlim(dates[0],dates[-1]);eq.set_ylabel('Net asset value (initial = 1)');eq.set_xlabel('Date',labelpad=8)
        eq.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1,7]))
        eq.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        handles,labels=eq.get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.53,.601),ncol=2,
                   frameon=False,fontsize=8.8,handlelength=2.6,columnspacing=1.7)
        for name,color,marker,values in [
            ('Validation (2020–2022)','#D95F02','s',[r['validation'] for r in rows]),
            ('Test (2023–2026-09-11)','#1F77B4','o',[r['test']['metrics'] for r in rows])]:
            style=dict(color=color,linewidth=1.45,marker=marker,markersize=3.8,
                       markerfacecolor='white',markeredgewidth=.9,zorder=3)
            ret.plot(stages,[m[metric] for m in values],label=name,**style)
            dd.plot(stages,[m['max_drawdown'] for m in values],**style)
        ret.axhline(baseline[metric],color='#777777',linestyle='--',lw=1,label=f'{title} buy-and-hold (test)')
        dd.axhline(baseline['max_drawdown'],color='#777777',linestyle='--',lw=1)
        values=[r[part][metric] if part=='validation' else r['test']['metrics'][metric] for r in rows for part in ['validation','test']]
        ret.set_ylim(min(0,math.floor(min(values)*1.08/step)*step),math.ceil(max(values)*1.08/step)*step)
        ret.yaxis.set_major_locator(MultipleLocator(step));ret.set_ylabel(label)
        dd.set_ylim(0,math.ceil(max([r['validation']['max_drawdown'] for r in rows]+[r['test']['metrics']['max_drawdown'] for r in rows]+[baseline['max_drawdown']])*1.05/.05)*.05);dd.yaxis.set_major_locator(MultipleLocator(.05));dd.set_ylabel('Maximum drawdown')
        for ax in (ret,dd):
            ax.set_xlim(.75,len(rows)+.25);ax.set_xticks(stages)
            ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
        plt.setp(ret.get_xticklabels(),visible=False)
        dd.set_xlabel('Stage',labelpad=8)
        handles,labels=ret.get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.53,.086),ncol=3,
                   frameon=False,fontsize=8.8,handlelength=2.6,columnspacing=1.7)
        fig.text(.53,.043,'Transaction costs of 0.05% per side are included.',ha='center',fontsize=9)
        fig.text(.53,.022,f'Top: post-hoc test comparison. Bottom: validation-champion milestones; frozen champion remains #{frozen}.',
                 ha='center',fontsize=8.5)
        for ext in ['png','pdf','svg']:
            fig.savefig(args.output/f'{stem}.{ext}',dpi=240)
        plt.close(fig)
    print(args.output.resolve())


if __name__=='__main__':main()
