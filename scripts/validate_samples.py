"""Local-only integration check; never copy private samples into Git."""
import argparse
from pathlib import Path
from iepirkumi.models import Procurement, Field
from iepirkumi.importer import read_file, extract_protocol, extract_offers
from iepirkumi.word import generate
from iepirkumi.storage import save_project

parser = argparse.ArgumentParser()
parser.add_argument('samples',type=Path)
parser.add_argument('--output',type=Path,default=Path('local'))
args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
p=Procurement()
chunks,warnings=read_file(next(args.samples.rglob('Folijas_segas_protokols.pdf')))
extract_protocol(p,chunks); p.warnings+=warnings
chunks,warnings=read_file(next(args.samples.rglob('Folijas_segas_piedavajumi.zip')))
extract_offers(p,chunks); p.warnings+=warnings
# User's specification explicitly supplies this short formulation; it remains unconfirmed.
p.fields['subject']=Field('Izotermisko folijas segu iegāde',p.fields['subject'].candidates,True,False)
assert p.fields['net'].value=='465.50'
assert p.fields['gross'].value=='563.26'
assert p.fields['supplier_name'].value=='DM PREMIUM SIA'
assert p.fields['deadline'].value=='15.12.2026'
assert p.fields['representative_role'].value=='Valdes locekle'
generate(p,args.output/'Folijas_segas_parskatisanai.docx')
save_project(p,args.output/'Folijas_segas.json')
print('Izveidots DOCX pārskatīšanai un rediģējams JSON projekts. Personas un nezināmie lauki nav izdomāti.')
print('Neatbilstīgie lauki:',', '.join(k for k,f in p.fields.items() if f.conflict) or 'nav')
