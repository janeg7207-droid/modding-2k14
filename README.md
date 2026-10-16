# WWE 2K14 Mod Formatter

Windows-friendly source analysis and ZIP packaging for the Banshee WWE 2K14 PC launcher's Mods tab. Python 3.10+; no third-party packages.

**This is not an automatic 2K26-to-2K14 converter.** It does not extract CAK archives, retarget models or animations, convert textures, or rebuild PACs. Renaming a file does not convert it. Export validates paths and packaging, not binary compatibility.

## Run on Windows

1. Extract the formatter ZIP.
2. Install Python 3.10 or newer from https://www.python.org/downloads/windows/ with Tcl/Tk and the Python launcher (included in the normal installer).
3. Double-click **Launch Formatter.bat**. Alternatively, open PowerShell in that folder and run `py -3 mod_formatter.py`.

## Included source library: Jeff Hardy 26 A0

The updated download includes the **actual Jeff Hardy 26 A0 source RAR**, recovered from the two uploaded 7z volumes, plus an inspected inventory. It is already attached in the UI's source library. Custom models and textures are credited to **JeffIsMyName2K** in the supplied archive; its original README is preserved inside the RAR.

Select **Jeff Hardy 26 A0** and click **Analyze attached source** to see its 58 files, including model/material data and DDS textures with dimensions and format identifiers. The supplied archive was fully decompressed to check entry sizes and integrity. Its contents have not been converted or tested in 2K14. The inventory is used only when the attached archive's SHA-256 matches the inspected source.

**Attach archive (keep local copy)** lets you replace the current source reference with a local RAR, 7z, ZIP, CAK or Gorilla archive. Streamed copies and SHA-256 records are kept in `source_library/` beside the formatter and survive restarts. Identical copies are reused; changed versions are retained separately. Keep the entire formatter folder when backing it up. The supplied Jeff Hardy archive and initial library index are included in this repository; additional local source archives are ignored by Git.

Generic RAR/7z attachments cannot be inspected by the standalone tool; the Jeff Hardy inventory is included from this setup's inspection. Extract with 7-Zip on your PC and use **Analyze folder** for other sources. Source archives never enter exported 2K14 ZIPs. The library labels sources as unconverted; only converted assets you add separately can be packaged.

## Wrestler / attire workflow

1. Analyze a source ZIP, folder, or CAK. Save the JSON report if useful. Archives are inspected without extraction or execution. CAK contents cannot be inspected by this tool.
2. Extract the source with a tool supporting that exact 2K26 format. For attire textures, adapt to the original 2K14 texture dimensions, layout and encoding. For models, adapt geometry, skeleton, skin weights and materials to the target 2K14 wrestler. Import/rebuild using tools confirmed to support 2K14 Xbox 360 PACs. **These manual conversion steps require separate asset tools and are not supplied here.**
3. Choose your extracted Xbox 360 2K14 game folder containing `pac`. It is read only. ISO players still need an extracted reference to select exact original targets.
4. Add your converted asset; select the ORIGINAL 2K14 file it replaces. Matching extensions are required but do not prove compatibility. Use the actual target filename; don't guess wrestler IDs.
5. Confirm the assets were rebuilt for 2K14 and export a new ZIP outside the original game folder.
6. Close the game, import the ZIP in the launcher's Mods tab, enable it, and test the wrestler in a match. Disable other mods that replace the same file. Back up saves first.

Output layout:

```text
My_Attire_Mod.zip
  pac/
    ch/
      <actual-original-filename>.pac
```

Only original paths under `pac/`, `movies/`, and `sound/` are supported. This tool handles replacements, not new roster slots. It does not modify original game files or launcher manifests, start the game, or modify Gorilla. No automatic conflict scan, conversion or rollback is included. Existing output packages are not overwritten.

## CLI

```powershell
py -3 mod_formatter.py analyze "C:\Downloads\My2K26Mod.zip" --report report.json
py -3 mod_formatter.py pack --game-root "C:\Games\WWE2K14-Extracted" --asset "C:\Converted\chXXX.pac=pac/ch/chXXX.pac" --output "C:\Mods\My_Attire_Mod.zip" --confirm-2k14
```

Replace example paths with actual ones. Input analysis is heuristic. Limits: 20,000 input files or 2 GiB declared uncompressed input; 2 GiB output assets. GUI requires Tk and a desktop; Windows GUI and in-game behavior have not been validated in this cloud machine.

## Development checks

```sh
python -m unittest discover -s tests -v
```
