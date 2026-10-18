"""Platform-specific reference folders and an external RPCS3 launch route."""
from dataclasses import dataclass
from pathlib import Path
import subprocess

PLATFORM_NAMES = {'xbox360': 'Xbox 360 / PC recompilation', 'ps3': 'PlayStation 3 / RPCS3'}


@dataclass(frozen=True)
class GameLayout:
    platform: str
    asset_root: Path
    game_root: Path
    boot_file: Path | None


def _child(parent, name):
    direct = parent / name
    if direct.exists():
        return direct
    if parent.is_dir():
        matches = [path for path in parent.iterdir() if path.name.casefold() == name.casefold()]
        if len(matches) > 1:
            raise ValueError(f'Ambiguous game folder entry: {name}')
        if matches:
            return matches[0]
    return direct


def _ps3_layout(root):
    candidates = [root, _child(root, 'USRDIR'), _child(_child(root, 'PS3_GAME'), 'USRDIR')]
    for candidate in candidates:
        boot = _child(candidate, 'EBOOT.BIN')
        if boot.is_file():
            asset_root = candidate.resolve(strict=True)
            if not asset_root.is_relative_to(root):
                raise ValueError('PS3 asset folder escapes the selected game folder')
            boot = boot.resolve(strict=True)
            if not boot.is_relative_to(asset_root):
                raise ValueError('PS3 boot file escapes the game folder')
            if asset_root.name.casefold() == 'usrdir' and asset_root.parent.name.casefold() == 'ps3_game':
                disc_root = asset_root.parent.parent
            else:
                disc_root = asset_root
            return GameLayout('ps3', asset_root, disc_root, boot)
    return None


def game_layout(game_root, platform='auto'):
    if platform not in {*PLATFORM_NAMES, 'auto'}:
        raise ValueError('Platform must be xbox360, ps3 or auto')
    root = Path(game_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Select an extracted game folder, not an ISO or ZIP')
    ps3 = _ps3_layout(root)
    if ps3:
        if platform == 'xbox360':
            raise ValueError('This is a PS3 game. Select PS3 / RPCS3; the PC recompilation requires Xbox 360 files.')
        return ps3
    if platform == 'ps3':
        raise ValueError('No EBOOT.BIN found. Choose the PS3 disc folder, PS3_GAME, or USRDIR; extract ISO files first.')
    boot = _child(root, 'default.xex')
    if platform == 'auto' and not boot.is_file():
        raise ValueError('No EBOOT.BIN or default.xex found. Choose an extracted game folder.')
    # Explicit Xbox mode also permits asset-only reference folders, as earlier releases did.
    return GameLayout('xbox360', root, root, boot if boot.is_file() else None)


def rpcs3_command(game_root, executable):
    layout = game_layout(game_root, 'ps3')
    exe = Path(executable).resolve(strict=True)
    name = exe.name.casefold()
    if not exe.is_file() or not (name in {'rpcs3.exe', 'rpcs3'} or (name.startswith('rpcs3') and name.endswith('.appimage'))):
        raise ValueError('Choose the installed rpcs3.exe, rpcs3 executable, or RPCS3 AppImage')
    with layout.boot_file.open('rb') as stream:
        if stream.read(4) not in {b'SCE\x00', b'\x7fELF'}:
            raise ValueError('EBOOT.BIN is not a recognized PS3 SELF/ELF file. Check your game dump.')
    # Official RPCS3 CLI accepts a (S)ELF positional argument; keep the GUI visible for errors/setup.
    return [str(exe), str(layout.boot_file)]


def launch_ps3(game_root, executable):
    command = rpcs3_command(game_root, executable)
    return subprocess.Popen(command, cwd=str(Path(command[0]).parent), shell=False)
