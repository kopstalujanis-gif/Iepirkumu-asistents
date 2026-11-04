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
    with pytest.raises(ValueError):ai.request(job,'test',consent=True,transport=lambda *a,**k:response([e]))


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
    with pytest.raises(ValueError):ai.request(job,'test',consent=True,transport=lambda *a,**k:response([e]))
