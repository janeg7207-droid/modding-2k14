import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from mod_formatter import analyze, package
from source_library import SourceLibrary


class SourceLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(Path(__file__).resolve().parents[1] / 'mod_catalog.json', self.root)
        self.library = SourceLibrary(self.root)
        self.identity = 'jeff_hardy_26_a0'
        self.source = self.root / 'jeff_hardy_26_A0.rar'
        self.source.write_bytes(b'RAR source fixture, not a real game mod')

    def test_catalog_does_not_claim_bundled_archive(self):
        self.assertEqual(self.library.entries()[0]['name'], 'Jeff Hardy 26 A0')
        self.assertIsNone(self.library.archive(self.identity))

    def test_attachment_survives_restart_and_original_removal(self):
        payload = self.source.read_bytes()
        kept = self.library.attach(self.identity, self.source)
        self.assertEqual(self.source.read_bytes(), payload)
        self.source.unlink()
        restarted = SourceLibrary(self.root)
        self.assertEqual(restarted.archive(self.identity), kept)
        self.assertEqual(kept.read_bytes(), payload)
        record = json.loads(self.library.index.read_text())[self.identity]
        self.assertEqual(record['sha256'], hashlib.sha256(payload).hexdigest())
        self.assertEqual(record['conversion_status'], 'not_converted')

    def test_repeated_attach_and_changed_versions_preserved(self):
        first = self.library.attach(self.identity, self.source)
        self.assertEqual(first, self.library.attach(self.identity, self.source))
        payload = first.read_bytes()
        self.source.write_bytes(b'changed source fixture')
        second = self.library.attach(self.identity, self.source)
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), payload)
        self.assertEqual(self.library.archive(self.identity), second)

    def test_large_local_attachment_is_streamed(self):
        with self.source.open('wb') as stream:
            stream.truncate(33 * 1024 * 1024)
        kept = self.library.attach(self.identity, self.source)
        self.assertEqual(kept.stat().st_size, 33 * 1024 * 1024)

    def test_rar_report_explicitly_does_not_inspect_contents(self):
        report = analyze(self.source)
        self.assertEqual(report['file_count'], 1)
        self.assertIn('contents not inspected', report['files'][0]['assessment'])

    def test_source_archive_cannot_enter_export(self):
        original = self.root / 'game/pac/source.rar'
        original.parent.mkdir(parents=True)
        original.write_bytes(b'fixture')
        with self.assertRaises(ValueError):
            package(self.root / 'game', [(self.source, 'pac/source.rar')], self.root / 'export.zip', True)

    def test_invalid_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.library.attach('../outside', self.source)

    def test_tampered_local_copy_is_preserved_and_reported(self):
        kept = self.library.attach(self.identity, self.source)
        kept.write_bytes(b'locally changed')
        with self.assertRaisesRegex(ValueError, 'has changed'):
            self.library.attach(self.identity, self.source)
        self.assertEqual(kept.read_bytes(), b'locally changed')

    def test_inventory_only_used_for_matching_archive(self):
        details = self.root / 'source_details'
        details.mkdir()
        report = dict(source_sha256=hashlib.sha256(self.source.read_bytes()).hexdigest(),
                      files=[dict(path='model.mcd')], status='Not converted')
        (details / 'jeff_hardy_26_a0.json').write_text(json.dumps(report))
        kept = self.library.attach(self.identity, self.source)
        self.assertEqual(self.library.inventory(self.identity), report)
        kept.write_bytes(b'different archive contents')
        self.assertIsNone(self.library.inventory(self.identity))


if __name__ == '__main__':
    unittest.main()
