"""Fill the converted original form without rebuilding its tables or sections."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from copy import deepcopy
import sys
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from .models import Field, LABELS, money
from .validation import category


def default_template():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    return root / 'templates' / 'oficiala_2026.docx'


def font(run, size=None):
    run.font.name = 'Times New Roman'
    props = run._r.get_or_add_rPr()
    fonts = props.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts'); props.insert(0, fonts)
    for attr in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        fonts.set(qn('w:' + attr), 'Times New Roman')
    for attr in ('asciiTheme', 'hAnsiTheme', 'eastAsiaTheme', 'cstheme'):
        fonts.attrib.pop(qn('w:' + attr), None)
    if size:
        run.font.size = Pt(size)


def mark(run, uncertain):
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW if uncertain else None


def replace(p, token, f, size=None):
    """Replace only a known placeholder; keep paragraph and surrounding run styles."""
    full = p.text
    start = full.find(token)
    if start < 0:
        raise ValueError(f'Veidlapā nav paredzētā viettura: {token}')
    end = start + len(token)
    replacement = f.value if f.value else token
    offset, inserted = 0, False
    for run in list(p.runs):
        original = run.text
        a, b = offset, offset + len(original)
        offset = b
        if b <= start or a >= end:
            continue
        before = original[:max(0, start-a)]
        after = original[max(0, end-a):] if b > end else ''
        # Keep original run for prefix, add value and suffix in separate runs.
        run.text = before
        anchor = run._r
        if not inserted:
            new = OxmlElement('w:r')
            if run._r.rPr is not None:
                new.append(deepcopy(run._r.rPr))
            anchor.addnext(new)
            from docx.text.run import Run
            value_run = Run(new, p)
            value_run.text = replacement
            font(value_run, size)
            mark(value_run, not f.value or not f.confirmed)
            anchor = new
            inserted = True
        if after:
            new = deepcopy(run._r)
            anchor.addnext(new)
            from docx.text.run import Run
            Run(new, p).text = after


def put(cell, f, size=None):
    p = cell.paragraphs[0]
    placeholder = p.text or '…'
    replace(p, placeholder, f, size)


def _joined(p, keys):
    values = [p.fields[k] for k in keys]
    if not all(f.value for f in values):
        return Field()
    return Field(', '.join(f.value for f in values), confirmed=all(f.confirmed for f in values))


def _check(p, index, confirmed=True):
    text = p.text
    count = 0
    for r in p.runs:
        chars = []
        for c in r.text:
            if c == '☐':
                count += 1
                chars.append('☒' if count == index else c)
            else:
                chars.append(c)
        r.text = ''.join(chars)
        if not confirmed:
            mark(r, True)


def generate(p, output, template=None):
    template = Path(template or default_template())
    d = Document(template)
    # Reject different layouts rather than silently put values in wrong cells.
    if len(d.tables) != 4 or len(d.tables[3].rows) != 17 or len(d.paragraphs) < 25:
        raise ValueError('Neatpazīta veidlapas struktūra. Nepieciešams pārbaudīt lauku kartējumu.')
    if '[vārds, uzvārds]' not in d.paragraphs[4].text or 'LĪGUMA PRIEKŠMETS' not in d.tables[3].cell(0,0).text:
        raise ValueError('Veidlapa neatbilst 2026. gada kartējumam.')
    f = p.fields
    preparer = f['preparer']
    lines = preparer.value.split('\n')
    replace(d.paragraphs[4], '[vārds, uzvārds]', Field(lines[0] if preparer.value else '', confirmed=preparer.confirmed))
    replace(d.paragraphs[5], '[amats]', Field(lines[1] if len(lines)>1 else '', confirmed=preparer.confirmed))
    replace(d.paragraphs[7], '[norādīt līguma priekšmeta nosaukumu]', f['subject'])
    replace(d.paragraphs[8], '[izskaidrot, kāpēc darījums nepieciešams]', f['necessity'])
    replace(d.paragraphs[9], '[izklāstīt iemeslus]', f['offplan'])
    replace(d.tables[1].cell(0,0).paragraphs[0], '___.___.20____.', f['published'])
    put(d.tables[1].cell(2,1), _joined(p, ['supplier_name', 'registration']))
    put(d.tables[1].cell(3,1), f['award_reason'])
    put(d.tables[2].cell(0,1), f['exception_supplier'])
    put(d.tables[2].cell(1,1), f['exception_reason'])
    t = d.tables[3]
    for row, key in {0:'subject',3:'net',5:'gross',6:'advance',7:'advance_days',8:'payment',9:'budget',11:'deadline',12:'recurring',13:'delivery_place',15:'municipal_iban',16:'responsible'}.items():
        value = f[key]
        if key in ('net','gross') and value.value:
            value = Field(f'{money(value.value):.2f}'.replace('.',','), confirmed=value.confirmed)
        put(t.cell(row,5), value)
    if f['net'].value and f['gross'].value:
        vat = money(f['gross'].value) - money(f['net'].value)
        if vat < 0:
            raise ValueError('Summa ar PVN nedrīkst būt mazāka par summu bez PVN.')
        put(t.cell(4,5), Field(str(vat.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)).replace('.',','),
                              confirmed=f['net'].confirmed and f['gross'].confirmed))
    else:
        put(t.cell(4,5), Field())
    supplier = t.cell(1,5)  # vertically merged through row 2 in the original
    base = supplier.paragraphs[0]
    base.clear()
    supplier_keys = ['supplier_name','registration','address','representative','representative_role','authority','bank','iban','swift','email','phone','contact']
    for i, key in enumerate(supplier_keys):
        paragraph = base if i == 0 else supplier.add_paragraph()
        label = paragraph.add_run(LABELS[key] + ': '); font(label, 10)
        r = paragraph.add_run(f[key].value or '…'); font(r, 10)
        mark(r, not f[key].value or not f[key].confirmed)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
    chosen = f['category'].value
    if chosen not in ('','1','2','3'):
        raise ValueError('Nederīga vērtības kategorija.')
    if not chosen and f['net'].value:
        chosen = category(f['net'].value)
    for cp in d.tables[0].cell(0,1).paragraphs:
        if '☐' in cp.text:
            expected = ('1' if 'līdz 500' in cp.text else '2' if '500-5999' in cp.text else '3')
            if chosen == expected:
                _check(cp, 1, f['category'].confirmed if f['category'].value else f['net'].confirmed)
            elif not chosen:
                for run in cp.runs: mark(run, True)
    if f['deadline'].value:
        _check(t.cell(11,0).paragraphs[0], 1, f['deadline'].confirmed)
    if f['recurring'].value:
        _check(t.cell(12,0).paragraphs[0], 1, f['recurring'].confirmed)
    electronic = f['electronic'].value.lower()
    if electronic in ('jā','nē'):
        _check(t.cell(14,5).paragraphs[0], 1 if electronic == 'jā' else 2, f['electronic'].confirmed)
    else:
        for r in t.cell(14,5).paragraphs[0].runs: mark(r, True)
    # All text, including original headings, headers, footers and styles uses TNR.
    from docx.text.run import Run
    roots = [d.element] + [rel.target_part.element for rel in d.part.rels.values()
                           if rel.reltype.endswith(('/header', '/footer'))]
    for root in roots:
        for node in root.xpath('.//w:r'):
            r = Run(node, d)
            if '✍' in r.text: r.text = r.text.replace('✍', '')
            font(r)
    for style in d.styles:
        if hasattr(style, 'font'):
            style.font.name = 'Times New Roman'
    # Label cell is part of the supplier section, too.
    for row in [1,2]:
        for cell in t.rows[row].cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs: font(run, 10)
    # Remove only trailing empty layout paragraphs, which can create a blank last page.
    while d.paragraphs and not d.paragraphs[-1].text.strip():
        last = d.paragraphs[-1]._p
        if last.xpath('.//w:sectPr | .//w:drawing | .//w:br'): break
        last.getparent().remove(last)
    d.save(output)
    return Path(output)
