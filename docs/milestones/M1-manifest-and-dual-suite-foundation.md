# M1 — Manifest-driven ROM library foundation

Recorded: 2026-11-23
Status: PLANNED (not implemented, not validated)
Branch: feature/emudeck-retrodeck-integration
Parent spec: docs/emudeck-retrodeck-integration.md
Priority: P0

## Objective

Implement a lean, secure local ROM catalog and installer for Steam Deck with **equal first-class EmuDeck and RetroDECK support**, while keeping the existing standalone Bash CLI functional. The manifest is authoritative for app-managed metadata; the actual filesystem is authoritative for whether files exist. This milestone records the implementation requirements, not completed code.

## Product decisions

- Persistent SQLite manifest under the XDG data directory: $XDG_DATA_HOME/rom-cli-sd/manifest.sqlite3, or ~/.local/share/rom-cli-sd/manifest.sqlite3 if XDG_DATA_HOME is unset.
- Separate concepts: game, release, ROM file, physical storage location, installation, download, artwork. Support multiple discs and one physical file shared between platforms.
- Store original filename and normalized filename separately from display title. Default naming guideline: Game Title (Region) (Revision) (Disc).extension. Preserve format-specific filenames (arcade sets, BIOS, playlists).
- Discover actual EmuDeck and RetroDECK paths from verified configuration; support internal, microSD, custom roots and Flatpak access checks. Do not assume identical layouts.
- Treat artwork refresh and Steam ROM Manager import as separate workflows; installing a ROM does not guarantee automatic scraping or Steam integration.
- Future Decky Loader UI consumes a constrained backend API; standalone CLI must not depend on Decky.
- Future optional offline, push-to-talk STT for spoken game searches (evaluate whisper.cpp) and optional TTS (evaluate Piper). No continuous listening or automatic downloads.
- Download authorized homebrew/openly licensed content and user-controlled mirror files only, retaining existing source capabilities.

## Stage 1 — Research and specification

- [ ] Audit upstream Bash downloader v1.1.1, including download failure handling, href parsing, collisions, unsafe names, redirects, and extraction concerns.
- [ ] Verify official EmuDeck and RetroDECK install/config discovery, each console's folder names, supported formats, and Flatpak permissions. Document evidence and unknowns, not guesses.
- [ ] Produce source-backed compatibility matrix and read-only detection algorithm.
- [ ] Verify current Decky plugin API for eventual frontend design; defer UI implementation.

## Stage 2 — Implementation (incremental commits)

### First deliverable: SQLite manifest
- [ ] Create schema/migrations for games, releases, rom_files, installations, downloads, artwork, and any required relations.
- [ ] Track system, region, revision, disc, source, original/installed filename, format, size, SHA-256, source checksum (if any), status, paths, timestamps, scraper IDs and artwork paths.
- [ ] Enforce foreign keys, uniqueness, indexing, transactional updates, busy timeout, backups, schema upgrades, recovery handling, and suitable WAL behavior.
- [ ] Implement query and mutation layer, command-line inspection, and optional versioned JSON export.
- [ ] Unit tests for relationships, multi-disc releases, shared files, duplicates, migrations and failure recovery.

### Platform adapters and safe installer
- [ ] Detect neither/one/both emulation suites, configured ROM roots, unavailable removable media, and write/access permissions; explicitly ask when both are installed.
- [ ] Use verified per-suite/per-system path and extension mappings; refuse unknown systems and unsupported formats.
- [ ] Download to private staging, validate source metadata, format, filenames, capacity, archive limits and integrity, then safely finalize without silent overwrites.
- [ ] Prevent path traversal, symlink escapes, zip-slip and archive bombs; protect against partial copies and interrupted downloads.
- [ ] Design recoverable DB/filesystem workflow: an SQLite transaction and a filesystem move cannot commit atomically together. Use atomic rename only on the same filesystem; cross-device copies need verified staged finalization.
- [ ] Track installation into EmuDeck, RetroDECK or a shared library without double-counting physical files.
- [ ] Implement read-only-by-default reconciliation for missing, modified, renamed and untracked ROM files; no automatic deletion.

### CLI and future API
- [ ] Preserve original Internet Archive and self-hosted mirror workflows where practical.
- [ ] Add platform discovery, path inspection, game listing, integrity checking, duplicate lookup, reconciliation, history and JSON output.
- [ ] Document a constrained backend interface for Decky. No arbitrary shell execution from the frontend.
- [ ] Voice and artwork scraping engines are deferred; only define their integration boundaries now.

## Stage 3 — Verification and review

- [ ] Mock installation tests: EmuDeck only, RetroDECK only, both, neither, internal, microSD, custom paths, invalid configuration and inaccessible Flatpak roots.
- [ ] Security tests: malicious filenames, traversal, symlinks, malformed archives, disk full, disconnected SD card, interrupted download, checksum failure, collisions and shared ROM folders.
- [ ] Synthetic benchmarks for 1,000 and 10,000 games; measure database size, query latency, CPU, memory, and targeted scan time.
- [ ] Independent architecture/security review with explicit issues, evidence, and readiness ratings.
- [ ] Validate on a physical Steam Deck before claiming full platform compatibility.

## Mandatory constraints

- Lightweight Python standard-library orchestration (sqlite3) is preferred; avoid always-on services and unnecessary dependencies.
- SteamOS user-space only: no changing read-only partitions, permanent root, or system package manager installs without approval.
- No Docker; use Podman only if test containers are justified.
- Preserve upstream GPL-3.0 obligations. Do not force-push or merge to master without approval.
- Commit small, tested changes on feature/emudeck-retrodeck-integration.
- Repository Issues were disabled when this milestone was created, so this document serves as the tracking record.

## Codex handoff

1. Read the existing integration spec and audit the repository.
2. Verify official references first; document uncertain platform-specific details.
3. Implement the SQLite manifest and tests as the first executable milestone. Continue to read-only adapters, safe installer, reconciliation and CLI in independently testable increments.
4. Keep Decky, STT and TTS as later phases; document their backend contracts, not untested functionality.
5. Report exact commits/files, tests, performance, risks, blocked hardware checks and remaining tasks. Never claim proposed or mocked functionality is production verified.

## Exit gate

M1 can be marked complete only after code and automated tests exist for the manifest, both verified path adapters, the safe install/reconcile CLI, and committed review/benchmark results. Production-level dual-suite compatibility remains gated on physical Steam Deck tests.

**Recorded status: SPECIFICATION LOGGED ONLY; executable implementation not yet done.**
