# Local library commands

From the checkout, run `./rom-cli --library --help`. All library commands return JSON on stdout. Runtime failures return exit 1 and an error on stderr. Argument errors use argparse's usage text and exit 2. Read operations can inspect an empty library before initialization. Mutations initialize the private XDG data directory on demand. Keep XDG data on user-owned internal storage. Use the supplied feature branch installation instructions in the README.

```sh
./rom-cli --library platforms
./rom-cli --library consoles --platform retrodeck
./rom-cli --library install --platform emudeck --system gba --title "Demo" --region USA "$HOME/Downloads/demo.gba"
./rom-cli --library games
./rom-cli --library inspect 1
./rom-cli --library history
./rom-cli --library verify --platform emudeck --system gba
./rom-cli --library scan --platform retrodeck --system gba
./rom-cli --library reconcile --platform emudeck --system gba
./rom-cli --library export > catalog.json
./rom-cli --library backup "$HOME/manifest-backup.sqlite3"
```

**Source and destination.** Install accepts a local file or a direct file URL from Internet Archive or an authorized mirror. Use `--sha256 HEX` for a known source checksum. A bare filename with a unique allowed suffix can identify its system. Supply `--system` for ambiguous disc formats. Each install requires a platform choice. `paths` shows configured roots and availability. `--root` checks that the discovered root matches the expected storage path. Console directories must already exist. Library paths containing symbolic links require a physical-path configuration. On Linux directory handles stay pinned throughout file operations. Managed publication uses Linux no-replace rename, with a hard-link fallback. Legacy Bash downloads require hard-link support. Host write access and RetroDECK read access are checked separately. The software leaves platform configuration and Flatpak permissions under user control.

**Release metadata.** Supply a title, region, revision, language, edition or disc number when known. The default retains the source basename. A title or release label enables naming such as `Demo (USA) (Rev 1) (Disc 2).chd`. Language and edition are stored on the release. If names collide, choose another explicit title or cancel. Formats with external filename references, exact set names or archive extraction requirements are excluded. Local ES-DE systeminfo.txt, when present, narrows each console’s documented suffix list. Header checks cover recognized containers and common error responses. Headerless image identification still depends on user-supplied metadata.

**Duplicates and storage.** SHA-256 identifies content, releases own file descriptors, locations identify full paths, and installations connect those paths to a platform. The same canonical path can serve both platforms. Identical bytes at two independent roots share content metadata while retaining distinct locations. Register a shared path by installing it for the second platform under its existing name. An identical destination with a supplied matching SHA-256 can be registered without downloading again. A different existing file or an identical registered file under another name in the selected console causes an error. Choose the registered name, another platform/root, or cancel. A collection, URL or checksum cannot establish distribution rights.

**Inspection and recovery.** `games` shows recorded status and last verification. `verify` rehashes files. Ordinary scan/reconcile can reuse an installation hash after device, inode, size, modification time and change time all match. Untracked candidates and pending installs get hashed. Omitting `--system` scans the immediate children of each supported console in the selected root. Moves to unrelated roots, arbitrary nested folders or unsupported extensions require manual inspection. Missing and matching paths are reported as candidates. Hard-linked aliases at different names appear as duplicate paths.

The installer stages on the destination filesystem, copies bytes, checks the staged content, commits a pending record, publishes without replacement, syncs the directory on Linux, then rehashes the final file before marking the installation complete. A full disk, dropped connection or collision leaves the existing ROM intact. After interruption, first run read-only reconciliation. Run the following only after reviewing the findings.

```sh
./rom-cli --library reconcile --platform emudeck --system gba --confirm-pending
```

This confirms matching pending files, updates associated failed/interrupted history where possible and removes identified, inactive Linux worker staging files in that console. A missing pending installation can be retried using its original source and metadata. A staging file created immediately before its inode was recorded may need individual inspection and manual cleanup. A path reused by unrelated content requires manual resolution. Historical downloads from the interactive Bash search are outside the managed history. Managed transfers restart after failure.

**Database recovery.** Schema migrations run together in a write transaction. `init` applies pending supported migrations. Foreign keys, an eight-second busy timeout and WAL support concurrent readers. Use the online `backup` command with a new filename while the catalog is healthy. If SQLite reports corruption, close every CLI instance, preserve the entire manifest directory including WAL sidecars under a new name, and restore the verified backup into a fresh private manifest directory. Run `verify` against mounted libraries afterward. Exported JSON is versioned and intended for inspection. The application provides no JSON import command.

**Legacy behavior changes.** IA search, mirror browsing, the search-term syntax and multi-select remain available. IA subdirectories are flattened to a validated leaf. Private staging replaces cross-run aria2 continuation, and existing filename collisions stop the operation. Interactive listings target simple, trusted HTTP(S) directory indexes. Use the managed URL installer for redirect restrictions, transfer size bounds, integrity checks and history.

