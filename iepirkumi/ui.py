import sys
import logging
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QEvent
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QPlainTextEdit,
    QCheckBox, QComboBox, QFileDialog, QMessageBox, QSplitter, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QListWidget, QProgressDialog,
    QHeaderView, QAbstractItemView,
)
from .models import Procurement, LABELS, VISIBLE_LABELS, Field
from .storage import Store, save_project, load_project, data_dir
from .importer import read_file, extract_protocol, extract_offers
from .validation import validate
from .word import generate
from .pipeline import import_chunks

EMPLOYEE = {'first_name':'Vārds','last_name':'Uzvārds','position':'Amats','phone':'Tālrunis','email':'E-pasts','header_name':'Vārds, uzvārds ģenitīvā (no …)','header_role':'Amats ģenitīvā'}
SUPPLIER = {k: LABELS[k] for k in ['supplier_name','registration','vat_number','address','bank','iban','swift','phone','email','representative','representative_role','authority','contact']}


def person_text(r):
    return '\n'.join([f"{r.get('first_name','')} {r.get('last_name','')}".strip(), r.get('position','')] + [x for x in [r.get('phone',''),r.get('email','')] if x])


class RecordDialog(QDialog):
    def __init__(self, labels, values=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Reģistra ieraksts'); self.resize(520,400)
        self.inputs = {}; layout = QFormLayout(self)
        for key, label in labels.items():
            edit = QLineEdit((values or {}).get(key,''))
            layout.addRow(label, edit); self.inputs[key] = edit
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self):
        return {key: edit.text().strip() for key,edit in self.inputs.items()}


class ImportWorker(QThread):
    result = Signal(object, object)
    failed = Signal(str)

    def __init__(self, path, ocr):
        super().__init__(); self.path = path; self.ocr = ocr

    def run(self):
        try:
            chunks, warnings = read_file(self.path, self.ocr)
            self.result.emit(chunks, warnings)
        except Exception as exc:
            logging.warning('Import failed: %s', type(exc).__name__)
            self.failed.emit(str(exc))


class Window(QMainWindow):
    def __init__(self, store=None):
        super().__init__()
        self.store = store or Store();
        from .profile import seed_store
        seed_store(self.store)
        self.project = Procurement(); self.path = None
        self.loading = False; self.dirty = False; self.busy = False; self.worker = None
        self.session_api_key=''; self.import_message=''; self.import_failed=False
        self.setWindowTitle('Iepirkumu asistents 0.2'); self.resize(1320,880)
        self.toolbar = self.addToolBar('Darbības'); self.toolbar.setMovable(False)
        for label, fn in [('Jauns',self.new),('Atvērt',self.open),('Saglabāt',self.save),('Importēt protokolu',lambda:self.import_doc(True)),('Importēt piedāvājumus',lambda:self.import_doc(False)),('Ģenerēt DOCX',self.export),('MI analīze',self.analyze_ai)]:
            action = QAction(label,self); action.triggered.connect(fn); self.toolbar.addAction(action)
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.build_project(); self.build_sources(); self.build_registers(); self.build_help()
        self.statusBar().showMessage('Lokāla apstrāde · MI un ārējā datu nosūtīšana izslēgta')
        self.refresh_registers(); self.load_fields(); self.restore_people()

    def build_project(self):
        tab = QWidget(); outer = QVBoxLayout(tab)
        title = QLabel('Iepirkuma iesniegums'); title.setObjectName('title'); outer.addWidget(title)
        outer.addWidget(QLabel('Pārbaudiet avotus, labojiet vērtības un apstipriniet katru pārbaudīto lauku. Neapstiprinātie dati DOCX būs dzelteni.'))
        people = QHBoxLayout(); self.combos = {}
        for key,label in [('preparer','Sagatavotājs'),('responsible','Atbildīgā persona'),('supplier','Piegādātājs')]:
            people.addWidget(QLabel(label)); combo = QComboBox(); combo.setMinimumWidth(170)
            people.addWidget(combo); self.combos[key] = combo
            combo.activated.connect(lambda index,k=key:self.choose_record(k,index))
        outer.addLayout(people)
        self.ocr = QCheckBox('Automātisks OCR skenētiem PDF un attēliem (lav+eng iekļauts programmā)'); self.ocr.setChecked(True); outer.addWidget(self.ocr)
        self.category_choice=QComboBox();self.category_choice.addItems(['Vērtības robežgadījums — izvēlieties','1 — līdz 500 EUR','2 — 500–5999 EUR','3 — virs 6000 EUR']);self.category_choice.activated.connect(self.choose_category);outer.addWidget(self.category_choice);self.category_choice.hide()
        self.import_summary=QLabel('Pievienojiet protokolu un piedāvājumus jebkurā secībā.');self.import_summary.setWordWrap(True);outer.addWidget(self.import_summary)
        split = QSplitter(Qt.Horizontal)
        self.table = QTableWidget(len(VISIBLE_LABELS),3)
        self.table.setHorizontalHeaderLabels(['Lauks','Vērtība (var labot)','Pārbaudīts'])
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.table.setColumnWidth(0,325); self.table.setColumnWidth(2,100)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.editors, self.checks = {}, {}
        for row,(key,label) in enumerate(VISIBLE_LABELS.items()):
            item = QTableWidgetItem(label); item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row,0,item)
            edit = QPlainTextEdit(); edit.setTabChangesFocus(True); edit.setMaximumHeight(72)
            edit.setProperty('field_row',row);edit.installEventFilter(self)
            edit.setAccessibleName(label); edit.textChanged.connect(lambda k=key:self.changed(k))
            self.table.setCellWidget(row,1,edit); self.editors[key] = edit
            check = QCheckBox('Jā'); check.toggled.connect(lambda value,k=key:self.confirm(k,value))
            self.table.setCellWidget(row,2,check); self.checks[key] = check
            self.table.setRowHeight(row,62)
        self.table.currentCellChanged.connect(self.show_evidence)
        split.addWidget(self.table)
        side = QWidget(); layout = QVBoxLayout(side)
        layout.addWidget(QLabel('Atlasītā lauka avoti'))
        self.evidence_list = QListWidget(); layout.addWidget(self.evidence_list)
        self.evidence_list.currentRowChanged.connect(self.show_fragment)
        self.fragment = QPlainTextEdit(); self.fragment.setReadOnly(True); layout.addWidget(self.fragment)
        apply = QPushButton('Izmantot atlasīto vērtību'); apply.clicked.connect(self.use_candidate); layout.addWidget(apply)
        layout.addWidget(QLabel('Pārbaudes un brīdinājumi'))
        self.issues = QPlainTextEdit(); self.issues.setReadOnly(True); layout.addWidget(self.issues)
        split.addWidget(side); split.setSizes([900,360]); outer.addWidget(split)
        self.tabs.addTab(tab,'Iepirkums')

    def build_sources(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        layout.addWidget(QLabel('Importētais teksts un atpazīšanas kvalitāte. EDOC saturs ir nolasāms; paraksti netiek validēti.'))
        self.sources = QListWidget(); self.sources.currentRowChanged.connect(self.show_source); layout.addWidget(self.sources,1)
        self.source_text = QPlainTextEdit(); self.source_text.setReadOnly(True); layout.addWidget(self.source_text,3)
        self.tabs.addTab(tab,'Avoti')

    def build_registers(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        layout.addWidget(QLabel('Reģistra labojumi nemaina jau saglabāto iepirkumu vērtības. Piegādātāja vienreizējos labojumus veiciet sadaļā “Iepirkums”.'))
        self.record_lists = {}
        for kind,label in [('employee','Darbinieki'),('supplier','Piegādātāji')]:
            layout.addWidget(QLabel(label)); listing = QListWidget(); layout.addWidget(listing)
            self.record_lists[kind] = listing
            buttons = QHBoxLayout()
            for text,func in [('Pievienot',lambda _,k=kind:self.edit_record(k,True)),('Labot',lambda _,k=kind:self.edit_record(k,False)),('Dzēst',lambda _,k=kind:self.delete_record(k))]:
                b = QPushButton(text); b.clicked.connect(func); buttons.addWidget(b)
            layout.addLayout(buttons)
        save_supplier = QPushButton('Saglabāt pašreizējā iepirkuma piegādātāju kā jaunu reģistra ierakstu')
        save_supplier.clicked.connect(self.register_supplier); layout.addWidget(save_supplier)
        backup = QPushButton('Saglabāt reģistru rezerves kopiju'); backup.clicked.connect(self.backup); layout.addWidget(backup)
        erase = QPushButton('Dzēst visus vietējos reģistrus un pēdējās izvēles'); erase.clicked.connect(self.erase); layout.addWidget(erase)
        self.tabs.addTab(tab,'Reģistri')

    def build_help(self):
        view = QPlainTextEdit(); view.setReadOnly(True)
        view.setPlainText('IEPIRKUMU ASISTENTS — lokāla Windows lietotne\n\n'
            '1. Pievienojiet darbiniekus reģistram un neatkarīgi izvēlieties sagatavotāju un atbildīgo.\n'
            '2. Importējiet protokolu, tad piedāvājumus (PDF, DOCX, XLSX, ZIP, EDOC saturs).\n'
            '3. Katram iegūtajam laukam apskatiet avotu. Neatbilstību gadījumā izvēlieties vai ievadiet vērtību un atzīmējiet “Pārbaudīts”.\n'
            '4. Ierakstiet īsu līguma priekšmetu, piemēram, “Izotermisko folijas segu iegāde”. Pārbaudiet pamatojumu, EKK, avansu un termiņus.\n'
            '5. Saglabājiet iepirkumu JSON failā. Ģenerējiet DOCX un pārbaudiet to Word pirms ievietošanas DVS.\n\n'
            'Robežgadījumi: precīzi 500 EUR un intervāls (5999; 6000] EUR jāizvērtē manuāli. Kategoriju ievadiet kā 1, 2 vai 3; oriģinālais veidlapas teksts nemainās.\n'
            'Darba piezīmes (iestāde, identifikators, DVS datums, pielikumu saraksts, piezīmes) saglabājas projektā. Veidlapā tiem nav atsevišķa lauka, tāpēc tie netiek patvaļīgi pievienoti.\n'
            'Iesnieguma datums ir DVS kartiņas datums; to automātiski neaizvieto ar protokola datumu.\n'
            'Tukšie vietturi un neapstiprinātie dati ir iezīmēti tikai ar Word teksta highlight. Neizmantojamo sadaļu piemērojamību pārbauda cilvēks.\n\n'
            'Drošība un ierobežojumi\n'
            'Pēc noklusējuma dati netiek sūtīti ārpakalpojumiem. “MI analīze” ir izvēles OpenAI API modulis; katrs pieprasījums prasa skaidru piekrišanu. OCR darbojas lokāli ar komplektā esošajiem lav+eng datiem. OCR teksts vienmēr jāpārbauda.\n'
            'Piedāvājumu automātiskie noteikumi atpazīst marķētas tabulu rindas un salīdzina tikai dokumentus ar izvēlētā piegādātāja reģistrācijas numuru. Citi teksti ir apskatāmi avotos manuālai ievadei.\n'
            'DOC fails vispirms jākonvertē uz DOCX ar Word vai LibreOffice. EDOC elektroniskā paraksta derīgumu pārbaudiet atsevišķi.\n'
            'Reģistri: ' + str(self.store.path) + '\n'
            'Projektu JSON satur ievadītos datus un avotu fragmentus. Glabājiet tos aizsargātā mapē. Reģistru dzēšana neizdzēš projektu failus, eksportus vai rezerves kopijas; tos dzēsiet arī failu pārvaldniekā.\n'
            'Windows EXE būvēšanas un instalēšanas soļi ir README. Šī ir pirmā versija; gala apstiprinājumu veic cilvēks.')
        self.tabs.addTab(view,'Lietošana')

    def choose_category(self,index):
        self.project.fields['category']=Field(str(index) if index else '',edited=True,confirmed=bool(index))
        self.dirty=True;self.update_issues()

    def changed(self,key):
        if self.loading: return
        f = self.project.fields[key]; f.value = self.editors[key].toPlainText(); f.edited = True; f.confirmed = False
        self.loading = True; self.checks[key].setChecked(False); self.loading = False
        self.dirty = True; self.update_issues()

    def confirm(self,key,value):
        if self.loading: return
        self.project.fields[key].confirmed = value
        self.dirty = True; self.update_issues()

    def load_fields(self):
        self.loading = True
        for key,f in self.project.fields.items():
            if key not in self.editors: continue
            self.editors[key].setPlainText(f.value); self.checks[key].setChecked(f.confirmed)
        self.loading = False
        for combo in self.combos.values(): combo.setCurrentIndex(0)
        self.sources.clear(); self.source_text.clear()
        for c in self.project.imports:
            self.sources.addItem(f"{c['source']} · {c['location']} · {c['quality']}")
        self.show_evidence(); self.update_issues()

    def update_issues(self):
        from .validation import category
        try:boundary=bool(self.project.fields['net'].value) and category(self.project.fields['net'].value) is None
        except ValueError:boundary=False
        chosen=self.project.fields['category'].value
        self.category_choice.setVisible(boundary or bool(chosen))
        self.category_choice.setCurrentIndex(int(chosen) if chosen in ('1','2','3') else 0)
        self.issues.setPlainText('\n\n'.join(validate(self.project)) or 'Pārbaudes brīdinājumu nav. Pārskatiet gala dokumentu.')
        for row,key in enumerate(VISIBLE_LABELS):
            f=self.project.fields[key]
            self.table.item(row,0).setToolTip('Avotos ir neatbilstība' if f.conflict else '')

    def eventFilter(self,obj,event):
        if event.type()==QEvent.FocusIn:
            row=obj.property('field_row')
            if row is not None:self.table.setCurrentCell(int(row),0)
        return super().eventFilter(obj,event)

    def current_key(self):
        row = self.table.currentRow()
        return list(VISIBLE_LABELS)[row] if row >= 0 else None

    def show_evidence(self,*_):
        self.evidence_list.clear(); self.fragment.clear()
        key = self.current_key()
        if key:
            for e in self.project.fields[key].candidates:
                self.evidence_list.addItem(f'{e.value}\n{e.source} · {e.location} · {e.confidence}')

    def show_fragment(self,row):
        key = self.current_key()
        if key and 0 <= row < len(self.project.fields[key].candidates):
            self.fragment.setPlainText(self.project.fields[key].candidates[row].excerpt)

    def use_candidate(self):
        key, row = self.current_key(), self.evidence_list.currentRow()
        if key and row >= 0:
            self.editors[key].setPlainText(self.project.fields[key].candidates[row].value)

    def show_source(self,row):
        self.source_text.setPlainText(self.project.imports[row]['text'] if 0 <= row < len(self.project.imports) else '')

    def refresh_registers(self):
        self.records = {k:self.store.records(k) for k in ('employee','supplier')}
        for kind,listing in self.record_lists.items():
            listing.clear()
            for i,r in self.records[kind]:
                listing.addItem(person_text(r) if kind == 'employee' else r.get('supplier_name','') + ' · ' + r.get('registration',''))
        for key,combo in self.combos.items():
            combo.clear(); combo.addItem('Manuāla ievade',None)
            kind = 'supplier' if key=='supplier' else 'employee'
            for i,r in self.records[kind]:
                combo.addItem(r.get('supplier_name','') if kind=='supplier' else f"{r.get('first_name','')} {r.get('last_name','')}",i)

    def restore_people(self):
        for key in ('preparer','responsible'):
            saved = self.store.setting(key)
            index = self.combos[key].findData(int(saved)) if saved.isdigit() else -1
            if index >= 0:
                self.combos[key].setCurrentIndex(index); self.choose_record(key,index)

    def choose_record(self,key,index):
        record_id = self.combos[key].itemData(index)
        if record_id is None: return
        kind = 'supplier' if key=='supplier' else 'employee'
        r = next(r for i,r in self.records[kind] if i==record_id)
        if kind=='employee':
            self.editors[key].setPlainText(r.get('responsible_text') or person_text(r) if key=='responsible' else person_text(r))
            if key=='preparer':
                self.editors['preparer_genitive'].setPlainText(r.get('header_name',''))
                self.editors['preparer_role_genitive'].setPlainText(r.get('header_role',''))
            self.store.set_setting(key,record_id)
        else:
            for field in SUPPLIER:
                self.editors[field].setPlainText(r.get(field,''))
            if self.project.imports:
                import_chunks(self.project,[]);self.load_fields()

    def edit_record(self,kind,new):
        row = self.record_lists[kind].currentRow()
        if not new and row < 0: return
        i,r = (None,{}) if new else self.records[kind][row]
        dialog = RecordDialog(EMPLOYEE if kind=='employee' else SUPPLIER,r,self)
        if dialog.exec():
            values = dialog.values()
            if not any(values.values()): return
            self.store.save_record(kind,values,i); self.refresh_registers()

    def delete_record(self,kind):
        row = self.record_lists[kind].currentRow()
        if row >= 0 and QMessageBox.question(self,'Dzēst','Dzēst atlasīto reģistra ierakstu?')==QMessageBox.Yes:
            self.store.delete_record(self.records[kind][row][0]); self.refresh_registers()

    def register_supplier(self):
        self.store.save_record('supplier',{k:self.project.fields[k].value for k in SUPPLIER}); self.refresh_registers()

    def backup(self):
        path,_ = QFileDialog.getSaveFileName(self,'Reģistru rezerves kopija','','SQLite (*.sqlite3)')
        if path:
            if Path(path).resolve() == self.store.path.resolve():
                return self.error('Izvēlieties citu failu nekā aktīvā datubāze.')
            try: self.store.backup(path)
            except Exception as e: self.error(str(e))

    def erase(self):
        if QMessageBox.question(self,'Dzēst reģistrus','Dzēst visus darbiniekus, piegādātājus un pēdējās izvēles? Projektu faili un kopijas paliks.')==QMessageBox.Yes:
            self.store.erase(); self.refresh_registers()

    def may_discard(self):
        if not self.dirty: return True
        choice = QMessageBox.question(self,'Nesaglabāti dati','Saglabāt pašreizējo iepirkumu?',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
        return self.save() if choice==QMessageBox.Save else choice==QMessageBox.Discard

    def new(self):
        if not self.may_discard(): return
        self.project = Procurement(); self.path = None; self.dirty = False; self.load_fields(); self.restore_people()
        self.setWindowTitle('Iepirkumu asistents — jauns iepirkums')

    def open(self):
        if not self.may_discard(): return
        path,_ = QFileDialog.getOpenFileName(self,'Atvērt iepirkumu vai importēt dokumentu','','Iepirkums vai dokuments (*.json *.pdf *.zip *.edoc *.docx *.xlsx *.jpg *.jpeg *.png *.tif *.tiff)')
        if not path: return
        if Path(path).suffix.lower()!='.json':
            self.start_import(path);return
        try:
            self.project = load_project(path); self.path = path; self.load_fields(); self.dirty = False
            self.setWindowTitle('Iepirkumu asistents — ' + Path(path).name)
        except Exception as e: self.error(str(e))

    def save(self):
        path = self.path
        if not path: path,_ = QFileDialog.getSaveFileName(self,'Saglabāt iepirkumu','iepirkums.json','Iepirkums (*.json)')
        if not path: return False
        try:
            save_project(self.project,path); self.path = path; self.dirty = False
            self.statusBar().showMessage('Iepirkums saglabāts: ' + path); return True
        except Exception as e:
            self.error(str(e)); return False

    def import_doc(self,protocol):
        path,_ = QFileDialog.getOpenFileName(self,'Protokols' if protocol else 'Piedāvājumi','','Dokumenti (*.pdf *.docx *.xlsx *.zip *.edoc *.jpg *.jpeg *.png *.tif *.tiff)')
        if not path: return
        self.start_import(path)

    def start_import(self,path):
        self.import_failed=False
        self.busy = True; self.centralWidget().setEnabled(False); self.toolbar.setEnabled(False)
        self.progress = QProgressDialog('Nolasa dokumentus lokāli…',None,0,0,self)
        self.progress.setWindowModality(Qt.WindowModal); self.progress.show()
        self.worker = ImportWorker(path,self.ocr.isChecked())
        self.worker.result.connect(lambda chunks,warnings:self.imported(None,chunks,warnings))
        self.worker.failed.connect(self.import_error)
        self.worker.finished.connect(self.import_finished)
        self.worker.start()

    def imported(self,protocol,chunks,warnings):
        stats=import_chunks(self.project,chunks,warnings)
        self.load_fields(); self.dirty=True
        self.import_message=(f"Nolasīts {stats['fragments']} avotu fragmentos, {stats['characters']:,} rakstzīmes. "
                             f"Aizpildīti {stats['filled']} lauki; neatbilstības: {stats['conflicts']}. "
                             f"Importa ziņojumi: {stats['warnings']}.")
        if stats['characters']==0:self.import_message+=' Teksts nav nolasīts; pārbaudiet OCR vai izmantojiet MI vizuālo PDF nolasīšanu.'
        elif stats['new_fields']==0:self.import_message+=' Jaunu lauku nav: avotus var nolasīt MI vai pārbaudīt manuāli sadaļā “Avoti”.'
        self.import_summary.setText(self.import_message)

    def import_error(self,message):
        self.import_failed=True;self.import_message='Imports neizdevās: '+message
        self.error(message)

    def import_finished(self):
        self.busy=False;self.progress.close();self.centralWidget().setEnabled(True);self.toolbar.setEnabled(True)
        self.statusBar().showMessage(self.import_message)

    def analyze_ai(self):
        from .ui_ai import AIDialog, AIWorker
        dialog=AIDialog(self.project,self,self.session_api_key)
        if not dialog.exec():return
        self.session_api_key=dialog.api_key
        self.busy=True;self.centralWidget().setEnabled(False);self.toolbar.setEnabled(False)
        self.progress=QProgressDialog('OpenAI API analizē atlasītos dokumentus…',None,0,0,self)
        self.progress.setWindowModality(Qt.WindowModal);self.progress.show()
        self.worker=AIWorker(dialog.job,dialog.api_key)
        self.worker.result.connect(self.ai_finished)
        self.worker.failed.connect(self.import_error)
        self.worker.finished.connect(self.import_finished);self.worker.start()

    def ai_finished(self,entries,usage):
        from .ai import apply
        apply(self.project,entries);self.load_fields();self.dirty=True
        self.import_message=f'MI atgrieza {len(entries)} vērtības. Ievades tokeni: {usage.get("input_tokens","nav ziņu")}; atbildes tokeni: {usage.get("output_tokens","nav ziņu")}. Pārbaudiet citātus un neatbilstības.'
        self.import_summary.setText(self.import_message)

    def export(self):
        warnings = validate(self.project)
        if warnings:
            msg = QMessageBox(self); msg.setWindowTitle('Pirms DOCX izveides')
            msg.setText('Ir pārbaudāmi vai trūkstoši dati. Izveidot pārskatīšanas dokumentu ar dzelteniem iezīmējumiem?')
            msg.setDetailedText('\n'.join(warnings)); msg.setStandardButtons(QMessageBox.Yes|QMessageBox.Cancel)
            if msg.exec()!=QMessageBox.Yes: return
        path,_ = QFileDialog.getSaveFileName(self,'Saglabāt DOCX','Iepirkuma_iesniegums.docx','Word (*.docx)')
        if not path: return
        try:
            generate(self.project,path)
            if QMessageBox.question(self,'DOCX saglabāts','Dokuments saglabāts. Atvērt pārskatīšanai?')==QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))
        except Exception as e: self.error(str(e))

    def error(self,message):
        QMessageBox.warning(self,'Darbību neizdevās pabeigt',message)

    def closeEvent(self,event):
        if self.busy:
            event.ignore(); return
        if self.may_discard():
            self.store.close(); event.accept()
        else: event.ignore()


def main():
    from logging.handlers import RotatingFileHandler
    log = RotatingFileHandler(data_dir()/'asistents.log', maxBytes=200000, backupCount=2, encoding='utf-8')
    logging.basicConfig(level=logging.WARNING, handlers=[log], format='%(asctime)s %(levelname)s %(message)s')
    app = QApplication(sys.argv); app.setApplicationName('Iepirkumu asistents')
    app.setStyle('Fusion')
    app.setStyleSheet('''
    QMainWindow, QWidget { background: #f5f6fa; color: #20273b; font-size: 13px; }
    QLabel#title { font-size: 25px; font-weight: 600; margin: 8px 0; }
    QPlainTextEdit, QListWidget, QLineEdit, QComboBox { background: white; border: 1px solid #d9ddeb; border-radius: 4px; padding: 5px; }
    QPushButton { background: #e8eaf5; border: 1px solid #d4d9eb; border-radius: 4px; padding: 8px 12px; }
    QPushButton:hover { background: #dce1f4; }
    QToolBar { background: #27364e; padding: 9px; spacing: 9px; }
    QToolButton { color: white; background: #354963; padding: 9px; border-radius: 4px; }
    QTabBar::tab { padding: 11px 25px; } QTabBar::tab:selected { background: white; color: #314d8d; }
    QHeaderView::section { background: #e9edf5; padding: 7px; border: 0; }
    ''')
    window = Window(); window.show(); sys.exit(app.exec())
