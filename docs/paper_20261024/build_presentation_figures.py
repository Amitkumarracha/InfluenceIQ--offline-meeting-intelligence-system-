#!/usr/bin/env python3
"""Improve the architecture and plot stored coverage, uncertainty and ablations."""
from pathlib import Path
import hashlib
import importlib.util
import json

import numpy as np

FOLDER=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('figure_base',FOLDER/'build_figures.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
plt=base.plt


def architecture():
    fig,ax=plt.subplots(figsize=(7.16,5.5));fig.subplots_adjust(left=.01,right=.99,bottom=.02,top=.98)
    ax.set_xlim(0,7.2);ax.set_ylim(0,5.6);ax.axis('off')
    gray=base.GRAY;blue=base.BLUE;orange=base.ORANGE
    ax.text(.1,5.42,'1  INPUTS AND OBSERVATIONS',fontsize=8.2,weight='bold',color=gray)
    base.box(ax,.15,4.77,1.95,.42,'Meeting audio',color=gray,fill='#f5f6f7',fontsize=8)
    base.box(ax,2.63,4.77,1.95,.42,'Optional presentation',color=gray,fill='#f5f6f7',fontsize=8)
    base.box(ax,5.09,4.77,1.95,.42,'GAP reference inputs',color=orange,fill=base.PALE_ORANGE,fontsize=8)
    base.box(ax,.15,4.00,1.95,.48,'Local ASR + diarization\nWords, times, speaker clusters',color=gray,fill='#f5f6f7',fontsize=7.4)
    base.box(ax,2.63,4.00,1.95,.48,'Native slide text + semantic links\nDisplay timing when available',color=gray,fill='#f5f6f7',fontsize=7.2)
    base.box(ax,5.09,4.00,1.95,.48,'Supplied English transcripts\nSpeaker IDs; no slide input',color=orange,fill=base.PALE_ORANGE,fontsize=7.5)
    for x,color in [(1.125,gray),(3.605,gray),(6.065,orange)]:base.arrow(ax,(x,4.69),(x,4.55),color=color)
    base.box(ax,.75,3.23,5.7,.43,'SOURCE LEDGER  |  utterance ID · speaker · text · timestamp · optional slide references',fontsize=7.5)
    for x,color in [(1.125,gray),(3.605,gray),(6.065,orange)]:base.arrow(ax,(x,3.93),(x,3.73),color=color)
    ax.text(.1,3.04,'2  CANDIDATE CONTRIBUTION EVIDENCE',fontsize=8.2,weight='bold',color=blue)
    base.box(ax,.76,2.38,1.6,.44,'Utterance events\nProposal, objection, evidence, ...',fontsize=7.1)
    base.box(ax,2.80,2.38,1.6,.44,'Candidate evidence links\nDecision reconstruction',fontsize=7.4)
    base.box(ax,4.84,2.38,1.6,.44,'Interactions and lineage\nSource and target IDs retained',fontsize=7.1)
    base.arrow(ax,(1.56,3.15),(1.56,2.90))
    base.arrow(ax,(2.44,2.60),(2.72,2.60));base.arrow(ax,(4.48,2.60),(4.76,2.60))
    ax.text(.1,2.12,'3  PARTICIPANT REPRESENTATIONS AND OUTPUTS',fontsize=8.2,weight='bold',color=blue)
    base.box(ax,.76,1.43,2.25,.43,'6 participation features\nVolume, duration, turns, position',fontsize=7.5)
    base.box(ax,4.19,1.43,2.25,.43,'7 contribution features\nDecision-linked category scores',fontsize=7.5)
    # Activity is computed directly from observations, without event-role gating.
    ax.plot([.73,.035,.035,1.00],[3.45,3.45,1.99,1.99],color=blue,lw=.8)
    base.arrow(ax,(1.00,1.99),(1.00,1.94))
    base.arrow(ax,(5.64,2.30),(5.64,1.94))
    base.box(ax,.76,.55,2.61,.48,'CONTROLLED RESEARCH COMPARISON\n13 inputs → nested Ridge → outer predictions',color=orange,fill=base.PALE_ORANGE,fontsize=7.1)
    base.box(ax,3.89,.55,2.55,.48,'PRODUCTION REVIEW\nFixed contribution score + source rationale',fontsize=7.3)
    base.arrow(ax,(1.89,1.35),(1.89,1.10),color=orange)
    base.arrow(ax,(5.32,1.35),(5.32,1.10),color=blue)
    # The production score consumes contribution features, not the activity branch.
    ax.plot([4.12,3.55,3.55,2.80],[1.65,1.65,1.20,1.20],color=orange,lw=.8)
    base.arrow(ax,(2.80,1.20),(2.80,1.11),color=orange)
    ax.text(3.60,.28,'AII labels enter research scoring/selection only; the research ranker is not the installed app score.',ha='center',fontsize=7.2)
    ax.text(3.60,.07,'Audio/slide branches are implemented capabilities; the reported GAP comparison begins at supplied reference inputs.',ha='center',fontsize=7.0,color=gray)
    base.save(fig,'architecture')


def main():
    r=json.loads((FOLDER/'analysis/results.json').read_text());architecture()
    order=[('combined','Latest combined ridge'),('speaking_duration','Speaking-duration baseline'),('word_count','Word-count baseline'),
           ('participation','Participation-only ridge'),('prototype_fixed_weights','Fixed contribution score'),
           ('contribution','Contribution-only ridge'),('constant_ties','Constant-tie reference')]
    fig,ax=plt.subplots(figsize=(7.16,3.1));fig.subplots_adjust(left=.29,right=.91,bottom=.20,top=.88)
    for i,(key,label) in enumerate(order):
        row=r['scores'][key];mean=100*row['pairwise_accuracy'];lo,hi=np.array(row['descriptive_bootstrap_95_ci'])*100
        color=base.BLUE if key=='combined' else base.GRAY
        ax.errorbar(mean,6-i,xerr=[[mean-lo],[hi-mean]],fmt='o',color=color,ecolor=color,capsize=2,lw=1,ms=5)
        ax.text(103,6-i,f'{mean:.2f}%',va='center',fontsize=8,weight='bold' if key=='combined' else 'normal',color=color)
    ax.set(yticks=list(range(6,-1,-1)),yticklabels=[label for _,label in order],xlim=(0,104),xticks=[0,25,50,75,100],
           xlabel='Meeting-average pairwise accuracy (%)')
    ax.axvline(50,color=base.LIGHT,ls='--',lw=.8);ax.grid(axis='x',color=base.LIGHT,lw=.5)
    ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False)
    ax.set_title('Matched 28-meeting comparison: latest model = 68.93%',fontsize=9,pad=12)
    fig.text(.51,.03,'Intervals are descriptive; overlapping training folds and prior corpus reuse limit inference.',ha='center',fontsize=7.4)
    base.save(fig,'controlled_results')

    features=r['feature_coverage'];names=[row['feature'].replace('influence_','').replace('_',' ').title() for row in features]
    fig,axes=plt.subplots(1,2,figsize=(7.16,2.9),sharey=True);fig.subplots_adjust(left=.16,right=.96,bottom=.19,top=.84,wspace=.16)
    for ax,field,total,title in [(axes[0],'active_participants',84,'Participant coverage'),(axes[1],'active_meetings',28,'Meeting coverage')]:
        values=[100*row[field]/total for row in features];y=np.arange(7)
        ax.barh(y,values,height=.55,color=base.BLUE)
        for i,row in enumerate(features):ax.text(max(values[i]+1,1),i,f'{row[field]}/{total} ({values[i]:.1f}%)',va='center',fontsize=7.2)
        ax.set(xlim=(0,105),xticks=[0,25,50,75,100],yticks=y,yticklabels=names,title=title,xlabel='Nonzero feature coverage (%)')
        ax.grid(axis='x',color=base.LIGHT,lw=.5);ax.set_axisbelow(True);ax.tick_params(axis='y',length=0)
    axes[0].invert_yaxis()
    fig.text(.52,.03,'Slide grounding is unavailable by design; other zero categories reflect this extraction/association pipeline.',ha='center',fontsize=7.1)
    base.save(fig,'feature_coverage')

    contrast_order=[('combined_minus_participation','Combined − participation ridge'),('combined_minus_word_count','Combined − word count'),
                    ('contribution_minus_participation','Contribution − participation ridge')]
    fig,ax=plt.subplots(figsize=(7.16,2.55));fig.subplots_adjust(left=.33,right=.91,bottom=.25,top=.83)
    for i,(key,label) in enumerate(contrast_order):
        row=r['contrasts'][key];mean=row['difference']*100;lo,hi=np.array(row['descriptive_paired_bootstrap_95_ci'])*100;y=2-i
        ax.errorbar(mean,y,xerr=[[mean-lo],[hi-mean]],fmt='o',color=base.BLUE,capsize=3,lw=1)
        ax.text(27,y,f'{mean:+.2f} pp',va='center',fontsize=7.7)
    ax.set(yticks=[2,1,0],yticklabels=[label for _,label in contrast_order],xlim=(-30,28),xlabel='Paired change in pairwise accuracy (percentage points)')
    ax.axvline(0,color=base.ORANGE,ls='--',lw=1);ax.grid(axis='x',color=base.LIGHT,lw=.5);ax.tick_params(axis='y',length=0)
    ax.set_title('Paired comparisons: every descriptive interval crosses zero',fontsize=8.5,pad=12)
    base.save(fig,'paired_differences')

    fig,axes=plt.subplots(1,2,figsize=(7.16,3.4));fig.subplots_adjust(left=.22,right=.97,bottom=.20,top=.82,wspace=.75)
    full=r['scores']['combined']['pairwise_accuracy']
    learned=[('Remove contribution\n(participation-only refit)','participation'),('Remove participation\n(contribution-only refit)','contribution')]
    for i,(label,key) in enumerate(learned):
        delta=100*(r['scores'][key]['pairwise_accuracy']-full)
        axes[0].barh(1-i,delta,height=.45,color=base.BLUE);axes[0].text(delta-.3,1-i,f'{delta:+.2f}',ha='right',va='center',fontsize=7.5)
    axes[0].set(yticks=[1,0],yticklabels=[label for label,_ in learned],xlim=(-23,1),xlabel='Change from full Ridge (pp)',title='Refitted feature families\nFull Ridge: 68.93%')
    fixed=r['scores']['prototype_fixed_weights']['pairwise_accuracy'];deletions=r['fixed_weight_deletions']
    labels=[]
    for i,row in enumerate(deletions):
        delta=100*(row['pairwise_accuracy']-fixed);name=row['deleted_feature'].replace('influence_','').replace('_',' ')
        labels.append('Remove '+name);axes[1].scatter(delta,6-i,color=base.BLUE,s=20)
        axes[1].text(3.8,6-i,f'{delta:+.2f}',ha='right',va='center',fontsize=7.3)
    axes[1].set(yticks=list(range(6,-1,-1)),yticklabels=labels,xlim=(-6.5,4.1),xticks=[-6,-4,-2,0,2],xlabel='Change from fixed score (pp)',title='Fixed-weight deletions\nFull fixed score: 55.77%')
    for ax in axes:ax.axvline(0,color=base.GRAY,ls='--',lw=.8);ax.grid(axis='x',color=base.LIGHT,lw=.5);ax.tick_params(axis='y',length=0)
    fig.text(.5,.03,'Each panel uses its own reference. Weight deletion has no refitting or renormalization; zero means no ranking change.',ha='center',fontsize=7.0)
    base.save(fig,'ablation_results')
    manifest={'inputs':{name:hashlib.sha256((FOLDER/name).read_bytes()).hexdigest() for name in ['analysis/results.json','analysis/comparison_table_manifest.json']},
              'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'figures':['architecture','controlled_results','feature_coverage','paired_differences','ablation_results'],
              'note':'No new training; all numerical figures use frozen stored measurements.'}
    (FOLDER/'figures/presentation_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Improved architecture and four comparative/diagnostic graphs generated.')


if __name__=='__main__':main()
