import subprocess
import sys

from thermalmaster_p3.cli import main
from thermalmaster_p3.recording import SessionWriter


def test_core_import_does_not_load_viewer():
    subprocess.run([sys.executable, '-c', "import sys; import thermalmaster_p3; assert 'cv2' not in sys.modules"], check=True)


def test_empty_replay(tmp_path, capsys):
    with SessionWriter(tmp_path / 'session'):
        pass
    assert main(['replay', str(tmp_path / 'session')]) == 0
    assert '"frames": 0' in capsys.readouterr().out


def test_invalid_replay_path(tmp_path, capsys):
    assert main(['replay', str(tmp_path / 'absent')]) == 1
    assert 'p3:' in capsys.readouterr().err
