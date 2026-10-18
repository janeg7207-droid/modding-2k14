"""Exercise both desktop modes with synthetic assets. Never runs a real emulator.

Run on a desktop: python tools/check_desktop.py
On Linux a DISPLAY (for example Xvfb) is required. No third-party Python packages.
"""
from pathlib import Path
import json
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import tkinter as tk
from tkinter import filedialog as fd, messagebox as mb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mod_formatter import gui
from source_library import SourceLibrary


def check_mode(mode):
    errors, checks = [], []
    library = SourceLibrary(Path(__file__).resolve().parents[1])
    source = library.archive('jeff_hardy_26_a0')
    if source is None:
        raise RuntimeError('Use a complete formatter checkout containing the Jeff Hardy source')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        game = root / 'Game with spaces'
        usrdir = game / 'PS3_GAME/USRDIR' if mode == 'ps3' else game
        original = usrdir / 'pac/ch/ch123.pac'
        original.parent.mkdir(parents=True)
        original.write_bytes(b'original synthetic reference')
        (usrdir / ('EBOOT.BIN' if mode == 'ps3' else 'default.xex')).write_bytes(
            b'SCE\x00fixture' if mode == 'ps3' else b'XEX fixture')
        replacement = root / 'converted.pac'
        replacement.write_bytes(b'replacement fixture; NOT a real game PAC')
        exe = root / 'RPCS3 with spaces/rpcs3.exe'
        exe.parent.mkdir()
        exe.write_bytes(b'fake executable; never run')
        output = root / 'Mod.zip'
        selections = [str(source)] + ([str(exe)] if mode == 'ps3' else []) + [str(replacement), str(original)]
        selections = iter(selections)
        original_tk = tk.Tk

        class CheckedTk(original_tk):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.after(100, self.start)
                self.after(20000, lambda: self.fail('Desktop smoke check timed out'))

            def fail(self, error):
                errors.append(str(error))
                self.destroy()

            def report_callback_exception(self, kind, error, tb):
                self.fail(error)

            def widgets(self, parent=None):
                result = []
                for child in (parent or self).winfo_children():
                    result.append(child)
                    result.extend(self.widgets(child))
                return result

            def control(self, prefix):
                return next(w for w in self.widgets() if w.winfo_class() in ('Button', 'TCheckbutton')
                            and str(w.cget('text')).startswith(prefix))

            def has_label(self, text):
                return any(w.winfo_class() == 'Label' and w.cget('text') == text for w in self.widgets())

            def start(self):
                assert str(self.control('Export 2K14').cget('state')) == 'disabled'
                self.control('Choose 2K26 file').invoke()
                self.after(50, self.loaded)

            def loaded(self):
                if not self.has_label('Conversion required'):
                    self.after(50, self.loaded)
                    return
                assert self.has_label('58 files   /   2 models   /   32 textures')
                assert str(self.control('Export 2K14').cget('state')) == 'disabled'
                checks.append('Automatic source inspection; unconverted export blocked')
                if mode == 'ps3':
                    self.control('Choose PS3 game').invoke()
                    self.control('Choose RPCS3').invoke()
                    self.control('Play in RPCS3').invoke()
                    self.after(50, self.emulator_started)
                else:
                    self.prepare_export()

            def emulator_started(self):
                if not self.has_label('RPCS3 started'):
                    self.after(50, self.emulator_started)
                    return
                mocked_popen.assert_called_once_with(
                    [str(exe), str(usrdir / 'EBOOT.BIN')], cwd=str(exe.parent), shell=False)
                checks.append('PS3 game selected and RPCS3 dispatch verified (mocked, no boot)')
                self.prepare_export()

            def prepare_export(self):
                self.control('I have converted assets').invoke()
                if mode == 'xbox360':
                    self.control('Choose 2K14 reference').invoke()
                self.control('Add converted asset').invoke()
                self.control('These assets were rebuilt').invoke()
                assert str(self.control('Export 2K14').cget('state')) == 'normal'
                self.control('Export 2K14').invoke()
                self.after(50, self.exported)

            def exported(self):
                if not self.has_label('Package + test JSON saved'):
                    self.after(50, self.exported)
                    return
                report = json.loads(output.with_suffix('.test.json').read_text())
                assert output.is_file()
                assert report['target_platform'] == mode
                assert report['packaging']['status'] == 'passed'
                assert report['in_game']['status'] == 'not_tested'
                assert original.read_bytes() == b'original synthetic reference'
                checks.append('ZIP + platform-specific JSON exported; original preserved')
                self.destroy()

        def unexpected_dialog(title, text):
            raise AssertionError(f'{title}: {text}')

        with patch.object(tk, 'Tk', CheckedTk), \
                patch.object(fd, 'askopenfilename', side_effect=lambda **kw: next(selections)), \
                patch.object(fd, 'askdirectory', return_value=str(game)), \
                patch.object(fd, 'asksaveasfilename', return_value=str(output)), \
                patch.object(mb, 'showerror', side_effect=unexpected_dialog), \
                patch.object(mb, 'showinfo', side_effect=unexpected_dialog), \
                patch('game_support.subprocess.Popen', return_value=SimpleNamespace(pid=123)) as mocked_popen:
            gui(mode)
        assert not errors, errors
        assert len(checks) == (3 if mode == 'ps3' else 2), checks
        print(mode + ': ' + '; '.join(checks))


if __name__ == '__main__':
    check_mode('xbox360')
    check_mode('ps3')
    print('Desktop checks passed. Real RPCS3 gameplay and asset compatibility are NOT tested.')
