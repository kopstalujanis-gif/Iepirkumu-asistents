import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from iepirkumi.ui import Window, person_text
from iepirkumi.storage import Store
from iepirkumi.importer import Chunk
from iepirkumi.models import Evidence


def test_independent_people_and_supplier_override(tmp_path):
    app=QApplication.instance() or QApplication([])
    s=Store(tmp_path/'registry.db')
    a=s.save_record('employee',{'first_name':'Anna','last_name':'Ozola','position':'Vadītāja'})
    b=s.save_record('employee',{'first_name':'Berta','last_name':'Liepa','position':'Speciāliste'})
    supplier=s.save_record('supplier',{'supplier_name':'Piegādātājs','registration':'123','phone':'111'})
    w=Window(s)
    w.choose_record('preparer',w.combos['preparer'].findData(a))
    w.choose_record('responsible',w.combos['responsible'].findData(b))
    assert w.project.fields['preparer'].value.startswith('Anna Ozola')
    assert w.project.fields['responsible'].value.startswith('Berta Liepa')
    w.choose_record('supplier',w.combos['supplier'].findData(supplier))
    w.editors['phone'].setPlainText('222')
    assert w.project.fields['phone'].value=='222'
    assert s.records('supplier')[0][1]['phone']=='111'
    w.checks['phone'].setChecked(True); assert w.project.fields['phone'].confirmed
    w.editors['phone'].setPlainText('333'); assert not w.project.fields['phone'].confirmed
    w.dirty=False;w.close()
    s2=Store(tmp_path/'registry.db'); w2=Window(s2)
    assert w2.project.fields['preparer'].value.startswith('Anna')
    assert w2.project.fields['responsible'].value.startswith('Berta')
    w2.dirty=False; w2.close()


def test_missing_role_does_not_become_phone():
    assert person_text({'first_name':'Anna','phone':'123'}).split('\n')[1]==''


def test_hidden_sections_and_personal_defaults(tmp_path,monkeypatch):
    import json
    from iepirkumi.models import HIDDEN_FIELDS
    profile=tmp_path/'defaults.json'
    profile.write_text(json.dumps({'employee':{'first_name':'Anna','last_name':'Ozola','position':'Direktore',
        'header_name':'ANNAS OZOLAS','header_role':'direktores','responsible_text':'Anna Ozola; 111; anna@example.lv'}}),encoding='utf-8')
    monkeypatch.setenv('IEPIRKUMI_PROFILE',str(profile))
    app=QApplication.instance() or QApplication([])
    window=Window(Store(tmp_path/'r.db'))
    assert not (set(window.editors)&HIDDEN_FIELDS)
    assert window.project.fields['preparer_genitive'].value=='ANNAS OZOLAS'
    assert window.project.fields['preparer_role_genitive'].value=='direktores'
    assert window.project.fields['responsible'].value=='Anna Ozola; 111; anna@example.lv'
    window.editors['net'].setPlainText('500');window.choose_category(2)
    assert window.project.fields['category'].value=='2'
    window.dirty=False;window.close()


def test_partial_ai_rejections_remain_separate_and_persist(tmp_path,monkeypatch):
    from iepirkumi.importer import Chunk
    from iepirkumi.storage import save_project,load_project
    from iepirkumi.pipeline import import_chunks
    app=QApplication.instance() or QApplication([])
    monkeypatch.setenv('IEPIRKUMI_PROFILE',str(tmp_path/'absent.json'))
    w=Window(Store(tmp_path/'db'))
    monkeypatch.setattr(w,'show_ai_rejections',lambda:None)
    rejected={'field':'bank','value':'Invented','quote':'Invented','source':'offer.pdf','location':'lpp. 2','reason':'Nav avotā'}
    w.ai_finished([('gross','1397.91',Chunk('offer.pdf','lpp. 2','1 397,91','MI; obligāti pārbaudīt'))],
                  {'input_tokens':100,'output_tokens':20,'validation':{'accepted':1,'rejected':[rejected]}})
    assert w.project.fields['gross'].value=='1397.91' and not w.project.fields['gross'].confirmed
    assert not w.project.fields['bank'].value and not w.project.imports
    assert w.project.ai_rejections==[rejected]
    save_project(w.project,tmp_path/'p.json');p=load_project(tmp_path/'p.json')
    import_chunks(p,[])
    assert p.ai_rejections==[rejected] and not p.fields['bank'].value
    w.dirty=False;w.close()
