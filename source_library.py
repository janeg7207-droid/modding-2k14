"""Persistent, local source archives; these are never treated as converted assets."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


class SourceLibrary:
    def __init__(self, app_root):
        self.root = Path(app_root)
        self.storage = self.root / 'source_library'
        self.index = self.storage / 'library.json'

    def _saved(self):
        if not self.index.exists():
            return {}
        return json.loads(self.index.read_text(encoding='utf-8'))

    def entries(self):
        return json.loads((self.root / 'mod_catalog.json').read_text(encoding='utf-8'))

    def _identity(self, identity):
        if not re.fullmatch(r'[a-z0-9_-]+', identity):
            raise ValueError('Invalid source library ID')
        if not any(item['id'] == identity for item in self.entries()):
            raise ValueError('Unknown source mod')
        return identity

    def archive(self, identity):
        self._identity(identity)
        record = self._saved().get(identity)
        if not record:
            return None
        filename = record['file']
        if Path(filename).name != filename or '/' in filename or '\\' in filename:
            raise ValueError('Invalid source library record')
        path = self.storage / filename
        if path.is_symlink():
            raise ValueError('Source archive symlinks are unsupported')
        return path if path.is_file() else None

    def attach(self, identity, source):
        self._identity(identity)
        source = Path(source).resolve(strict=True)
        suffix = source.suffix.lower()
        if suffix not in {'.rar', '.7z', '.zip', '.cak', '.gorillamod'} or not source.is_file():
            raise ValueError('Choose a RAR, 7z, ZIP, CAK, or Gorilla source archive')
        if source.stat().st_size == 0:
            raise ValueError('Source archive is empty')
        self.storage.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        # Stream large archives; do not extract, execute, or load them into memory.
        with tempfile.NamedTemporaryFile(dir=self.storage, delete=False) as stream:
            temp = Path(stream.name)
            try:
                with source.open('rb') as original:
                    while chunk := original.read(1024 * 1024):
                        digest.update(chunk)
                        stream.write(chunk)
            except Exception:
                stream.close()
                temp.unlink(missing_ok=True)
                raise
        try:
            checksum = digest.hexdigest()
            filename = identity + '-' + checksum + suffix
            target = self.storage / filename
            if target.exists():
                # Do not replace a retained archive, including on repeated attachment.
                if target.is_symlink():
                    raise ValueError('Source archive symlinks are unsupported')
                existing = hashlib.sha256()
                with target.open('rb') as original:
                    while chunk := original.read(1024 * 1024):
                        existing.update(chunk)
                if existing.hexdigest() != checksum:
                    raise ValueError('Stored source copy has changed; preserve it and investigate before reattaching')
            else:
                os.replace(temp, target)
            saved = self._saved()
            saved[identity] = dict(file=filename, original_filename=source.name,
                                   sha256=checksum, bytes=source.stat().st_size,
                                   conversion_status='not_converted')
            with tempfile.NamedTemporaryFile(mode='w', dir=self.storage, encoding='utf-8', delete=False) as stream:
                index_temp = Path(stream.name)
                try:
                    json.dump(saved, stream, indent=2)
                    stream.close()
                    os.replace(index_temp, self.index)
                finally:
                    index_temp.unlink(missing_ok=True)
            return target
        finally:
            temp.unlink(missing_ok=True)

    def inventory(self, identity):
        """Return the included inspection only if it matches the actual retained bytes."""
        source = self.archive(identity)
        if source is None:
            return None
        entry = next(item for item in self.entries() if item['id'] == identity)
        if not entry.get('inventory'):
            return None
        path = (self.root / entry['inventory']).resolve(strict=True)
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError('Inventory path is outside this formatter')
        report = json.loads(path.read_text(encoding='utf-8'))
        digest = hashlib.sha256()
        with source.open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return report if report['source_sha256'] == digest.hexdigest() else None
