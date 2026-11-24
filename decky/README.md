# ROM Library for Decky

ROM Library 0.2.0 is a hardware-validation build for a Steam Deck with an existing Decky installation. It uses the logged-in user's M1 catalog and supports EmuDeck and RetroDECK. Both suites use their configured ROM roots and the M1 format allowlist.

## Install or build

Download the feature branch's **rom-library-m2** CI artifact. Extract the outer GitHub artifact once and select the inner `rom-library-m2.zip` in Decky Settings → Developer → Install plugin from ZIP. Enable Decky developer settings if necessary. Use the same ZIP when testing a locally built copy. The plugin requests no root flag. The [official installation guidance](https://github.com/SteamDeckHomebrew/decky-loader) and [Decky sideloading notes](https://github.com/SteamDeckHomebrew/wiki/blob/main/user-guide/plugin-safety.md) describe the loader and external ZIP workflow.

From the repository root, with Node 22+, npm and Python available:

```sh
npm ci --prefix decky --ignore-scripts
npm --prefix decky run check
npm --prefix decky test
npm --prefix decky run build
python3 decky/package_plugin.py decky/rom-library-m2.zip --source-output decky/rom-library-m2-source.zip
```

Install the runtime ZIP containing the frontend bundle, Python backend, M1 library and license notices. CI publishes the corresponding frontend sources, vendored Decky API source, lockfile and build configuration in the sibling **rom-library-m2-source** artifact. TypeScript uses the official Decky React components and callable API. Development dependencies and Node stay on the build machine.

## Search, install and play

1. Open **ROM Library** in the Quick Access menu. Enter a title with the Steam keyboard (Steam + X), select a provider and optionally filter by console.
2. Choose a file, then its console and destination suite. For Archive, each source page represents an item. **More files in this item** pages through its supported files. Empty pages can occur after format filtering.
3. Review the source, filename, size, available checksum, duplicate warning and exact destination. Activate **I’m authorized · Download and install** to enqueue. Back returns to the previous selection. Collection membership supplies provenance only.
4. Open **Downloads** for progress and cancellation. Retry starts with fresh bytes. Cancellation stops being available when installation begins. A completed job has passed final file and manifest verification.
5. Reopen ES-DE in the selected suite, select the game and launch it there. Use the ES-DE metadata editor's scraper for artwork. For Steam shortcuts use Steam ROM Manager's parser, preview and save workflow. **Installed library** shows recorded installation paths and offers read-only console checks, including consoles with no recorded games.

## Optional mirror

Internet Archive works independently of a mirror. For a user-controlled mirror, create `mirror.json` in this plugin's Decky settings directory in Desktop Mode, then reload the plugin. Decky supplies the directory as `DECKY_PLUGIN_SETTINGS_DIR`. The configuration must belong to the SteamOS account and allow writes only by its owner.

```json
{"base":"https://mirror.example.org/roms/","allow_private":false}
```

For your own LAN or loopback server, set its exact base URL and explicitly set `allow_private` to `true`. Use a trailing slash and a simple HTML directory listing of ROM files or one level of supported console folders. A selected folder such as `gba/` narrows supported files. Credentials, arbitrary child pages, external redirects and query-string links are unsupported. Mirror indexes often omit digests and sizes; transfer counts become available from HTTP where supplied.

## Recovery and troubleshooting

- **No destination or format unavailable.** Confirm the suite is installed and initialized, its actual ROM directory is mounted, the console directory exists, and the account can write it. Check RetroDECK's effective Flatpak access. The backend never changes grants or creates a missing ROM directory.
- **Destination changed.** Remount the original medium, or search again and explicitly confirm the new location. The job stores the directory path, device and inode at confirmation.
- **Existing filename or checksum match.** The installer checks the filesystem and rejects conflicting content. For a destination with unknown source SHA-256 the plugin stops before transfer. A known SHA-256 can validate an existing file. Use the library view to inspect the recorded installation.
- **Interrupted or cancelled job.** Review the destination, then use **Confirm retry**. On Linux the next attempt can reclaim that job's recorded abandoned staging file after checking owner and inode. Read-only preview and the M1 CLI recovery tools are available for further inspection. A process killed before the temporary file identity was recorded can leave a part requiring manual review.
- **Untrusted account or storage.** The plugin refuses root, mismatched Decky/OS accounts and linked or shared-write catalog directories. Keep the manifest and job database in private user storage. The standalone CLI remains usable without loading Decky.

## Removal and rollback

Let installation finish, cancel queued transfers and unload the plugin through Decky. Use the CLI's online `--library backup NEW_FILE` command before testing. For a complete rollback snapshot with every writer stopped, copy the entire user-owned `rom-cli-sd` data directory, including SQLite sidecars and job history, to a separate backup. Decky's uninstall action removes the plugin package. ROMs and the shared M1 manifest persist. Reinstall the previous trusted ZIP or continue with the standalone CLI. Restore a backup into a fresh data directory while all writers are stopped. Review any files installed since the backup separately. No system partition edits are required.

## Physical acceptance matrix

| Check | EmuDeck | RetroDECK |
|---|---|---|
| Record device and software inventory | SteamOS, Decky, ES-DE and EmuDeck recorded | SteamOS, Decky and RetroDECK recorded |
| Discover configured ROM root and console access | Verified on microSD | Verified on internal SSD and inside Flatpak |
| Controller/OSK search, focus, Back, confirmation and progress | BLOCKED | BLOCKED |
| Authorized fixture installation and emulator launch in Desktop Mode | Passed in disposable library with installed ES-DE and Mesen | Passed in initialized suite with bundled ES-DE and Mesen |
| Reconciliation after physical storage loss | Pending | Pending |
| Remove/remount test medium, verify failure and retry, unload/reload | BLOCKED | BLOCKED |

Run read-only discovery and backup first. Use an approved disposable library and removable medium for write and interruption tests. Record versions, paths, file digests, job state, launch outcome and observed UI latency for each row. An unattended action against a personal ROM collection is outside this procedure.

Voice and TTS remain M3. See the repository's M2 verification report for host measurements and residual risks.


## Hardware-validation build

The physical SSH session and tested candidate digest are recorded in the [hardware report](../docs/m2-steamdeck-hardware.md). If removable storage disappears during staging cleanup, restore the original medium, unload the plugin, verify the worker exited and reconcile the original attempt before retrying. The installed suites may already manage a personal library. Use the isolated test fixture for command-line verification and the official ZIP installation screen for loader acceptance.
