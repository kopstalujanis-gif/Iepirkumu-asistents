# Oficiālās 2026. gada veidlapas lauku kartējums

Avots: lietotāja iesniegtais “Pielikums_3_paraugs_2026 gpt 3.doc”, Ādažu novada pašvaldības 29.01.2026. noteikumu Nr. 2 3. pielikums. Autoritatīvā ir iesniegtā veidlapa; atbilstība ārēji publicētai versijai nav neatkarīgi pārbaudīta. Oriģināls glabāts `templates/oficiala_2026.doc`, LibreOffice 25.2.3 konvertētā kopija — `templates/oficiala_2026.docx`. DOCX netiek veidots no tukša dokumenta.

Tabulu un rindu indeksi zemāk ir no nulles. Apvienotās šūnas saglabātas. Nekartētas struktūras aizpildīšana tiek apturēta ar kļūdu.

| Veidlapas vieta | Datu lauks | Izcelsme / noteikums |
|---|---|---|
| Rindkopas 4–5 “no”, amats | `preparer` | Neatkarīga darbinieka izvēle; 1. rinda vārds, uzvārds, 2. rinda amats |
| Rindkopa 7 | `subject` | Īss cilvēka pārbaudīts līguma priekšmets; papildus tabula 3, rinda 0 |
| Rindkopa 8 | `necessity` | Nepieciešamības pamatojums, manuāli |
| Rindkopa 9 | `offplan` | Neiekļaušanas plānā iemesls, ja attiecināms, manuāli |
| Tabula 0, šūna 0,1 | `category` / `net` | Kategorijas burtiski no veidlapas; skatīt robežgadījumus zemāk |
| Tabula 1, rinda 0 | `published` | Publicēšanas datums, protokola “Publicēts”; nav protokola izveides datums |
| Tabula 1, rinda 2 | `supplier_name`, `registration` | Lēmumā izvēlētais piegādātājs un tā protokola piedāvājuma bloks |
| Tabula 1, rinda 3 | `award_reason` | Komersanta izvēles pamatojums, manuāli |
| Tabula 2, rinda 0 | `exception_supplier` | Izņēmuma sadaļai, tikai manuāli, neveic pieņēmumu par piemērojamību |
| Tabula 2, rinda 1 | `exception_reason` | Argumentēts izņēmuma pamatojums, tikai manuāli |
| Tabula 3, rindas 1–2, apvienotā pēdējā šūna | Izpildītāja rekvizīti | Nosaukums, reģ. Nr., adrese, pārstāvis, amats, pārstāvības pamats, banka, IBAN, SWIFT, e-pasts, tālrunis, kontaktpersona; katrs atsevišķā rindkopā; visa sadaļa 10 pt Times New Roman |
| Tabula 3, rinda 3 | `net` | EUR bez PVN |
| Tabula 3, rinda 4 | Aprēķins | `gross - net`, tikai tad, ja abas summas ir ievadītas; bez pieņēmuma par PVN likmi |
| Tabula 3, rinda 5 | `gross` | Kopā EUR ar PVN |
| Tabula 3, rindas 6–7 | `advance`, `advance_days` | Avanss, %, termiņš; “0” netiek izdomāts |
| Tabula 3, rinda 8 | `payment` | Piegādātāja norēķinu nosacījumi, lietotājam jāpārbauda kalendāra dienu interpretācija |
| Tabula 3, rinda 9 | `budget` | EKK, manuāli |
| Tabula 3, rinda 11 | `deadline` | Vienreizējs datums / termiņš; atzīmē attiecīgo rūtiņu |
| Tabula 3, rinda 12 | `recurring` | Regulāri termiņi, manuāli; atzīmē attiecīgo rūtiņu |
| Tabula 3, rinda 13 | `delivery_place` | Izpildes vietas adrese; abu avotu pierakstu atšķirības uzrāda pārbaudei |
| Tabula 3, rinda 14 | `electronic` | “Jā” / “Nē”, atzīmē oriģinālās izvēles rūtiņas |
| Tabula 3, rinda 15 | `municipal_iban` | Pašvaldības projekta konts, ja attiecināms, manuāli |
| Tabula 3, rinda 16 | `responsible` | Atsevišķa izvēle: amats, vārds, uzvārds, tālrunis, e-pasts |
| Rindkopas 15–24 | Oriģinālais teksts | Apliecinājumi un DVS datuma noteikums netiek pārveidoti |

`institution`, `procurement_id`, `date`, `attachments`, `notes` ir projektā saglabājamas darba piezīmes. Veidlapā nav atsevišķu šādu lauku, tādēļ tos patvaļīgi nepievieno juridiskajam tekstam. Veidlapā jau ir norāde par nepieciešamo DVS pielikumu pievienošanu. Programma neapstiprina, ka DVS pielikumi faktiski iesniegti.

## Robežgadījumi

Veidlapas teksts: “līdz 500”, “500-5999”, “virs 6000”. Lietotājs apstiprināja manuālu izvēli ar brīdinājumu neskaidrajos gadījumos: precīzi 500 EUR un (5999; 6000] EUR. Pārējos gadījumos `<500` → 1, `500<summa<=5999` → 2, `>6000` → 3. Trešajai kategorijai saglabājas arī veidlapas nosacījums par 28.1.–28.2. apakšpunktu; to cilvēks izvērtē pats. Lietotāja ievadīta cita kategorija netiek klusējot pārrakstīta.

## Avoti un šaubas

Automātisks lauks satur failu, lappusi vai rindas adresi, teksta fragmentu, atpazīšanas statusu un kandidātvērtību. “Pārbaudīts” vienmēr ir cilvēka darbība. Atšķirīgas kandidātvērtības rada neatbilstību un automātiski neaizpilda lauku. Cilvēka labojums saglabājas, bet jauna avota pievienošana noņem pārbaudes atzīmi. Naudas summu punkts/komats un divu decimāldaļu pieraksts tiek normalizēts. Nosaukuma “SIA DM PREMIUM” / “DM PREMIUM SIA” kārtība netiek uzskatīta par citu piegādātāju, ja tas ir sasaistīts ar vienu reģistrācijas numuru.

Trūkstošs lauks atstāj veidlapas vietturi; rekvizītu sadalītajā šūnā — oriģinālo “…” katram nezināmam rekvizītam. Tikai run highlight `yellow`, bez `w:shd`. Neapstiprinātas vērtības arī iezīmētas. Apstiprināšana nenoslēpj sākotnējos kandidātus. Tukšs lauks saglabā iezīmējumu arī pēc pārbaudes atzīmes.

Pārējais oriģinālais teksts, tabulu režģi, apvienojumi un piemales saglabāti. No oriģināla izņemts tikai dekoratīvais ✍ simbols un noslēdzošās tukšās rindkopas, lai nerastos tukša pēdējā lapa; izvēles rūtiņas saglabātas. Lappušu skaitu nenodrošina ar fonta samazināšanu.
