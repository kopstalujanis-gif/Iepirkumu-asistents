"""Application entry point, including a noninteractive packaged-runtime check."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


def smoke_test():
    # Only temporary data: never open or change the user's normal registry.
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    from docx import Document
    from .models import Procurement, Field
    from .storage import Store, save_project, load_project
    from .word import generate, default_template
    from .ui import Window
    from .importer import read_file
    import pymupdf
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix='iepirkumi-smoke-') as folder:
        root = Path(folder)
        if not default_template().is_file():
            raise RuntimeError('Komplektā nav oficiālās DOCX veidlapas.')
        project = Procurement()
        project.fields['subject'] = Field('Palaišanas pārbaude', confirmed=True)
        save_project(project, root / 'project.json')
        restored = load_project(root / 'project.json')
        generate(restored, root / 'document.docx')
        document = Document(root / 'document.docx')
        if len(document.tables) != 4 or 'Palaišanas pārbaude' not in document.tables[3].cell(0,5).text:
            raise RuntimeError('Komplektētā lietotne neizveidoja sagaidīto DOCX.')
        sample=pymupdf.open();page=sample.new_page(width=500,height=180)
        page.insert_text((25,75),'Invoice 12345',fontsize=26)
        (root/'scan.png').write_bytes(page.get_pixmap(matrix=pymupdf.Matrix(2,2)).tobytes('png'))
        chunks,warnings=read_file(root/'scan.png',ocr=True)
        if not chunks or '12345' not in chunks[0].text:
            raise RuntimeError('Komplektētās lietotnes OCR lav+eng pārbaude neizdevās.')
        sample.close()
        window = Window(Store(root / 'registry.sqlite3'))
        try:
            window.show()
            app.processEvents()
            if window.tabs.count() != 4:
                raise RuntimeError('Neizdevās izveidot lietotnes sadaļas.')
        finally:
            window.dirty = False
            window.close()
    return {'status': 'passed', 'platform': sys.platform,
            'frozen': bool(getattr(sys, 'frozen', False)),
            'checks': ['bundled_template', 'project_roundtrip', 'docx_export', 'sqlite_registry', 'qt_window', 'ocr_lav_eng']}


def main():
    parser = argparse.ArgumentParser(description='Iepirkumu asistents')
    parser.add_argument('--smoke-test', metavar='REPORT_JSON', type=Path,
                        help='Pārbaudīt palaišanu un rakstīt JSON rezultātu norādītajā failā.')
    args = parser.parse_args()
    if args.smoke_test is not None:
        try:
            result = smoke_test()
            code = 0
        except Exception as exc:
            result = {'status': 'failed', 'error': str(exc), 'type': type(exc).__name__}
            code = 1
        args.smoke_test.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return code
    from .ui import main as run_ui
    run_ui()
    return 0
