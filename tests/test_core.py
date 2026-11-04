from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import pytest
from docx import Document
from docx.oxml.ns import qn
from iepirkumi.models import Procurement, Field, Evidence
from iepirkumi.validation import category, validate
from iepirkumi.storage import Store, save_project, load_project
from iepirkumi.word import generate, default_template
from iepirkumi.importer import read_file, extract_protocol, extract_offers, Chunk, ImportFailure


@pytest.mark.parametrize('amount,expected',[('465,50','1'),('499.99','1'),('500',None),('500.01','2'),('5999','2'),('5999.01',None),('6000',None),('6000.01','3')])
def test_categories(amount,expected):
    assert category(amount)==expected


@pytest.mark.parametrize('amount',['NaN','Infinity','-1','abc'])
def test_invalid_money(amount):
    with pytest.raises(ValueError): category(amount)


def test_conflict_preserves_evidence():
    f=Field(); f.add(Evidence('465.50','protocol.pdf','lpp. 5','summa'))
    f.add(Evidence('480.00','offer.docx','rinda 1','summa'))
    assert f.conflict and not f.value
    f.value='465.50'; f.edited=True; f.confirmed=True
    f.add(Evidence('490','new.pdf','lpp. 1','summa'))
    assert f.value=='465.50' and not f.confirmed and len(f.candidates)==3


def test_roundtrip_and_registries(tmp_path):
    s=Store(tmp_path/'db.sqlite3')
    a=s.save_record('employee',{'first_name':'Anna','last_name':'A','position':'Vadītāja'})
    b=s.save_record('employee',{'first_name':'Berta','last_name':'B','position':'Grāmatvede'})
    s.set_setting('preparer',a); s.set_setting('responsible',b)
    assert s.setting('preparer')!=s.setting('responsible')
    p=Procurement(); p.fields['subject']=Field('Līgums', [Evidence('Līgums','a.pdf','1','test')],True,True)
    save_project(p,tmp_path/'p.json'); assert load_project(tmp_path/'p.json').to_json()==p.to_json()
    s.backup(tmp_path/'backup.db'); s.erase(); assert not s.records('employee')
    saved=Store(tmp_path/'backup.db'); assert len(saved.records('employee'))==2
    saved.close(); s.close()


def test_word_preserves_original_and_font(tmp_path):
    p=Procurement()
    for k,v in {'subject':'Izotermisko folijas segu iegāde','net':'465.50','gross':'563.26',
                'preparer':'Anna Ozola\nDirektore\n111\na@example.lv','responsible':'Berta Liepa\nSpeciāliste\n222\nb@example.lv',
                'supplier_name':'DM PREMIUM SIA','registration':'40103206925','deadline':'15.12.2026','electronic':'Jā'}.items():
        p.fields[k]=Field(v,confirmed=True)
    out=tmp_path/'out.docx'; generate(p,out,approved_layout=False)
    d=Document(out); orig=Document(default_template())
    assert len(d.tables)==len(orig.tables)==4
    assert [len(t.rows) for t in d.tables]==[len(t.rows) for t in orig.tables]
    assert d.sections[0]._sectPr.xml==orig.sections[0]._sectPr.xml
    assert 'Anna Ozola' in d.paragraphs[4].text and 'Direktore'==d.paragraphs[5].text
    assert 'Berta Liepa' in d.tables[3].cell(16,5).text
    assert 'Anna Ozola' not in d.tables[3].cell(16,5).text
    assert '97,76'==d.tables[3].cell(4,5).text
    assert '☒' in d.tables[0].cell(0,1).text
    for r in d.element.xpath('.//w:r'):
        assert r.find('w:rPr/w:rFonts',r.nsmap).get(qn('w:ascii'))=='Times New Roman'
    for row in [1,2]:
        for c in d.tables[3].rows[row].cells:
            for paragraph in c.paragraphs:
                for r in paragraph.runs: assert r.font.size.pt==10
    assert not d.element.xpath('.//w:shd')
    assert not d.element.xpath('.//w:drawing')
    assert d.element.xpath('.//w:highlight')
    assert {x.get(qn('w:val')) for x in d.element.xpath('.//w:highlight')}=={'yellow'}
    assert '[izskaidrot, kāpēc darījums nepieciešams]' in d.paragraphs[8].text
    for i in range(15,25): assert d.paragraphs[i].text==orig.paragraphs[i].text


def test_empty_and_boundary_export(tmp_path):
    p=Procurement(); generate(p,tmp_path/'empty.docx')
    p.fields['net'].value='500'; generate(p,tmp_path/'boundary.docx')
    d=Document(tmp_path/'boundary.docx')
    assert '☒' not in d.tables[0].cell(0,1).text
    assert any('robežgadījums' in w for w in validate(p))


def test_zip_path_protection(tmp_path):
    path=tmp_path/'bad.zip'
    with ZipFile(path,'w') as z: z.writestr('../escape.docx',b'bad')
    with pytest.raises(ImportFailure): read_file(path)
    assert not (tmp_path.parent/'escape.docx').exists()


def test_offer_conflicting_deadline():
    p=Procurement(); p.fields['registration'].value='40103206925'
    p.fields['deadline'].add(Evidence('15.12.2026','protocol','2','date'))
    chunks=[Chunk('offer.docx','row 1','Reģistrācijas numurs | 40103206925'),
            Chunk('offer.docx','row 2','Piegādes termiņš | līdz 16.12.2026.')]
    extract_offers(p,chunks)
    assert p.fields['deadline'].conflict and not p.fields['deadline'].value


def test_sample_documents(tmp_path):
    # User-provided sensitive samples stay outside Git; opt-in via environment variable.
    import os
    root=os.environ.get('IEPIRKUMI_SAMPLES')
    if not root: pytest.skip('Set IEPIRKUMI_SAMPLES for private integration samples')
    root=Path(root)
    pdf=next(root.rglob('Folijas_segas_protokols.pdf'))
    offers=next(root.rglob('Folijas_segas_piedavajumi.zip'))
    p=Procurement(); c,w=read_file(pdf); extract_protocol(p,c)
    assert p.fields['net'].value=='465.50'
    assert p.fields['supplier_name'].value=='DM PREMIUM SIA'
    assert p.fields['registration'].value=='40103206925'
    c,w=read_file(offers); extract_offers(p,c)
    assert p.fields['gross'].value=='563.26'
    assert p.fields['payment'].value=='60 dienu pēcapmaksa'
    assert p.fields['deadline'].value=='15.12.2026' and not p.fields['deadline'].conflict
    assert p.fields['iban'].value=='LV24RIKO0000081996780'
    assert len(p.fields['net'].candidates)==2
    generate(p,tmp_path/'sample.docx')


def test_xlsx_offer_and_pdf_manual_fallback(tmp_path):
    from openpyxl import Workbook
    import pymupdf
    w=Workbook();s=w.active
    for row in [('Reģistrācijas numurs','40103206925'),('Kopējā cena par 950 gab. bez PVN (EUR)',480.50),('Kopējā cena ar PVN (EUR)',581.41)]:
        s.append(row)
    path=tmp_path/'offer.xlsx';w.save(path)
    p=Procurement();p.fields['registration'].value='40103206925'
    p.fields['net'].add(Evidence('465.50','protocol.pdf','5','summa'))
    chunks,warnings=read_file(path);extract_offers(p,chunks)
    assert p.fields['net'].conflict and not p.fields['net'].value
    assert p.fields['gross'].value=='581.41'
    d=pymupdf.open();d.new_page();d.save(tmp_path/'scan.pdf')
    chunks,warnings=read_file(tmp_path/'scan.pdf')
    assert warnings and 'skenējums' in chunks[0].quality


def test_export_rejects_wrong_template_and_invalid_amount(tmp_path):
    wrong=Document();wrong.save(tmp_path/'wrong.docx')
    with pytest.raises(ValueError):generate(Procurement(),tmp_path/'out.docx',tmp_path/'wrong.docx')
    p=Procurement();p.fields['net'].value='abc'
    with pytest.raises(ValueError):generate(p,tmp_path/'out.docx')
