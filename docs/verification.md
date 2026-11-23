# M1 verification and release assessment

As of November 23, 2026, the feature branch is ready for supervised Steam Deck testing. Current implementation commit: `8470743`. The [Ubuntu run](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45275576991) passed all 23 tests in 1.055 s, the shell syntax checks and both launcher smoke checks. The Windows run passed 20 tests in 1.343 s with three Linux-specific skips. All fixtures used temporary directories and synthetic bytes.

```sh
python3 -B -m unittest discover -s tests -v
bash -n rom-cli && bash -n PKGBUILD
./rom-cli --version && ./rom-cli --library platforms
python3 -B tests/benchmark.py
```

## Coverage

The suite exercises SQLite initialization and upgrade, rollback, foreign keys, backup, corruption detection, two releases and multiple discs, two suite references to one location, neither/either/both suite configurations, inaccessible Flatpak and missing storage, validation of names and installed formats, staging failures, insufficient capacity, checksums, collisions, interrupted HTTP responses, concurrent reservations and no-replace publication. Linux tests kill a real staging worker, reconcile its orphaned transfer, exercise symlink checks and run the Bash IA/mirror entry points with deterministic source/selection fixtures. The HTTP integration test uses a real local server. Reconciliation fixtures cover unknown files, moves and renames within a console, duplicates, modified files and missing paths. Coverage is assessed by scenarios; no line-coverage percentage was measured.

Still unverified on-device: physical SSD and microSD install/unplug/remount under I/O, effective Flatpak grants/denials, permissions on actual user installations, the installed versions of both suites, launching representative games, ES-DE scraping and Steam shortcut import. Live public IA service and external mirror availability were outside this test. The Arch package recipe was syntax-checked only. A source checkout is the tested install layout.

## Performance

Windows 11 build 26300, AMD Ryzen 7 5800X3D, CPython 3.15.0, SQLite 3.53.4. Synthetic catalogs populated one game, release, content, physical location and installation per title. The selected console held 100 eight-byte files. Measurements use a warm process, including five full lists, 101 lookups of each kind and five targeted scans. A separate traced scan measured peak Python heap. Initialization is a single observation per catalog.

| Operation | 1,000 games | 10,000 games |
|---|---:|---:|
| Initialize empty catalog | 7.63 ms | 7.21 ms |
| List all joined installation rows, median | 1.27 ms | 17.46 ms |
| Indexed title lookup, median | 0.005 ms | 0.005 ms |
| Indexed SHA-256 lookup, median | 0.004 ms | 0.004 ms |
| Targeted scan, median | 97.36 ms | 101.37 ms |
| CPU time, entire timed query/scan batch | 500 ms | 609 ms |
| Peak traced Python allocations, separate scan | 1,267,087 bytes | 1,267,039 bytes |
| Checkpointed database size | 1,163,264 bytes | 10,813,440 bytes |

Each scan read 800 bytes of ROM contents plus filesystem metadata. Database size excludes transient WAL and SHM files. These measurements cover backend operations. Process RSS, physical I/O counters, UI serialization, large-disc hashing and removable-media latency need separate device measurements. No backend process remains after the CLI exits.

## Independent review

The initial review scored architecture 6/10, security 6/10 and deployment readiness 3/10. It found a concurrent reservation race, abandoned staging, weak payload checks, unnecessary preflight downloads, writes during read-only scans and a shared-root classification error. Fixes added a persistent worker ledger, two-phase installation, Linux worker identity checks, stat-keyed hashes, explicit full verification, known-hash lookup before transfer, a read-only database path, container checks and shared-file reporting.

The independent follow-up at `4f3621b` scored **architecture 8/10, security 7/10, Steam Deck release readiness 5/10**. Subsequent commit `8470743` added native Linux no-replace rename with a hard-link fallback, limited recovery to the latest matching attempt and added regression coverage. The scores apply to the review snapshot. Device verification remains the release gate.

### Residual risks and scope

- A process killed between creation and recording of its temporary file can leave an unjournaled hidden part. Review such files manually after stopping all library workers. A pending record with a missing final file requires retry using the same source and metadata.
- The installer handles untrusted remote names and file contents inside user-controlled library directories. A local actor with write access to the same directory can still replace entries after verification. Hard-linked aliases and custom ES-DE nesting may require inspection. A mount replaced by another device at the identical configured path requires user attention.
- A remote checksum checks bytes against the supplied digest. Container signatures and installed suffix lists provide limited validation. Running the emulator and confirming rights to distribute content are separate steps.
- Managed URL transfers cap each item at 16 GiB and perform no extraction. Archives, exact-name arcade/BIOS layouts, companion references, generated playlists and 3DS install workflows need dedicated validation. Disc metadata and individually validated single-file disc images are supported.
- Existing Bash downloads use a simple mirror index parser and trusted mirror redirects. They stage privately and reject collisions. Use the library installer for managed restrictions. Synchronous transfers record terminal bytes/status; active byte-level progress, cancellation and a queue manager belong to the Decky milestone.
- Host and CI tests exercise filesystem safety, synthetic configuration discovery and local HTTP. They provide no emulator launch or real Steam Deck compatibility certification.

## Delivery history

| Commit | Change |
|---|---|
| `f10ae01` | Audit, upstream evidence and console matrix |
| `20c91ea` | SQLite schema, migration, backup, export and tests |
| `0c33cbd` | Discovery and metadata-aware naming |
| `9380280` | Installation, reconciliation and CLI |
| `6a13dd7` | Concurrency, interrupted transfers, hash cache, Bash hardening, CI and benchmarks |
| `4f3621b` | Installed format definitions, targeted root scans and Bash fixtures |
| `8470743` | No-replace rename, recovery history and additional regressions |

The [implementation diff](https://github.com/Dukeraider2/rom-cli-sd/compare/379da0e...8470743) lists the exact changed files. GPL-3.0 licensing and upstream history are preserved. The [Decky plan](../decky/README.md) covers the constrained backend API, download jobs and optional push-to-talk search.

