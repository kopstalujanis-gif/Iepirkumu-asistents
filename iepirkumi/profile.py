"""Optional personal defaults, stored outside Git and outside reusable form templates."""
import json
import os
import sys
from pathlib import Path


def read_profile():
    if os.environ.get('IEPIRKUMI_PROFILE'):
        path=Path(os.environ['IEPIRKUMI_PROFILE'])
    elif getattr(sys,'frozen',False):
        path=Path(sys.executable).parent/'IepirkumuAsistents.profile.json'
    else:
        path=Path(__file__).resolve().parent.parent/'local'/'defaults.json'
    if not path.is_file():return {}
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data,dict) else {}
    except (ValueError,OSError):return {}


def seed_store(store):
    profile=read_profile();employee=profile.get('employee')
    if not isinstance(employee,dict):return
    allowed={'first_name','last_name','position','phone','email','header_name','header_role','responsible_text'}
    employee={k:v for k,v in employee.items() if k in allowed and isinstance(v,str)}
    if not employee.get('first_name') or not employee.get('last_name'):return
    records=store.records('employee')
    matching=next((i for i,r in records if r.get('first_name')==employee['first_name'] and r.get('last_name')==employee['last_name']),None)
    if matching is None:matching=store.save_record('employee',employee)
    for key in ('preparer','responsible'):
        if not store.setting(key):store.set_setting(key,matching)
