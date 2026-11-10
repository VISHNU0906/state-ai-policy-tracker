"""Render the submission and one-page rationale from the Markdown sources."""
from pathlib import Path
import re,html
import markdown
from xml.etree import ElementTree as ET
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyClean',fontName='Helvetica',fontSize=10.5,leading=14.5,spaceAfter=9,textColor=colors.black))
styles['Title'].fontName='Helvetica-Bold';styles['Title'].fontSize=20;styles['Title'].leading=24;styles['Title'].alignment=0;styles['Title'].spaceAfter=17
styles['Heading2'].fontName='Helvetica-Bold';styles['Heading2'].fontSize=13;styles['Heading2'].leading=17;styles['Heading2'].spaceBefore=14;styles['Heading2'].spaceAfter=8;styles['Heading2'].textColor=colors.black
styles['Heading2'].keepWithNext=True

def inline(node):
    value=ET.tostring(node,encoding='unicode').strip()
    value=re.sub(r'<a href="([^"]+)"[^>]*>',r'<link href="\1" color="#135b78">',value).replace('</a>','</link>')
    value=value.replace('<strong>','<b>').replace('</strong>','</b>')
    return re.sub(r'^<(p|h1|h2)>|</(p|h1|h2)>$','',value)

def footer(canvas,doc):
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawString(50,25,'State AI Policy Tracker | Vishnu Kosuri | Cutoff 10 November 2026')
    canvas.drawRightString(562,25,str(doc.page))

def render(source,destination):
    soup=ET.fromstring('<root>'+markdown.markdown(source.read_text(encoding='utf-8'))+'</root>')
    story=[]
    for n in soup:
        if n.tag in ['h1','h2','p']:
            img=n.find('img') if n.tag=='p' else None
            if img is not None:
                f=ROOT/img.attrib['src'];im=Image(str(f));im.drawHeight=im.imageHeight*490/im.imageWidth;im.drawWidth=490
                story.extend([Spacer(1,5),im,Spacer(1,10)])
            else:story.append(Paragraph(inline(n),styles['Title' if n.tag=='h1' else 'Heading2' if n.tag=='h2' else 'BodyClean']))
    doc=SimpleDocTemplate(str(destination),pagesize=letter,leftMargin=50,rightMargin=50,topMargin=42,bottomMargin=44,title=source.stem,author='Vishnu Kosuri')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

def main():
    OUT.mkdir(exist_ok=True)
    render(ROOT/'SUBMISSION.md',OUT/'Submission.pdf')
    render(ROOT/'RATIONALE.md',OUT/'Rationale.pdf')
    import fitz
    qa=ROOT.parent/'qa';qa.mkdir(exist_ok=True)
    for name in ['Submission','Rationale']:
        d=fitz.open(OUT/f'{name}.pdf')
        print(name,len(d),'pages')
        if name=='Rationale':assert len(d)==1
        for i,page in enumerate(d):page.get_pixmap(matrix=fitz.Matrix(1,1)).save(qa/f'{name}-{i+1}.png')

if __name__=='__main__':main()
