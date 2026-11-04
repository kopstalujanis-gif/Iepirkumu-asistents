"""PyMuPDF uses its built-in OCR engine; only trained language data is needed."""
from pathlib import Path
import os
import sys


def tessdata_dir():
    candidates = []
    if os.environ.get('TESSDATA_PREFIX'):
        candidates.append(Path(os.environ['TESSDATA_PREFIX']))
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys._MEIPASS) / 'tessdata')
    candidates.append(Path(__file__).resolve().parent.parent / 'assets' / 'tessdata')
    for directory in candidates:
        if all((directory / f'{lang}.traineddata').is_file() for lang in ('lav', 'eng')):
            return str(directory)
    return None


def needs_ocr(page, text):
    broken = text.count('\ufffd') > max(2, len(text) // 40)
    # An image-only page may still contain a digital page number/header.
    large_image = any(pymupdf_rect_area(i['bbox']) > page.rect.get_area() * .35
                      for i in page.get_image_info())
    return len(text.strip()) < 30 or broken or (large_image and len(text.strip()) < 200)


def pymupdf_rect_area(bbox):
    return max(0, bbox[2]-bbox[0]) * max(0, bbox[3]-bbox[1])


def recognize(page):
    directory = tessdata_dir()
    if directory is None:
        raise RuntimeError('Trūkst lav/eng OCR valodu datu; atkārtoti izpakojiet visu programmas arhīvu.')
    # Bound rendering memory for unusually large page dimensions.
    dpi = min(250, max(72, int(250 * min(1, 2000 / max(page.rect.width, page.rect.height)))))
    tp = page.get_textpage_ocr(language='lav+eng', dpi=dpi, full=True, tessdata=directory)
    return page.get_text(textpage=tp, sort=True)
