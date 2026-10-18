import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from game_support import game_layout, rpcs3_command, launch_ps3
from mod_formatter import package, validate


class Ps3SupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.disc = self.root / 'WWE 2K14 PS3'
        self.usrdir = self.disc / 'PS3_GAME/USRDIR'
        self.original = self.usrdir / 'pac/ch/ch123.pac'
        self.original.parent.mkdir(parents=True)
        self.original.write_bytes(b'original PS3 PAC fixture')
        self.boot = self.usrdir / 'EBOOT.BIN'
        self.boot.write_bytes(b'SCE\x00PS3 SELF fixture')
        self.replacement = self.root / 'converted.pac'
        self.replacement.write_bytes(b'PS3 replacement fixture; not a real game PAC')
        self.exe = self.root / 'RPCS3 folder/rpcs3.exe'
        self.exe.parent.mkdir()
        self.exe.write_bytes(b'fake emulator; NEVER executed')

    def test_normalizes_all_three_ps3_folder_levels(self):
        for root in (self.disc, self.disc / 'PS3_GAME', self.usrdir):
            with self.subTest(root=root):
                layout = game_layout(root)
                self.assertEqual(layout.platform, 'ps3')
                self.assertEqual(layout.asset_root, self.usrdir)
                self.assertEqual(layout.game_root, self.disc)
                self.assertEqual(layout.boot_file, self.boot)

    def test_xbox_mode_refuses_ps3_reference(self):
        with self.assertRaisesRegex(ValueError, 'Select PS3'):
            validate(self.disc, self.replacement, 'pac/ch/ch123.pac')

    def test_missing_ps3_boot_has_actionable_error(self):
        self.boot.unlink()
        with self.assertRaisesRegex(ValueError, 'No EBOOT.BIN'):
            game_layout(self.disc, 'ps3')

    def test_pc_layout_detects_xex(self):
        root = self.root / 'Xbox game'
        root.mkdir()
        (root / 'default.xex').write_bytes(b'XEX fixture')
        self.assertEqual(game_layout(root).platform, 'xbox360')

    def test_ps3_export_layout_and_report(self):
        output = self.root / 'PS3_mod.zip'
        report_path = package(self.disc, [(self.replacement, 'pac/ch/ch123.pac')], output, True, 'ps3')
        report = json.loads(report_path.read_text())
        self.assertEqual(report['target_platform'], 'ps3')
        self.assertEqual(report['installation']['relative_to'], 'PS3_GAME/USRDIR')
        self.assertEqual(report['binary_compatibility']['status'], 'not_tested')
        self.assertEqual(report['in_game']['status'], 'not_tested')
        self.assertEqual(report['in_game']['checks']['rpcs3_boot'], 'not_tested')
        self.assertNotIn('launcher_import', report['in_game']['checks'])
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.namelist(), ['pac/ch/ch123.pac'])
            self.assertEqual(archive.read('pac/ch/ch123.pac'), self.replacement.read_bytes())
        self.assertEqual(self.original.read_bytes(), b'original PS3 PAC fixture')

    def test_ps3_catalog_replacement_requires_original(self):
        catalog = self.usrdir / 'plistps3.arc'
        catalog.write_bytes(b'original catalog fixture')
        replacement = self.root / 'updated.arc'
        replacement.write_bytes(b'rebuilt catalog fixture')
        self.assertEqual(validate(self.disc, replacement, 'plistps3.arc', 'ps3')[1], 'plistps3.arc')
        with self.assertRaises(FileNotFoundError):
            validate(self.disc, replacement, 'missing.arc', 'ps3')

    def test_ps3_output_cannot_write_anywhere_inside_original_disc(self):
        with self.assertRaises(ValueError):
            package(self.usrdir, [(self.replacement, 'pac/ch/ch123.pac')], self.disc / 'bad.zip', True, 'ps3')

    def test_rpcs3_command_preserves_spaces_as_separate_arguments(self):
        self.assertEqual(rpcs3_command(self.disc, self.exe), [str(self.exe), str(self.boot)])

    def test_ps3_launch_dispatch_only_no_real_emulator_started(self):
        with patch('game_support.subprocess.Popen') as popen:
            process = launch_ps3(self.disc, self.exe)
            popen.assert_called_once_with([str(self.exe), str(self.boot)], cwd=str(self.exe.parent), shell=False)
            self.assertIs(process, popen.return_value)

    def test_native_pc_launcher_is_not_a_ps3_runtime(self):
        native = self.exe.parent / 'WWE 2K14 PC.exe'
        native.write_bytes(b'fake native executable')
        with self.assertRaisesRegex(ValueError, 'installed rpcs3'):
            rpcs3_command(self.disc, native)

    def test_invalid_eboot_is_not_launched(self):
        self.boot.write_bytes(b'MZinvalid executable')
        with patch('game_support.subprocess.Popen') as popen:
            with self.assertRaisesRegex(ValueError, 'SELF/ELF'):
                launch_ps3(self.disc, self.exe)
            popen.assert_not_called()

    def test_external_ps3_asset_symlink_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'EBOOT.BIN').write_bytes(b'SCE\x00fixture')
        fake = self.root / 'linked game'
        (fake / 'PS3_GAME').mkdir(parents=True)
        (fake / 'PS3_GAME/USRDIR').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            game_layout(fake, 'ps3')


if __name__ == '__main__':
    unittest.main()
