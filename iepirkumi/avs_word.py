"""Fill the sanitized, user-approved final layout; formatting is never delegated to AI."""
from decimal import Decimal
from docx import Document
from .models import Field, money
from .validation import category
from .word import replace, font, mark, _check


def generate_avs(project, output, template):
    d=Document(template); f=project.fields
    values={k:v for k,v in f.items()}
    values['selected_supplier']=Field(
        f"{f['supplier_name'].value}, reģ. Nr. {f['registration'].value}"
        if f['supplier_name'].value and f['registration'].value else '',
        confirmed=f['supplier_name'].confirmed and f['registration'].confirmed)
    # Header grammar is explicit input; do not invent Latvian inflections.
    for key in ['net','gross']:
        if f[key].value:
            values[key]=Field(f'{money(f[key].value):.2f}'.replace('.',','),confirmed=f[key].confirmed)
    values['vat']=Field()
    if f['net'].value and f['gross'].value:
        vat=money(f['gross'].value)-money(f['net'].value)
        if vat<0: raise ValueError('Summa ar PVN nedrīkst būt mazāka par summu bez PVN.')
        values['vat']=Field(f'{vat:.2f}'.replace('.',','),confirmed=f['net'].confirmed and f['gross'].confirmed)
    # Do not infer calendar days from a supplier's unspecified "dienas".
    if f['deadline'].value:
        date=f['deadline'].value.strip().removeprefix('līdz ').rstrip('.')
        values['deadline']=Field('līdz '+date+'.',confirmed=f['deadline'].confirmed)
    if f['published'].value:
        values['published']=Field(f['published'].value.rstrip('.')+'.',confirmed=f['published'].confirmed)
    roots=[d.element]+[r.target_part.element for r in d.part.rels.values() if r.reltype.endswith(('/header','/footer'))]
    from docx.text.paragraph import Paragraph
    import re
    for root in roots:
        for node in root.xpath('.//w:p'):
            p=Paragraph(node,d)
            for key in re.findall(r'\{\{(\w+)\}\}',p.text):
                if key=='supplier_details':continue
                if key not in values:raise ValueError('Nezināms veidlapas lauks: '+key)
                v=values[key]
                # Preserve the approved example's blank unused exception section.
                if key.startswith('exception_') and not v.value:
                    replace(p,'{{'+key+'}}',Field(' ',confirmed=True))
                else:
                    replace(p,'{{'+key+'}}',v if v.value else Field('…'))
    supplier=d.tables[3].cell(1,5); p=supplier.paragraphs[0]; p.clear()
    parts=[('supplier_name',''),('registration','Reģ. Nr. '),('vat_number','PVN Nr. '),('address','Juridiskā adrese: '),
           ('bank','Banka: '),('swift','SWIFT: '),('iban','Konts: '),('phone','Tālrunis: '),('email','E-pasts: ')]
    for i,(key,label) in enumerate(parts):
        if i:p.add_run('\n')
        font(p.add_run(label),10)
        r=p.add_run(f[key].value or '…');font(r,10);mark(r,not f[key].value or not f[key].confirmed)
    for label,keys in [('Paraksttiesīgā persona: ',['representative_role','representative','authority']),
                       ('Kontaktpersona līguma izpildei: ',['contact'])]:
        p.add_run('\n');font(p.add_run(label),10)
        for i,key in enumerate(keys):
            if i:p.add_run(' ')
            r=p.add_run(f[key].value or '…');font(r,10);mark(r,not f[key].value or not f[key].confirmed)
    chosen=f['category'].value or (category(f['net'].value) if f['net'].value else '')
    if chosen not in ('','1','2','3',None):raise ValueError('Nederīga vērtības kategorija.')
    for p in d.tables[0].cell(0,1).paragraphs:
        if '☐' not in p.text:continue
        index='1' if 'līdz 500' in p.text else '2' if '500-5999' in p.text else '3'
        if chosen==index:_check(p,1,f['category'].confirmed if f['category'].value else f['net'].confirmed)
        elif not chosen:
            for r in p.runs:mark(r,True)
    t=d.tables[3]
    for row,key in [(11,'deadline'),(12,'recurring')]:
        if f[key].value:_check(t.cell(row,0).paragraphs[0],1,f[key].confirmed)
    electronic=f['electronic'].value.lower()
    if electronic in ('jā','nē'):_check(t.cell(14,5).paragraphs[0],1 if electronic=='jā' else 2,f['electronic'].confirmed)
    else:
        for r in t.cell(14,5).paragraphs[0].runs:mark(r,True)
    from docx.text.run import Run
    for root in roots:
        for node in root.xpath('.//w:r'):font(Run(node,d))
    for row in [1,2]:
        for cell in t.rows[row].cells:
            for para in cell.paragraphs:
                for run in para.runs:font(run,10)
    for style in d.styles:
        if hasattr(style,'font'):style.font.name='Times New Roman'
    d.save(output)
