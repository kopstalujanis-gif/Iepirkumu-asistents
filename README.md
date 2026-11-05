# Iepirkumu asistents

Versija 0.2. Lokāla Python/PySide6 darbvirsmas lietotne Ādažu vidusskolas iepirkumu iesniegumu sagatavošanai pēc iesniegtās 2026. gada oficiālās veidlapas. Izveido rediģējamu DOCX, saglabājot oriģināla tabulas, piemales un juridiskos formulējumus. Gala apstiprinājumu veic cilvēks.

## Windows palaišana no pirmkoda

Nepieciešams Windows 10/11 un Python 3.12 vai jaunāks ar darbvirsmas saskarnes atbalstu. Word dokumentu pārskatīšanai izmantojiet Microsoft Word vai LibreOffice.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m iepirkumi
```

Atkarības ir piesaistītas konkrētām versijām `pyproject.toml`. Qt nodrošina `PySide6-Essentials`; WebEngine un ārējie API netiek izmantoti.

## Lietošana

1. Reģistru sadaļā pievienojiet darbiniekus. Sagatavotāju un par līguma izpildi atbildīgo izvēlieties neatkarīgi. Pēdējās izvēles saglabājas; katrā iepirkumā tās var mainīt.
2. Importējiet protokolu un piedāvājumus vai ZIP jebkurā secībā. Pēc katra importa avoti tiek pāranalizēti, vispirms nosakot uzvarētāju no protokola. Teksti un kvalitātes statuss redzami “Avoti”. Piedāvājumu noteikumi salīdzina izvēlētā piegādātāja dokumentus pēc reģistrācijas numura; citu pretendentu summas netiek sajauktas ar uzvarētāja summu.
3. Katru lauku var ievadīt un labot manuāli. Atlasot lauka rindu, redzami kandidāti un avotu fragmenti. Izvēlieties kandidātu vai ierakstiet labojumu; atzīmējiet “Pārbaudīts” tikai pēc salīdzināšanas ar avotu. Jauni avoti atceļ iepriekšējo pārbaudes atzīmi.
4. Ierakstiet īsu līguma priekšmetu, pamatojumu un EKK. Sagatavotāja manuālajā laukā 1. rinda ir vārds un uzvārds, 2. rinda — amats. Atbildīgās personas laukā iekļaujiet arī tālruni un e-pastu.
5. Kategorija tiek aprēķināta automātiski; robežgadījumā virs tabulas parādās manuāla izvēle. Precīzi 500 EUR un (5999;6000] EUR rada brīdinājumu. Veidlapas teksts netiek pārveidots. Citas juridiskās piemērojamības prasības pārbauda lietotājs.
6. Saglabājiet iepirkumu JSON failā un ģenerējiet DOCX. Nezināmie vietturi un neapstiprinātie dati ir dzelteni iezīmēti; pie brīdinājumiem programma piedāvā ģenerēt pārskatīšanas dokumentu. Pārbaudiet gala izkārtojumu Word un pievienojiet prasītos DVS pielikumus.

Piegādātāja izvēle kopē reģistra vērtības konkrētajā iepirkumā. Turpmākie labojumi iepirkumā nemaina pamatierakstu. Reģistra labojumi savukārt nepārraksta saglabātu iepirkumu.

## Formāti un OCR

PDF (arī skenējumi ar lokālu OCR), DOCX, XLSX, ZIP, JPG, PNG un TIFF. EDOC tiek lasīts kā konteineris; elektroniskie paraksti netiek pārbaudīti. Oriģinālus arhīvus neizpako uz diska un neizpilda. Ir izmēra, failu skaita un ligzdošanas ierobežojumi. Vecais DOC jāatver Word/LibreOffice un jāsaglabā kā DOCX. Lietotnei komplektā jau ir konvertēta oficiālā veidlapa.

OCR tagad ir ieslēgts pēc noklusējuma. `lav` un `eng` dati ir komplektā; PyMuPDF izmanto iebūvētu OCR dzini, tādēļ atsevišķs tesseract.exe nav vajadzīgs. Izpakojiet visu programmas mapi, arī `_internal/tessdata`. Tiek nolasīti skenēti PDF un JPG/JPEG/PNG/TIFF/BMP attēli. OCR joprojām var kļūdīties, īpaši fotogrāfijās un tabulās, un rezultāti vienmēr jāpārbauda. Vecais DOC formāts jākonvertē uz DOCX ar Word vai LibreOffice. EDOC satura nolasīšana nav elektroniskā paraksta pārbaude.

Automātiskā ekstrakcija atpazīst pievienotā iepirkumi.lv protokola struktūru un marķētas piedāvājumu tabulu rindas / `nosaukums: vērtība` PDF rindas. Patvaļīga dokumentu izkārtojuma pilnīga atpazīšana netiek solīta; visi importētie teksti ir pieejami manuālai pārbaudei. Pēc noklusējuma lietotne nesūta dokumentus ārpakalpojumiem. Izvēles MI režīms aprakstīts zemāk.

## Windows izpildfails un instalēšana

Windows datorā palaidiet:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Skripts izpilda testus, būvē EXE un pārbauda pašu komplektēto lietotni: Qt loga izveidi, lokālo datubāzi, projekta saglabāšanu/atvēršanu un DOCX ģenerēšanu ar komplektā iekļauto veidlapu. Tikai pēc sekmīgas pārbaudes tas veido `dist/IepirkumuAsistents-Windows.zip`. Izpakojiet **visu** mapi, nevis tikai EXE, un palaidiet `IepirkumuAsistents.exe`. Iespējams izveidot darbvirsmas saīsni. Python lietotāja datorā pēc būvēšanas vairs nav vajadzīgs. OCR valodu dati ir iekļauti komplektā; saglabājiet visu izpakoto mapi.

GitHub Actions darbplūsma `.github/workflows/windows.yml` izpilda to pašu būvēšanas skriptu. Tā saglabā portatīvo ZIP artefaktā `IepirkumuAsistents-Windows` un palaišanas rezultātu `Windows-startup-check`. Par sekmīgu Windows būvi drīkst uzskatīt tikai izpildi ar `status: passed`, `frozen: true`, `platform: win32` pārbaudes JSON failā. Šajā Linux mākoņa vidē 0.2 versijas Windows EXE un Microsoft Word pārbaude vēl jāapstiprina būvēšanas rezultātos; būvēšanas instrukcija nav gatava EXE pārbaudes apliecinājums. MSI/EXE instalētājs un koda parakstīšana šajā versijā nav realizēti.

## Izstrāde Linux / mākoņa vidē

Izmantojiet esošo checkout; katrs mākoņa uzdevums jau ir izolēts. Jauns Git worktree nav nepieciešams.

```bash
cd /workspace/Iepirkumu-asistents
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
IEPIRKUMI_DATA_DIR="$PWD/local/data" .venv/bin/python -m iepirkumi
```

Bez grafiskās darbvirsmas Qt testos lietojiet `QT_QPA_PLATFORM=offscreen`. Interaktīvai lietošanai vajadzīgs darbvirsmas displejs. Lokālajai pamatplūsmai nav nepieciešami tīkla servisi vai datubāzes serveris; izvēles MI analīzei vajag OpenAI API savienojumu. Atkarību instalēšanai vajadzīga piekļuve PyPI.

Lietotāja paraugdokumentus glabā ārpus Git. Papildu integrācijas pārbaude:

```bash
IEPIRKUMI_SAMPLES=/workspace/attachments QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_samples.py /workspace/attachments
```

Otra komanda izveido `local/Folijas_segas_parskatisanai.docx` un JSON projektu. Tas ir pārskatīšanas paraugs: darbinieki, EKK, pamatojums un citi neapstiprinātie lauki nav izdomāti. Piegādes adrešu atšķirīgais pieraksts tiek parādīts kā pārbaudāma neatbilstība.

## Dati, kopijas un dzēšana

Windows reģistri: `%LOCALAPPDATA%/IepirkumuAsistents/registri.sqlite3`. Citur: `~/.local/share/IepirkumuAsistents/`. Var norādīt citu mapi ar `IEPIRKUMI_DATA_DIR`. Dati nav šifrēti pašas lietotnes līmenī; glabājiet tos aizsargātā lietotāja kontā / diskā. JSON projekts satur arī avotu tekstus un labojumus.

Reģistru sadaļā var labot/dzēst ierakstus un saglabāt SQLite rezerves kopiju. Atjaunošanai aizveriet lietotni, saglabājiet pašreizējās DB kopiju un aizvietojiet DB ar izvēlēto kopiju. “Dzēst visus” dzēš reģistrus un pēdējās izvēles; projektu failus, DOCX, rezerves kopijas un oriģinālus dzēsiet atsevišķi failu pārvaldniekā. Dzēšana negarantē fizisku datu neatjaunojamību no diska vai ārējām kopijām.

Kļūdu žurnāls `asistents.log` ir tajā pašā datu mapē, ar ierobežotu izmēru; dokumentu saturs žurnālā netiek rakstīts. API atslēgas nedrīkst pievienot Git vai projektu JSON failiem. MI ir izvēles papildmodulis ar skaidru piekrišanu katram pieprasījumam.

Detalizēts lauku un šaubu kartējums: [docs/lauku-kartejums.md](docs/lauku-kartejums.md).

## Gatavās lietotnes pārbaude

Būvēšanas rezultātu var atkārtoti pārbaudīt arī citā Windows datorā bez Python:

```powershell
$process = Start-Process -FilePath '.\IepirkumuAsistents.exe' -ArgumentList '--smoke-test', 'palaisanas-parbaude.json' -PassThru -Wait
$process.ExitCode
Get-Content palaisanas-parbaude.json
```

Pārbaude izmanto pagaidu datus un nemaina lietotāja reģistrus. Ja EXE nevar pat startēt trūkstošu sistēmas bibliotēku dēļ, JSON var netikt izveidots; tā ir neveiksmīga pārbaude. Sekmīga automātiskā pārbaude neaizvieto gala dokumenta vizuālu pārbaudi Microsoft Word.

## Izvēles MI analīze (OpenAI API)

1. Vispirms importējiet protokolu un piedāvājumus lokāli. Apskatiet kopsavilkumu par nolasīto tekstu un aizpildītajiem laukiem.
2. Spiediet **MI analīze**. Atlasiet tikai analizējamos avotus — vispirms protokolu un izvēlētā piegādātāja pieteikumu. Reģistri un viss projekta JSON netiek automātiski nosūtīti.
3. Sarežģītam vai skenētam PDF tajā pašā logā izvēlieties **Pievienot PDF arī vizuālai nolasīšanai**. Tas nosūta pilnu PDF ar lapu attēliem, ne tikai jau nolasīto tekstu. ZIP netiek sūtīts kā fails; no tā izvēlas nolasītos avotus. Vecs DOC pirms tam jākonvertē.
4. Ievadiet OpenAI API atslēgu. To var izmantot tikai šai sesijai vai pēc izvēles saglabāt Windows Credential Manager. Atslēga netiek rakstīta projekta failā, žurnālā vai instalācijas paketē. Glabātuvē saglabāto atslēgu var dzēst tajā pašā logā. Vides konfigurācijā var izmantot `IEPIRKUMI_API_KEY`; vērtību ievadiet drošajos vides iestatījumos, nevis čatā.
5. Noklusējuma modelis ir `gpt-4.1-mini`; to var mainīt, ja cits modelis atbalsta Responses API, strukturētu JSON un PDF ievadi. API ir maksas pakalpojums atsevišķi no ChatGPT abonementa.
6. Pirms katra pieprasījuma atzīmējiet piekrišanu un apstipriniet precīzu avotu sarakstu, teksta apjomu un PDF lapu skaitu. Ierobežojumi: 120 000 teksta rakstzīmes, 12 MB / 40 PDF lapas, 6000 atbildes tokeni. Ievades izmaksas pieaug arī ar PDF attēliem; atbildes tokenu limits nav naudas izdevumu limits. Nav automātisku maksas atkārtojumu vai klusas ievades saīsināšanas.
7. Rezultāti parādās kā **neapstiprināti kandidāti ar citātiem**. Teksta citāts tiek pārbaudīts pret norādīto avotu; vizuāla PDF citāts jāpārbauda norādītajā lapā. Dažādas vērtības rada neatbilstību. MI nevar mainīt veidlapu vai izvēlēties EKK/kategoriju. Tas neaizvieto cilvēka pārbaudi un negarantē visu datu pareizu nolasīšanu.

API pieprasījums ir HTTPS uz `api.openai.com`, ar `store:false`. Tas neatceļ API pakalpojuma piemērojamo datu apstrādes un drošības noteikumus. Mākoņa videi vajag atļaut šo domēnu; Windows datoram — interneta pieslēgumu. API atslēga nav vajadzīga lokālajai OCR un DOCX pamatplūsmai.

## Gala parauga izkārtojums un personas noklusējumi

Noklusējuma izvadē izmanto `templates/avs_2026.docx`: no lietotāja apstiprinātā gala parauga sagatavotu vispārīgu veidlapu bez konkrētā iepirkuma datiem. Oriģinālā oficiālā veidlapa saglabāta atsevišķi. Īsais līguma priekšmets tabulā un locītais formulējums teikumā “par …” ir neatkarīgi lauki. Sagatavotāja vārds un amats ģenitīvā ievadāms vai izvēlams no darbinieka ieraksta. PVN reģistrācijas numurs ir atsevišķs avotā iegūstams lauks; to neizdomā no reģistrācijas numura. Apmaksas kalendāra dienu lauks ir atsevišķs no norēķinu nosacījumiem.

Pēc lietotāja lūguma no rediģēšanas tabulas izņemti sākotnējās versijas lauki 24, 25, 26, 37, 38: kategorija, iestāde, DVS datuma darba piezīme, papildu piezīmes, pielikumu darba saraksts. Veco JSON savietojamībai dati iekšēji saglabājas. Robežgadījumu kategorijas izvēle paliek atsevišķā vadīklā. Lauki jaunajā versijā ir pārnumurēti; lietojiet to nosaukumus.

Personiskie noklusējumi atrodas ārpus Git: izstrādē `local/defaults.json`, portatīvai lietotnei `IepirkumuAsistents.profile.json` blakus EXE. Profils var saturēt vienu sākotnējo darbinieku ar `first_name`, `last_name`, `position`, `phone`, `email`, `header_name`, `header_role`, `responsible_text`. To izmanto sākotnējām izvēlēm, nepārrakstot lietotāja pēdējās izvēles. Personiskais profils un pilnais lietotāja iesniegums netiek pievienots publiskajam repozitorijam. Windows būvēšanā profilu var padot ar repozitorija Actions secret `IEPIRKUMI_PERSONAL_PROFILE`; tā saturs netiek izdrukāts, bet pēc lietotāja izvēles nonāk izplatāmajā programmas arhīvā blakus EXE. Arhīvs ar šo profilu satur personas norādīto kontaktinformāciju, tāpēc izplatiet to paredzētajiem lietotājiem. Profils nav paredzēts API atslēgām. Var norādīt citu profilu ar `IEPIRKUMI_PROFILE`.

## 0.2.1 — MI citātu kļūdas labojums

Atsevišķs nepārbaudāms MI citāts vairs nenoraida visu atbildi. Derīgās vērtības tiek piemērotas kā neapstiprināti kandidāti, noraidītās tiek saglabātas atsevišķā “MI noraidījumi” sarakstā ar lauka nosaukumu, MI vērtību, citātu, avotu un iemeslu. Šie noraidījumi nekļūst par importa avotiem un automātiski neaizpilda laukus. Saraksts saglabājas projekta JSON.

Pārbaude normalizē Unicode tipogrāfiju, atstarpes un alfabētisku vārdu pārnesumus rindu beigās. Tā neizmanto aptuvenu vārdu, skaitļu vai datumu meklēšanu. Ja MI sajauc lapas identifikatoru, citātu drīkst piesaistīt unikāli atrastai citai lapai tikai tajā pašā atlasītajā failā. Starp dažādu pretendentu failiem citāti netiek pārvietoti.

Vairāku kolonnu PDF tabulā modelis joprojām var pārformulēt citātu vai savienot atsevišķas šūnas. Tādā gadījumā konkrētā vērtība paliek noraidīta. Izmantojiet MI loga PDF vizuālo analīzi, atatlasot teksta avotus un izvēloties pašu PDF. Vizuālo citātu un vērtību pārbauda cilvēks norādītajā lapā. Nav automātiska atkārtota maksas pieprasījuma.
