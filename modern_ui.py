"""Dark desktop UI. Source inspection never implies binary conversion."""
from pathlib import Path
import hashlib
import json
from queue import Queue, Empty
from threading import Thread

from source_library import SourceLibrary
from game_support import game_layout, PLATFORM_NAMES, launch_ps3

BG = '#0c1018'
CARD = '#151c28'
BORDER = '#273348'
TEXT = '#f4f7fc'
MUTED = '#9ba9be'
ACCENT = '#a3f077'
INK = '#14220c'
AMBER = '#f2c779'


def source_summary(report):
    """No source-only input can be certified as a converted game asset."""
    files = report['files']
    models = sum(Path(item['path']).suffix.lower() in {'.mcd', '.fbx', '.obj', '.blend'} for item in files)
    textures = sum(Path(item['path']).suffix.lower() in {'.dds', '.png', '.tga', '.jpg', '.bmp'} for item in files)
    opaque = any(Path(item['path']).suffix.lower() in {'.rar', '.7z', '.cak', '.gorillamod'} for item in files)
    if opaque:
        message = 'This archive needs extraction with compatible asset tools before its contents can be checked.'
    elif models:
        message = 'Model and attire data found. It needs a 2K14 skeleton, materials and a rebuilt character PAC.'
    else:
        message = 'Source checked. A 2K14-ready replacement asset is required before export.'
    return dict(title='Conversion required', message=message, models=models, textures=textures,
                files=len(files), export_ready=False)


def inspect_source(source, library, analyze):
    """Reuse the included inventory when the user's selected bytes match it."""
    source = Path(source)
    if source.is_file():
        for entry in library.entries():
            retained = library.archive(entry['id'])
            if retained is None:
                continue
            if source.resolve() == retained.resolve():
                return library.inventory(entry['id']) or analyze(source)
            if source.stat().st_size == retained.stat().st_size and entry.get('inventory'):
                digest = hashlib.sha256()
                with source.open('rb') as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                inventory = library.inventory(entry['id'])
                if inventory and digest.hexdigest() == inventory['source_sha256']:
                    return inventory
    return analyze(source)


def launch(analyze, package, validate, initial_platform='xbox360'):
    import tkinter as tk
    from tkinter import ttk, filedialog as fd, messagebox as mb, font as tkfont

    app = tk.Tk()
    app.title('2K14 Mod Formatter')
    app.geometry('960x800')
    app.minsize(740, 640)
    app.configure(bg=BG)
    families = {name.casefold() for name in tkfont.families(app)}
    family = 'Segoe UI' if 'segoe ui' in families else 'Arial'
    app.option_add('*Font', (family, 10))
    style = ttk.Style(app)
    style.theme_use('clam')
    style.configure('Vertical.TScrollbar', background=BORDER, troughcolor=BG, bordercolor=BG,
                    arrowcolor=MUTED)
    style.configure('TCheckbutton', background=CARD, foreground=TEXT, font=(family, 10))
    style.map('TCheckbutton', background=[('active', CARD)], foreground=[('disabled', MUTED)])
    style.configure('TProgressbar', troughcolor=BORDER, background=ACCENT, bordercolor=CARD,
                    lightcolor=ACCENT, darkcolor=ACCENT)

    canvas = tk.Canvas(app, bg=BG, highlightthickness=0)
    scroll = ttk.Scrollbar(app, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    canvas.pack(fill='both', expand=True)
    page = tk.Frame(canvas, bg=BG, padx=34, pady=28)
    page_window = canvas.create_window((0, 0), window=page, anchor='nw')
    page.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda e: canvas.itemconfigure(page_window, width=e.width))

    def wheel(event):
        if getattr(event, 'num', None) == 4:
            delta = -3
        elif getattr(event, 'num', None) == 5:
            delta = 3
        else:
            delta = -int(event.delta / 120)
        canvas.yview_scroll(delta, 'units')

    app.bind('<MouseWheel>', wheel)
    app.bind('<Button-4>', wheel)
    app.bind('<Button-5>', wheel)

    def label(parent, text='', size=10, color=TEXT, bg=None, bold=False, **kw):
        return tk.Label(parent, text=text, bg=bg or parent.cget('bg'), fg=color,
                        font=(family, size, 'bold' if bold else 'normal'), anchor='w',
                        justify='left', **kw)

    def button(parent, text, command, primary=False, **kw):
        return tk.Button(parent, text=text, command=command,
                         bg=ACCENT if primary else BORDER, fg=INK if primary else TEXT,
                         activebackground='#b9ff92' if primary else '#36455e',
                         activeforeground=INK if primary else TEXT,
                         disabledforeground='#687789', relief='flat', borderwidth=0,
                         padx=18, pady=11, cursor='hand2',
                         font=(family, 10, 'bold'), **kw)

    def card(parent):
        return tk.Frame(parent, bg=CARD, padx=22, pady=20,
                        highlightbackground=BORDER, highlightthickness=1)

    library = SourceLibrary(Path(__file__).resolve().parent)
    report = None
    selected_source = None
    assets = []
    game_root = tk.StringVar()
    platform = tk.StringVar(value=initial_platform)
    rpcs3_path = tk.StringVar()
    confirmed = tk.BooleanVar()
    busy = False
    jobs = Queue()
    busy_controls = []
    poll_job = None

    def stop_poll(event):
        nonlocal poll_job
        if event.widget == app and poll_job is not None:
            app.after_cancel(poll_job)
            poll_job = None

    app.bind('<Destroy>', stop_poll, add='+')

    top = tk.Frame(page, bg=BG)
    top.pack(fill='x')
    label(top, '2K14 / MOD FORMATTER', size=10, color=ACCENT, bold=True).pack(side='left')
    label(top, 'WRESTLERS + ATTIRE', size=9, color=MUTED).pack(side='right')
    label(page, 'Bring your mod over.', size=30, bold=True).pack(anchor='w', pady=(20, 4))
    label(page, 'Choose a 2K26 file. We’ll check what it needs for WWE 2K14.',
          color=MUTED, wraplength=650).pack(anchor='w', pady=(0, 22))

    modes = tk.Frame(page, bg=BG)
    modes.pack(fill='x', pady=(0, 14))

    def select_platform(value):
        if value != platform.get():
            platform.set(value)
            game_root.set('')
            assets.clear()
            asset_list.delete(0, 'end')
            confirmed.set(False)
        ps3 = value == 'ps3'
        for mode, control in [('xbox360', pc_mode), ('ps3', ps3_mode)]:
            control.configure(bg=ACCENT if value == mode else BORDER, fg=INK if value == mode else TEXT)
        confirmation.configure(text='These assets were rebuilt for WWE 2K14 ' + ('PS3.' if ps3 else 'Xbox 360.'))
        output_note.configure(text=('PS3 ZIPs install into USRDIR of a separate test copy. Use RPCS3 to play.' if ps3
                                   else 'ZIP packaging checks files and paths. Import in the PC launcher’s Mods tab.'))
        game_button.configure(text='Choose PS3 reference folder' if ps3 else 'Choose 2K14 reference folder')
        if ps3:
            runtime_card.pack(fill='x', pady=(0, 14), before=source_card)
        else:
            runtime_card.pack_forget()
        update_export_state()

    pc_mode = button(modes, 'PC / Xbox 360', lambda: select_platform('xbox360'))
    pc_mode.pack(side='left')
    ps3_mode = button(modes, 'PS3 / RPCS3', lambda: select_platform('ps3'))
    ps3_mode.pack(side='left', padx=8)
    busy_controls.extend([pc_mode, ps3_mode])

    runtime_card = card(page)
    label(runtime_card, 'PLAYSTATION 3', size=9, color=ACCENT, bold=True).pack(anchor='w')
    label(runtime_card, 'Play through RPCS3', size=18, bold=True).pack(anchor='w', pady=(8, 4))
    label(runtime_card, 'The PC recompilation uses Xbox 360 code. Your PS3 copy boots separately in RPCS3.',
          color=MUTED, wraplength=650).pack(anchor='w')
    runtime_actions = tk.Frame(runtime_card, bg=CARD)
    runtime_actions.pack(fill='x', pady=(12, 0))
    ps3_game_button = button(runtime_actions, 'Choose PS3 game', lambda: choose_game())
    ps3_game_button.pack(side='left')

    def choose_rpcs3():
        name = fd.askopenfilename(title='Choose your installed rpcs3.exe / RPCS3 executable',
                                  filetypes=[('RPCS3', 'rpcs3.exe rpcs3 *.AppImage'), ('All files', '*')])
        if name:
            rpcs3_path.set(name)

    emulator_button = button(runtime_actions, 'Choose RPCS3', choose_rpcs3)
    emulator_button.pack(side='left', padx=8)

    def play_ps3():
        if not game_root.get() or not rpcs3_path.get():
            return mb.showinfo('Set up RPCS3 first', 'Choose your extracted PS3 game and installed RPCS3 executable.\n'
                              'Install official PS3 firmware in RPCS3 and verify your game dump there first.')

        def started(process):
            status_title.configure(text='RPCS3 started', fg=ACCENT)
            status_text.configure(text='Check the RPCS3 window for boot progress or setup errors. The game has not been verified here.')
            stats.configure(text='External emulator launched / gameplay not tested')
        game = game_root.get()
        emulator = rpcs3_path.get()
        run_task(lambda: launch_ps3(game, emulator), started)

    play_button = button(runtime_actions, 'Play in RPCS3', play_ps3, primary=True)
    play_button.pack(side='left')
    label(runtime_card, textvariable=game_root, color=MUTED, wraplength=650).pack(anchor='w', pady=(8, 0))
    label(runtime_card, textvariable=rpcs3_path, color=MUTED, wraplength=650).pack(anchor='w')
    label(runtime_card, 'Use an extracted PS3 disc folder with PS3_GAME/USRDIR/EBOOT.BIN. Firmware and RPCS3 are installed separately.',
          size=9, color=MUTED, wraplength=650).pack(anchor='w', pady=(8, 0))
    busy_controls.extend([ps3_game_button, emulator_button, play_button])

    source_card = card(page)
    source_card.pack(fill='x')
    label(source_card, '01  /  SOURCE', size=9, color=MUTED, bold=True).pack(anchor='w')
    filename = label(source_card, 'Choose your 2K26 mod', size=18, bold=True, wraplength=650)
    filename.pack(anchor='w', pady=(10, 3))
    source_caption = label(source_card, 'ZIP, RAR, 7z, CAK or an extracted model file', color=MUTED,
                           wraplength=650)
    source_caption.pack(anchor='w')
    source_actions = tk.Frame(source_card, bg=CARD)
    source_actions.pack(fill='x', pady=(16, 0))

    status_card = card(page)
    status_card.pack(fill='x', pady=14)
    status_title = label(status_card, 'Ready when you are', size=15, bold=True)
    status_title.pack(anchor='w')
    status_text = label(status_card, 'Select a file to see its conversion status.', color=MUTED, wraplength=650)
    status_text.pack(anchor='w', pady=(6, 0))
    stats = label(status_card, '', size=10, color=ACCENT)
    stats.pack(anchor='w', pady=(10, 0))
    progress = ttk.Progressbar(status_card, mode='indeterminate', style='TProgressbar')

    def update_export_state():
        ready = not busy and assets and confirmed.get()
        export_button.configure(state='normal' if ready else 'disabled',
                                bg=ACCENT if ready else BORDER, disabledforeground=MUTED)

    def run_task(work, done):
        nonlocal busy
        if busy:
            return
        busy = True
        for control in busy_controls:
            control.configure(state='disabled')
        export_button.configure(state='disabled', bg=BORDER)
        status_title.configure(text='Working…', fg=TEXT)
        progress.pack(fill='x', pady=(12, 0))
        progress.start(12)

        def worker():
            try:
                jobs.put((done, work(), None))
            except Exception as ex:
                jobs.put((done, None, ex))
        Thread(target=worker, daemon=True).start()

    def poll():
        nonlocal busy, poll_job
        poll_job = None
        try:
            done, result, error = jobs.get_nowait()
        except Empty:
            poll_job = app.after(80, poll)
            return
        busy = False
        progress.stop()
        progress.pack_forget()
        for control in busy_controls:
            control.configure(state='normal')
        if error is not None:
            status_title.configure(text='Could not finish', fg=AMBER)
            status_text.configure(text=str(error))
        else:
            try:
                done(result)
            except Exception as ex:
                status_title.configure(text='Could not finish', fg=AMBER)
                status_text.configure(text=str(ex))
        update_export_state()
        poll_job = app.after(80, poll)

    def load_source(path, display_name=None):
        nonlocal selected_source, report
        if busy:
            return
        selected_source = Path(path)
        report = None
        assets.clear()
        asset_list.delete(0, 'end')
        confirmed.set(False)
        filename.configure(text=display_name or selected_source.name)
        source_caption.configure(text='Checking source. Original file stays unchanged.')
        stats.configure(text='')

        def loaded(result):
            nonlocal report
            report = result
            summary = source_summary(report)
            filename.configure(text=display_name or report.get('source', selected_source.name))
            status_title.configure(text=summary['title'], fg=AMBER)
            status_text.configure(text=summary['message'])
            stats.configure(text=f"{summary['files']} files   /   {summary['models']} models   /   {summary['textures']} textures")
            source_caption.configure(text='Source checked • No binary conversion performed')
            choose_button.configure(text='Choose another file')
        run_task(lambda: inspect_source(selected_source, library, analyze), loaded)

    def choose_source(folder=False):
        if busy:
            return
        name = fd.askdirectory(title='Choose an extracted source folder') if folder else fd.askopenfilename(
            title='Choose a WWE 2K26 mod file',
            filetypes=[('Mod files', '*.zip *.rar *.7z *.cak *.gorillamod *.mcd *.pac *.dds'), ('All files', '*')])
        if name:
            load_source(name)

    choose_button = button(source_actions, 'Choose 2K26 file', choose_source, primary=True)
    choose_button.pack(side='left')
    folder_button = button(source_actions, 'Choose folder', lambda: choose_source(True))
    folder_button.pack(side='left', padx=8)
    busy_controls.extend([choose_button, folder_button])

    included_row = tk.Frame(page, bg=BG)
    included_row.pack(fill='x', pady=(0, 14))
    label(included_row, 'INCLUDED SOURCE', size=9, color=MUTED, bold=True).pack(side='left', padx=(0, 12))

    def open_jeff():
        try:
            path = library.archive('jeff_hardy_26_a0')
            if path is None:
                return mb.showinfo('Source missing', 'Extract the complete formatter download to restore the Jeff Hardy source.')
            load_source(path, 'Jeff Hardy 26 A0')
        except Exception as ex:
            mb.showerror('Cannot open source', str(ex))

    jeff_button = button(included_row, 'Jeff Hardy 26 A0  ↗', open_jeff)
    jeff_button.pack(side='left')
    busy_controls.append(jeff_button)

    export_card = card(page)
    export_card.pack(fill='x')
    label(export_card, '02  /  WWE 2K14 OUTPUT', size=9, color=MUTED, bold=True).pack(anchor='w')
    label(export_card, 'Finish with a converted PAC', size=17, bold=True).pack(anchor='w', pady=(9, 4))
    label(export_card, 'Automatic 2K26 model conversion is not available yet. Already rebuilt your asset? Add it below.',
          color=MUTED, wraplength=650).pack(anchor='w')
    setup = tk.Frame(export_card, bg=CARD)
    setup_open = False

    def toggle_setup():
        nonlocal setup_open
        setup_open = not setup_open
        if setup_open:
            setup.pack(fill='x', after=setup_toggle, pady=(12, 0))
            setup_toggle.configure(text='Hide export setup  −')
        else:
            setup.pack_forget()
            setup_toggle.configure(text='I have converted assets  +')

    setup_toggle = button(export_card, 'I have converted assets  +', toggle_setup)
    setup_toggle.pack(anchor='w', pady=(12, 0))

    def choose_game():
        name = fd.askdirectory(title='Choose extracted 2K14 game folder (PS3 disc, PS3_GAME, USRDIR, or Xbox 360)')
        if name:
            try:
                try:
                    layout = game_layout(name, 'auto')
                except ValueError:
                    layout = game_layout(name, platform.get())
                select_platform(layout.platform)
                game_root.set(str(layout.asset_root))
                assets.clear()
                asset_list.delete(0, 'end')
                confirmed.set(False)
                update_export_state()
            except Exception as ex:
                mb.showerror('Cannot use game folder', str(ex))

    game_button = button(setup, 'Choose 2K14 reference folder', choose_game)
    game_button.pack(anchor='w')
    label(setup, textvariable=game_root, color=MUTED, wraplength=650).pack(anchor='w', pady=(4, 10))

    def add_asset():
        if not game_root.get():
            return mb.showinfo('Reference folder needed', 'Choose your extracted 2K14 reference folder first.')
        replacement = fd.askopenfilename(title='Choose your converted 2K14 asset')
        if not replacement:
            return
        target = fd.askopenfilename(title='Select the ORIGINAL 2K14 asset it replaces', initialdir=game_root.get())
        if not target:
            return
        try:
            relative = Path(target).resolve().relative_to(Path(game_root.get()).resolve()).as_posix()
            entry = validate(game_root.get(), replacement, relative, platform.get())
            if any(old.casefold() == entry[1].casefold() for _, old in assets):
                raise ValueError('This target already has a replacement.')
            assets.append(entry)
            asset_list.insert('end', entry[0].name + '  →  ' + entry[1])
            confirmed.set(False)
            update_export_state()
        except Exception as ex:
            mb.showerror('Cannot add asset', str(ex))

    def remove_asset():
        for index in reversed(asset_list.curselection()):
            assets.pop(index)
            asset_list.delete(index)
        confirmed.set(False)
        update_export_state()

    asset_actions = tk.Frame(setup, bg=CARD)
    asset_actions.pack(fill='x')
    add_button = button(asset_actions, 'Add converted asset', add_asset)
    add_button.pack(side='left')
    remove_button = button(asset_actions, 'Remove', remove_asset)
    remove_button.pack(side='left', padx=8)
    asset_list = tk.Listbox(setup, height=3, bg=BG, fg=TEXT, selectbackground=BORDER,
                           selectforeground=TEXT, relief='flat', highlightthickness=1,
                           highlightbackground=BORDER, font=(family, 10), selectmode='extended')
    asset_list.pack(fill='x', pady=10)
    confirmation = ttk.Checkbutton(setup, text='These assets were rebuilt for WWE 2K14 Xbox 360.',
                                  variable=confirmed, command=update_export_state)
    confirmation.pack(anchor='w')
    busy_controls.extend([game_button, add_button, remove_button, confirmation, setup_toggle])

    def export():
        if busy or not assets or not confirmed.get():
            return
        name = fd.asksaveasfilename(title='Save 2K14 mod package', defaultextension='.zip',
                                   initialfile='My_2K14_PS3_Mod.zip' if platform.get() == 'ps3' else 'My_2K14_Mod.zip')
        if not name:
            return
        export_assets = list(assets)
        export_root = game_root.get()
        export_platform = platform.get()

        def exported(test_path):
            status_title.configure(text='Package + test JSON saved', fg=ACCENT)
            installation = ('Extract into USRDIR of a separate PS3 test copy, then boot that copy in RPCS3.'
                            if export_platform == 'ps3' else 'Import the ZIP in the 2K14 launcher’s Mods tab.')
            status_text.configure(text=f'{Path(name).name}\n{test_path.name}\n{installation}')
            stats.configure(text='Packaging passed   /   In-game compatibility: not tested')
        run_task(lambda: package(export_root, export_assets, name, True, export_platform), exported)

    export_button = button(export_card, 'Export 2K14 ZIP + test JSON  →', export, primary=True, state='disabled')
    export_button.pack(fill='x', pady=(18, 0))
    output_note = label(export_card, '', size=9, color=MUTED, wraplength=650)
    output_note.pack(anchor='w', pady=(8, 0))

    footer = tk.Frame(page, bg=BG)
    footer.pack(fill='x', pady=(18, 0))

    def details():
        if report is None:
            return mb.showinfo('Choose a file', 'Select a source file first.')
        window = tk.Toplevel(app)
        window.title('Source analysis')
        window.geometry('850x550')
        window.configure(bg=BG)
        text = tk.Text(window, bg=BG, fg=TEXT, insertbackground=TEXT, relief='flat', wrap='word',
                       font=('Consolas', 10), padx=18, pady=18)
        bar = ttk.Scrollbar(window, command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        text.pack(fill='both', expand=True)
        text.insert('end', json.dumps(report, indent=2))
        text.configure(state='disabled')

    def save_report():
        if report is None:
            return mb.showinfo('Choose a file', 'Select a source file first.')
        name = fd.asksaveasfilename(defaultextension='.json', initialfile='source-analysis.json')
        if name:
            try:
                Path(name).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            except Exception as ex:
                mb.showerror('Cannot save analysis', str(ex))

    button(footer, 'File details', details).pack(side='left')
    button(footer, 'Save analysis JSON', save_report).pack(side='left', padx=8)
    label(page, 'Jeff Hardy source: JeffIsMyName2K • Original source archive included.',
          size=9, color=MUTED, wraplength=650).pack(anchor='w', pady=(16, 0))
    select_platform(initial_platform)
    poll_job = app.after(80, poll)
    app.mainloop()
