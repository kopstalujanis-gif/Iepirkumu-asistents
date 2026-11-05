from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation
import json


@dataclass
class Evidence:
    value: str
    source: str
    location: str
    excerpt: str
    confidence: str = "jāpārbauda"


@dataclass
class Field:
    value: str = ""
    candidates: list[Evidence] = field(default_factory=list)
    edited: bool = False
    confirmed: bool = False

    def add(self, evidence):
        if evidence in self.candidates:
            return
        self.candidates.append(evidence)
        if len({normalize(x.value) for x in self.candidates}) == 1 and not self.edited:
            self.value = evidence.value
        elif self.conflict and not self.edited:
            self.value = ""
        self.confirmed = False

    @property
    def conflict(self):
        return len({normalize(x.value) for x in self.candidates}) > 1


def normalize(value):
    return " ".join(value.lower().split()).strip(". ")


def money(value):
    text = value.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        number = Decimal(text)
        if not number.is_finite() or number < 0:
            raise ValueError("Summai jābūt nenegatīvam skaitlim.")
        if number.as_tuple().exponent < -2:
            raise ValueError("Summai atļautas ne vairāk kā divas zīmes aiz komata.")
        return number
    except InvalidOperation as exc:
        raise ValueError("Nederīga naudas summa.") from exc


# Field labels are also used by the GUI. Template locations live in word.py.
LABELS = {
    "necessity": "Darījuma nepieciešamības pamatojums",
    "offplan": "Iepirkuma plānā neiekļaušanas iemesls (ja attiecināms)",
    "published": "Publicēšanas datums portālā Iepirkumi.lv",
    "award_reason": "Komersanta izvēles pamatojums",
    "exception_supplier": "Izņēmumā izvēlētais komersants un reģ. Nr. (ja attiecināms)",
    "exception_reason": "Izņēmuma pamatojums (ja attiecināms)",
    "advance": "Avansa summa un %", "advance_days": "Avansa samaksas termiņš",
    "budget": "Budžeta finansējums (EKK)", "recurring": "Regulāras izpildes termiņi",
    "electronic": "Elektroniskā parakstīšana (Jā / Nē)",
    "municipal_iban": "Pašvaldības projekta bankas konts (ja attiecināms)",
    "category": "Vērtības kategorija (1 / 2 / 3; robežgadījumos manuāli)",
    "institution": "Iestāde / struktūrvienība (darba piezīme)", "subject": "Līguma priekšmets",
    "request_subject": "Formulējums iesnieguma teikumā (par …)",
    "preparer_genitive": "Sagatavotājs ģenitīvā (no …)",
    "preparer_role_genitive": "Sagatavotāja amats ģenitīvā",
    "payment_days": "Apmaksas termiņš kalendāra dienās",
    "procurement_id": "Iepirkuma identifikators", "date": "DVS kartiņas datums (darba piezīme)",
    "net": "Summa bez PVN (EUR)", "gross": "Summa ar PVN (EUR)",
    "deadline": "Piegādes / izpildes termiņš", "delivery_place": "Piegādes vieta",
    "payment": "Norēķinu kārtība", "supplier_name": "Izpildītāja nosaukums",
    "registration": "Reģistrācijas numurs", "vat_number": "PVN reģistrācijas numurs", "address": "Juridiskā adrese",
    "bank": "Banka", "iban": "IBAN", "swift": "SWIFT",
    "phone": "Izpildītāja tālrunis", "email": "Izpildītāja e-pasts",
    "representative": "Paraksttiesīgā persona / amats", "representative_role": "Paraksttiesīgās personas amats", "authority": "Pārstāvības pamatojums",
    "contact": "Izpildītāja kontaktpersona", "notes": "Papildu nosacījumi (darba piezīme)",
    "attachments": "Pielikumi (darba piezīme)", "preparer": "Iesnieguma sagatavotājs",
    "responsible": "Par iepirkumu atbildīgā persona",
}


_PRIORITY = ['subject', 'procurement_id', 'preparer', 'responsible', 'supplier_name', 'registration',
             'net', 'gross', 'deadline', 'delivery_place', 'payment', 'necessity', 'published', 'award_reason']
LABELS = {k: LABELS[k] for k in _PRIORITY + [k for k in LABELS if k not in _PRIORITY]}


@dataclass
class Procurement:
    fields: dict[str, Field] = field(default_factory=lambda: {k: Field() for k in LABELS})
    imports: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ai_rejections: list[dict] = field(default_factory=list)

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text):
        obj = json.loads(text)
        p = cls()
        for key, data in obj.get("fields", {}).items():
            if key in p.fields:
                p.fields[key] = Field(data.get("value", ""), [Evidence(**e) for e in data.get("candidates", [])],
                                      data.get("edited", False), data.get("confirmed", False))
        p.imports = obj.get("imports", [])
        p.warnings = obj.get("warnings", [])
        p.ai_rejections = obj.get("ai_rejections", [])
        return p

# Keep legacy fields in saved projects for compatibility, but remove the requested UI sections.
HIDDEN_FIELDS = {'category','institution','date','notes','attachments'}
VISIBLE_LABELS = {k:v for k,v in LABELS.items() if k not in HIDDEN_FIELDS}
