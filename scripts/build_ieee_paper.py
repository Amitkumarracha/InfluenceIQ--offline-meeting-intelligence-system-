"""Render the authored IEEE manuscript to LaTeX, editable Word and HTML.

PDF uses the unmodified IEEEtran conference class; Word mirrors its page geometry.
Run --pdf with a local tectonic compiler, or compile RESEARCH_PAPER.tex separately.
"""
import argparse
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FOLDER = ROOT / 'professor_guidelines'
SOURCE = FOLDER / 'RESEARCH_PAPER.md'
OUT = FOLDER / 'evaluation/ieee_paper'


def blocks(source):
    result = []
    references = False
    for chunk in re.split(r'\n\s*\n', source.strip()):
        text = chunk.strip()
        if text.startswith('### '):
            kind, text = 'subsection', re.sub(r'^[A-Z]\. ', '', text[4:])
        elif text.startswith('## '):
            kind, text = 'section', re.sub(r'^[IVX]+\. ', '', text[3:])
            references = text == 'References'
        elif text.startswith('# '):
            kind, text = 'title', text[2:]
        elif text.startswith('|'):
            rows = [[cell.strip() for cell in line.strip().strip('|').split('|')] for line in text.splitlines()]
            assert len(rows) >= 3 and all(re.fullmatch(r':?-+:?', cell) for cell in rows[1])
            assert all(len(row) == len(rows[0]) for row in rows)
            result.append(('table', [rows[0], *rows[2:]])); continue
        elif text.startswith('!['):
            match = re.fullmatch(r'!\[([^]]+)\]\(([^)]+)\)', text)
            assert match, text
            result.append(('image', match.groups())); continue
        elif re.match(r'Table [IVX]+\.', text):
            kind = 'table_caption'
        elif re.match(r'Fig\. \d+\.', text):
            kind = 'figure_caption'
        elif references:
            assert re.match(r'^\[\d+\] ', text)
            kind = 'reference'
        elif text.startswith('Index Terms—'):
            kind = 'keywords'
        elif re.search(r'\. \([12]\)$', text):
            kind = 'equation'
        else:
            kind = 'paragraph'
        result.append((kind, text))
    return result


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import FancyBboxPatch
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'savefig.dpi': 350,
                         'pdf.fonttype': 42, 'ps.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(3.5, 3.0)); ax.set_axis_off()
    boxes = [(.03, .75, .44, .21, 'Audio recording', 'Local ASR + speakers'),
             (.53, .75, .44, .21, 'Optional PPTX', 'Text + available times'),
             (.07, .45, .86, .21, 'Source passages and slide links', 'Word cache / segment IDs / timestamps'),
             (.07, .13, .86, .22, 'Learned English discussion review', 'Forest + linear scores / audio seek')]
    for x, y, w, h, title, detail in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.008',facecolor='#f2f5f7',edgecolor='#263c4f',linewidth=.8))
        ax.text(x+w/2,y+h*.68,title,ha='center',va='center',fontsize=7.8)
        ax.text(x+w/2,y+h*.28,detail,ha='center',va='center',fontsize=6.9)
    for start,end in [((.25,.74),(.4,.67)),((.75,.74),(.6,.67)),((.5,.44),(.5,.36))]:
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','lw':.9})
    ax.plot([0,1],[.08,.08],ls='--',color='#555',lw=.8)
    ax.text(.5,.015,'Separate: decision rules / exploratory influence',ha='center',va='center',fontsize=7)
    fig.tight_layout(pad=.25)
    for suffix in ['png','pdf','svg']: fig.savefig(FOLDER/f'figures/ieee_architecture.{suffix}',bbox_inches='tight')
    plt.close(fig)
    data=json.loads((FOLDER/'evaluation/classifier_comparison/summary.json').read_text())
    names=['Logistic','Naive Bayes','Linear SVM','Forest','Combination']
    rows=[next(row['test'] for row in data['models'] if row['method']==name+'__context_40')
          for name in ['logistic_regression','complement_nb','linear_svm','random_forest']]
    rows.append(json.loads((FOLDER/'evaluation/pipeline_improvement/summary.json').read_text())['test'])
    fig,ax=plt.subplots(figsize=(3.5,2.2)); y=np.arange(len(rows))
    for shift,key,label,color in [(-.17,'f1','F1','#364e63'),(.17,'average_precision','Average precision','#a0aeb7')]:
        ax.barh(y+shift,[100*row[key] for row in rows],height=.32,label=label,color=color)
    ax.set_yticks(y,names);ax.invert_yaxis();ax.set_xlim(0,70)
    ax.set_xlabel('Historical score (%)')
    ax.legend(loc='lower left',bbox_to_anchor=(0,1.03),ncol=2,frameon=False,fontsize=7,borderaxespad=0)
    fig.tight_layout(pad=.4)
    for suffix in ['png','pdf','svg']: fig.savefig(FOLDER/f'figures/ieee_classifier_results.{suffix}',bbox_inches='tight')
    plt.close(fig)


def tex_escape(text, citations=True):
    # Token placeholders keep URLs and citation commands out of text escaping.
    tokens=[]
    def hold(value):
        tokens.append(value); return f'ZZTOKEN{len(tokens)-1}ZZ'
    text=re.sub(r'https?://[^\s]+',lambda m:hold(r'\url{'+m.group().rstrip('.')+'}'+('.' if m.group().endswith('.') else '')),text)
    if citations:
        text=re.sub(r'\[(\d+)\]',lambda m:hold(r'\cite{ref'+m[1]+'}'),text)
    replacements={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_',
                  '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
                  '—':'---','–':'--','−':r'\(-\)','≥':r'\(\geq\)',
                  '“':'``','”':"''",'’':"'",'á':r"\'{a}",'č':r'\v{c}','é':r"\'{e}",'ř':r'\v{r}'}
    text=''.join(replacements.get(c,c) for c in text)
    for i,token in enumerate(tokens):text=text.replace(f'ZZTOKEN{i}ZZ',token)
    return text


def latex(items):
    title=items[0][1]; abstract=next(items[i+1][1] for i,(k,v) in enumerate(items) if k=='section' and v=='Abstract')
    abstract_index=next(i for i,(k,v) in enumerate(items) if k=='section' and v=='Abstract')
    authors=[v for k,v in items[1:abstract_index] if k=='paragraph']
    assert len(authors)>=3
    parts=[r'\documentclass[conference,a4paper]{IEEEtran}',r'\usepackage[T1]{fontenc}',
           r'\usepackage{amsmath,graphicx,booktabs,url,balance}',r'\urlstyle{same}',
           r'\begin{document}',r'\title{'+tex_escape(title)+'}',
           r'\author{\IEEEauthorblockN{'+tex_escape(authors[0])+r'}\IEEEauthorblockA{'+r'\\'.join(tex_escape(line) for line in authors[1:])+'}}',
           r'\maketitle',r'\begin{abstract}'+tex_escape(abstract)+r'\end{abstract}']
    active=False;caption='';image=None;in_references=False
    for kind,text in items:
        if kind=='keywords':
            parts.append(r'\begin{IEEEkeywords}'+tex_escape(text.split('—',1)[1].strip())+r'\end{IEEEkeywords}');continue
        if kind=='section':
            if text=='Abstract':continue
            active=True
            if text=='References':parts.append(r'\begin{thebibliography}{99}');in_references=True
            else:
                if text=='Discussion and Limitations':parts.append(r'\balance')
                parts.append(('\\section*{' if text=='Acknowledgment' else '\\section{')+tex_escape(text)+'}')
            continue
        if not active:continue
        if kind=='subsection':parts.append(r'\subsection{'+tex_escape(text)+'}')
        elif kind=='paragraph':parts.append(tex_escape(text)+'\n')
        elif kind=='equation':
            assert text in ['s(i) = 0.75 f(i) + 0.25 l(i). (1)',
                            'y_hat(i) = 1[mean_{j in N(i)} s(j) >= 0.357740]. (2)']
            eq=(r's_i=0.75f_i+0.25l_i' if text.endswith('(1)') else
                r'\hat y_i=\mathbf{1}\!\left[\frac{1}{|N(i)|}\sum_{j\in N(i)}s_j\geq0.357740\right]')
            parts.append(r'\begin{equation}'+eq+r'\end{equation}')
        elif kind=='table_caption':caption=re.sub(r'^Table [IVX]+\. ','',text)
        elif kind=='table':
            assert caption
            columns=len(text[0]); first=.33 if columns==5 else (.38 if columns==3 else .31)
            spec=f'p{{{first:.3f}\\columnwidth}}'+('r'*(columns-1))
            # Text-width first column plus numeric columns keeps five-column results readable.
            lines=[r'\begin{table}[t]',r'\caption{'+tex_escape(caption)+'}',r'\centering\footnotesize',
                   r'\setlength{\tabcolsep}{2pt}',r'\begin{tabular}{'+spec+'}',r'\toprule']
            for i,row in enumerate(text):
                lines.append(' & '.join(tex_escape(c,citations=False) for c in row)+r' \\')
                if i==0:lines.append(r'\midrule')
            lines.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}']);parts.extend(lines);caption=''
        elif kind=='image':image=text[1]
        elif kind=='figure_caption':
            assert image
            parts.extend([r'\begin{figure}[t]',r'\centering',r'\includegraphics[width=\columnwidth]{'+str(Path(image).with_suffix('.pdf'))+'}',
                          r'\caption{'+tex_escape(re.sub(r'^Fig\. \d+\. ','',text))+'}',r'\end{figure}']);image=None
        elif kind=='reference':
            match=re.match(r'\[(\d+)\] (.+)',text)
            parts.append(r'\bibitem{ref'+match[1]+'} '+tex_escape(match[2],citations=False))
    assert in_references and not image and not caption
    parts.extend([r'\end{thebibliography}',r'\end{document}'])
    return '\n'.join(parts)+'\n'


W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ET.register_namespace('w',W)
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
ET.register_namespace('r',R)

def element(tag,attrs=None,text=None):
    result=ET.Element('{'+W+'}'+tag,{'{'+W+'}'+k:str(v) for k,v in (attrs or {}).items()})
    if text is not None:result.text=text
    return result


def paragraph(text='',style='Body'):
    p=element('p');props=element('pPr');props.append(element('pStyle',{'val':style}));p.append(props)
    run=element('r');rp=element('rPr');rp.append(element('rFonts',{'ascii':'Times New Roman','hAnsi':'Times New Roman','eastAsia':'Times New Roman','cs':'Times New Roman'}));run.append(rp)
    t=element('t',text=text);t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');run.append(t);p.append(run)
    return p


def section(columns):
    props=element('sectPr');props.append(element('type',{'val':'continuous'}))
    props.append(element('pgSz',{'w':11906,'h':16838}))
    props.append(element('pgMar',{'top':1080,'right':812,'bottom':2435,'left':812,'header':0,'footer':0,'gutter':0}))
    props.append(element('cols',{'num':columns,'space':240}));return props


def word(items):
    from PIL import Image
    doc=element('document');body=element('body');doc.append(body);media={};relations=[];active=False;abstract_pending=False
    for kind,text in items:
        if kind=='title':body.append(paragraph(text,'Title'));continue
        if kind=='section' and text=='Abstract':
            body[-1].find('{'+W+'}pPr').append(section(1));active=True;abstract_pending=True;continue
        if not active:
            body.append(paragraph(text,'Author'));continue
        if kind=='table':
            table=element('tbl');props=element('tblPr');props.append(element('tblW',{'w':5021,'type':'dxa'}))
            borders=element('tblBorders')
            for edge in ['top','bottom','insideH']:borders.append(element(edge,{'val':'single','sz':4,'color':'777777'}))
            props.append(borders);table.append(props)
            n=len(text[0]);widths=([1900]+[(5021-1900)//(n-1)]*(n-1))
            grid=element('tblGrid')
            for width in widths:grid.append(element('gridCol',{'w':width}))
            table.append(grid)
            for i,row in enumerate(text):
                tr=element('tr');trprops=element('trPr');trprops.append(element('cantSplit'))
                if i==0:trprops.append(element('tblHeader'))
                tr.append(trprops)
                for width,value in zip(widths,row):
                    cell=element('tc');cp=element('tcPr');cp.append(element('tcW',{'w':width,'type':'dxa'}));cell.append(cp)
                    cell.append(paragraph(value,'TableHead' if i==0 else 'TableCell'));tr.append(cell)
                table.append(tr)
            body.append(table);continue
        if kind=='image':
            path=FOLDER/text[1];width,height=Image.open(path).size;rid=f'rIdImage{len(media)+1}'
            name=f'image{len(media)+1}.png';media[name]=path.read_bytes();relations.append((rid,'media/'+name))
            cx=3180000;cy=round(cx*height/width)
            drawing=ET.fromstring(f'''<w:r xmlns:w="{W}" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" xmlns:r="{R}"><w:drawing><wp:inline><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{len(media)}" name="{html.escape(text[0],quote=True)}"/><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>''')
            p=paragraph(style='Figure');p.append(drawing);body.append(p);continue
        if kind=='section':style='Heading1'
        elif kind=='subsection':style='Heading2'
        elif kind=='reference':style='Reference'
        elif kind=='table_caption':style='TableCaption'
        elif kind=='figure_caption':style='Caption'
        elif kind=='equation':style='Equation'
        elif kind=='keywords':style='Keywords'
        else:
            style='Abstract' if abstract_pending else 'Body'
            if abstract_pending:text='Abstract—'+text;abstract_pending=False
        body.append(paragraph(text,style))
    # Explicit numbering avoids Word version-dependent outline defaults.
    count=0;subcount=0
    for p in body.findall('{'+W+'}p'):
        s=p.find('{'+W+'}pPr/{'+W+'}pStyle'); t=p.find('.//{'+W+'}t')
        if s is not None and s.get('{'+W+'}val')=='Heading1' and t.text not in ['Acknowledgment','References']:
            count+=1;subcount=0;t.text=['I','II','III','IV','V','VI','VII'][count-1]+'. '+t.text.upper()
        elif s is not None and s.get('{'+W+'}val')=='Heading2':
            t.text=chr(65+subcount)+'. '+t.text;subcount+=1
    body.append(section(2))
    styles=element('styles')
    for name,size,align,bold,italic in [('Body',20,'both',False,False),('Title',48,'center',False,False),
        ('Author',22,'center',False,False),('Abstract',18,'both',True,False),('Keywords',18,'both',True,True),
        ('Heading1',20,'center',False,False),('Heading2',20,'left',False,True),('Reference',16,'both',False,False),
        ('Caption',16,'center',False,False),('TableCaption',16,'center',False,False),('Figure',20,'center',False,False),('Equation',20,'center',False,False),
        ('TableCell',16,'left',False,False),('TableHead',16,'left',True,False)]:
        s=element('style',{'type':'paragraph','styleId':name});s.append(element('name',{'val':name}))
        pp=element('pPr');pp.append(element('jc',{'val':align}));pp.append(element('spacing',{'after':0,'before':100 if name.startswith('Heading') else 0,'line':240,'lineRule':'auto'}))
        if name=='Body':pp.append(element('ind',{'firstLine':200}))
        if name.startswith('Heading') or name in ['TableCaption','Figure']:pp.append(element('keepNext'))
        if name in ['Caption','TableCaption','Figure']:pp.append(element('keepLines'))
        if name=='Reference':pp.append(element('ind',{'left':230,'hanging':230}))
        s.append(pp);rp=element('rPr');rp.append(element('rFonts',{'ascii':'Times New Roman','hAnsi':'Times New Roman'}));rp.append(element('sz',{'val':size}))
        if bold:rp.append(element('b'))
        if italic:rp.append(element('i'))
        s.append(rp);styles.append(s)
    relns='http://schemas.openxmlformats.org/package/2006/relationships'
    rel=ET.Element('Relationships',xmlns=relns)
    ET.SubElement(rel,'Relationship',Id='rIdStyles',Type=R+'/styles',Target='styles.xml')
    for rid,target in relations:ET.SubElement(rel,'Relationship',Id=rid,Type=R+'/image',Target=target)
    content='''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    with zipfile.ZipFile(FOLDER/'RESEARCH_PAPER.docx','w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml',content)
        archive.writestr('_rels/.rels',f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml',ET.tostring(doc,encoding='utf-8',xml_declaration=True))
        archive.writestr('word/styles.xml',ET.tostring(styles,encoding='utf-8',xml_declaration=True))
        archive.writestr('word/_rels/document.xml.rels',ET.tostring(rel,encoding='utf-8',xml_declaration=True))
        for name,data in media.items():archive.writestr('word/media/'+name,data)


def webpage(source):
    from markdown_it import MarkdownIt
    parser=MarkdownIt('commonmark',{'html':False}).enable('table')
    split=source.index('## Abstract');head=parser.render(source[:split]);body=parser.render(source[split:])
    body=body.replace('<h2>Abstract</h2>\n<p>','<p>Abstract—',1)
    for path in [FOLDER/'figures/ieee_architecture.png',FOLDER/'figures/ieee_classifier_results.png']:
        body=body.replace('src="figures/'+path.name+'"','src="data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()+'"')
    css='''@page{size:A4;margin:19mm 14.3mm 43mm}*{box-sizing:border-box}body{max-width:181.4mm;margin:19mm auto;color:#111;background:#fff;font:10pt/1.16 "Times New Roman","Noto Serif",serif}header{text-align:center;margin-bottom:7mm}h1{font-size:24pt;font-weight:normal;line-height:1.08;margin:0 0 5mm}header p{margin:1mm 0;font-size:11pt}main{column-count:2;column-gap:4.22mm}p{text-align:justify;margin:0;text-indent:1em;orphans:2;widows:2}h2{text-align:center;font-size:10pt;font-weight:normal;text-transform:uppercase;margin:3mm 0 1.5mm;break-after:avoid}h3{font-size:10pt;font-weight:normal;font-style:italic;margin:2mm 0 1mm;break-after:avoid}table{width:100%;border-collapse:collapse;font-size:8pt;break-inside:avoid;margin:1mm 0 3mm}th,td{padding:1mm .5mm;text-align:left;border-bottom:.3pt solid #aaa}img{width:100%;height:auto}p:has(img){text-indent:0;break-inside:avoid;break-after:avoid}main>p:first-child{font-size:9pt;font-weight:bold;text-indent:0}a{color:inherit;overflow-wrap:anywhere}p:has(+table){font-size:8pt;text-indent:0;text-align:center;break-after:avoid}p:has(img)+p{font-size:8pt;text-indent:0;margin-bottom:2mm}h2:last-of-type~p{font-size:8pt;text-indent:-1em;padding-left:1em;margin-bottom:1mm}@media(max-width:650px){body{margin:20px}main{column-count:1}}'''
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>InfluenceIQ — IEEE paper</title><style>'+css+'</style></head><body><header>'+head+'</header><main>'+body+'</main></body></html>'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pdf',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    source=SOURCE.read_text();items=blocks(source)
    assert len([1 for k,v in items if k=='reference'])==15
    assert len([1 for k,v in items if k=='table'])==4
    assert len([1 for k,v in items if k=='image'])==2
    figures()
    (FOLDER/'RESEARCH_PAPER.tex').write_text(latex(items))
    shutil.copy2(FOLDER/'templates/IEEEtran.cls',FOLDER/'IEEEtran.cls')
    word(items);(FOLDER/'RESEARCH_PAPER.html').write_text(webpage(source))
    with zipfile.ZipFile(FOLDER/'RESEARCH_PAPER_LATEX.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in ['RESEARCH_PAPER.tex','RESEARCH_PAPER.md','IEEEtran.cls','templates/README',
                     'figures/ieee_architecture.pdf','figures/ieee_classifier_results.pdf']:
            archive.write(FOLDER/name,name)
        archive.writestr('README.txt','Compile RESEARCH_PAPER.tex with pdfLaTeX twice, or upload this ZIP to Overleaf.\n'
                         'IEEEtran conference mode, A4; author and faculty-guide details are from the supplied project cover.\n'
                         'Author and faculty-guide emails were supplied by the user; no corresponding author is designated.\n'
                         'Venue-specific submission metadata has not been supplied.\n'
                         'IEEEtran is unmodified; original license/support text is included.\n')
    if args.pdf:
        compiler=ROOT/'.runtime/ieee-tools/tectonic'
        assert compiler.exists(),'Install tectonic or compile the generated source with your LaTeX distribution'
        subprocess.run([str(compiler),'--keep-logs','--keep-intermediates','RESEARCH_PAPER.tex'],cwd=FOLDER,check=True)
        shutil.copy2(FOLDER/'RESEARCH_PAPER.log',OUT/'latex.log')
        assert (FOLDER/'RESEARCH_PAPER.pdf').stat().st_size>20000
    provenance={'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'IEEEtran_sha256':hashlib.sha256((FOLDER/'IEEEtran.cls').read_bytes()).hexdigest(),
                'format':'IEEEtran conference,a4paper; 10pt default; two columns',
                'format_sources':['https://cai.ieee.org/2025/manuscript-templates-for-conference-proceedings/',
                                  'https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/'],
                'class_source':'https://mirrors.ctan.org/macros/latex/contrib/IEEEtran.zip',
                'author_details':{'source':'User-provided Screenshot_20261019_231611.png',
                                  'status':'Names, affiliation and faculty guide transcribed; all five contact emails supplied by the user'},
                'limits':['No venue selected; its page limit and review/anonymity rules remain to be checked.',
                          'PDF eXpress certification not performed.','Word uses matching geometry; pagination may differ by installed fonts.']}
    (OUT/'build.json').write_text(json.dumps(provenance,indent=2))
    print(json.dumps(provenance,indent=2))


if __name__=='__main__':main()
