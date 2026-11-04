from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QListWidget,QListWidgetItem,QLineEdit,
                              QCheckBox,QPushButton,QFileDialog,QMessageBox,QFormLayout)
from . import ai
from .importer import Chunk


class AIDialog(QDialog):
    def __init__(self,project,parent=None,session_key=''):
        super().__init__(parent);self.setWindowTitle('Izvēles MI analīze — OpenAI API');self.resize(760,650)
        self.project=project;self.pdf=None;self.job=None
        layout=QVBoxLayout(self)
        intro=QLabel('Pēc jūsu apstiprinājuma izvēlēto avotu teksts un izvēlētais PDF (ar lapu attēliem) tiks nosūtīts OpenAI API. '
                     'API lietošana ir maksas pakalpojums atsevišķi no ChatGPT abonementa. '
                     'Netiek sūtīti reģistri vai viss iepirkuma projekts. MI rezultāti būs neapstiprināti.');intro.setWordWrap(True);layout.addWidget(intro)
        self.sources={}
        for entry in project.imports:
            self.sources.setdefault(entry['source'],[]).append(Chunk(**{k:entry[k] for k in ('source','location','text','quality')}))
        self.listing=QListWidget();layout.addWidget(self.listing)
        registration=project.fields['registration'].value
        for name,chunks in self.sources.items():
            text='\n'.join(c.text for c in chunks)
            item=QListWidgetItem(f'{name} — {len(text):,} rakstzīmes');item.setData(Qt.UserRole,name)
            item.setFlags(item.flags()|Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if ('Slēgt līgumu ar' in text or (registration and registration in text)) else Qt.Unchecked)
            self.listing.addItem(item)
        self.pdf_label=QLabel('Vizuāls PDF nav izvēlēts. Teksta analīzei tas nav obligāts.');self.pdf_label.setWordWrap(True)
        layout.addWidget(self.pdf_label)
        pdf_button=QPushButton('Pievienot PDF arī vizuālai nolasīšanai (skenējumi, sarežģītas tabulas)')
        pdf_button.clicked.connect(self.choose_pdf);layout.addWidget(pdf_button)
        form=QFormLayout();self.key=QLineEdit(session_key or ai.read_key());self.key.setEchoMode(QLineEdit.Password)
        form.addRow('API atslēga',self.key)
        self.model=QLineEdit(ai.DEFAULT_MODEL);form.addRow('Modelis',self.model);layout.addLayout(form)
        self.remember=QCheckBox('Saglabāt atslēgu Windows Credential Manager (nevis projekta failā)');layout.addWidget(self.remember)
        delete=QPushButton('Dzēst saglabāto API atslēgu');delete.clicked.connect(self.delete_key);layout.addWidget(delete)
        self.agree=QCheckBox('Piekrītu atlasīto dokumentu nosūtīšanai OpenAI API šajā pieprasījumā.');layout.addWidget(self.agree)
        send=QPushButton('Pārskatīt un sūtīt OpenAI API');send.clicked.connect(self.prepare_send);layout.addWidget(send)
        layout.addWidget(QLabel('Līdz 120 000 rakstzīmēm, 12 MB / 40 PDF lappusēm un 6000 atbildes tokeniem. Automātisku atkārtojumu nav.'))

    def choose_pdf(self):
        path,_=QFileDialog.getOpenFileName(self,'Izvēlēties PDF nosūtīšanai API','','PDF (*.pdf)')
        if path:self.pdf=path;self.pdf_label.setText('OpenAI API tiks nosūtīts pilns PDF: '+Path(path).name)

    def delete_key(self):
        try:
            ai.save_key('');self.key.clear()
            if self.parent() is not None:self.parent().session_api_key=''
            QMessageBox.information(self,'API atslēga','Atslēga dzēsta no Windows glabātuves. Vides mainīgos norādītas atslēgas pārvaldiet vides iestatījumos.')
        except Exception as e:QMessageBox.warning(self,'Atslēgas dzēšana',str(e))

    def prepare_send(self):
        if not self.agree.isChecked():return QMessageBox.warning(self,'Piekrišana','Atzīmējiet piekrišanu šim pieprasījumam.')
        if not self.key.text().strip():return QMessageBox.warning(self,'API atslēga','Ievadiet OpenAI API atslēgu šajā logā. Nesūtiet atslēgu tērzēšanā.')
        chunks=[]
        for i in range(self.listing.count()):
            item=self.listing.item(i)
            if item.checkState()==Qt.Checked:chunks+=self.sources[item.data(Qt.UserRole)]
        try:
            job=ai.prepare(chunks,self.project.fields['registration'].value,self.pdf)
            model=self.model.text().strip()
            if not model or len(model)>100 or any(c.isspace() for c in model):raise ValueError('Nederīgs modeļa nosaukums.')
            job['payload']['model']=model
            message=('Saņēmējs: OpenAI API (api.openai.com)\nModelis: '+model+
                     f"\nTeksts: {job['characters']:,} rakstzīmes\nVizuālais PDF: {job['pages']} lappuses\nAtbildes limits: 6000 tokeni\n\n"+
                     '\n'.join(job['files'])+'\n\nPDF attēli palielina ievades izmaksas. Precīza cena atkarīga no modeļa un apjoma; tokenu limits nav naudas budžets. Sūtīt?')
            if QMessageBox.question(self,'Apstiprināt ārējo API pieprasījumu',message,QMessageBox.Yes|QMessageBox.Cancel)!=QMessageBox.Yes:return
            if self.remember.isChecked():ai.save_key(self.key.text().strip())
            self.job=job;self.api_key=self.key.text().strip();self.accept()
        except Exception as e:QMessageBox.warning(self,'MI analīze',str(e))


class AIWorker(QThread):
    result=Signal(object,object)
    failed=Signal(str)
    def __init__(self,job,key):
        super().__init__();self.job=job;self.key=key
    def run(self):
        try:
            entries,usage=ai.request(self.job,self.key,consent=True)
            self.result.emit(entries,usage)
        except Exception as e:self.failed.emit(str(e))
        finally:self.key=''
