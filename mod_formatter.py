"""WWE 2K14 Mod Formatter: analysis and packaging, not binary conversion."""
from pathlib import Path, PurePosixPath
import argparse
import json
import zipfile
import hashlib
from datetime import datetime, timezone
from source_library import SourceLibrary

BLOCKED = {'.cak', '.gorillamod', '.rar', '.7z', '.zip', '.exe', '.dll', '.ps1', '.bat', '.py'}
LIMIT = 2 * 1024**3


def safe_path(name):
    path = PurePosixPath(name.replace('\\', '/'))
    if path.is_absolute() or '..' in path.parts or ':' in name or not path.parts:
        raise ValueError('Unsafe path: ' + name)
    return path


def assessment(name):
    ext = PurePosixPath(name).suffix.lower()
    if ext in {'.cak', '.gorillamod'}:
        return '2K26 package: requires a compatible extractor and manual asset conversion'
    if ext == '.rar':
        return 'RAR source archive: contents not inspected; extract locally with 7-Zip, then analyze the extracted folder'
    if ext == '.7z':
        return '7z source archive: extract locally with 7-Zip, then analyze the extracted folder'
    if ext in {'.mcd', '.mtls', '.jmtl', '.ycl'}:
        return '2K26 model/material data: requires format-specific tools and a 2K14 asset rebuild'
    if ext == '.pac':
        return 'PAC container: must be rebuilt for 2K14; extension does not prove compatibility'
    if ext in {'.dds', '.png', '.tga', '.jpg', '.bmp'}:
        return 'Texture candidate: adapt to target texture format and import into a 2K14 PAC'
    if ext in {'.fbx', '.obj', '.blend'}:
        return 'Model source: adapt skeleton, weights, geometry and materials; rebuild as 2K14 PAC'
    return 'Unknown compatibility: manual investigation required'


def analyze(source):
    source = Path(source).resolve(strict=True)
    records, total = [], 0

    def add(name, size):
        nonlocal total
        safe_path(name)
        total += size
        if len(records) >= 20000 or total > LIMIT:
            raise ValueError('Input exceeds 20,000 files or 2 GiB; analyze a smaller mod')
        records.append(dict(path=name, bytes=size, assessment=assessment(name)))

    if source.is_dir():
        for item in sorted(source.rglob('*')):
            if item.is_symlink():
                raise ValueError('Symlinks are unsupported')
            if item.is_file():
                add(item.relative_to(source).as_posix(), item.stat().st_size)
    elif source.suffix.lower() == '.zip':
        with zipfile.ZipFile(source) as archive:
            for entry in archive.infolist():
                safe_path(entry.filename)
                if entry.flag_bits & 1 or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Encrypted entries and symlinks are unsupported')
                if not entry.is_dir():
                    add(entry.filename, entry.file_size)
    else:
        add(source.name, source.stat().st_size)
    return dict(source=source.name, status='Analysis only: no conversion or in-game validation performed',
                file_count=len(records), total_bytes=total, files=records)


def validate(game_root, replacement, target):
    root = Path(game_root).resolve(strict=True)
    relative = safe_path(target)
    if relative.parts[0].lower() not in {'pac', 'movies', 'sound'}:
        raise ValueError('Target must be under pac/, movies/ or sound/')
    original = root.joinpath(*relative.parts).resolve(strict=True)
    if not original.is_relative_to(root) or not original.is_file():
        raise ValueError('Target must be an original file within the selected 2K14 folder')
    replacement = Path(replacement).resolve(strict=True)
    if not replacement.is_file() or replacement.stat().st_size == 0:
        raise ValueError('Replacement must be a nonempty file')
    if replacement.suffix.lower() in BLOCKED:
        raise ValueError('Cannot export 2K26 packages or executable files as 2K14 assets')
    if replacement.suffix.lower() != original.suffix.lower():
        raise ValueError('Replacement must match original extension; renaming is not conversion')
    with replacement.open('rb') as stream:
        if stream.read(2) == b'MZ':
            raise ValueError('Executable content is not a game asset')
    return replacement, relative.as_posix()


def package(game_root, assets, output, confirmed=False):
    if not confirmed or not assets:
        raise ValueError('Add assets and confirm they were rebuilt for WWE 2K14 Xbox 360')
    checked = [validate(game_root, source, target) for source, target in assets]
    names = [target.casefold() for _, target in checked]
    if len(names) != len(set(names)):
        raise ValueError('Multiple replacements target the same game file')
    if sum(source.stat().st_size for source, _ in checked) > LIMIT:
        raise ValueError('Export exceeds 2 GiB')
    output = Path(output).resolve()
    if output.suffix.lower() != '.zip':
        raise ValueError('Output must end in .zip')
    if output.is_relative_to(Path(game_root).resolve()):
        raise ValueError('Save outside your original game folder')
    report_path = output.with_suffix('.test.json')
    if report_path.exists():
        raise FileExistsError(f'Test report already exists: {report_path.name}; choose a new export name')
    expected = {}
    for source, target in checked:
        digest = hashlib.sha256()
        with source.open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        expected[target] = digest.hexdigest()
    report_created = False
    # Exclusive creation preserves existing packages and original game data.
    with output.open('x+b') as stream:
        try:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for source, target in checked:
                    archive.write(source, target)
            stream.flush()
            stream.seek(0)
            exported = []
            with zipfile.ZipFile(stream, 'r') as archive:
                if archive.namelist() != [target for _, target in checked]:
                    raise ValueError('Exported archive paths do not match selected assets')
                for source, target in checked:
                    digest = hashlib.sha256()
                    with archive.open(target) as asset:
                        while chunk := asset.read(1024 * 1024):
                            digest.update(chunk)
                    if digest.hexdigest() != expected[target]:
                        raise ValueError(f'Exported bytes differ from selected asset: {target}')
                    exported.append(dict(target=target, source_filename=source.name,
                                         bytes=archive.getinfo(target).file_size,
                                         sha256=digest.hexdigest(), readback='passed'))
            stream.seek(0)
            digest = hashlib.sha256()
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
            report = dict(
                schema_version=1,
                generated_at=datetime.now(timezone.utc).isoformat(),
                tool='WWE 2K14 Mod Formatter',
                package=dict(filename=output.name, sha256=digest.hexdigest(), file_count=len(exported)),
                conversion=dict(status='user_declared', verified_by_tool=False),
                packaging=dict(status='passed', checks={
                    'original_targets_exist': 'passed', 'matching_extensions': 'passed',
                    'unique_safe_paths': 'passed', 'archive_readback_crc_and_sha256': 'passed'}),
                binary_compatibility=dict(status='not_tested'),
                in_game=dict(status='not_tested', checks={
                    name: 'not_tested' for name in ['launcher_import', 'wrestler_select', 'entrance',
                                                   'attire_and_textures', 'match_gameplay', 'victory']},
                    notes='Test the port in WWE 2K14 and record observations here. Packaging does not validate a port.'),
                files=exported,
            )
            with report_path.open('x', encoding='utf-8') as report_stream:
                report_created = True
                json.dump(report, report_stream, indent=2)
                report_stream.write('\n')
        except Exception:
            stream.close()
            output.unlink()
            if report_created:
                report_path.unlink(missing_ok=True)
            raise
    return report_path


def gui():
    from modern_ui import launch
    launch(analyze, package, validate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command')
    scan = sub.add_parser('analyze')
    scan.add_argument('source', type=Path)
    scan.add_argument('--report', type=Path)
    pack = sub.add_parser('pack')
    pack.add_argument('--game-root', type=Path, required=True)
    pack.add_argument('--asset', action='append', required=True, metavar='CONVERTED_FILE=GAME_PATH')
    pack.add_argument('--output', type=Path, required=True)
    pack.add_argument('--confirm-2k14', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'analyze':
            result = json.dumps(analyze(args.source), indent=2)
            if args.report:
                args.report.write_text(result + '\n', encoding='utf-8')
            else:
                print(result)
        elif args.command == 'pack':
            assets = []
            for value in args.asset:
                source, sep, target = value.rpartition('=')
                if not sep:
                    raise ValueError('Use --asset converted-file=original/game/path')
                assets.append((source, target))
            test_report = package(args.game_root, assets, args.output, args.confirm_2k14)
            print(f'Created package and {test_report.name}. Packaging passed; in-game compatibility is not tested.')
        else:
            gui()
    except Exception as ex:
        parser.exit(1, f'Error: {ex}\n')


if __name__ == '__main__':
    main()
