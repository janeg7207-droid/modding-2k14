"""WWE 2K14 Mod Formatter: analysis and packaging, not binary conversion."""
from pathlib import Path, PurePosixPath
import argparse
import json
import zipfile
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
    # Exclusive creation preserves existing packages and original game data.
    with output.open('xb') as stream:
        try:
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for source, target in checked:
                    archive.write(source, target)
        except Exception:
            stream.close()
            output.unlink()
            raise


def gui():
    import tkinter as tk
    from tkinter import ttk, filedialog as fd, messagebox as mb
    app = tk.Tk()
    app.title('WWE 2K14 Mod Formatter')
    app.geometry('980x850')
    frame = ttk.Frame(app, padding=16)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='WWE 2K14 Mod Formatter', font=('Segoe UI', 19, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Wrestler / attire workflow: analyze → convert with asset tools → map original PAC → export',
              wraplength=850).pack(anchor='w', pady=6)
    ttk.Label(frame, text='Does not extract CAK archives or convert models, skeletons, animations or textures.',
              wraplength=850).pack(anchor='w')
    report = None
    assets = []
    root = tk.StringVar()
    confirmed = tk.BooleanVar()
    library = SourceLibrary(Path(__file__).resolve().parent)
    library_frame = ttk.LabelFrame(frame, text='Source mod library', padding=8)
    library_frame.pack(fill='x', pady=8)
    library_rows = ttk.Treeview(library_frame, columns=('name', 'status'), show='headings', height=2)
    library_rows.heading('name', text='Mod')
    library_rows.heading('status', text='Source status')
    library_rows.column('name', width=220)
    library_rows.column('status', width=650)
    library_rows.pack(fill='x')

    def refresh_library():
        library_rows.delete(*library_rows.get_children())
        for entry in library.entries():
            available = library.archive(entry['id']) is not None
            status = 'Kept locally — extraction / 2K14 conversion required' if available else 'Not bundled — attach ' + entry['filename']
            library_rows.insert('', 'end', iid=entry['id'], values=(entry['name'], status))
        if library_rows.get_children():
            library_rows.selection_set(library_rows.get_children()[0])

    def selected_source():
        selection = library_rows.selection()
        if not selection:
            mb.showinfo('Select a source', 'Select a mod in the source library first')
            return None
        return selection[0]

    def attach_source():
        identity = selected_source()
        if identity is None:
            return
        name = fd.askopenfilename(title='Attach the original source archive; a local copy will be kept',
                                  filetypes=[('Source archives', '*.rar *.7z *.zip *.cak *.gorillamod'), ('All files', '*')])
        if name:
            try:
                library.attach(identity, Path(name))
                refresh_library()
                mb.showinfo('Source kept', 'A copy is saved in source_library beside the formatter.\n'
                            'This source has not been converted or enabled as a 2K14 mod.')
            except Exception as ex:
                mb.showerror('Cannot keep source', str(ex))

    def inspect_source():
        nonlocal report
        identity = selected_source()
        if identity is None:
            return
        source = library.archive(identity)
        if source is None:
            return mb.showinfo('Attach source archive', 'Attach the archive from your PC first. Its contents are not bundled.')
        try:
            report = library.inventory(identity) or analyze(source)
            log.delete('1.0', 'end')
            log.insert('end', report['status'] + '\n\n')
            for item in report['files']:
                log.insert('end', item['path'] + '\n  ' + item['assessment'] + '\n')
        except Exception as ex:
            mb.showerror('Analysis failed', str(ex))

    library_bar = ttk.Frame(library_frame)
    library_bar.pack(fill='x', pady=(6, 0))
    ttk.Button(library_bar, text='Attach archive (keep local copy)', command=attach_source).pack(side='left')
    ttk.Button(library_bar, text='Analyze attached source', command=inspect_source).pack(side='left', padx=6)
    ttk.Label(library_frame, text='Source archives stay separate from converted assets and are never added to mod exports.',
              wraplength=900).pack(anchor='w', pady=(6, 0))
    ttk.Label(library_frame, text='Jeff Hardy source credit: JeffIsMyName2K (from the supplied archive).',
              wraplength=900).pack(anchor='w')
    refresh_library()

    def inspect(folder=False):
        nonlocal report
        name = fd.askdirectory() if folder else fd.askopenfilename(title='Choose 2K26 source mod / ZIP')
        if not name:
            return
        try:
            report = analyze(name)
            log.delete('1.0', 'end')
            log.insert('end', report['status'] + '\n\n')
            for item in report['files']:
                log.insert('end', item['path'] + '\n  ' + item['assessment'] + '\n')
        except Exception as ex:
            mb.showerror('Analysis failed', str(ex))

    def save_report():
        if report is None:
            return mb.showinfo('Analyze first', 'Choose a source mod first')
        name = fd.asksaveasfilename(defaultextension='.json', initialfile='conversion-report.json')
        if name:
            try:
                Path(name).write_text(json.dumps(report, indent=2), encoding='utf-8')
            except Exception as ex:
                mb.showerror('Save failed', str(ex))

    bar = ttk.Frame(frame)
    bar.pack(fill='x', pady=8)
    ttk.Button(bar, text='1. Analyze file / ZIP', command=inspect).pack(side='left')
    ttk.Button(bar, text='Analyze folder', command=lambda: inspect(True)).pack(side='left', padx=6)
    ttk.Button(bar, text='Save analysis', command=save_report).pack(side='left')
    log = tk.Text(frame, height=9, wrap='word')
    log.pack(fill='both', expand=True)

    def choose_root():
        name = fd.askdirectory(title='Choose extracted 2K14 Xbox 360 game folder containing pac')
        if name:
            root.set(name)
            assets.clear()
            listing.delete(0, 'end')

    ttk.Button(frame, text='2. Choose extracted 2K14 reference folder', command=choose_root).pack(anchor='w', pady=(12, 0))
    ttk.Label(frame, textvariable=root, wraplength=850).pack(anchor='w')

    def add():
        if not root.get():
            return mb.showinfo('Reference needed', 'Choose the extracted 2K14 game folder first')
        converted = fd.askopenfilename(title='Choose replacement already rebuilt for 2K14')
        if not converted:
            return
        original = fd.askopenfilename(title='Choose ORIGINAL 2K14 game asset this replaces', initialdir=root.get())
        if not original:
            return
        try:
            target = Path(original).resolve().relative_to(Path(root.get()).resolve()).as_posix()
            entry = validate(root.get(), converted, target)
            if any(t.casefold() == entry[1].casefold() for _, t in assets):
                raise ValueError('This target already has a replacement')
            assets.append(entry)
            listing.insert('end', entry[0].name + ' → ' + entry[1])
        except Exception as ex:
            mb.showerror('Cannot add asset', str(ex))

    def remove():
        for index in reversed(listing.curselection()):
            assets.pop(index)
            listing.delete(index)

    bar = ttk.Frame(frame)
    bar.pack(fill='x', pady=8)
    ttk.Button(bar, text='3. Add converted asset + original target', command=add).pack(side='left')
    ttk.Button(bar, text='Remove selected', command=remove).pack(side='left', padx=6)
    listing = tk.Listbox(frame, height=6, selectmode='extended')
    listing.pack(fill='x')
    ttk.Checkbutton(frame, text='I rebuilt these assets for WWE 2K14 Xbox 360. Packaging does not verify compatibility.',
                    variable=confirmed).pack(anchor='w', pady=10)

    def export():
        if not confirmed.get() or not assets:
            return mb.showinfo('Converted assets required', 'Add converted assets and confirm the target format first')
        name = fd.asksaveasfilename(defaultextension='.zip', initialfile='My_2K14_Attire.zip')
        if name:
            try:
                package(root.get(), assets, name, confirmed.get())
                mb.showinfo('Package created', "Import the ZIP in the 2K14 launcher's Mods tab. Test one mod at a time.\n"
                            'In-game compatibility has not been verified.')
            except Exception as ex:
                mb.showerror('Export failed', str(ex))

    ttk.Button(frame, text='4. Export launcher mod ZIP', command=export).pack(anchor='w')
    app.mainloop()


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
            package(args.game_root, assets, args.output, args.confirm_2k14)
            print('Created package. Test asset compatibility in game.')
        else:
            gui()
    except Exception as ex:
        parser.exit(1, f'Error: {ex}\n')


if __name__ == '__main__':
    main()
