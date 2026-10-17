import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from modern_ui import source_summary, inspect_source
from mod_formatter import analyze
from source_library import SourceLibrary


class SourceFlowTests(unittest.TestCase):
    def test_model_source_requires_conversion(self):
        result = source_summary(dict(files=[dict(path='body.mcd'), dict(path='attire.dds')]))
        self.assertEqual(result['title'], 'Conversion required')
        self.assertEqual((result['models'], result['textures']), (1, 1))
        self.assertFalse(result['export_ready'])

    def test_pac_extension_does_not_enable_port(self):
        result = source_summary(dict(files=[dict(path='pac/ch/ch123.pac')]))
        self.assertFalse(result['export_ready'])
        self.assertIn('2K14-ready', result['message'])

    def test_cak_requires_extractor(self):
        result = source_summary(dict(files=[dict(path='wrestler.cak')]))
        self.assertFalse(result['export_ready'])
        self.assertIn('extraction', result['message'])

    def test_selected_original_archive_uses_matching_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'mod_catalog.json').write_text(json.dumps([dict(
                id='jeff_hardy_26_a0', name='Jeff Hardy', inventory='inventory.json')]))
            original = root / 'original.rar'
            original.write_bytes(b'synthetic RAR fixture')
            report = dict(source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                          files=[dict(path='body.mcd')], status='Not converted')
            (root / 'inventory.json').write_text(json.dumps(report))
            library = SourceLibrary(root)
            retained = library.attach('jeff_hardy_26_a0', original)
            self.assertEqual(inspect_source(original, library, analyze), report)
            self.assertEqual(inspect_source(retained, library, analyze), report)
            original.write_bytes(b'different source fixture')
            other = inspect_source(original, library, analyze)
            self.assertIn('contents not inspected', other['files'][0]['assessment'])
            self.assertNotEqual(other, report)


if __name__ == '__main__':
    unittest.main()
