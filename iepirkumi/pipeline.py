"""Re-evaluate saved source text in dependency order, irrespective of upload order."""
from dataclasses import fields as dataclass_fields
from .importer import Chunk, extract_protocol, extract_offers


def import_chunks(project, chunks, warnings=()):
    before = sum(bool(f.value) for f in project.fields.values())
    existing = {(c['source'], c['location'], c['text']) for c in project.imports}
    for c in chunks:
        key = (c.source, c.location, c.text)
        if key not in existing:
            project.imports.append(vars(c).copy()); existing.add(key)
    project.warnings = list(dict.fromkeys(project.warnings + list(warnings)))
    all_chunks = [Chunk(**{f.name: c.get(f.name, f.default) for f in dataclass_fields(Chunk)}) for c in project.imports]
    # Protocol rules require an explicit decision; offers alone cannot select a winner.
    # These extractors historically also stored chunks. Keep one canonical source list.
    canonical = project.imports.copy()
    extract_protocol(project, all_chunks)
    extract_offers(project, all_chunks)
    project.imports = canonical
    filled = sum(bool(f.value) for f in project.fields.values())
    return {'fragments': len(chunks), 'characters': sum(len(c.text) for c in chunks),
            'filled': filled, 'new_fields': max(0, filled-before),
            'conflicts': sum(f.conflict for f in project.fields.values()),
            'warnings': len(warnings)}
