#!/usr/bin/env python3
"""Typeset the historical supplement and assemble the local research package."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import zipfile

FOLDER=Path(__file__).resolve().parent
ROOT=FOLDER.parents[1]
spec=importlib.util.spec_from_file_location("paper_builder",FOLDER/"build_paper.py")
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


def esc(text):
    value=builder.renderer.tex_escape(text.replace("−","-"),citations=False)
    value=re.sub(r"\b[a-f0-9]{64}\b",lambda m:r"\allowbreak{}".join(m[0][i:i+8] for i in range(0,64,8)),value)
    return value.replace(r"\_",r"\_\allowbreak{}")


def main():
    source=(FOLDER/"SUPPLEMENT.md").read_text()
    items=builder.renderer.blocks(source)
    lines=[r"\documentclass[journal,onecolumn]{IEEEtran}",r"\usepackage[T1]{fontenc}",
           r"\usepackage{graphicx,booktabs,url}",r"\urlstyle{same}",
           r"\setlength{\textfloatsep}{10pt}\setlength{\intextsep}{10pt}\setlength{\floatsep}{10pt}",r"\begin{document}",
           r"\title{InfluenceIQ: Supplementary Research Records}",builder.author_latex(),r"\maketitle"]
    captions=["Version and target matrix","Historical cohorts","Original GAP comparison",
              "Historical exploratory comparisons","Supporting component results","AI-label agreement pilot",
              "Fixed-weight deletion sensitivity"]
    count=0
    for kind,value in items:
        if kind=="title":continue
        if kind in ("section","subsection"):
            lines.append(r"\section*{"+esc(value)+"}")
        elif kind=="paragraph":lines.append(esc(value)+"\n")
        elif kind=="table":
            n=len(value[0]);count+=1
            widths=[.35]+[.59/(n-1)]*(n-1)
            columns="".join("p{"+f"{w:.3f}"+r"\textwidth}" for w in widths)
            lines.extend([r"\begin{table}[htbp]",r"\centering\footnotesize",r"\caption{"+captions[count-1]+"}",
                          r"\setlength{\tabcolsep}{3pt}",r"\renewcommand{\arraystretch}{1.15}",
                          r"\begin{tabular}{"+columns+"}",r"\toprule"])
            for i,row in enumerate(value):
                lines.append(" & ".join(r"{\raggedright "+esc(cell)+r"\par}" for cell in row)+r" \\")
                if i==0:lines.append(r"\midrule")
            lines.extend([r"\bottomrule",r"\end{tabular}",r"\end{table}"])
    assert count==7
    lines.extend([r"\end{document}"])
    (FOLDER/"supplement.tex").write_text("\n".join(lines)+"\n")
    compiler=ROOT/".runtime/ieee-tools/tectonic"
    process=subprocess.run([str(compiler),"--only-cached","--keep-logs","supplement.tex"],cwd=FOLDER,text=True,capture_output=True)
    (FOLDER/"supplement_build.log").write_text(process.stdout+process.stderr)
    if process.returncode:raise RuntimeError("\n".join((process.stdout+process.stderr).splitlines()[-15:]))
    (FOLDER/"supplement.html").write_text(builder.webpage(source))
    # Preserve source versions instead of silently substituting current code.
    for label,base in [("initial","gap_influence_20261024"),("canonical","xgb_influence_20261024_v2")]:
        origin=ROOT/"outputs/training"/base/"source_snapshot"
        target=FOLDER/"snapshot_sources"/label
        shutil.copytree(origin,target,dirs_exist_ok=True)
    package=["README.md","manuscript.md","paper.md","paper.tex","paper.pdf","InfluenceIQ_comparative_revision.pdf","paper.docx","paper.html",
             "SUPPLEMENT.md","supplement.tex","supplement.pdf","supplement.html","IEEEtran.cls",
             "references.bib","references.json","REFERENCES_VERIFIED.md","EVIDENCE_AUDIT.md",
             "REVISION_RESPONSE.md","run_revision_analysis.py","reproduce_controlled.py",
             "build_paper.py","build_figures.py","build_revision_figures.py","build_research_package.py","check_paper.py","check_revision.py",
             "authors.json","update_comparisons.py","build_presentation_figures.py","figures/presentation_manifest.json","figures/README.md"]
    paths=[FOLDER/name for name in package if (FOLDER/name).exists()]
    for directory in ["analysis","historical_records","snapshot_sources"]:
        paths.extend(p for p in (FOLDER/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for kind,data in builder.renderer.blocks((FOLDER/"paper.md").read_text()):
        if kind=="image":
            for extension in [".pdf",".png",".svg"]:
                paths.append((FOLDER/data[1]).with_suffix(extension))
    manifest={str(p.relative_to(FOLDER)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (FOLDER/"research_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    with zipfile.ZipFile(FOLDER/"research_package.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,str(p.relative_to(FOLDER)))
        archive.write(FOLDER/"research_manifest.json","research_manifest.json")
        archive.writestr("DATA_ATTRIBUTION.txt","Derived GAP features and brief source examples originate from Braley and Murray (2018), The Group Affect and Performance (GAP) Corpus, DOI10.1145/3279981.3279985; release documentation https://convokit.cornell.edu/documentation/gap.html. GAP release license: CC BY-NC4.0, https://creativecommons.org/licenses/by-nc/4.0/. Derived features are normalized and target ranks transformed as described in protocol.json. Original corpora and private recordings are not redistributed. AI-labelled AMI pilot records are identified as assistant judgments, not new human annotations. IEEEtran retains its original license. No public upload or archival DOI is implied by this local package.\n")
    print("Supplement PDF and research package built:",len(paths),"files.")


if __name__=="__main__":main()
