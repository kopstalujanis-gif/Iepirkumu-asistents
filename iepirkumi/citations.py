"""Conservative citation matching; never fuzzy-match words, dates or amounts."""
import re
import unicodedata


def normalized(text, *, dehyphenate=False):
    text=unicodedata.normalize('NFKC',text).replace('\u00ad','')
    text=text.translate(str.maketrans({'“':'"','”':'"','„':'"','‘':"'",'’':"'",'–':'-','—':'-','−':'-'}))
    # Join only alphabetic words broken at a printed line ending, never numeric ranges.
    join=r'\1\2' if dehyphenate else r'\1-\2'
    text=re.sub(r'([^\W\d_])-\s*\n\s*([^\W\d_])',join,text)
    return ' '.join(text.split()).casefold()


def locate(quote,source,sources):
    q=normalized(quote)
    def contains(c):
        return bool(q) and (q in normalized(c.text) or q in normalized(c.text,dehyphenate=True))
    if contains(source):return source
    # Correct a page/paragraph attribution only inside the SAME selected file.
    matches=[c for c in sources.values() if c.source==source.source and contains(c)]
    unique={(c.source,c.location,c.text):c for c in matches}
    return next(iter(unique.values())) if len(unique)==1 else None
