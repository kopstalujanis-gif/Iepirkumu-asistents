"""Local SQLite registries and remembered selections; no external services."""
import json
import sqlite3
from pathlib import Path
import os
import tempfile
from .models import Procurement


def data_dir():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share'))
    p = Path(os.environ['IEPIRKUMI_DATA_DIR']) if os.environ.get('IEPIRKUMI_DATA_DIR') else base / 'IepirkumuAsistents'
    p.mkdir(parents=True, exist_ok=True)
    return p


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / 'registri.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')

    def records(self, kind):
        return [(i, json.loads(p)) for i, p in self.db.execute('SELECT id,payload FROM records WHERE kind=? ORDER BY id', (kind,))]

    def save_record(self, kind, payload, record_id=None):
        text = json.dumps(payload, ensure_ascii=False)
        with self.db:
            if record_id is None:
                return self.db.execute('INSERT INTO records(kind,payload) VALUES (?,?)', (kind,text)).lastrowid
            self.db.execute('UPDATE records SET payload=? WHERE id=? AND kind=?', (text,record_id,kind))
        return record_id

    def delete_record(self, record_id):
        with self.db:
            self.db.execute('DELETE FROM records WHERE id=?', (record_id,))

    def setting(self, key, default=''):
        row = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key,str(value)))

    def backup(self, path):
        with sqlite3.connect(path) as target:
            self.db.backup(target)

    def erase(self):
        self.db.execute('PRAGMA secure_delete=ON')
        with self.db:
            self.db.execute('DELETE FROM records')
            self.db.execute('DELETE FROM settings')
        self.db.execute('VACUUM')

    def close(self):
        self.db.close()


def save_project(p, path):
    path = Path(path)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.iepirkums-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(p.to_json())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def load_project(path):
    return Procurement.from_json(Path(path).read_text(encoding='utf-8'))
