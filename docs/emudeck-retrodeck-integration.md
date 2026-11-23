# EmuDeck + RetroDECK integration specification (draft v0.1)

Status: design only; no compatibility claims or executable changes yet.

## Goal
First-class, equal support for EmuDeck and RetroDECK ROM placement from the standalone CLI and a future Decky Loader UI. Only download/install content users are authorized to obtain.

## Verified upstream baseline
- Bash `rom-cli` v1.1.1 uses Internet Archive search and optional self-hosted HTTP mirror, fzf, jq, curl and aria2.
- IA downloads currently land under `$ROM_CLI_DOWNLOAD_DIR/<identifier>`; mirror downloads under `$ROM_CLI_DOWNLOAD_DIR/mirror`.
- No EmuDeck/RetroDECK detection or console-specific destination mapping exists.
- Existing mirror HTML parsing, filename handling, collision handling and download-error reporting require security review before automatic placement.

## Integration contracts
### EmuDeck
- Detect installed EmuDeck and its *actual configured* `Emulation/roms` root; do not hardcode internal SSD or microSD paths.
- Resolve each system using verified EmuDeck cheat-sheet and installed `systeminfo.txt` format guidance.
- EmulationStation visibility and Steam ROM Manager library shortcuts are distinct: SRM requires parser/parse/save workflow; do not silently edit Steam files.

References: https://manual.emudeck.com/install-guide/1_index/ ; https://manual.emudeck.com/install-guide/srm/ ; https://emudeck.github.io/tools/steamos/steam-rom-manager/

### RetroDECK
- Detect Flatpak application `net.retrodeck.retrodeck` and read its user configuration (normally `~/.var/app/net.retrodeck.retrodeck/config/retrodeck/retrodeck.cfg`) to resolve the dynamic userdata/ROM root.
- ROM directory structure follows ES-DE; verify specific folder names and formats against installed version and official docs.
- Check Flatpak permissions and custom/microSD storage accessibility. Never alter RetroDECK configs merely to install a ROM.

References: https://retrodeck.readthedocs.io/en/latest/wiki_management/retrodeck-folders/ ; https://retrodeck.readthedocs.io/en/latest/wiki_development/general/folders-filepaths/

## Required flow
1. Read-only discovery of installations and actual roots; show explicit choice if both exist.
2. User selects system and authorized content; determine validated system mapping.
3. Download into private staging; report errors, verify checksums where available and inspect archive safely.
4. Validate supported extension, disk space, write access and Flatpak access; prohibit path/symlink traversal.
5. Confirm target and collisions; atomic placement without overwriting existing files.
6. Report success and guide optional ES-DE refresh or Steam ROM Manager import; do not claim an automatic Steam library refresh.

## Architecture
Keep CLI operational without Decky. Introduce separate suite adapters and a constrained backend API for Decky. No arbitrary shell execution from the plugin UI. Do not modify SteamOS system partitions or install pacman packages as part of the application.

## Test matrix
- Neither, either, or both suites installed; internal/microSD/custom paths; missing/remounted storage.
- System mapping for NES/SNES/N64/GB/GBC/GBA/DS/3DS/GC/Wii/PS1/PS2/PSP/Dreamcast/Genesis/Saturn/arcade, checked individually against documentation.
- Correct archive handling, multi-disc titles, duplicate names, interrupted downloads, malformed archive entries, malicious filenames and symlinks.
- Flatpak permission denied; non-writable target; zero disk space; failed checksum; unsupported format.
- Mock layouts first; real Steam Deck Gaming Mode tests before claiming full compatibility.

## Milestones
1. Baseline audit, official mapping table, read-only detection tests.
2. Safe staging and install pipeline with CLI flags and mocked integration tests; measure overhead.
3. Decky UI prototype and constrained backend; independent security review; on-device validation.

## Open questions
- Confirm exact EmuDeck discovery source and RetroDECK configuration keys from installed builds.
- Verify Decky Loader API and plugin deployment compatibility with current SteamOS.
- Decide whether a shared library or independent copies should be supported when both suites are installed.
