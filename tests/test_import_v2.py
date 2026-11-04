from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import os
import pytest
import pymupdf
from docx import Document
from iepirkumi.importer import Chunk, read_file
from iepirkumi.models import Procurement, Field, Evidence
from iepirkumi.pipeline import import_chunks
from iepirkumi.word import generate, default_template
from iepirkumi.ocr import tessdata_dir


def test_import_offers_before_protocol_and_recheck_confirmation():
    p=Procurement()
    offers=[Chunk('offer.docx','row 1','Reģistrācijas numurs | 40103206925'),
            Chunk('offer.docx','row 2','Kopējā cena ar PVN (EUR) | 563.26'),
            Chunk('offer.docx','row 3','Banka | Luminor')]
    import_chunks(p,offers)
    assert not p.fields['gross'].value
    protocol=[Chunk('p.pdf','lpp. 1','Slēgt līgumu ar DM PREMIUM SIA. Piedāvājums atbilst TS.\nNosaukums: DM PREMIUM SIA\nReģ.Nr.: 40103206925\nPiedāvājuma summa (EUR bez PVN): 465,50')]
    import_chunks(p,protocol)
    assert p.fields['gross'].value=='563.26' and p.fields['bank'].value=='Luminor'
    p.fields['gross'].confirmed=True
    import_chunks(p,offers)
    assert p.fields['gross'].confirmed and len(p.imports)==4
    assert len(p.fields['gross'].candidates)==1


def test_packaged_ocr_reads_pdf_and_image_without_tesseract_executable(tmp_path,monkeypatch):
    assert tessdata_dir()
    monkeypatch.setenv('PATH','')
    source=pymupdf.open();page=source.new_page(width=500,height=180)
    page.insert_text((25,75),'Invoice 563.26 EUR',fontsize=26)
    png=page.get_pixmap(matrix=pymupdf.Matrix(2,2)).tobytes('png')
    (tmp_path/'invoice.png').write_bytes(png)
    scan=pymupdf.open();p=scan.new_page(width=500,height=180);p.insert_image(p.rect,stream=png)
    scan.save(tmp_path/'scan.pdf')
    for path in [tmp_path/'invoice.png',tmp_path/'scan.pdf']:
        chunks,warnings=read_file(path,ocr=True)
        assert '563.26' in chunks[0].text, warnings
        assert 'OCR' in chunks[0].quality


def test_import_private_zip_with_ocr_in_reverse_order():
    samples=os.environ.get('IEPIRKUMI_SAMPLES')
    if not samples:pytest.skip('Private samples are not in Git')
    root=Path(samples);p=Procurement()
    chunks,warnings=read_file(next(root.rglob('Folijas_segas_piedavajumi.zip')),ocr=True)
    import_chunks(p,chunks,warnings)
    chunks,warnings=read_file(next(root.rglob('Folijas_segas_protokols.pdf')),ocr=True)
    import_chunks(p,chunks,warnings)
    assert p.fields['gross'].value=='563.26'
    assert p.fields['iban'].value=='LV24RIKO0000081996780'
    assert p.fields['vat_number'].value=='LV40103206925'
    assert p.fields['representative_role'].value=='Valdes locekle'
    assert not any('OCR neizdevās' in x for x in p.warnings)
    assert any('OCR' in c['quality'] and c['text'].strip() for c in p.imports if c['source'].endswith('.jpg'))


def test_approved_final_layout_is_generic_and_uses_new_fields(tmp_path):
    p=Procurement()
    for k,v in {'subject':'Izotermisko folijas segu iegāde','request_subject':'izotermisko folijas segu iegādi',
                'preparer_genitive':'ANNAS OZOLAS','preparer_role_genitive':'direktores',
                'net':'465.50','gross':'563.26','payment_days':'60','vat_number':'LV12345678901'}.items():
        p.fields[k]=Field(v,confirmed=True)
    generate(p,tmp_path/'out.docx')
    d=Document(tmp_path/'out.docx')
    assert d.paragraphs[4].text=='no ANNAS OZOLAS'
    assert 'par izotermisko folijas segu iegādi.' in d.paragraphs[7].text
    assert d.tables[3].cell(8,5).text=='60'
    assert 'PVN Nr. LV12345678901' in d.tables[3].cell(1,5).text
    for row in [1,2]:
        for c in d.tables[3].rows[row].cells:
            for para in c.paragraphs:
                for r in para.runs:assert r.font.size.pt==10
    assert not d.element.xpath('.//w:shd')
    # The bundled reusable form contains no sample supplier or employee data.
    template=Document(default_template().with_name('avs_2026.docx'))
    text=' '.join(template.element.itertext())
    for private in ['DM PREMIUM','40103206925','JĀŅA','KOPŠTĀLA','Lilijas','2350','563,26']:
        assert private not in text
