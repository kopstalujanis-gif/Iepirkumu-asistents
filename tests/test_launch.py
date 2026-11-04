import json
import os
from pathlib import Path
import subprocess
import sys


def test_entry_point_checks_runtime_from_another_directory(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    report = tmp_path / 'report.json'
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONPATH=str(repo))
    result = subprocess.run([sys.executable, '-m', 'iepirkumi', '--smoke-test', str(report)],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['status'] == 'passed'
    assert 'bundled_template' in data['checks'] and 'qt_window' in data['checks']
    assert not list(tmp_path.glob('*.sqlite3'))
