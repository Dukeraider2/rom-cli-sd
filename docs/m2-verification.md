# M2 verification and release decision

**Physical SSH validation has started. Production and Gaming Mode acceptance remain open.** The original measurements below predate access to the Deck. The new device report records SSD and microSD results, installed components and remaining interactive checks. [Device results](m2-steamdeck-hardware.md) · [Device procedure and rollback](../decky/README.md)

## Implementation and compatibility

- Both suites follow the same search → file → console → suite → confirmation → persistent job → verified installation workflow. The worker uses M1's installed format checks, pinned console directory, SHA-256 identity, no-replace publication and final filesystem verification. A temporary HTTP-server test exercises that RPC sequence for each suite; the RetroDECK configuration and Flatpak probe are fixtures.
- Internet Archive uses actual advanced-search and metadata schemas with bounded metadata and item/file pagination. The mirror searches the configured directory index and one level of supported console directories. Unsupported suffixes and invalid names are excluded. The frontend sees source/item labels and opaque result IDs. Public IA availability, site-specific mirror behavior and distribution rights cannot be established by these fixtures.
- The plugin implements twelve operations behind one version-checked RPC with exact argument allowlists. Version 1 replies contain a success flag and either data or a typed error. Requests support suite/system enums, page numbers, query text, confirmation tokens and result/job/game identifiers. Paths and HTTP targets originate in the backend.
- Package version 0.2.0 pins @decky/api 1.1.3, @decky/ui 4.11.0, @decky/rollup 1.0.2, TypeScript 5.6.3 and Rollup 4.53.3. Decky's plugin manifest requests API version 1 with an empty flags array. React and UI components are supplied by Steam/Decky at runtime. Exact installed hardware/software version compatibility awaits physical testing. [Contracts and official sources](m2-design.md)
- Session-side SQLite stores job identity, original confirmed metadata, destination identity, progress and the associated M1 attempt. A Linux file lock serializes plugin ownership. The queue holds up to 16 unfinished jobs and runs a single worker that exits when drained. Previously queued jobs resume scheduling on plugin load. Interrupted active jobs require an explicit retry. Up to 200 terminal jobs plus the current active set are retained around enqueue-time pruning.
- Post-install play is through the selected suite. Standard ES-DE scraper and Steam ROM Manager workflows remain manual. Voice and TTS remain outside M2.

## Verification

Run from the repository root:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B tests/benchmark_m2.py
bash -n rom-cli && bash -n PKGBUILD
bash rom-cli --version && bash rom-cli --library platforms
npm ci --prefix decky --ignore-scripts
npm --prefix decky run check
npm --prefix decky test
npm --prefix decky run build
python3 decky/package_plugin.py decky/rom-library-m2.zip
```

Windows ran 33 Python tests with 30 passing and three Linux-only skips. The frontend passed three tests, including execution of the actual React selection flow against mocked Decky controls and RPC. Back from confirmation produced zero enqueue calls; subsequent explicit activation enqueued once. Type checking, Rollup bundling and ZIP integrity checks passed. The [implementation CI](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45282735952) runs the Linux-only cases, existing M1 suite, M2 regressions, frontend checks, baseline launcher checks, benchmark and packaging.

Coverage includes paginated indexes, unsafe/unavailable sources, unsupported file metadata, privacy policy, cross-user startup checks by code review, wrong types/operations, expired selection IDs, explicit confirmation, idempotent replay across restart, bounded concurrent jobs, cancelled network reads, interruption on unload, retry from fresh bytes, changed directory identity, checksums, truncated HTTP and prepublication cancellation. M1 tests cover disk capacity, symlinks, concurrent publication, shared libraries and killed staging workers. Simulated failure and real card removal have separate evidence gates. Physical controller focus, Steam rendering latency, live Decky install/upgrade/rollback, actual Flatpak grants and both emulator launches remain outstanding.

## Measured resource use

Linux CI at `19b2654` passed all 33 Python tests in 4.079 seconds and all three frontend tests. The ZIP artifact upload succeeded.

The synthetic benchmark transfers 8 MiB through loopback, verifies the final file, commits both databases and polls until completion. The temporary HTTP server shares the process. RSS includes Python, SQLite and the server; the peak is sampled. Windows uses process I/O counters and Linux uses procfs write_bytes, which have different accounting. The reported throughput includes hash and publication overhead. [Linux benchmark run](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45282302188)

| Measurement | Linux CI, CPython 3.14.4 | Windows 11 build 26300, CPython 3.15.0 |
|---|---:|---:|
| End-to-end time | 53 ms | 139 ms |
| Throughput | 149.86 MiB/s | 57.72 MiB/s |
| CPU seconds / one-core utilization | 0.046 / 86.7% | 0.047 / 33.8% |
| RSS before enqueue / sampled peak | 30,011,392 / 33,267,712 B | 32,452,608 / 35,201,024 B |
| Process write counter delta | 9,048,064 B | 8,771,692 B |
| Queue mutation statements including initialization | 11 | 11 |
| Local mirror search RPC | 1.48 ms | 2.73 ms |
| Median progress RPC, 50 calls | 0.377 ms | 1.657 ms |
| Idle CPU over one second / active transfer worker | 0.14 ms / none | 0.00 ms / none |

The UI checks active jobs once per second while the downloads screen is mounted. Progress persistence is throttled to twice per second plus terminal byte counts. The headless React test completed the selection/Back/confirmation sequence in about 23–26 ms on the Windows host. This includes the test harness and mocked RPC. Hardware input-to-frame latency and power usage remain unmeasured. M1's 10,000-game full list took 17.46 ms on the Windows host; M2 pages library results in groups of 20. The two measurements exercise different operations.

## Independent review

| Dimension | Score | Evidence and limit |
|---|---:|---|
| Architecture | 8/10 | M1 installer reused; explicit confirmation and queue boundaries |
| Security | 8/10 | User identity checks, origin-scoped pinned addresses, no-replace install |
| Functional completeness | 8/10 | Host search-to-install and controller flow; physical acceptance outstanding |
| EmuDeck compatibility | 6/10 | Configured-root fixtures passed; actual install/launch outstanding |
| RetroDECK compatibility | 6/10 | Both schemas supported; Flatpak grant and launch require hardware |
| Resource efficiency | 8/10 | On-demand worker, bounded queue, progress throttling and paging |
| Deployment readiness | 5/10 | ZIP builds and passes host CI; live loader lifecycle/rollback outstanding |

The independent reviewer assessed commit `a03d866` after fixes for unbounded unload, stage ownership on retry, error envelopes, empty-library reconciliation and controller test coverage. No open critical or high-severity issue was identified in that review. Commit `19b2654` subsequently enforced a length-or-digest boundary for fresh transfers, preserved enqueue replay across session restarts and surfaced filename conflicts at confirmation.

### Remaining limits

- Closing the plugin interrupts its active HTTP sockets. New connections use bounded DNS waits and socket timeouts. An install already in publication can finish after the four-second worker join; the lock remains held while it finishes. A blocked filesystem syscall or OS resolver cannot be forcibly completed by Python. Validate shutdown, reload and storage loss on real hardware.
- Source checksums verify bytes against provider metadata. HTTP mirrors, headerless formats, and a changed upstream file having the same length without an independent digest still require trust in the source. Downloads restart from byte zero. LAN access requires an explicitly configured origin and private-network permission.
- M1 has a small crash window between creating a temporary part and recording its identity. Retry only cleans a journaled, matching, abandoned part. Unjournaled files require manual inspection. A file published just before unexpected shutdown requires verification before calling the job complete.
- The UI's reconciliation preview is read-only and capped at one console, 1,000 entries, 100 displayed findings and a cooperative time budget. Use the CLI for larger scans. Archive searches intentionally restrict collections and supported single-file formats. Mirror browsing supports simple directory indexes.
- The frontend test uses the pinned development-only React test renderer, which emits a deprecation notice. The dependency is excluded from the plugin's runtime bundle.

## Delivery

Branch: `feature/emudeck-retrodeck-integration`. Baseline: `7af3ecd`.

| Commit | Work |
|---|---|
| `20c4a80` | Investigation, reuse plan and compatibility gates |
| `6375bb5` | Search providers and scoped HTTP |
| `6c3dfbd` | Durable downloads and M1 transfer integration |
| `9d984bb` | Unprivileged Decky backend and versioned request contract |
| `e248eae` | Controller workflow, package and Linux CI |
| `a03d866` | Review remediation, React flow, benchmarks and integration tests |
| `19b2654` | Idempotent replay, conflict preview and transfer completeness |

[Implementation file diff](https://github.com/Dukeraider2/rom-cli-sd/compare/7af3ecd...19b2654). The final documentation commit adds the device procedure, updates the evidence checklist and records this assessment. No production release or pull request was created.


## Physical SSH validation

The Galileo device passed 33 backend tests, real EmuDeck path discovery, live Archive metadata pagination and disposable SSD/microSD mirror transfers. EmuDeck ES-DE and RetroDECK each listed and launched the test cartridge using Mesen in separate SSH-controlled desktop tests. RetroDECK completed its official first run and verified read-write access from inside its Flatpak. Interactive Gaming Mode, Decky ZIP installation and controller acceptance remain open. [Device inventory, recovery and measured results](m2-steamdeck-hardware.md)

### Live acceptance gates at preflight

| Gate | Status | Evidence still required |
|---|---|---|
| A. Live installation | BLOCKED | Official ZIP installation, frontend render, backend UID, versioned RPC and startup job count |
| B. Controller and OSK | BLOCKED | Physical D-pad, OSK edit, focus recovery and Back with unchanged job count |
| C. EmuDeck end-to-end | BLOCKED | Confirmed live job in the configured microSD root, library entry and launch |
| D. RetroDECK end-to-end | BLOCKED | Confirmed live job in the internal root, library entry and launch |
| E. Cancellation and recovery | BLOCKED | Live active cancel, retry, controlled interruption and loader unload/reload |
| F. Performance and stability | BLOCKED | Gaming Mode timings, resource recovery, frame times and power observations |
| G. Security and regression | BLOCKED | Regression suite and independent static review passed; live startup identity, confirmation and worker invariants await observation |

**Release held.** The staged candidate and recovery snapshots were verified. At the last observation the active session was KDE Desktop and ROM Library awaited installation through Decky. [Device commands, prior desktop launches and preflight observations](m2-steamdeck-hardware.md)

**Live gate update.** Gate A failed on installed 0.2.0. The operator saw the plugin, but the live loader logged a missing standard-library import before backend initialization. The 0.2.1 correction passed CI and its on-device extracted-package regression. Gate A awaits the corrected version's live-loader retest. Gates B–G remain blocked and the release remains held. [Live failure and replacement checksum](m2-steamdeck-hardware.md)
