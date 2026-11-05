from io import BytesIO
import json
import pytest
from iepirkumi import ai
from iepirkumi.models import Procurement, Field
from iepirkumi.importer import Chunk


def response(entries,status='completed'):
    return BytesIO(json.dumps({'status':status,'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'extractions':entries})}]}],
                              'usage':{'input_tokens':100,'output_tokens':20}}).encode())


def test_ai_requires_key_and_consent_before_any_network_call():
    job=ai.prepare([Chunk('a.docx','row 1','Kopējā cena: 563.26')])
    def never(*a,**k):pytest.fail('Network must not be called')
    with pytest.raises(PermissionError):ai.request(job,'secret',transport=never)
    with pytest.raises(ValueError):ai.request(job,'',consent=True,transport=never)


def test_ai_evidence_and_request_properties():
    job=ai.prepare([Chunk('a.docx','row 1','Kopējā cena: 563.26')])
    entry={'field':'gross','value':'563.26','source_id':'0','quote':'Kopējā cena: 563.26','page':None}
    def mock(req,timeout):
        assert req.full_url==ai.ENDPOINT and req.get_method()=='POST'
        body=json.loads(req.data)
        assert body['store'] is False and body['max_output_tokens']==6000
        assert body['text']['format']['strict'] is True
        return response([entry])
    entries,usage=ai.request(job,'test-key',consent=True,transport=mock)
    p=Procurement();ai.apply(p,entries)
    assert p.fields['gross'].value=='563.26' and not p.fields['gross'].confirmed
    assert p.fields['gross'].candidates[0].source=='a.docx'
    assert usage['input_tokens']==100
    assert 'test-key' not in p.to_json()


@pytest.mark.parametrize('change',[{'field':'category'},{'source_id':'missing'},{'quote':'invented'},{'quote':''}])
def test_ai_rejects_unsupported_or_unverifiable_results(change):
    job=ai.prepare([Chunk('a.docx','row 1','Kopējā cena: 563.26')])
    e={'field':'gross','value':'563.26','source_id':'0','quote':'Kopējā cena: 563.26','page':None};e.update(change)
    entries,usage=ai.request(job,'test',consent=True,transport=lambda *a,**k:response([e]))
    assert not entries and len(usage['validation']['rejected'])==1


def test_ai_limits_never_silently_truncate():
    with pytest.raises(ValueError):ai.prepare([Chunk('big','1','x'*(ai.MAX_CHARS+1))])
    with pytest.raises(ValueError):ai.prepare([])


def test_ai_pdf_input_and_page_validation(tmp_path):
    import pymupdf
    doc=pymupdf.open();doc.new_page();path=tmp_path/'scan.pdf';doc.save(path)
    job=ai.prepare([],pdf_path=path)
    assert job['pages']==1
    assert job['payload']['input'][0]['content'][1]['type']=='input_file'
    e={'field':'net','value':'10.00','source_id':'pdf','quote':'10.00','page':2}
    entries,usage=ai.request(job,'test',consent=True,transport=lambda *a,**k:response([e]))
    assert not entries and len(usage['validation']['rejected'])==1


def test_one_bad_quote_does_not_discard_valid_fields():
    job=ai.prepare([Chunk('offer.pdf','lpp. 2','Kopējā cena ar PVN: 1 397,91 EUR')])
    good={'field':'gross','value':'1397.91','source_id':'0','quote':'1 397,91 EUR','page':2}
    bad={'field':'bank','value':'Nezināma banka','source_id':'0','quote':'Nezināma banka','page':2}
    entries,usage=ai.request(job,'test',consent=True,transport=lambda *a,**k:response([good,bad]))
    p=Procurement();ai.apply(p,entries)
    assert p.fields['gross'].value=='1397.91' and not p.fields['gross'].confirmed
    assert not p.fields['bank'].value
    assert usage['validation']['accepted']==1 and len(usage['validation']['rejected'])==1


def test_typography_normalization_does_not_change_numbers_or_wording():
    from iepirkumi.citations import normalized,locate
    source=Chunk('offer.pdf','lpp. 2','Piegāde – “statīvi”\nKonta nr. LV31HABA0551031799745\nsaņem-\nšanas')
    assert locate('Piegāde - "statīvi"',source,{'0':source})
    assert locate('saņemšanas',source,{'0':source})
    assert locate('e-rēķina',Chunk('a','1','e-\nrēķina'),{})
    assert not locate('LV31HABA0551031799746',source,{'0':source})
    assert not locate('citāda piegāde',source,{'0':source})
    assert normalized('500-\n5999')!='5005999'


def test_page_correction_is_limited_to_same_file():
    from iepirkumi.citations import locate
    a=Chunk('a.pdf','lpp. 1','Ievads');b=Chunk('a.pdf','lpp. 2','Banka: Swedbank')
    c=Chunk('other.pdf','lpp. 1','IBAN 123')
    assert locate('Banka: Swedbank',a,{'0':a,'1':b,'2':c}) is b
    assert locate('IBAN 123',a,{'0':a,'1':b,'2':c}) is None


def test_drying_rack_private_pdf_quote_recovery():
    import os
    from pathlib import Path
    from iepirkumi.importer import read_file
    root=os.environ.get('IEPIRKUMI_SAMPLES')
    if not root:pytest.skip('Private PDF regression samples are outside Git')
    files=list(Path(root).rglob('AVS_zimejumu_zavesanas_stativi_pretendenta_pieteikums_2026.pdf'))
    if not files:pytest.skip('Drying rack sample is unavailable')
    chunks,warnings=read_file(files[0]);assert len(chunks)==2 and not warnings
    job=ai.prepare(chunks)
    good={'field':'payment','value':'14 kalendāro dienu pēcapmaksa','source_id':'0',
          'quote':'pēcapmaksa 14 kalendāro dienu laikā pēc preču pieņemšanas un korekta e-rēķina saņemšanas','page':1}
    bad={'field':'bank','value':'Cita banka','source_id':'1','quote':'Cita banka','page':2}
    entries,usage=ai.request(job,'test',consent=True,transport=lambda *a,**k:response([good,bad]))
    assert len(entries)==1 and entries[0][2].location=='lpp. 2'
    assert len(usage['validation']['rejected'])==1
