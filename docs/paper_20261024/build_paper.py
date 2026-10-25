#!/usr/bin/env python3
"""Build the new manuscript, reusing the project's existing document renderer.

Run: .venv/bin/python docs/paper_20261024/build_paper.py
The authored Markdown and reference catalog are the sources. No training runs.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from xml.etree import ElementTree as ET

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[1]
spec = importlib.util.spec_from_file_location("existing_paper_renderer", ROOT / "scripts/build_ieee_paper.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
renderer.FOLDER = FOLDER

EQUATIONS = {
    1: r"z_{pk}=\begin{cases}x_{pk}/\max_q x_{qk},&\max_q x_{qk}>0,\\0,&\text{otherwise},\end{cases}",
    2: r"S_p=\sum_{k=1}^{7}w_kz_{pk},\qquad w_k\geq0,\quad\sum_{k=1}^{7}w_k=1.",
    3: r"\begin{aligned}P&=\{(p,q):p<q,\ a_p\ne a_q\},\\h_{pq}&=\begin{cases}1,&\delta_{pq}(a_q-a_p)>0,\\0.5,&\delta_{pq}=0,\\0,&\text{otherwise},\end{cases}\\\mathrm{PA}_m&=\frac{1}{|P|}\sum_{(p,q)\in P}h_{pq}.\end{aligned}",
    4: r"\mathrm{MacroPA}=\frac{1}{|\mathcal M|}\sum_{m\in\mathcal M}\mathrm{PA}_m.",
}

# Fractions leave room for intercolumn spacing within the IEEE text width.
TABLE_WIDTHS = {
    1: [.18, .23, .23, .30], 2: [.13, .75, .06],
    3: [.38, .28, .28], 4: [.19, .19, .11, .15, .14, .14],
    5: [.29, .12, .18, .17, .16], 6: [.40, .14, .14, .26],
    7: [.43, .14, .14, .23], 8: [.34, .09, .16, .12, .21],
    9: [.15, .25, .25, .15, .14], 10: [.22, .28, .44],
}


def tex_inline(text, **kwargs):
    pieces = re.split(r'(\*\*.*?\*\*)', text.replace('−', '-'))
    return ''.join(r'\textbf{' + renderer.tex_escape(p[2:-2], **kwargs) + '}'
                   if p.startswith('**') and p.endswith('**')
                   else renderer.tex_escape(p, **kwargs) for p in pieces)


def author_latex():
    metadata = json.loads((FOLDER / 'authors.json').read_text())
    names = ', '.join(a['name'] for a in metadata['authors'])
    affiliation = ', '.join(metadata[k] for k in ['department', 'institution', 'university', 'address'])
    contacts = '; '.join(tex_inline(a['name']) + ': ' + r'\mbox{' + tex_inline(a['email']) + '}'
                         for a in metadata['authors'])
    return (r'\author{' + tex_inline(names) + r'\thanks{The authors are with the '
            + tex_inline(affiliation) + '. E-mail: ' + contacts + '.}}')


def resolve_citations(source):
    catalog = json.loads((FOLDER / "references.json").read_text())
    order = []

    def replace(match):
        keys = re.findall(r"@([a-z0-9]+)", match[0])
        for key in keys:
            assert key in catalog, f"Missing reference: {key}"
            if key not in order:
                order.append(key)
        return ", ".join(f"[{order.index(key)+1}]" for key in keys)

    resolved = re.sub(r"\[@[a-z0-9]+(?:;\s*@[a-z0-9]+)*\]", replace, source)
    assert "[@" not in resolved
    refs = "\n\n".join(f"[{i}] {catalog[key]}" for i, key in enumerate(order, 1))
    return resolved + "\n\n## References\n\n" + refs + "\n", order


def latex(items):
    # A text minus avoids invoking unavailable small math fonts inside abstracts/tables.
    esc = tex_inline
    title = items[0][1]
    abstract_pos = next(i for i, (kind, value) in enumerate(items) if kind == "section" and value == "Abstract")
    abstract = items[abstract_pos+1][1]
    lines = [r"\documentclass[journal]{IEEEtran}", r"\usepackage[T1]{fontenc}",
             r"\usepackage{amsmath,graphicx,booktabs,url}",
             r"\urlstyle{same}", r"\hyphenation{InfluenceIQ MiniLM}",
             r"\begin{document}",
             r"\ifdefined\pdfinfo\pdfinfo{/Title ("+title+r")}\else\special{pdf:docinfo << /Title ("+title+r") >>}\fi",
             r"\title{" + esc(title) + "}",
             author_latex(),
             r"\maketitle", r"\begin{abstract}" + esc(abstract) + r"\end{abstract}"]
    active = False
    table_caption = ""
    figure = None
    table_number = 0
    for kind, value in items[abstract_pos+2:]:
        if kind == "keywords":
            lines.append(r"\begin{IEEEkeywords}" + esc(value.split("—", 1)[1].strip()) + r"\end{IEEEkeywords}")
        elif kind == "section":
            active = True
            # Flush result/configuration floats before the next discussion block.
            # This keeps the expanded comparisons out of the bibliography.
            if value in ("Interpretation, Reproducibility, and Limits", "References"):
                lines.append(r"\clearpage")
            if value == "References":
                lines.append(r"\begin{thebibliography}{99}")
            else:
                command = r"\section*{" if value == "Acknowledgment" else r"\section{"
                lines.append(command + esc(value) + "}")
        elif not active:
            continue
        elif kind == "subsection":
            lines.append(r"\subsection{" + esc(value) + "}")
        elif kind == "paragraph":
            match = re.match(r"Equation \((\d+)\)\.", value)
            if match:
                number = int(match[1])
                lines.extend([r"\begin{equation}", EQUATIONS[number], r"\label{eq:"+str(number)+"}", r"\end{equation}"])
            else:
                lines.append(esc(value) + "\n")
        elif kind == "table_caption":
            table_caption = re.sub(r"^Table [IVX]+\. ", "", value)
        elif kind == "table":
            assert table_caption
            table_number += 1
            wide = True
            env = "table*" if wide else "table"
            width = r"\textwidth" if wide else r"\columnwidth"
            columns = ''.join('p{' + str(w) + r'\textwidth}' for w in TABLE_WIDTHS[table_number])
            assert len(value[0]) == len(TABLE_WIDTHS[table_number])
            lines.extend([r"\begin{"+env+r"}[t]", r"\caption{"+esc(table_caption)+"}",
                          r"\label{tab:"+str(table_number)+"}", r"\centering\footnotesize",
                          r"\setlength{\tabcolsep}{3pt}", r"\renewcommand{\arraystretch}{1.13}",
                          r"\begin{tabular}{"+columns+"}", r"\toprule"])
            for i, row in enumerate(value):
                cells = [r"{\raggedright "+esc(cell)+r"\par}" for cell in row]
                lines.append(" & ".join(cells) + r" \\")
                if i == 0:
                    lines.append(r"\midrule")
            lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{"+env+"}"])
            table_caption = ""
        elif kind == "image":
            figure = value[1]
        elif kind == "figure_caption":
            assert figure
            wide = True
            env = "figure*" if wide else "figure"
            width = r"\textwidth" if wide else r"\columnwidth"
            lines.extend([r"\begin{"+env+r"}[t]", r"\centering",
                          r"\includegraphics[width="+width+"]{"+str(Path(figure).with_suffix(".pdf"))+"}",
                          r"\caption{"+esc(re.sub(r"^Fig\. \d+\. ", "", value))+"}", r"\end{"+env+"}"])
            figure = None
        elif kind == "reference":
            match = re.match(r"\[(\d+)\] (.+)", value)
            lines.append(r"\bibitem{ref"+match[1]+"} "+esc(match[2], citations=False))
    assert not figure and not table_caption
    lines.extend([r"\end{thebibliography}", r"\end{document}"])
    return "\n".join(lines)+"\n"


def editable_word(items):
    word_items = [("equation" if k == "paragraph" and v.startswith("Equation (") else k, v) for k, v in items]
    renderer.word(word_items)
    source = FOLDER / "RESEARCH_PAPER.docx"
    target = FOLDER / "paper.docx"
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as new:
        for name in old.namelist():
            data = old.read(name)
            if name == "[Content_Types].xml":
                data = data.decode().replace('</Types>', '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>').encode()
            elif name == "_rels/.rels":
                data = data.decode().replace('</Relationships>', '<Relationship Id="rIdCoreProperties" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>').encode()
            if name == "word/document.xml":
                root = ET.fromstring(data)
                w = "{"+renderer.W+"}"
                body = root.find(w+"body")
                children = list(body)
                before, after = {}, {}
                table_number = 0
                image_number = 0
                for index, child in enumerate(children):
                    if child.tag == w+"tbl":
                        table_number += 1
                        wide = True
                        ratios = TABLE_WIDTHS[table_number]
                        widths = [round(10260 * r / sum(ratios)) for r in ratios]
                        child.find(w+"tblPr/"+w+"tblW").set(w+"w",str(sum(widths)))
                        for node, width in zip(child.findall(w+"tblGrid/"+w+"gridCol"), widths):
                            node.set(w+"w", str(width))
                        for row in child.findall(w+"tr"):
                            for cell, width in zip(row.findall(w+"tc"), widths):
                                cell.find(w+"tcPr/"+w+"tcW").set(w+"w",str(width))
                        if wide:
                            before[index-1] = 2
                            after[index] = 1
                    if child.find(".//"+w+"drawing") is not None:
                        image_number += 1
                        before[index] = 2
                        after[index+1] = 1
                        for node in child.iter():
                            if node.tag.endswith("}extent") or node.tag.endswith("}ext"):
                                if "cx" in node.attrib and "cy" in node.attrib:
                                    ratio = 6515100 / int(node.get("cx"))
                                    node.set("cx", "6515100")
                                    node.set("cy", str(round(int(node.get("cy"))*ratio)))
                body[:] = []
                for index, child in enumerate(children):
                    if index in before:
                        marker = renderer.paragraph()
                        marker.find(w+"pPr").append(renderer.section(before[index]))
                        body.append(marker)
                    body.append(child)
                    if index in after:
                        marker = renderer.paragraph()
                        marker.find(w+"pPr").append(renderer.section(after[index]))
                        body.append(marker)
                for size in root.findall(".//"+w+"pgSz"):
                    size.set(w+"w", "12240"); size.set(w+"h", "15840")
                for margin in root.findall(".//"+w+"pgMar"):
                    for key, val in {"top":"1080", "bottom":"1080", "left":"990", "right":"990"}.items():
                        margin.set(w+key, val)
                for cols in root.findall(".//"+w+"cols"):
                    cols.set(w+"space", "360")
                # Preserve emphasis in the editable Word tables and prose.
                for paragraph in root.findall('.//' + w + 'p'):
                    for run in list(paragraph):
                        node = run.find(w + 't')
                        if node is None or '**' not in (node.text or ''):
                            continue
                        index = list(paragraph).index(run)
                        for offset, piece in enumerate(re.split(r'(\*\*.*?\*\*)', node.text)):
                            clone = copy.deepcopy(run)
                            bold = piece.startswith('**') and piece.endswith('**')
                            clone.find(w + 't').text = piece[2:-2] if bold else piece
                            if bold:
                                properties = clone.find(w + 'rPr')
                                if properties is None:
                                    properties = ET.Element(w + 'rPr'); clone.insert(0, properties)
                                ET.SubElement(properties, w + 'b')
                            paragraph.insert(index + offset, clone)
                        paragraph.remove(run)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            new.writestr(name, data)
        properties = ET.Element("{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}coreProperties")
        ET.SubElement(properties, "{http://purl.org/dc/elements/1.1/}title").text = items[0][1]
        new.writestr("docProps/core.xml", ET.tostring(properties, encoding="utf-8", xml_declaration=True))
    source.unlink()


def webpage(source):
    from markdown_it import MarkdownIt
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(source)
    for image in (FOLDER / "figures").glob("*.png"):
        embedded = base64.b64encode(image.read_bytes()).decode()
        body = body.replace('src="figures/'+image.name+'"', 'src="data:image/png;base64,'+embedded+'"')
    css = 'body{max-width:1000px;margin:40px auto;padding:0 24px;color:#18212a;font:17px/1.6 Georgia,serif}h1{font-size:30px;line-height:1.25}h2{margin-top:2em}h3{font-size:19px}table{border-collapse:collapse;width:100%;font:13px/1.45 Arial,sans-serif;margin:20px 0}td,th{padding:8px;border-bottom:1px solid #cdd5dc;text-align:left}img{max-width:100%;height:auto}a{overflow-wrap:anywhere}p{margin:12px 0}@media print{body{font-size:10pt}h2,h3{break-after:avoid}table{font-size:8pt}img{max-height:230mm}}'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(source.splitlines()[0][2:])+'</title><style>'+css+'</style></head><body>'+body+'</body></html>'


def main():
    source, order = resolve_citations((FOLDER / "manuscript.md").read_text())
    items = renderer.blocks(source)
    abstract_index = next(i for i, pair in enumerate(items) if pair == ("section", "Abstract"))
    abstract = items[abstract_index+1][1]
    assert 150 <= len(abstract.split()) <= 250
    assert not re.search(r"\[\d+\]", abstract)
    assert len([1 for k, _ in items if k == "table"]) == 10
    assert len([1 for k, _ in items if k == "image"]) == 7
    assert len([1 for k, _ in items if k == "reference"]) == len(order)
    assert all((FOLDER / image[1]).exists() for kind, image in items if kind == "image")
    (FOLDER / "paper.md").write_text(source)
    (FOLDER / "paper.tex").write_text(latex(items))
    shutil.copy2(ROOT / "professor_guidelines/templates/IEEEtran.cls", FOLDER / "IEEEtran.cls")
    editable_word(items)
    (FOLDER / "paper.html").write_text(webpage(source))
    compiler = ROOT / ".runtime/ieee-tools/tectonic"
    result = subprocess.run([str(compiler), "--only-cached", "--keep-logs", "--keep-intermediates", "paper.tex"], cwd=FOLDER, text=True, capture_output=True)
    (FOLDER / "build_console.log").write_text(result.stdout+result.stderr)
    if result.returncode:
        raise RuntimeError("\n".join((result.stdout+result.stderr).splitlines()[-20:]))
    shutil.copy2(FOLDER / "paper.pdf", FOLDER / "InfluenceIQ_comparative_revision.pdf")
    bundle_files = ["paper.tex", "paper.md", "manuscript.md", "authors.json", "references.bib", "references.json", "IEEEtran.cls"]
    with zipfile.ZipFile(FOLDER / "paper_latex.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in bundle_files:
            archive.write(FOLDER / name, name)
        for path in (FOLDER / "figures").glob("*.pdf"):
            archive.write(path, str(path.relative_to(FOLDER)))
        archive.write(ROOT / "professor_guidelines/templates/README", "IEEEtran_distribution_README")
        archive.writestr("README.txt", "Compile paper.tex with pdfLaTeX twice, or upload this ZIP to Overleaf. IEEEtran journal mode. Bibliography is embedded in paper.tex; references.bib is supplied for editing. No journal identity, acceptance, copyright notice, or received date is asserted.\n")
    metadata = {"format": "IEEEtran journal; two columns; US Letter", "abstract_words":len(abstract.split()),
                "references":len(order), "tables":10, "figures":7, "equations":4,
                "citation_order":order, "source_sha256":hashlib.sha256((FOLDER / "manuscript.md").read_bytes()).hexdigest(),
                "limitations":["No target journal selected; venue-specific requirements remain.", "Word is an editable companion; the IEEEtran PDF is canonical.", "Independent influence validation remains incomplete."]}
    (FOLDER / "build_manifest.json").write_text(json.dumps(metadata, indent=2)+"\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
