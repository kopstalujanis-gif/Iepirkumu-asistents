from decimal import Decimal
from .models import LABELS, money


def category(value):
    """Literal template ranges; ambiguous endpoints deliberately return None."""
    n = money(value)
    if n < 500:
        return '1'
    if 500 < n <= 5999:
        return '2'
    if n > 6000:
        return '3'
    return None


def validate(p):
    warnings = []
    for key, f in p.fields.items():
        if f.conflict and not f.confirmed:
            warnings.append(f'{LABELS[key]}: avotos ir dažādas vērtības; izvēlieties un apstipriniet.')
    for key in ['request_subject','preparer_genitive','preparer_role_genitive','subject', 'net', 'supplier_name', 'registration', 'preparer', 'responsible', 'necessity', 'budget']:
        if not p.fields[key].value:
            warnings.append(f'{LABELS[key]}: nav ievadīts.')
    net = p.fields['net'].value
    if net:
        try:
            cat = category(net)
            chosen = p.fields['category'].value
            if cat is None:
                warnings.append('Vērtības kategorijas robežgadījums: veidlapas teksts nav viennozīmīgs. Nepieciešama manuāla izvēle un pārbaude.')
            elif chosen and chosen != cat:
                warnings.append('Manuālā vērtības kategorija neatbilst summai. Pārbaudiet veidlapas kategorijas.')
            gross = p.fields['gross'].value
            if gross and money(gross) < money(net):
                warnings.append('Summa ar PVN ir mazāka nekā summa bez PVN.')
        except ValueError as e:
            warnings.append(str(e))
    if p.fields['category'].value not in ('', '1', '2', '3'):
        warnings.append('Kategorijā atļauts 1, 2 vai 3.')
    if p.fields['electronic'].value.lower() not in ('', 'jā', 'nē'):
        warnings.append('Elektroniskā parakstīšana: ievadiet Jā vai Nē.')
    if p.fields['subject'].value and len(p.fields['subject'].value) > 120:
        warnings.append('Līguma priekšmets ir garš; pārformulējiet īsi.')
    for key, f in p.fields.items():
        if f.value and not f.confirmed:
            warnings.append(f'{LABELS[key]}: vērtība nav apstiprināta; dokumentā būs iezīmēta.')
    warnings.extend(p.warnings)
    return list(dict.fromkeys(warnings))
