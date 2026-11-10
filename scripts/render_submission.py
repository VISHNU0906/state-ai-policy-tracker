"""Render portable PDFs from the maintained report blocks and saved figures.

Install reportlab, then run python -m scripts.render_submission.
The submitted PDF and DOCX are Google Docs exports. Rebuilt files have a
separate name so this command never overwrites the checked submission copies.
"""
from pathlib import Path
import html, json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'
STYLES={
 'p':ParagraphStyle('p',fontName='Helvetica',fontSize=10.2,leading=14.1,spaceAfter=9),
 'heading':ParagraphStyle('heading',fontName='Times-Roman',fontSize=23,leading=27,spaceAfter=15),
 'subheading':ParagraphStyle('subheading',fontName='Helvetica-Bold',fontSize=12,leading=16,spaceBefore=8,spaceAfter=7),
 'caption':ParagraphStyle('caption',fontName='Helvetica',fontSize=8.3,leading=11,spaceBefore=5,spaceAfter=12,textColor=colors.HexColor('#444444')),
 'cell':ParagraphStyle('cell',fontName='Helvetica',fontSize=9,leading=12),
 'code':ParagraphStyle('code',fontName='Courier',fontSize=9,leading=13,spaceAfter=12)
}
def para(text,style='p'):return Paragraph(text.replace('\n','<br/>'),STYLES[style])
def render(pages,destination):
 story=[]
 for index,blocks in enumerate(pages):
  if index:story.append(PageBreak())
  for b in blocks:
   kind=b['type']
   if kind in STYLES:story.append(para(b['text'],kind))
   elif kind=='links':story.append(para(' | '.join(f'<a href="{url}">{label}</a>' for label,url in b['items'])))
   elif kind=='image':
    image=Image(str(ROOT/'docs/figures/report'/(b['name']+'.png')))
    ratio=image.imageHeight/image.imageWidth
    image.drawWidth=b['width'];image.drawHeight=ratio*b['width']
    story.append(KeepTogether([image,para(b['caption'],'caption')]))
   elif kind=='table':
    rows=[[para('<b>'+html.escape(c)+'</b>','cell') for c in b['headers']]]
    rows += [[para(html.escape(c),'cell') for c in row] for row in b['rows']]
    table=Table(rows,colWidths=b['widths'],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([
     ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E6EEF7')),
     ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#EFF4F8')]),
     ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D9D9D9')),
     ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
     ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
     ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.extend([table,Spacer(1,10)])
 SimpleDocTemplate(str(destination),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=39,bottomMargin=45,title=destination.stem,author='Vishnu Kosuri').build(story)
def main():
 content=json.loads((OUT/'submission_content.json').read_text(encoding='utf-8'))
 render(content['pages'],OUT/'Submission-rebuilt.pdf')
 render([[{'type':'heading','text':'Rationale'}]+[{'type':'p','text':t} for t in content['rationale']]],OUT/'Rationale-rebuilt.pdf')
 print('Wrote reports/Submission-rebuilt.pdf and reports/Rationale-rebuilt.pdf')
if __name__=='__main__':main()
