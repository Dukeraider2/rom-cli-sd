# M3A real offline transcription benchmark: first measured comparison

**Date:** 2026-11-23  
**Decision:** **COLLECT MORE EVIDENCE**. Neither model is approved as a default or advanced to M3B.  
**Source:** [GitHub Actions real CPU run](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45285611032), commit `7a079674`.  
**Machine-readable compact extract:** [m3a-results.json](m3a-results.json).  
**Complete JSON and fixture manifest:** download `m3a-real-synthetic-cpu` artifact from the run.  
**Reproduction:** [M3A instructions](../experiments/m3a/README.md).

## Conditions and limits

The pinned `whisper.cpp` revision `96ec4d9823e9d0211944172da35f9f29134af990` was built CPU-only on an Ubuntu 24.04 GitHub Actions host (Linux 7.0.0-1017-azure, AMD EPYC 9V74, four allocated logical CPUs, Python 3.12.3). Both upstream model SHA-1 values were verified before testing; the exact SHA-256 values appear below and in the JSON extract.

All 14 spoken clips were **locally synthesized** with eSpeak 1.48.15, including two with deterministic background noise. Silence and noise-only clips made 16 total. Each was run twice against each model (32 runs per model, 64 total). No human speech, Steam Deck microphone, controller focus, game-load impact or battery/power measurement was available. Results are **host-only, synthetic-speech evidence**, not real-user recognition estimates.

The process was launched anew for every clip, four threads, English, CPU-only, zero temperature, no fallback, suppressed non-speech tokens and fixed beam/best-of settings. Times include CLI startup, model loading, inference and publication of editable text, excluding one-time integrity verification. First/subsequent timings are fresh processes with different possible OS cache states, **not** resident-model cold/warm measurements. Peak RSS is sampled and may be underestimated. CPU totals include multithreaded child CPU time.

## Comparison

| Measure | tiny.en | base.en |
|---|---:|---:|
| Raw exact, synthesized titles | 4/28 (14.3%) | 12/28 (42.9%) |
| Normalized exact, synthesized titles | 16/28 (57.1%) | 20/28 (71.4%) |
| Fixed-catalog retrieval, synthesized titles | 18/28 (64.3%) | 20/28 (71.4%) |
| Nonempty transcript on silence | 0/2 | **2/2** |
| Nonempty transcript on noise-only | 0/2 | 0/2 |
| Spoken-title p50 / p95 latency | 590 / 665 ms | 1,258 / 1,347 ms |
| Fresh-process first-run p50 | 589 ms | 1,258 ms |
| Fresh-process subsequent-run p50 | 584 ms | 1,254 ms |
| Sampled peak process RSS | 182,513,664 B (174 MiB) | 295,821,312 B (282 MiB) |
| Total child CPU time, 32 runs | 65.68 s | 157.80 s |
| Model file size | 77,704,715 B | 147,964,211 B |
| Peak temporary transcript bytes | 41 B | 41 B |
| Engine failures | 0 | 0 |

The `base.en` silence result was **"You"** on both runs. This is a real false-input observation, not a mock test. `tiny.en` was faster and lighter, but missed more catalog titles. Both models struggled with certain numerals and similar-sounding titles. The fixed catalog is a documented local matching simulation, not the Internet Archive search algorithm.

### Model identity

| Model | Upstream SHA-1 (verified) | SHA-256 measured in CI |
|---|---|---|
| tiny.en | `c78c86eb1a8faa21b369bcd33207cc90d64ae9df` | `921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f` |
| base.en | `137c40403d78fd54d454da0f9bd998f78703390c` | `a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002` |

Engine binary SHA-256: `f8bb2ccd644bd37cb19a4809bf5e4f035ebe65cbdbb1ec92cad209446057554f`.

## Inspectable raw transcripts

The table shows **repeat 1** for each spoken fixture. Both repeats produced identical text for these fixtures; the linked JSON contains all 64 individual rows, including silence and noise.

| Fixture | Model | Expected title | Actual transcript | Retrieved expected? |
|---|---|---|---|---|
| mario-2 | tiny.en | Super Mario Bros. 2 | Super Mario Bros. 2 | Yes |
| mario-2 | base.en | Super Mario Bros. 2 | Super Mario Bros. 2. | Yes |
| mario-3 | tiny.en | Super Mario Bros. 3 | Super Mario Bros. Free. | No |
| mario-3 | base.en | Super Mario Bros. 3 | Super Mario Bros. 3 | Yes |
| metroid-prime | tiny.en | Metroid Prime | Metroid Prime. | Yes |
| metroid-prime | base.en | Metroid Prime | Metroid Prime. | Yes |
| metroid-prime-2 | tiny.en | Metroid Prime 2: Echoes | Metroid Prime 2 Air Ghost | No |
| metroid-prime-2 | base.en | Metroid Prime 2: Echoes | Metroid Prime 2 and it goes | No |
| mega-man-2 | tiny.en | Mega Man 2 | I'm Mega Man 2. | Yes |
| mega-man-2 | base.en | Mega Man 2 | Mega Man 2 | Yes |
| mega-man-3 | tiny.en | Mega Man 3 | Mega Man 3. | Yes |
| mega-man-3 | base.en | Mega Man 3 | Mega Man free. | No |
| zelda | tiny.en | The Legend of Zelda | The legend of Zelda. | Yes |
| zelda | base.en | The Legend of Zelda | I'll see you in the next one! | No |
| zelda-past | tiny.en | The Legend of Zelda: A Link to the Past | The legend of Zelda, a link to the past. | Yes |
| zelda-past | base.en | The Legend of Zelda: A Link to the Past | The legend of Zelda, a link to the past. | Yes |
| sonic | tiny.en | Sonic the Hedgehog | Sonic Maghaj. | No |
| sonic | base.en | Sonic the Hedgehog | Sonic the Hedgehog | Yes |
| sonic-2 | tiny.en | Sonic the Hedgehog 2 | Salyak Mepanjhak II. | No |
| sonic-2 | base.en | Sonic the Hedgehog 2 | Sonic the Hedgehog 2 | Yes |
| chrono | tiny.en | Chrono Trigger | Chrono Trigger | Yes |
| chrono | base.en | Chrono Trigger | Chrono Trigger | Yes |
| street-fighter-2 | tiny.en | Street Fighter II | Street Fighter Woman 2 | No |
| street-fighter-2 | base.en | Street Fighter II | Street Fighter Roman II | No |
| mario-2-noisy | tiny.en | Super Mario Bros. 2 | Super Mario Bros. 2. | Yes |
| mario-2-noisy | base.en | Super Mario Bros. 2 | Super Mario Bros. 2. | Yes |
| metroid-prime-noisy | tiny.en | Metroid Prime | Metroid Prime. | Yes |
| metroid-prime-noisy | base.en | Metroid Prime | Metroid Prime | Yes |

## Verification and next decision gate

The [M3A mock/regression workflow](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45285465171) passed 48 Python tests, the deterministic 64-run pipeline smoke, M2 benchmark, Bash checks, Decky TypeScript/controller tests and plugin ZIP exclusion check. The real benchmark [passed](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45285611032) with 64 real inference runs and no engine failures. Mock scores are excluded from the table above.

**Decision: collect more evidence.** Obtain a consented human title-query set with different voices, accents, microphones, numeral pronunciations, and realistic background game audio; repeat the same pinned comparison. Investigate silence gating and ambiguous title retrieval before selecting a model. On actual Steam Deck hardware measure release-to-editable-text latency, power, peak memory, CPU contention and game impact. Keep M2 physical validation as the release priority and do not ship capture, TTS or continuous listening under M3A.
