# WWE 2K14 Mod Formatter

Windows-friendly source analysis and ZIP packaging for the Banshee WWE 2K14 PC launcher's Mods tab. Python 3.10+; no third-party packages.

Also includes a **PS3 / RPCS3** mode for extracted PS3 game references, PS3 mod packaging, and an external RPCS3 launch button. The native PC launcher in the uploaded release still requires Xbox 360 game files. This tool does not modify that executable or turn a PS3 game into an Xbox 360 game.

**This is not an automatic 2K26-to-2K14 converter.** It does not extract CAK archives, retarget models or animations, convert textures, or rebuild PACs. Renaming a file does not convert it. Export validates paths and packaging, not binary compatibility.

## Run on Windows

1. Extract the formatter ZIP.
2. Install Python 3.10 or newer from https://www.python.org/downloads/windows/ with Tcl/Tk and the Python launcher (included in the normal installer).
3. Double-click **Launch Formatter.bat**. Alternatively, open PowerShell in that folder and run `py -3 mod_formatter.py`.

## Use your PS3 game

1. Install [RPCS3](https://rpcs3.net/download). Follow its [quickstart](https://rpcs3.net/quickstart), including installing official PS3 firmware. Use your own valid game dump and first verify it boots directly in RPCS3. RPCS3, firmware and game files are not bundled here.
2. Extract your PS3 disc dump. The supported folder layout is:

   ```text
   WWE 2K14 PS3/
     PS3_GAME/
       USRDIR/
         EBOOT.BIN
         pac/
         ...other game files...
   ```

3. Double-click **Launch PS3.bat**, or choose **PS3 / RPCS3** in the formatter.
4. Click **Choose PS3 game** and select the disc folder, `PS3_GAME`, or `USRDIR`. The formatter detects PS3 and uses `USRDIR` as the asset reference folder. ISO, PKG and compressed game files must be prepared separately with RPCS3-supported tools; selecting an ISO is not supported here.
5. Click **Choose RPCS3**, select your installed `rpcs3.exe`, then click **Play in RPCS3**. This passes the game's `EBOOT.BIN` to the external emulator. Starting the process does not establish that the game booted successfully; inspect RPCS3's window for errors.

The screenshot's **No default.xex in this folder** message comes from the Xbox 360-only recompilation. PS3 uses `EBOOT.BIN`; renaming it to `default.xex` will not work. Use the formatter's RPCS3 launch route for your PS3 game. The recompilation's graphics options, achievements and mod staging do not apply to the external emulator.

### PS3 mods

Select **PS3 / RPCS3**, choose the extracted PS3 reference, and add assets rebuilt specifically for **WWE 2K14 PS3**. The original PS3 target files must exist. Xbox 360 PACs and 2K26 models are not automatically converted. Existing PS3 `.arc` and `.def` catalogs at the `USRDIR` root can also be included if your asset tool rebuilt them. The formatter does not rebuild catalogs itself.

Exports contain paths relative to `USRDIR`, e.g. `pac/ch/<original-name>.pac`. Extract the mod ZIP into `PS3_GAME/USRDIR` of a **separate test copy** of the complete game, keeping the original backed up. Select that test copy under **Choose PS3 game** and boot it through RPCS3. Do not import PS3 asset ZIPs into the native PC launcher's Mods tab. The formatter never automatically installs or overwrites game assets.

The `.test.json` records `target_platform: "ps3"`, installation instructions, packaging checks and a separate `rpcs3_boot` checklist item. Compatibility and in-game tests remain `not_tested` until performed. Game-region and title-update differences may require matching rebuilt assets.

## Simplified desktop UI

Choose **PC / Xbox 360** or **PS3 / RPCS3**. Click **Choose 2K26 file**. The app checks it automatically in the background, without freezing the window. **Choose folder** handles already extracted source files. **Jeff Hardy 26 A0** opens the included source in one click. The dark interface keeps file details and converted-asset setup out of the main selection flow and scrolls on smaller screens.

Source inspection is automatic; binary conversion is not implemented. The source status shows **Conversion required**. To package assets you have already rebuilt, expand **I have converted assets**, choose the extracted 2K14 reference folder, add replacements against original target files, and confirm their format. **Export 2K14 ZIP + test JSON** then becomes available. It remains disabled for an unconverted 2K26 source.

## Included source library: Jeff Hardy 26 A0

The updated download includes the **actual Jeff Hardy 26 A0 source RAR**, recovered from the two uploaded 7z volumes, plus an inspected inventory. It is already attached in the UI's source library. Custom models and textures are credited to **JeffIsMyName2K** in the supplied archive; its original README is preserved inside the RAR.

Click **Jeff Hardy 26 A0**, then **File details** to see its 58 files, including model/material data and DDS textures with dimensions and format identifiers. The supplied archive was fully decompressed to check entry sizes and integrity. Its contents have not been converted or tested in 2K14. The inventory is used only when the source archive's SHA-256 matches the inspected source.

**Choose 2K26 file** selects any local RAR, 7z, ZIP, CAK, Gorilla archive, or source asset without replacing the included Jeff Hardy source. Selected files are read in place. The included archive and its SHA-256 record are kept in `source_library/`; keep the entire formatter folder when backing it up. The supplied Jeff Hardy archive and initial library index are included in this repository; additional local library files are ignored by Git.

Generic RAR/7z files cannot be inspected by the standalone tool; the Jeff Hardy inventory is included from this setup's inspection. Extract with 7-Zip on your PC and use **Choose folder** for other sources. Source archives never enter exported 2K14 ZIPs. Sources remain unconverted; only converted assets you add separately can be packaged.

## Wrestler / attire workflow

1. Analyze a source ZIP, folder, or CAK. Save the JSON report if useful. Archives are inspected without extraction or execution. CAK contents cannot be inspected by this tool.
2. Extract the source with a tool supporting that exact 2K26 format. For attire textures, adapt to the original 2K14 texture dimensions, layout and encoding. For models, adapt geometry, skeleton, skin weights and materials to the target 2K14 wrestler. Import/rebuild using tools confirmed to support 2K14 Xbox 360 PACs. **These manual conversion steps require separate asset tools and are not supplied here.**
3. Choose your extracted Xbox 360 2K14 game folder containing `pac`. It is read only. ISO players still need an extracted reference to select exact original targets.
4. Add your converted asset; select the ORIGINAL 2K14 file it replaces. Matching extensions are required but do not prove compatibility. Use the actual target filename; don't guess wrestler IDs.
5. Confirm the assets were rebuilt for 2K14 and export a new ZIP outside the original game folder. A matching `.test.json` is saved beside it automatically.
6. Close the game, import the ZIP in the launcher's Mods tab, enable it, and test the wrestler in a match. Disable other mods that replace the same file. Back up saves first.

Output layout:

```text
My_Attire_Mod.zip
  pac/
    ch/
      <actual-original-filename>.pac
```

Only original paths under `pac/`, `movies/`, and `sound/` are supported; PS3 mode also accepts original root `.arc`/`.def` catalogs. This tool handles replacements, not new roster slots. It does not modify original game files or launcher manifests, or modify Gorilla. Game launch is external through RPCS3 in PS3 mode. No automatic conflict scan, conversion or rollback is included. Existing output packages are not overwritten.

## Test JSON after export

Exporting `My_Attire_Mod.zip` also creates `My_Attire_Mod.test.json` **beside** the ZIP. It stays outside the mod archive so the launcher cannot mistake it for a game asset. Both GUI and CLI generate it automatically. Choose a new export name if either file already exists; existing results are preserved.

The JSON records the export timestamp, package and asset SHA-256 hashes, file sizes, original target paths, and packaging checks. Every archive entry is read back to check CRC integrity and compare its SHA-256 with the selected asset. A failed export does not leave a passing test report.

`conversion.status` is `user_declared`; the tool has not verified the binary conversion. `binary_compatibility.status` and `in_game.status` start as `not_tested`. After testing in 2K14, you can edit the in-game checklist and notes to record actual results (`passed`, `failed`, or `not_tested`) for launcher import, wrestler selection, entrance, attire/textures, match gameplay, and victory. Do not treat a packaging pass as proof that the port works.

Schema version 2 adds `target_platform`, `runtime`, installation instructions and platform-specific in-game checks. Xbox 360 remains the default export target for existing CLI commands.

## CLI

```powershell
py -3 mod_formatter.py analyze "C:\Downloads\My2K26Mod.zip" --report report.json
py -3 mod_formatter.py pack --game-root "C:\Games\WWE2K14-Extracted" --asset "C:\Converted\chXXX.pac=pac/ch/chXXX.pac" --output "C:\Mods\My_Attire_Mod.zip" --confirm-2k14
py -3 mod_formatter.py --ps3
py -3 mod_formatter.py play-ps3 --game-root "C:\Games\WWE2K14-PS3" --rpcs3 "C:\Emulators\RPCS3\rpcs3.exe"
py -3 mod_formatter.py pack --platform ps3 --game-root "C:\Games\WWE2K14-PS3" --asset "C:\Converted-PS3\chXXX.pac=pac/ch/chXXX.pac" --output "C:\Mods\My_PS3_Mod.zip" --confirm-2k14
```

Replace example paths with actual ones. Input analysis is heuristic. Limits: 20,000 input files or 2 GiB declared uncompressed input; 2 GiB output assets. GUI requires Tk and a desktop. The desktop file picker, source status, converted-asset export and JSON flow were exercised with real Tk on a virtual Linux display, using synthetic PAC fixtures for export. Windows GUI and in-game behavior have not been validated.

## Development checks

```sh
python -m unittest discover -s tests -v
python tools/check_desktop.py
```

The desktop check requires a display (or Xvfb on Linux). It exercises source selection, both platform modes, converted-asset export and test JSON. RPCS3 process creation is mocked; no emulator or real game is run. Actual PS3 gameplay and real converted assets have not been validated here.
