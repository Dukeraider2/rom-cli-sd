# M2 — Steam Deck Gaming Mode integration

**Recorded:** 2026-11-23  
**Status:** HOST IMPLEMENTED / PHYSICAL ACCEPTANCE BLOCKED
**Priority:** P0 for the first controller-operated release candidate  
**Working branch:** `feature/emudeck-retrodeck-integration`  
**Predecessor:** [M1 manifest and dual-suite foundation](M1-manifest-and-dual-suite-foundation.md)  
**Backend interface planning:** [Decky integration notes](../../decky/README.md)  
**Evidence baseline:** [M1 verification report](../verification.md)

## Mission

Checked implementation rows refer to branch and fixture evidence in the [M2 verification report](../m2-verification.md). Combined requirements that include unperformed hardware checks remain open. The [device matrix and rollback procedure](../../decky/README.md) cover both suites.

Deliver a controller-first Steam Deck Gaming Mode workflow for **authorized** homebrew, public-domain, openly licensed, and otherwise lawfully accessible user-provided files:

**search → choose result → choose system and EmuDeck/RetroDECK destination → inspect duplicates → explicitly confirm → download with progress/cancel → verify → install → show how to discover/play.**

M1 already implements the SQLite catalog, configured suite discovery, a limited single-file format allowlist, safe managed installation, reconciliation, and a JSON-producing CLI. Its existing interactive Bash downloader and managed installer are not yet one end-to-end workflow. M1 host tests are not proof of physical Steam Deck compatibility. M2 closes that gap and adds a Decky Loader frontend without weakening the existing backend safety model.

## Non-goals and boundaries

- No automatic acquisition of copyrighted material merely because it appears on Internet Archive. Source metadata does not establish a redistribution license.
- No general-purpose file manager, arbitrary URL downloader, shell/SQL execution bridge, or unrestricted filesystem browser exposed through Decky.
- No automatic BIOS, arcade set, multi-disc playlist generation, archive extraction, 3DS installation, or other formats outside the verified M1 allowlist. Expand only with independent validation.
- No automatic ES-DE scraper invocation, Steam ROM Manager configuration mutation, or claims that games immediately appear in Steam. Document supported manual refresh steps.
- Local STT push-to-talk (whisper.cpp) and optional Piper TTS are **M3**, not M2 release blockers.
- Do not merge to `master` or publish a production plugin before the real-device release gate.

## Stage 0 — Rebaseline and hardware gate

- [ ] Audit latest branch, M1 verification report, M1 residual risks, current official Decky plugin template/API, and installed SteamOS/Decky/EmuDeck/RetroDECK versions. Record URLs, versions, and uncertainties.
- [x] Produce a non-destructive physical Steam Deck test plan with rollback and data backup instructions. Do not modify actual game libraries without approval.
- [ ] Test read-only suite discovery and configured internal/microSD/custom roots; test RetroDECK Flatpak effective visibility and permissions; test unplug/remount/mount identity behavior.
- [ ] With user-authorized synthetic/homebrew fixtures, test managed install, duplicate detection, integrity check, reconciliation, and actual emulator launch in each installed suite.
- [x] Record test results per suite and storage medium. If no Deck is available, mark hardware checks **BLOCKED** and continue with mock tests; do not claim them passed.

## Stage 1 — Shared search and managed job service

- [x] Introduce provider abstraction for Internet Archive metadata search and explicitly configured user-owned mirror search. Bounded queries, pagination, timeouts, source provenance, canonical opaque result IDs, and license/provenance notices. Never infer that collection membership proves legal availability.
- [x] Reuse verified M1 installer and manifest. Resolve provider result IDs to vetted downloads server-side; do not pass arbitrary URLs, paths, or shell commands from the UI.
- [x] Add a bounded, durable job queue with states such as `queued`, `resolving`, `downloading`, `verifying`, `installing`, `completed`, `failed`, `cancelled`, `needs_attention`. Define valid transitions, idempotency keys, crash recovery, and cleanup policy.
- [x] Add byte-level progress where the source permits it, cancellation, retry/resume policy based on content identity/ETag or checksums, duplicate and collision choices, and typed errors. Never resume bytes against an unverified changed source.
- [x] Keep jobs user-owned, with explicit per-download size/concurrency/disk limits. Default to one active transfer; benchmark before raising concurrency.
- [x] Make source access safe: scheme validation, redirect policy, URL/host restrictions, timeout and response size limits, metadata sanitization, and protection against unintended access to local/internal endpoints. A private mirror must be explicitly configured and authorized.
- [x] Preserve legacy Bash interactive Internet Archive and mirror workflows. Where possible share validation rules, but do not silently change user behavior.
- [x] Design no mandatory always-on system daemon. If a worker must outlive a single UI call, document its user-session lifecycle, stop/start behavior, recovery, idle overhead and security boundaries.

## Stage 2 — Narrow, versioned Decky backend contract

- [x] Use current official Decky Loader plugin template and supported Python backend/TypeScript frontend conventions; pin compatible dependency versions.
- [x] Define versioned request/response schemas, typed error codes, bounded input sizes, and permission checks for: `list_platforms`, `list_consoles`, `search`, `get_result`, `list_games`, `inspect_game`, `enqueue`, `list_jobs`, `get_progress`, `cancel`, `retry`, `reconcile_preview`.
- [x] Accept opaque result/job IDs, platform/system enums, explicit confirmation tokens, and validated metadata only. Backend derives destinations from verified configured roots.
- [x] No RPC accepting raw filesystem paths, arbitrary shell commands, SQL, unrestricted URLs, or arbitrary CLI argument arrays.
- [x] Prevent duplicate enqueue and unauthorized cross-user access; ensure one plugin cannot accidentally run as root or write another user's library.
- [x] Implement rate-limited progress updates/polling and clear UI-facing errors; avoid excessive SQLite writes.

## Stage 3 — Controller-first Decky frontend

- [ ] Controller-operated search, results, system/platform selection, explicit confirmation, duplicate warnings, job queue/progress/cancel/retry, installed library view, and read-only reconciliation findings.
- [x] Clear distinction between EmuDeck and RetroDECK. Show discovered root, storage availability and unsupported formats; require user choice when both exist.
- [x] Safe default: no transfer or file modification until explicit user confirmation. No silent overwrite or delete.
- [ ] Support Steam Deck on-screen keyboard, focus order, Back/B cancellation, screen-reader-friendly labels where possible, small-screen layouts, long names and error recovery.
- [x] Display post-install guidance for ES-DE library refresh, scraper usage and optional Steam ROM Manager import; do not claim automatic artwork.
- [x] Package as a user-space Decky plugin; document installation, removal, configuration, backup and rollback. Never modify SteamOS read-only system files.

## Stage 4 — Test, security and performance gates

- [x] Automated unit tests for provider parsing, source provenance, invalid input, state transitions, cancellation, idempotency, restart/recovery, retry, queue limits and typed errors.
- [ ] Integration tests using a local controlled HTTP server and synthetic freely redistributable fixtures: truncation, redirects, timeouts, content change, checksum mismatch, duplicate names, disk full, missing microSD, Flatpak denied, symlink/path traversal, concurrent requests and user cancellation.
- [x] Headless Decky backend contract tests and frontend build/typecheck/tests, with mocked controller/UI interactions. Run CI on Linux without actual ROMs or BIOS.
- [ ] Measure Steam Deck CPU, RSS, idle overhead, SQLite writes, download throughput, UI input-to-response latency, polling frequency, and behavior during game launch; compare against M1 baseline. Do not invent thresholds without measurements; set and justify limits from observed results.
- [x] Independent security and architecture review with documented findings, fixes, remaining risks and explicit release decision.

## Acceptance criteria / definition of done

- [ ] One end-to-end **authorized** search-to-installed-homebrew flow works in Gaming Mode using only controller/on-screen keyboard, without terminal interaction.
- [ ] EmuDeck and RetroDECK each pass their own real-device install and launch tests (or release remains **BLOCKED**, not complete).
- [x] Correct configured console destination is selected; unavailable/unauthorized storage fails safely.
- [ ] Progress, cancellation, retry, restart recovery, duplicate and collision handling work without silent overwrites or stranded misleading `completed` records.
- [ ] Decky RPC is narrowly scoped, validated and unprivileged; no arbitrary execution, path, URL or SQL access.
- [x] Existing M1 library CLI and legacy Bash download behavior pass regression tests.
- [ ] CI, benchmarks, physical-device test matrix, security review, and installation/rollback docs are committed.
- [x] No unapproved changes to `master`, real user ROM collections, system packages, Flatpak grants, or EmuDeck/RetroDECK configuration.

## Development and governance

Follow **Stage 1 spec + official sources → Stage 2 rationale, implementation, tests and measured resource use → Stage 3 independent review and scored readiness**. Make small, test-backed commits to `feature/emudeck-retrodeck-integration` or a descendant M2 feature branch. Do not force-push. Maintain GPL-3.0 notices and upstream history. SteamOS user-space only; no system `pacman`, root persistence or read-only image changes. **Podman only** if containers are needed; no Docker. Prefer lean Python standard library where practical, minimize dependencies, and do not add always-on overhead without measured justification.

## Codex handoff and reporting

1. Reopen M1, verification, this milestone, and Decky notes from the current repository head. Inspect actual code before editing.
2. Document official Decky/SteamOS and platform references. Establish testable backend contract and mock fixtures first.
3. Implement provider search + persistent job manager + secure API before UI; then create controller-friendly Decky frontend. Keep CLI functional at every step.
4. Use automated tests for host work. Record physical Steam Deck checks separately and request user participation when hardware access is required; never simulate a passing hardware test.
5. Commit each tested phase and report commit hashes, changed files, CI runs, known limitations, security review, CPU/RAM/disk/latency measurements, and explicit M2 acceptance status.
