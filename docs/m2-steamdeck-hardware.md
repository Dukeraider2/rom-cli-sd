# M2 Steam Deck deployment record

**SSH device validation executed. Gaming Mode acceptance pending.** Recovered the prior Steam Deck destination from connection history and authenticated with strict saved-host-key checking. The user selected SSH-only testing. The physical Deck was in KDE Wayland Desktop Mode. All remote operations ran as the active unprivileged account.

## Inventory before installation

| Item | Device observation |
|---|---|
| Hardware and OS | Galileo, SteamOS 3.9.5 stable build 20261023.100, kernel 7.2.7-valve2-2-neptune-72-g31504582a073. Account deck, UID 1000. MemTotal 15,153,384 KiB. |
| Storage | 953.9 GiB NVMe, 155 GiB available on the home filesystem. 928.3 GiB microSD with 671 GiB available on its ext4 partition. |
| Existing software | Decky v3.3.1 system service active. EmuDeck settings report 2.5.0. ES-DE AppImage reports 3.4.1 r51. RetroArch 1.22.2, Dolphin, melonDS, xemu, PPSSPP, ScummVM, PrimeHack and Supermodel installed in user scope. Existing SRM configuration found. Standalone SRM launch unverified. |
| EmuDeck discovery | The real settings.sh selects the microSD Emulation/roms directory. The extracted backend resolved the same path and validated access to its nes console directory. Separate user-owned test roots were used for writes. |
| Development and connectivity | git, curl, python3 and flatpak available. HTTPS checks returned 200 for EmuDeck, Flathub, GitHub Decky and Internet Archive. Existing user Flathub remote points at dl.flathub.org. |

On the confirmed device, collect `id`, `cat /sys/class/dmi/id/product_name`, `cat /etc/os-release`, `uname -r`, `free -h`, `lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS`, `df -hT`, `flatpak list --app`, `flatpak remotes --show-details`, and `command -v git curl python3 flatpak`. Record user/system installation scope and check existing suite settings, launcher and loader state before choosing installation steps. Use `bash rom-cli --library platforms` for the repository's discovery view. Compare its paths with each suite's own settings and effective access. Keep account names and personal paths out of shared logs.

## Installation and recovery record

Before any write, choose distinct disposable locations in the suites' supported setup flows. Record existing package versions, settings, grants, shortcuts and storage roots. With writers stopped, back up suite settings, Steam shortcut configuration and any existing ROM Library catalog and job data, including SQLite sidecars. Keep the previous plugin ZIP if upgrading. Confirm a restorable backup before changing installed components. Record each new component and exact test filename/digest so cleanup can be scoped to this run.

Install EmuDeck from its official SteamOS entry point. Record its active storage path, ES-DE and Steam ROM Manager configuration after setup. Install RetroDECK through Discover and run its Desktop Mode setup, recording the selected directory, Flatpak identity, installation scope, permissions and Steam shortcut. Check Decky compatibility against the observed SteamOS version. Obtain approval for any privileged installer or service change before executing it. Select ROM Library's inner ZIP through Decky's supported installer. [EmuDeck](https://www.emudeck.com/) · [RetroDECK first run](https://retrodeck.readthedocs.io/en/latest/wiki_devices/steamdeck/steamdeck-start/) · [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)

For rollback, stop new jobs, let atomic publication finish, unload the plugin and check the worker and lock. Preserve failure evidence before retry. Restore the previous trusted ZIP and, with all writers stopped, restore catalog backups into a fresh directory as needed. Inspect each disposable file against its recorded digest before removal. Revert only settings and shortcuts recorded as changed. Removal of installed suites or changes to storage or grants require a separate review of the actual device inventory.

## Physical evidence outstanding

| Trial | Evidence to collect |
|---|---|
| Archive and controlled mirror, separately | Authorized playable fixture and expected digest, source/item, pagination, invalid metadata, cancellation and unavailable source |
| Internal SSD for both suites, microSD if present | Actual preview path, available bytes, confirmed job, checksum, duplicate, interruption, explicit retry, verified file and reconciliation |
| ES-DE and RetroDECK | Desktop and Gaming Mode discovery, refresh steps, emulator selection, successful launch and exit |
| Controller and loader | Quick Access, focus, OSK, Back, explicit enqueue, progress, cancel, retry, unload/reopen, plugin UID and worker count |
| Performance | AC/battery state, idle and transfer CPU, peak RSS, search and UI latency, throughput, verification, launch time and post-unload recovery |

## Executed command-line checks

The build from baseline `c741bdc` and validation commit `b540924` passed the Linux Python and frontend suites, TypeScript, bundling, and ZIP checks. The physical Deck independently matched ZIP SHA-256 `dad5f7e1e47675e5c8cd4de01977b265855c94e09d3eb7cdff533af70d21eeb5`. The transferred ZIP was staged privately for the official installer. Importing the extracted backend and resolving the real EmuDeck destination succeeded as UID 1000. A private recovery directory contains snapshots of EmuDeck settings and Steam shortcut files. [Candidate CI](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45296951924)

On the device, `python3 -B -m unittest discover -s tests -v` passed 33 tests in 4.573 seconds. These exercise the service with fixtures. Live Archive metadata search for “homebrew” returned an empty filtered first page with a next page, then six supported candidates. A separate live query for “Nova the Squirrel” returned nova.nes from item novathesquirrel1.0.6 in 438 ms. Explicit confirmation downloaded, verified and published 262,160 bytes to a disposable Deck library in 1.132 s. The provider supplied SHA-1 and MD5. Installed SHA-256 was `b7cf50596f2f7ec1a1b7f77e033c9a52f743bb15e9ef15ae0cb0cf6ce9609a98`. NovaSquirrel publishes the code under GPL-3.0-or-later and assets under CC BY-NC-SA 4.0. No game payload is included in Git. [Author and license](https://github.com/NovaSquirrel/NovaTheSquirrel#license) The separate loopback mirror served an original NES cartridge. From an isolated runner, `PYTHONPATH="/path/to/extracted/ROM Library" python3 device_m2_fixture.py /path/to/private/stage` exercised search, selection, preview, explicit enqueue and verified publication in a disposable library. The installer published SHA-256 `02ad100b04e699cc050733affe8b75030be62d7b23f1116515080ed8aac89f64`; a duplicate preview disabled installation. [Reproducible test fixture](../tests/device_m2_fixture.py)

RetroArch with the installed Nestopia core loaded the published file and exited zero after a bounded 120-frame offscreen run. The log recorded one second of content and core unload. Initial headless attempts failed on the input and Qt display drivers. The successful run used null video/input and Qt offscreen. Audio initialization emitted errors. An earlier attempt wrote RetroArch's normal content history and the final run saved Nestopia core options. The test ROM remained in the disposable library.

### Physical performance sample

Each row is one 8 MiB HTTP loopback transfer, verified and published through the backend on the physical Deck. AC was connected during this session. The benchmark includes the local HTTP server. The Linux CI baseline was 149.86 MiB/s and 53 ms. Device figures include filesystem behavior and the polling interval. They cannot establish sustained download speeds, UI latency or energy use. Run `TMPDIR=/private/test/directory python3 -B tests/benchmark_m2.py` on the intended filesystem.

| Destination | End to end | Throughput | CPU s | RSS peak bytes | Search ms | Progress median ms | Idle CPU ms/1s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Internal SSD | 96 ms | 83.54 MiB/s | 0.071 | 32,374,784 | 2.21 | 0.628 | 0.12 |
| microSD | 391 ms | 20.45 MiB/s | 0.114 | 33,374,208 | 2.26 | 0.481 | 0.13 |

Both runs ended with zero active transfer workers and 11 queue mutation statements. A first run used tmpfs and measured 131.58 MiB/s. Physical card removal, game-load latency, battery behavior, graphical focus, actual controller input and full loader unload/reload are outstanding. [Host performance baseline and coverage](m2-verification.md)

Independent static review found no critical or high-severity issue in cancellation, shutdown or publication. Removing storage during cleanup can leave a journaled part owned by the still-running process. Remount the original volume, stop or reload the plugin to retire that process and reconcile the original attempt before retrying. A worker already publishing can retain its lease after the bounded unload wait. Verify it has exited before reloading.

### Device log excerpts

ES-DE launched with a private `--home`, disabled update checks and SDL offscreen. It logged `ViewController::preload(): Populating gamelist for system "nes"` before the 20-second test timeout. The separate Nestopia launch logged `Content ran for a total of: 00 hours, 00 minutes, 01 seconds.` and `Unloading core symbols...`. No input-to-frame or graphical launch measurement was made.

The extracted plugin entry point also completed two start/RPC/unload cycles with a test shim supplying Decky environment values. Each cycle returned success for version 1, `version` for version 2 and `invalid_request` for unexpected arguments. The worker was absent and the queue lease closed after unload. The live loader has yet to exercise these paths. [Raw physical storage samples](m2-steamdeck-storage.json)

### Application changes and rollback

The existing EmuDeck installation used the microSD and its settings identified version 2.5.0. The current official x86-64 AppImage was installed at the existing user-owned application path. Its internal desktop entry reported 2.7.1 and its installed SHA-256 matched `97ed9aee397052d99f0e5a580303a6ffe86b7f49d20c1a057b020b6e6270c98d`. Both backed-up EmuDeck settings files and Steam shortcuts remained byte-identical after the update. The prior executable is in the private recovery directory as `EmuDeck-original.AppImage`, SHA-256 `7b4b898567c2abcc7ebe791500b34ab2aadc8c2a23d1754d23d314215b4fcc66`. If rollback is required, close EmuDeck, verify both file identities, and restore that executable to its recorded original location. [Official EmuDeck release](https://github.com/EmuDeck/emudeck-electron/releases/tag/v2.7.1)

Steam ROM Manager's binary was missing. The installed EmuDeck backend specifies `Steam-ROM-Manager.AppImage` in the configured tools directory. Published the official x86-64 v2.6.3 file at that path without replacing an existing file. SHA-256 on the microSD matched `314b8fe6afb4ad7dcd06c66b6550c2771df7fce74593bfaf48ce6b1829c67a08`. Its AppImage runtime executed. Parser configuration, artwork and shortcut publication still require an interactive test. Rollback can remove this single new file after verifying its digest. [Official SRM release](https://github.com/SteamGridDB/steam-rom-manager/releases/tag/v2.6.3)

### Deployment candidate

The first candidate included build configuration and TypeScript sources. Commit `e12fbc6` moved those files into a companion source archive. After the complete Linux regressions, CI extracted the runtime ZIP and imported the backend in an isolated Python process. On the physical Deck the revised ZIP had 22 members, valid CRCs and 17 runtime Python/JavaScript files byte-identical to the previously tested candidate. A second mirror install with the revised package again verified the original NES digest and rejected its duplicate in preview.

The installable filename is `candidate/rom-library-m2.zip` inside the private device staging directory. Its SHA-256 is `ca3872f346206240a77e0fa95c33e53fd4db04cfbc66fb8b38136a73ee92d8d7`. The historical ZIP was renamed. The companion archive SHA-256 is `6108da777578f4e669b3f7ab39e39a4d09feffae5ad7dfa43af85fbf06ab54d9`. [Download the tested pair from the build run](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45300999912)
