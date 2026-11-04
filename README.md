# Iepirkumu asistents

Lokāla Python/PySide6 darbvirsmas lietotne Ādažu vidusskolas iepirkumu iesniegumu sagatavošanai pēc iesniegtās 2026. gada oficiālās veidlapas. Izveido rediģējamu DOCX, saglabājot oriģināla tabulas, piemales un juridiskos formulējumus. Gala apstiprinājumu veic cilvēks.

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
2. Importējiet protokolu, tad piedāvājumus vai ZIP. Teksti un kvalitātes statuss redzami “Avoti”. Piedāvājumu noteikumi salīdzina izvēlētā piegādātāja dokumentus pēc reģistrācijas numura; citu pretendentu summas netiek sajauktas ar uzvarētāja summu.
3. Katru lauku var ievadīt un labot manuāli. Atlasot lauka rindu, redzami kandidāti un avotu fragmenti. Izvēlieties kandidātu vai ierakstiet labojumu; atzīmējiet “Pārbaudīts” tikai pēc salīdzināšanas ar avotu. Jauni avoti atceļ iepriekšējo pārbaudes atzīmi.
4. Ierakstiet īsu līguma priekšmetu, pamatojumu un EKK. Sagatavotāja manuālajā laukā 1. rinda ir vārds un uzvārds, 2. rinda — amats. Atbildīgās personas laukā iekļaujiet arī tālruni un e-pastu.
5. Kategorijas 1/2/3 robežgadījumos izvēlieties manuāli. Precīzi 500 EUR un (5999;6000] EUR rada brīdinājumu. Veidlapas teksts netiek pārveidots. Citas juridiskās piemērojamības prasības pārbauda lietotājs.
6. Saglabājiet iepirkumu JSON failā un ģenerējiet DOCX. Nezināmie vietturi un neapstiprinātie dati ir dzelteni iezīmēti; pie brīdinājumiem programma piedāvā ģenerēt pārskatīšanas dokumentu. Pārbaudiet gala izkārtojumu Word un pievienojiet prasītos DVS pielikumus.

Piegādātāja izvēle kopē reģistra vērtības konkrētajā iepirkumā. Turpmākie labojumi iepirkumā nemaina pamatierakstu. Reģistra labojumi savukārt nepārraksta saglabātu iepirkumu.

## Formāti un OCR

PDF (arī skenējumi ar lokālu OCR), DOCX, XLSX, ZIP. EDOC tiek lasīts kā konteineris; elektroniskie paraksti netiek pārbaudīti. Oriģinālus arhīvus neizpako uz diska un neizpilda. Ir izmēra, failu skaita un ligzdošanas ierobežojumi. Vecais DOC jāatver Word/LibreOffice un jāsaglabā kā DOCX. Lietotnei komplektā jau ir konvertēta oficiālā veidlapa.

OCR papildus nepieciešams Tesseract 5 ar latviešu `lav` un angļu `eng` valodu datiem. Norādiet `TESSDATA_PREFIX` uz `tessdata` mapi un ieslēdziet “Lokāls OCR”. Ja OCR nav uzstādīts, pamatplūsma strādā ar teksta PDF un manuālo ievadi; skenējumi rada brīdinājumu. OCR rezultāts vienmēr jāpārbauda.

Automātiskā ekstrakcija atpazīst pievienotā iepirkumi.lv protokola struktūru un marķētas piedāvājumu tabulu rindas / `nosaukums: vērtība` PDF rindas. Patvaļīga dokumentu izkārtojuma pilnīga atpazīšana netiek solīta; visi importētie teksti ir pieejami manuālai pārbaudei. Lietotne nedarbojas ar MI un nesūta dokumentus ārpakalpojumiem.

## Windows izpildfails un instalēšana

Windows datorā palaidiet:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Skripts izpilda testus, būvē EXE un pārbauda pašu komplektēto lietotni: Qt loga izveidi, lokālo datubāzi, projekta saglabāšanu/atvēršanu un DOCX ģenerēšanu ar komplektā iekļauto veidlapu. Tikai pēc sekmīgas pārbaudes tas veido `dist/IepirkumuAsistents-Windows.zip`. Izpakojiet **visu** mapi, nevis tikai EXE, un palaidiet `IepirkumuAsistents.exe`. Iespējams izveidot darbvirsmas saīsni. Python lietotāja datorā pēc būvēšanas vairs nav vajadzīgs. OCR valodu dati nav iekļauti; tie jāuzstāda atsevišķi.

GitHub Actions darbplūsma `.github/workflows/windows.yml` izpilda to pašu būvēšanas skriptu. Tā saglabā portatīvo ZIP artefaktā `IepirkumuAsistents-Windows` un palaišanas rezultātu `Windows-startup-check`. Par sekmīgu Windows būvi drīkst uzskatīt tikai izpildi ar `status: passed`, `frozen: true`, `platform: win32` pārbaudes JSON failā. Šajā Linux mākoņa vidē Windows EXE un Microsoft Word pārbaude nav veikta; būvēšanas instrukcija nav gatava EXE pārbaudes apliecinājums. MSI/EXE instalētājs un koda parakstīšana šajā versijā nav realizēti.

## Izstrāde Linux / mākoņa vidē

Izmantojiet esošo checkout; katrs mākoņa uzdevums jau ir izolēts. Jauns Git worktree nav nepieciešams.

```bash
cd /workspace/Iepirkumu-asistents
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
IEPIRKUMI_DATA_DIR="$PWD/local/data" .venv/bin/python -m iepirkumi
```

Bez grafiskās darbvirsmas Qt testos lietojiet `QT_QPA_PLATFORM=offscreen`. Interaktīvai lietošanai vajadzīgs darbvirsmas displejs. Nav nepieciešami tīkla servisi vai datubāzes serveris. Atkarību instalēšanai vajadzīga piekļuve PyPI.

Lietotāja paraugdokumentus glabā ārpus Git. Papildu integrācijas pārbaude:

```bash
IEPIRKUMI_SAMPLES=/workspace/attachments QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_samples.py /workspace/attachments
```

Otra komanda izveido `local/Folijas_segas_parskatisanai.docx` un JSON projektu. Tas ir pārskatīšanas paraugs: darbinieki, EKK, pamatojums un citi neapstiprinātie lauki nav izdomāti. Piegādes adrešu atšķirīgais pieraksts tiek parādīts kā pārbaudāma neatbilstība.

## Dati, kopijas un dzēšana

Windows reģistri: `%LOCALAPPDATA%/IepirkumuAsistents/registri.sqlite3`. Citur: `~/.local/share/IepirkumuAsistents/`. Var norādīt citu mapi ar `IEPIRKUMI_DATA_DIR`. Dati nav šifrēti pašas lietotnes līmenī; glabājiet tos aizsargātā lietotāja kontā / diskā. JSON projekts satur arī avotu tekstus un labojumus.

Reģistru sadaļā var labot/dzēst ierakstus un saglabāt SQLite rezerves kopiju. Atjaunošanai aizveriet lietotni, saglabājiet pašreizējās DB kopiju un aizvietojiet DB ar izvēlēto kopiju. “Dzēst visus” dzēš reģistrus un pēdējās izvēles; projektu failus, DOCX, rezerves kopijas un oriģinālus dzēsiet atsevišķi failu pārvaldniekā. Dzēšana negarantē fizisku datu neatjaunojamību no diska vai ārējām kopijām.

Kļūdu žurnāls `asistents.log` ir tajā pašā datu mapē, ar ierobežotu izmēru; dokumentu saturs žurnālā netiek rakstīts. Nav API atslēgu un ārējas MI sūtīšanas. MI papildmodulis apzināti nav ieviests.

Detalizēts lauku un šaubu kartējums: [docs/lauku-kartejums.md](docs/lauku-kartejums.md).

## Gatavās lietotnes pārbaude

Būvēšanas rezultātu var atkārtoti pārbaudīt arī citā Windows datorā bez Python:

```powershell
$process = Start-Process -FilePath '.\IepirkumuAsistents.exe' -ArgumentList '--smoke-test', 'palaisanas-parbaude.json' -PassThru -Wait
$process.ExitCode
Get-Content palaisanas-parbaude.json
```

Pārbaude izmanto pagaidu datus un nemaina lietotāja reģistrus. Ja EXE nevar pat startēt trūkstošu sistēmas bibliotēku dēļ, JSON var netikt izveidots; tā ir neveiksmīga pārbaude. Sekmīga automātiskā pārbaude neaizvieto gala dokumenta vizuālu pārbaudi Microsoft Word.
