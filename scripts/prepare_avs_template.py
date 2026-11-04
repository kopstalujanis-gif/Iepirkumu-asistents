"""Sanitize the user-approved final example into a reusable, fact-free template.

Usage: python scripts/prepare_avs_template.py /path/to/final.docx
The user's filled example is never copied into the repository.
"""
import sys
from pathlib import Path
from docx import Document


def prepare(source, target):
    d = Document(source)
    if len(d.tables) != 4 or len(d.tables[3].rows) != 17:
        raise ValueError('Neatpazīta gala parauga struktūra.')
    texts = {4:'no {{preparer_genitive}}',5:'{{preparer_role_genitive}}',
             7:'Lūdzu organizēt iesnieguma izskatīšanu un līguma slēgšanu par {{request_subject}}.',
             8:'Pamatot nepieciešamību – {{necessity}}.',
             9:'Iemesls, kāpēc iepirkums netika iekļauts Iepirkuma plānā (ja attiecināms) – {{offplan}}'}
    def set_text(p, text):
        # Preserve the example's paragraph and first run formatting.
        runs = p.runs
        if runs:
            runs[0].text = text
            for r in runs[1:]: r.text = ''
        else: p.add_run(text)
    for i,text in texts.items(): set_text(d.paragraphs[i],text)
    for p in d.tables[0].cell(0,1).paragraphs:
        for r in p.runs:r.text=r.text.replace('☒','☐')
    set_text(d.tables[1].cell(0,0).paragraphs[0], '*Cenu aptauja {{published}} tika publicēta portālā “Iepirkumi.lv”')
    for table,row,key in [(1,2,'selected_supplier'),(1,3,'award_reason'),(2,0,'exception_supplier'),(2,1,'exception_reason')]:
        set_text(d.tables[table].cell(row,1).paragraphs[0],'{{'+key+'}}')
    t=d.tables[3]
    for row,key in {0:'subject',1:'supplier_details',3:'net',4:'vat',5:'gross',6:'advance',7:'advance_days',8:'payment_days',9:'budget',11:'deadline',12:'recurring',13:'delivery_place',15:'municipal_iban',16:'responsible'}.items():
        cell=t.cell(row,5)
        set_text(cell.paragraphs[0],'{{'+key+'}}')
        for p in cell.paragraphs[1:]:p._p.getparent().remove(p._p)
    set_text(t.cell(11,0).paragraphs[0],'☐')
    set_text(t.cell(14,5).paragraphs[0],'☐ Jā  ☐ Nē')
    for name in ['author','last_modified_by','title','subject','comments','keywords','category','identifier','content_status','language','version']:
        setattr(d.core_properties,name,'')
    d.save(target)


if __name__=='__main__':
    prepare(sys.argv[1], Path(__file__).resolve().parents[1]/'templates'/'avs_2026.docx')
