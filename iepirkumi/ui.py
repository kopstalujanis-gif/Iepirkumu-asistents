import sys
import logging
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QPlainTextEdit,
    QCheckBox, QComboBox, QFileDialog, QMessageBox, QSplitter, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QListWidget, QProgressDialog,
    QHeaderView, QAbstractItemView,
)
from .models import Procurement, LABELS, Field
from .storage import Store, save_project, load_project, data_dir
from .importer import read_file, extract_protocol, extract_offers
from .validation import validate
from .word import generate

EMPLOYEE = {'first_name':'Vārds','last_name':'Uzvārds','position':'Amats','phone':'Tālrunis','email':'E-pasts'}
SUPPLIER = {k: LABELS[k] for k in ['supplier_name','registration','address','bank','iban','swift','phone','email','representative','representative_role','authority','contact']}


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
        self.store = store or Store(); self.project = Procurement(); self.path = None
        self.loading = False; self.dirty = False; self.busy = False; self.worker = None
        self.setWindowTitle('Iepirkumu asistents'); self.resize(1320,880)
        self.toolbar = self.addToolBar('Darbības'); self.toolbar.setMovable(False)
        for label, fn in [('Jauns',self.new),('Atvērt',self.open),('Saglabāt',self.save),('Importēt protokolu',lambda:self.import_doc(True)),('Importēt piedāvājumus',lambda:self.import_doc(False)),('Ģenerēt DOCX',self.export)]:
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
        self.ocr = QCheckBox('Lokāls OCR skenētiem PDF (nepieciešams Tesseract ar lav+eng)'); outer.addWidget(self.ocr)
        split = QSplitter(Qt.Horizontal)
        self.table = QTableWidget(len(LABELS),3)
        self.table.setHorizontalHeaderLabels(['Lauks','Vērtība (var labot)','Pārbaudīts'])
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.table.setColumnWidth(0,325); self.table.setColumnWidth(2,100)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.editors, self.checks = {}, {}
        for row,(key,label) in enumerate(LABELS.items()):
            item = QTableWidgetItem(label); item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row,0,item)
            edit = QPlainTextEdit(); edit.setTabChangesFocus(True); edit.setMaximumHeight(72)
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
            'Nav MI integrācijas, API atslēgu vai dokumentu sūtīšanas ārpakalpojumiem. OCR darbojas lokāli un prasa Tesseract lav+eng. OCR teksts vienmēr jāpārbauda.\n'
            'Piedāvājumu automātiskie noteikumi atpazīst marķētas tabulu rindas un salīdzina tikai dokumentus ar izvēlētā piegādātāja reģistrācijas numuru. Citi teksti ir apskatāmi avotos manuālai ievadei.\n'
            'DOC fails vispirms jākonvertē uz DOCX ar Word vai LibreOffice. EDOC elektroniskā paraksta derīgumu pārbaudiet atsevišķi.\n'
            'Reģistri: ' + str(self.store.path) + '\n'
            'Projektu JSON satur ievadītos datus un avotu fragmentus. Glabājiet tos aizsargātā mapē. Reģistru dzēšana neizdzēš projektu failus, eksportus vai rezerves kopijas; tos dzēsiet arī failu pārvaldniekā.\n'
            'Windows EXE būvēšanas un instalēšanas soļi ir README. Šī ir pirmā versija; gala apstiprinājumu veic cilvēks.')
        self.tabs.addTab(view,'Lietošana')

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
            self.editors[key].setPlainText(f.value); self.checks[key].setChecked(f.confirmed)
        self.loading = False
        for combo in self.combos.values(): combo.setCurrentIndex(0)
        self.sources.clear(); self.source_text.clear()
        for c in self.project.imports:
            self.sources.addItem(f"{c['source']} · {c['location']} · {c['quality']}")
        self.show_evidence(); self.update_issues()

    def update_issues(self):
        self.issues.setPlainText('\n\n'.join(validate(self.project)) or 'Pārbaudes brīdinājumu nav. Pārskatiet gala dokumentu.')
        for row,(key,f) in enumerate(self.project.fields.items()):
            self.table.item(row,0).setToolTip('Avotos ir neatbilstība' if f.conflict else '')

    def current_key(self):
        row = self.table.currentRow()
        return list(LABELS)[row] if row >= 0 else None

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
            self.editors[key].setPlainText(person_text(r)); self.store.set_setting(key,record_id)
        else:
            for field in SUPPLIER:
                self.editors[field].setPlainText(r.get(field,''))

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
        path,_ = QFileDialog.getOpenFileName(self,'Atvērt iepirkumu','','Iepirkums (*.json)')
        if not path: return
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
        path,_ = QFileDialog.getOpenFileName(self,'Protokols' if protocol else 'Piedāvājumi','','Dokumenti (*.pdf *.docx *.xlsx *.zip *.edoc)')
        if not path: return
        self.busy = True; self.centralWidget().setEnabled(False); self.toolbar.setEnabled(False)
        self.progress = QProgressDialog('Nolasa dokumentus lokāli…',None,0,0,self)
        self.progress.setWindowModality(Qt.WindowModal); self.progress.show()
        self.worker = ImportWorker(path,self.ocr.isChecked())
        self.worker.result.connect(lambda chunks,warnings:self.imported(protocol,chunks,warnings))
        self.worker.failed.connect(self.error)
        self.worker.finished.connect(self.import_finished)
        self.worker.start()

    def imported(self,protocol,chunks,warnings):
        if protocol: extract_protocol(self.project,chunks)
        else: extract_offers(self.project,chunks)
        self.project.warnings.extend(warnings); self.load_fields(); self.dirty = True

    def import_finished(self):
        self.busy = False; self.progress.close(); self.centralWidget().setEnabled(True); self.toolbar.setEnabled(True)
        self.statusBar().showMessage('Imports pabeigts. Pārbaudiet laukus, avotus un brīdinājumus.')

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
