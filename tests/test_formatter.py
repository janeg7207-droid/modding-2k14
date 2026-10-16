import tempfile
import unittest
import zipfile
from pathlib import Path
from mod_formatter import analyze, package


class FormatterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.game = self.base / 'game'
        self.original = self.game / 'pac/ch/ch123.pac'
        self.original.parent.mkdir(parents=True)
        self.original.write_bytes(b'original fixture')
        self.converted = self.base / 'converted.pac'
        self.converted.write_bytes(b'replacement fixture; NOT a real game PAC')
        self.output = self.base / 'export.zip'

    def pack(self, target='pac/ch/ch123.pac', source=None, confirmed=True):
        package(self.game, [(source or self.converted, target)], self.output, confirmed)

    def test_export_exact_path_and_preserve_original(self):
        self.pack()
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), ['pac/ch/ch123.pac'])
            self.assertEqual(archive.read('pac/ch/ch123.pac'), self.converted.read_bytes())
            self.assertIsNone(archive.testzip())
        self.assertEqual(self.original.read_bytes(), b'original fixture')

    def test_reject_unconfirmed(self):
        with self.assertRaises(ValueError):
            self.pack(confirmed=False)
        self.assertFalse(self.output.exists())

    def test_reject_traversal(self):
        with self.assertRaises(ValueError):
            self.pack('../outside.pac')

    def test_reject_missing_target(self):
        with self.assertRaises(FileNotFoundError):
            self.pack('pac/ch/missing.pac')

    def test_reject_2k26_package(self):
        source = self.base / 'character.cak'
        source.write_bytes(b'source package fixture')
        with self.assertRaises(ValueError):
            self.pack(source=source)

    def test_reject_duplicate_targets(self):
        with self.assertRaises(ValueError):
            package(self.game, [(self.converted, 'pac/ch/ch123.pac')] * 2, self.output, True)

    def test_preserve_existing_export(self):
        self.output.write_bytes(b'existing package')
        with self.assertRaises(FileExistsError):
            self.pack()
        self.assertEqual(self.output.read_bytes(), b'existing package')

    def test_reject_game_output(self):
        with self.assertRaises(ValueError):
            package(self.game, [(self.converted, 'pac/ch/ch123.pac')], self.game / 'bad.zip', True)

    def test_reject_zip_traversal(self):
        source = self.base / 'unsafe.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            archive.writestr('../unsafe.cak', b'fixture')
        with self.assertRaises(ValueError):
            analyze(source)

    def test_source_report_does_not_claim_conversion(self):
        source = self.base / 'mod.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            archive.writestr('character.cak', b'fixture')
            archive.writestr('textures/attire.dds', b'fixture')
        report = analyze(source)
        self.assertEqual(report['file_count'], 2)
        self.assertIn('manual asset conversion', report['files'][0]['assessment'])
        self.assertIn('no conversion', report['status'])


if __name__ == '__main__':
    unittest.main()
