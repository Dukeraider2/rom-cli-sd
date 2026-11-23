# Phase 1 investigation and compatibility matrix

Baseline 379da0e contains Bash, packaging, a license and design notes. No existing database, test runner or platform adapter. Bash uses curl, jq, awk, fzf and aria2. Internet Archive metadata supplies the item and output name. Mirror discovery uses a regex on HTML, follows redirects and flattens paths. Resume and disabled autorenaming cannot establish file identity. Transfer failures can print a success footer. The build recipe downloads a different repository and installs only the shell script. Keep interactive search, isolate managed placement, validate path components and fail closed on collisions.

## Discovery evidence

EmuDeck's [vars.sh](https://github.com/dragoonDorise/EmuDeck/blob/main/vars.sh) sets the configuration directory. Its [settings](https://github.com/dragoonDorise/EmuDeck/blob/main/settings.sh) supply romsPath. Read literal assignments without executing shell. RetroDECK's [userdata guide](https://retrodeck.readthedocs.io/en/latest/wiki_management/retrodeck-folders/) locates the legacy cfg. Its [variable reference](https://retrodeck.readthedocs.io/en/latest/wiki_development/general/global-variables/) identifies rdhome and roms_folder. The [current configuration template](https://github.com/RetroDECK/RetroDECK/blob/main/config/retrodeck/retrodeck.json) uses paths.rd_home_path and paths.roms_path. Prefer current config if present. Discover the installed Flatpak and query effective per-path access with [flatpak info](https://docs.flatpak.org/en/latest/flatpak-command-reference.html#flatpak-info). Storage can be removable or custom. Never create a missing ROM root.

## Managed single-file allowlist

Each entry is an explicit subset of the [EmuDeck table](https://emudeck.github.io/cheat-sheet/) and [RetroDECK Linux systems definition](https://github.com/RetroDECK/ES-DE/blob/retrodeck-main/resources/systems/linux/es_systems.xml). These are documented mappings. Emulator launch and installed version overrides require device tests.

| System | EmuDeck folder | RetroDECK folder | Accepted suffix |
|---|---|---|---|
| NES | nes | nes | .nes |
| SNES | snes | snes | .sfc, .smc |
| Game Boy | gb | gb | .gb |
| Game Boy Color | gbc | gbc | .gbc |
| Game Boy Advance | gba | gba | .gba |
| Nintendo 64 | n64 | n64 | .z64, .n64, .v64 |
| Nintendo DS | nds | nds | .nds |
| PlayStation | psx | psx | .chd |
| PlayStation 2 | ps2 | ps2 | .chd, .iso |
| PSP | psp | psp | .iso, .cso |
| GameCube | gc | gc | .rvz |
| Wii | wii | wii | .rvz |
| Dreamcast | dreamcast | dreamcast | .chd |
| Saturn | saturn | saturn | .chd |
| Genesis | genesis | genesis | .md, .gen |

3DS setup varies by emulator and installed titles. Arcade sets, BIOS, archives, playlists and companion files require additional naming, reference or directory rules. Defer managed placement of these cases. Require explicit console for ambiguous suffixes. User-selected releases supply metadata.

## Deployment and frontend

[Valve's desktop FAQ](https://help.steampowered.com/en/faqs/view/671A-4453-E8D2-323C) describes the read-only image. Run from a user-owned checkout. Reopen ES-DE to rescan, select a game and use its metadata editor's scraper for targeted artwork. Use Steam ROM Manager's parser, preview and save workflow for shortcuts. [EmuDeck SRM](https://emudeck.github.io/tools/steamos/steam-rom-manager/) and [ES-DE user guide](https://github.com/RetroDECK/ES-DE/blob/retrodeck-main/USERGUIDE.md).

The [Decky template](https://github.com/SteamDeckHomebrew/decky-plugin-template) pairs TypeScript with named Python methods. Expose constrained operations after physical tests. Open questions include installed-core format overrides, remount behavior under load, sandbox visibility and hardware launch coverage.
