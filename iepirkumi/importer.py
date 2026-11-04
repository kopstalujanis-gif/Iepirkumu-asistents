"""Bounded local document reading. Files and archive members are never executed."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from io import BytesIO
from zipfile import ZipFile, BadZipFile
import re
import pymupdf
from docx import Document
from openpyxl import load_workbook
from .models import Evidence, money

MAX_BYTES = 40 * 1024 * 1024
MAX_TOTAL = 150 * 1024 * 1024
MAX_MEMBERS = 300


@dataclass
class Chunk:
    source: str
    location: str
    text: str
    quality: str = "teksts; jāpārbauda"


class ImportFailure(ValueError):
    pass


def read_file(path, ocr=False):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ImportFailure("Fails pārsniedz 40 MB ierobežojumu.")
    warnings, budget = [], [0, 0]
    chunks = _read(path.name, path.read_bytes(), ocr, warnings, budget, 0)
    return chunks, warnings


def _read(name, data, ocr, warnings, budget, depth):
    budget[0] += len(data)
    budget[1] += 1
    if len(data) > MAX_BYTES or budget[0] > MAX_TOTAL or budget[1] > MAX_MEMBERS:
        raise ImportFailure("Pārsniegts importa izmēra vai failu skaita ierobežojums.")
    ext = Path(name).suffix.lower()
    result = []
    if ext in (".zip", ".edoc"):
        if depth >= 3:
            raise ImportFailure("Arhīvam ir pārāk daudz ligzdošanas līmeņu.")
        with ZipFile(BytesIO(data)) as z:
            if len(z.infolist()) > MAX_MEMBERS:
                raise ImportFailure("Arhīvā ir pārāk daudz ierakstu.")
            for entry in z.infolist():
                if entry.is_dir():
                    continue
                part = PurePosixPath(entry.filename.replace('\\', '/'))
                if part.is_absolute() or '..' in part.parts or ':' in entry.filename:
                    raise ImportFailure("Arhīvā ir nedrošs faila ceļš.")
                if entry.file_size > MAX_BYTES or budget[0] + entry.file_size > MAX_TOTAL:
                    raise ImportFailure("Arhīva saturs pārsniedz atļauto izmēru.")
                if part.parts[0].lower() == 'meta-inf' or entry.filename == 'mimetype':
                    continue
                result += _read(name + '/' + entry.filename, z.read(entry), ocr, warnings, budget, depth + 1)
        if ext == '.edoc':
            warnings.append(name + ': nolasīts saturs; elektroniskais paraksts nav pārbaudīts.')
    elif ext == '.pdf':
        with pymupdf.open(stream=data, filetype='pdf') as d:
            if len(d) > 200:
                raise ImportFailure("PDF pārsniedz 200 lappuses.")
            for i, page in enumerate(d):
                text, quality = page.get_text(sort=True), 'PDF teksts; jāpārbauda'
                if len(text.strip()) < 30:
                    quality = 'maz teksta / iespējams skenējums'
                    if ocr:
                        try:
                            tp = page.get_textpage_ocr(language='lav+eng', dpi=200, full=True)
                            text, quality = page.get_text(textpage=tp), 'OCR; zema ticamība, obligāti pārbaudīt'
                        except Exception as exc:
                            warnings.append(f'{name}, lpp. {i+1}: OCR nav pieejams ({type(exc).__name__}).')
                    else:
                        warnings.append(f'{name}, lpp. {i+1}: iespējams skenējums; ieslēdziet lokālo OCR vai ievadiet manuāli.')
                result.append(Chunk(name, f'lpp. {i+1}', text, quality))
    elif ext == '.docx':
        d = Document(BytesIO(data))
        for i, p in enumerate(d.paragraphs):
            if p.text.strip():
                result.append(Chunk(name, f'rindkopa {i+1}', p.text))
        for i, table in enumerate(d.tables):
            for j, row in enumerate(table.rows):
                # Last cell is the submitted value, earlier cells may be requirements.
                cells = list(dict.fromkeys(c.text.strip() for c in row.cells))
                result.append(Chunk(name, f'tabula {i+1}, rinda {j+1}', ' | '.join(cells)))
    elif ext == '.xlsx':
        book = load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
        try:
            for sheet in book:
                for i, row in enumerate(sheet.iter_rows(values_only=True)):
                    if i >= 10000:
                        raise ImportFailure("Excel lapā vairāk nekā 10000 rindu.")
                    if any(x is not None for x in row):
                        result.append(Chunk(name, f'{sheet.title}, rinda {i+1}', ' | '.join(str(x) if x is not None else '' for x in row)))
        finally:
            book.close()
    else:
        warnings.append(name + ': formāts nav nolasīts; DOC konvertējiet uz DOCX, attēlus uz PDF.')
    return result


def add_match(p, key, value, chunk):
    value = value.strip().strip('|').strip()
    if value:
        if key in ('net', 'gross'):
            try: value = f'{money(value):.2f}'
            except ValueError: pass
        p.fields[key].add(Evidence(value, chunk.source, chunk.location, chunk.text[:1600], chunk.quality))


def extract_protocol(p, chunks):
    text = '\n'.join(c.text for c in chunks)
    winner = re.search(r'Slēgt līgumu ar\s+(.+?)[.\n]', text, re.I)
    if winner:
        selected = winner.group(1).strip()
        c = next(c for c in chunks if winner.group(0) in c.text)
        add_match(p, 'supplier_name', selected, c)
        for chunk in chunks:
            pattern = r'Nosaukums:\s*' + re.escape(selected) + r'\s+Reģ\.Nr\.:\s*(\d+).*?Piedāvājuma summa \(EUR bez PVN\):\s*([\d ,\.]+)'
            m = re.search(pattern, chunk.text, re.S | re.I)
            if m:
                add_match(p, 'registration', m[1], chunk)
                add_match(p, 'net', m[2].replace(' ', '').replace(',', '.'), chunk)
    for chunk in chunks:
        for key, pattern in {
            'procurement_id': r'Iepirkuma (?:numurs|Nr\.):\s*([^\n]+)',
            'subject': r'Iepirkuma priekšmets:\s*([^\n]+)',
            'published': r'Publicēts:\s*(\d{2}\.\d{2}\.\d{4})',
            'deadline': r'Piegādes termiņš:\s*(\d{2}\.\d{2}\.\d{4})',
            'delivery_place': r'Darba izpildes/piegādes vieta:\s*([^\n]+)',
        }.items():
            m = re.search(pattern, chunk.text, re.I)
            if m:
                add_match(p, key, m[1], chunk)
    p.imports += [vars(c) for c in chunks]


ROW_MAP = {
    'pretendenta nosaukums': 'supplier_name', 'reģistrācijas numurs': 'registration',
    'juridiskā adrese': 'address', 'tālrunis': 'phone', 'e-pasta adrese': 'email',
    'banka': 'bank', 'swift': 'swift', 'konta numurs': 'iban',
    'paraksttiesīgās personas vārds': 'representative',
    'paraksttiesīgās personas amats': 'representative_role', 'pārstāvības/pilnvaru': 'authority',
    'vai iespējama līguma elektroniska': 'electronic',
    'kontaktpersona līguma izpildei': 'contact', 'piedāvātie apmaksas': 'payment',
    'kopējā cena par': 'net', 'kopējā cena ar pvn': 'gross',
}


def extract_offers(p, chunks):
    # Compare only documents carrying the selected supplier's registration.
    # Other bidders and product sheets remain available in the source viewer.
    groups = {}
    for c in chunks:
        groups.setdefault(c.source, []).append(c)
    reg = p.fields['registration'].value
    for source, group in groups.items():
        if not reg or not re.search(r'(?<!\d)' + re.escape(reg) + r'(?!\d)', '\n'.join(c.text for c in group)):
            continue
        for c in group:
            if '|' not in c.text:
                # PDF text: accept explicit label:value pairs only.
                for line in c.text.splitlines():
                    if ':' in line:
                        label, value = line.split(':', 1)
                        for prefix, key in ROW_MAP.items():
                            if label.strip().lower().startswith(prefix) and key != 'supplier_name':
                                add_match(p, key, value, c)
                                break
                        if 'piegādes termiņš' in label.lower():
                            match = re.search(r'\d{2}\.\d{2}\.\d{4}', value)
                            if match: add_match(p, 'deadline', match[0], c)
                continue
            cells = c.text.split('|')
            label, value = cells[0].strip().lower(), cells[-1].strip()
            if re.fullmatch(r'\d+(?:\.\d+)*\.?', label) and len(cells)>1:
                label = cells[1].strip().lower()
            for prefix, key in ROW_MAP.items():
                if label.startswith(prefix):
                    if key == 'supplier_name':
                        # Legal-name order differs; registration establishes identity.
                        if p.fields[key].value:
                            continue
                    if key in ('net', 'gross'):
                        value = value.replace(',', '.')
                    add_match(p, key, value, c)
                    break
            if 'piegādes termiņš' in label:
                match = re.search(r'\d{2}\.\d{2}\.\d{4}', value)
                if match:
                    add_match(p, 'deadline', match[0], c)
            if 'piegādes adrese' in label:
                add_match(p, 'delivery_place', value.split('–')[-1].strip().rstrip('.'), c)
            if 'apmaksas nosacījumi' in label and not label.startswith('piedāvātie'):
                # The dedicated requisites row, when present, is more precise.
                if not any(x.text.lower().startswith('piedāvātie apmaksas') for x in group):
                    add_match(p, 'payment', value.split('–')[-1].strip(), c)
    p.imports += [vars(c) for c in chunks]
