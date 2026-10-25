#!/usr/bin/env python3
"""Render controlled-analysis figures and source-checked role examples."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

import numpy as np

FOLDER=Path(__file__).resolve().parent
ROOT=FOLDER.parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("original_figures",FOLDER/"build_figures.py")
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
plt=base.plt
from src.meeting.events import KeywordEventExtractor,_match_event_type,get_active_event_types
from scripts.benchmark_gap_influence import seconds


def main():
    result=json.loads((FOLDER/"analysis/results.json").read_text())
    source=ROOT/".runtime/research-influence-gap/utterances.jsonl"
    utterances={r["id"]:r for r in map(json.loads,source.read_text().splitlines())}
    choices=[("12.Pink.38","Role retrieval example"),("17.Orange.34","Threshold omission"),("13.Yellow.60","Role competition")]
    cases=[]
    for key,label in choices:
        r=utterances[key];text=r["text"].strip('"')
        kind,confidence=_match_event_type(text,get_active_event_types())
        seg={"segment_id":0,"speaker":r["speaker"],"start":seconds(r["timestamp"]),
             "end":seconds(r["meta"]["End"]),"text":text}
        events=KeywordEventExtractor().extract([seg],key).events
        case={"utterance_id":key,"speaker":r["speaker"],"start":seg["start"],"end":seg["end"],
              "text":text,"manual_role":r["meta"]["Decision"],"raw_candidate":kind,
              "match_density":confidence,"emitted_event":events[0].event_type if events else None,
              "threshold":KeywordEventExtractor().confidence_threshold,"illustration":label,
              "scope":"Manual role reference only; no adopted-idea, final-decision, or person-impact ground truth"}
        cases.append(case)
    assert cases[0]["emitted_event"] == "agreement" and cases[0]["manual_role"] == "Agreement"
    assert cases[1]["raw_candidate"] == "proposal" and cases[1]["emitted_event"] is None
    assert cases[2]["manual_role"] == "Proposal" and cases[2]["emitted_event"] == "question"
    record={"selection":"Three purposive explanatory examples, not a random accuracy sample",
            "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
            "events_source_sha256":hashlib.sha256((ROOT/"src/meeting/events.py").read_bytes()).hexdigest(),"cases":cases}
    (FOLDER/"analysis/cases.json").write_text(json.dumps(record,indent=2)+"\n")
    fig,ax=plt.subplots(figsize=(7.16,3.25));ax.set_xlim(0,7.2);ax.set_ylim(0,3.1);ax.axis("off")
    labels=["Agreement captured", "Proposal suppressed", "Proposal becomes\nquestion"]
    for i,(case,label) in enumerate(zip(cases,labels)):
        y=2.4-i*.91
        quote=case["text"]
        if i==2:quote="How about we split the ten and\nthe eight make it a nine"
        base.box(ax,.08,y,3.08,.52,case["utterance_id"]+" | "+case["manual_role"]+"\n“"+quote+"”",fontsize=7.4)
        base.arrow(ax,(3.24,y+.26),(3.60,y+.26))
        emitted=case["emitted_event"] or "no event"
        base.box(ax,3.68,y,2.05,.52,"Candidate: "+case["raw_candidate"]+"\nDensity "+f'{case["match_density"]:.4f}'+"\nOutput: "+emitted,fontsize=7.2)
        ax.text(5.91,y+.26,label,ha="left",va="center",fontsize=7.2,color=base.INK)
    ax.text(3.6,.11,"Human corpus labels validate these roles only; they do not establish adoption or causal influence.",ha="center",fontsize=7.4)
    base.save(fig,"trace_examples")

    fig,ax=plt.subplots(figsize=(7.16,2.6));ax.set_xlim(0,7.2);ax.set_ylim(0,2.6);ax.axis("off")
    base.box(ax,.08,1.55,1.45,.55,"28 GAP meetings\n84 participants",fontsize=8)
    base.box(ax,1.95,1.55,1.66,.55,"7 outer group folds\n24 fit / 4 evaluate",fontsize=8)
    base.box(ax,4.03,1.55,1.52,.55,"3 inner group folds\nSelect ridge alpha",fontsize=8)
    base.box(ax,5.96,1.55,1.1,.55,"Refit on 24\npredict 4",fontsize=8)
    for start,end in [((1.58,1.82),(1.87,1.82)),((3.66,1.82),(3.95,1.82)),((5.60,1.82),(5.89,1.82))]:base.arrow(ax,start,end)
    base.box(ax,.08,.56,3.35,.53,"Matched estimator and tuning grid\nParticipation (6); contribution (7)\nCombined (13)",fontsize=7.3)
    base.box(ax,3.89,.56,3.17,.53,"One outer prediction per person\nScaler fitted in its training partition\nPaired scores; predicted ties: half credit",fontsize=7.1)
    ax.text(3.6,.12,"Exploratory reuse of a previously examined corpus; nested fitting does not create a fresh test set.",ha="center",fontsize=7.4,color=base.ORANGE)
    base.save(fig,"nested_design")

    methods=[("combined","Combined ridge"),("participation","Participation ridge"),("contribution","Contribution ridge"),
             ("word_count","Word count"),("speaking_duration","Speaking duration"),
             ("prototype_fixed_weights","Fixed contribution score"),("constant_ties","Constant ties")]
    fig,ax=plt.subplots(figsize=(3.5,2.9));fig.subplots_adjust(left=.46,right=.95,bottom=.19,top=.88)
    for i,(key,label) in enumerate(methods):
        score=result["scores"][key]; mean=100*score["pairwise_accuracy"]
        color=base.BLUE if key in ("combined","participation","contribution") else base.GRAY
        ax.scatter(mean,6-i,color=color,s=24,zorder=3)
        ax.text(100,6-i,f"{mean:.2f}",ha="right",va="center",fontsize=7.1)
    ax.set(yticks=list(range(6,-1,-1)),yticklabels=[label for _,label in methods],xlim=(40,102),
           xticks=[40,50,60,70,80],xlabel="Meeting-average pairwise accuracy (%)")
    ax.axvline(50,color=base.LIGHT,lw=1,ls="--");ax.grid(axis="x",color=base.LIGHT,lw=.5)
    ax.tick_params(axis="y",length=0);ax.spines["left"].set_visible(False)
    ax.set_title("Exploratory nested group evaluation",fontsize=8.2,pad=12)
    base.save(fig,"controlled_results")
    print("Three revision figures and source-linked cases generated.")


if __name__ == "__main__":main()
