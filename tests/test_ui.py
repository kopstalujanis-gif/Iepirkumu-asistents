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
