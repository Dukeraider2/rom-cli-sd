# M3A Phase 2 · Offline title recognition

## Evidence

The paired experiment uses 46 locally generated recordings. The 16 original controls reproduce Phase 1. Eight development clips select the gate threshold. The held-out set consists of 18 spoken clips and four non-speech clips. Each clip runs twice per condition. These repetitions measure repeatability on a recording. They give no estimate of variation between speakers.

The complete archive includes raw editable text, normalization, every retrieval candidate, errors, gate decisions, process ordinals, timings, child resource measurements, fixture hashes and generation parameters. Every comparison uses the same executable and models from the pinned whisper.cpp revision. [Measurement archive](m3a2-results.json.gz) · [Measured code at 8b08d2a](https://github.com/Dukeraider2/rom-cli-sd/commit/8b08d2a) · [Eight CI comparisons](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45288188725) · [Baseline audit](m3a2-audit.md)

## Held-out recognition and retrieval

Each row covers 36 spoken trials (18 clips twice) and eight non-speech trials (four clips twice). Original and title-aware matching produced identical counts at catalog sizes 20 and 53 for each respective matcher. The ambiguity column counts title-aware candidate sets with multiple entries. The final column counts nonempty transcripts on non-speech.

| Model and configuration | Raw exact /36 | Normalized exact /36 | Original retrieval /36 | Title-aware retrieval /36 | Ambiguous /36 | False input /8 |
|---|---:|---:|---:|---:|---:|---:|
| tiny.en beam, 4 threads | 0 | 4 | 8 | 12 | 2 | 0 |
| tiny.en greedy, 4 | 2 | 12 | 16 | 20 | 2 | 0 |
| tiny.en beam, 2 | 0 | 4 | 8 | 12 | 2 | 0 |
| tiny.en gated beam, 4 | 0 | 4 | 8 | 12 | 2 | 0 |
| base.en beam, 4 | 18 | 24 | 24 | 24 | 0 | 2 |
| base.en greedy, 4 | 16 | 22 | 22 | 22 | 2 | 2 |
| base.en beam, 2 | 18 | 24 | 24 | 24 | 0 | 2 |
| base.en gated beam, 4 | 18 | 24 | 24 | 24 | 0 | 0 |

On the original 15-title catalog, four-thread beam reproduced historical retrieval (tiny.en 18/28, base.en 20/28) and normalized exact recognition (16/28 and 20/28). All 16 control WAV hashes matched the historical manifest. The expanded held-out set exposed a larger model difference. On tiny.en beam, original matching recovered the expected title on four trials with incorrect normalized transcripts. The title-aware matcher recovered four more. Adding 33 catalog entries produced no change in aggregate retrieval here. Larger libraries still need evaluation. [Original measurements](m3a-results.md)

## Failure analysis

The following paired observations use the original beam decoder with two threads. Every quoted string is a raw transcript from the archive.

| Target | What changed on the same model |
|---|---|
| Super Mario Bros. 3 | tiny.en produced “Super Mario Bros. Free.” on the original and faster renderings. Changing the voice produced “Super Mario Bros. 3.” Speaking “brothers three” produced “Super Mario Brothers 3.” The last variant shows where a title-aware alias helps retrieval. |
| Metroid Prime 2: Echoes | tiny.en retained “Metroid Prime 2 Air Ghost” at the slower rate. base.en produced the correct words, with a line break before “Echoes”, on the slower rendering. Spelling out the number and changing the pause produced “Metroid Prime 2 and Killz.” on base.en. |
| Sonic the Hedgehog | tiny.en produced “Sonic Maghaj.” on the control and “Sonic percentage hog.” with another voice. base.en recognized the control, alternate voice and quiet version. |
| Street Fighter II | tiny.en changed from “Street Fighter Woman 2” to “Street Fighter 2” when the synthesizer received “two”. The numeral alias can retrieve the latter. base.en changed from “Street Fighter Roman II” to the exact title. |
| The Legend of Zelda | base.en returned “I'll see you in the next one!” on the control and “but that don't matter” with the alternate voice. Peak clipping produced unrelated singing-like text on both models. |
| Silence | base.en returned “You” on the held-out silence. Its identical response to the very quiet spoken “Doom” illustrates why filtering transcript text would also affect real utterances. |

Noise level also mattered. At measured SNR near 15 dB, base.en gave “Chrono Trigger.” At 3 dB it gave “The throne of glitter.” These controlled changes show sensitivity to rendering, background and model choice. They cannot establish how often a human speaker would encounter the same errors. Matching is evaluated downstream on fixed transcripts.

## Non-speech and gate behavior

Threshold 12 minimized development errors under the prespecified rule, rejecting zero of four speech recordings and passing two of four non-speech recordings. On held-out data it rejected silence and room hum, passed game tones and clicks (4/8 non-speech trials sent to inference), and rejected the very quiet, short “Doom” twice (2/36 speech trials). Quiet “Sonic” passed. Ungated conditions sent all eight non-speech trials to inference. base.en beam's held-out false transcripts fell from 2/8 to 0/8. Development clicks still produced “Thanks for watching!” with the gate. Matching accuracy alone would hide the lost “Doom” input because neither ungated model recognized it.

Across each 92-trial gated condition, gate-only wall p50/p95 was 1.26/2.26 ms for tiny.en and 1.20/2.08 ms for base.en. Total gate CPU was 0.122 and 0.118 seconds respectively. Separately profiling the energy pass over the corpus gave 28,953,128 bytes of peak traced Python heap and zero temporary file bytes. Whole-clip PCM unpacking contributes to that heap cost. The parent process heap and child RSS measure different things.

## Resource cost

The eight conditions produced 736 decisions with zero run errors. The gate skipped 24 invocations, leaving 712 fresh engine processes. The Ubuntu runners had four allocated logical CPUs on AMD EPYC 7763, Intel Xeon Platinum 8573C or Intel Xeon 6975P-C hosts. The per-row host index identifies the machine in the archive. Differences in measured latency across shards cannot establish a thread-count or decoder speedup on a Steam Deck.

| Condition | Title p50 / p95 ms | First / later median ms | Total child CPU s | Peak child RSS MiB | Temp bytes |
|---|---:|---:|---:|---:|---:|
| tiny.en beam 4 | 565 / 626 | 572 / 561 | 191 | 173.6 | 80 |
| tiny.en greedy 4 | 496 / 511 | 496 / 496 | 159 | 144.4 | 41 |
| tiny.en beam 2 | 749 / 817 | 750 / 741 | 135 | 171.6 | 80 |
| tiny.en gated beam 4 | 622 / 686 | 625 / 618 | 183 | 173.7 | 80 |
| base.en beam 4 | 1,191 / 1,250 | 1,189 / 1,190 | 430 | 281.5 | 41 |
| base.en greedy 4 | 1,088 / 1,107 | 1,102 / 1,086 | 374 | 234.4 | 41 |
| base.en beam 2 | 1,543 / 1,624 | 1,532 / 1,541 | 289 | 279.7 | 41 |
| base.en gated beam 4 | 1,201 / 1,266 | 1,258 / 1,194 | 347 | 281.4 | 41 |

Model storage was 77,704,715 bytes for tiny.en and 147,964,211 for base.en. The common executable SHA-256 was `220f99d5d5e8bdef6729e0ca99a13e78e043b9731689b5732e4085638df23214`. The archive records both model digests per model, Python 3.12.3, eSpeak 1.48.15, ffmpeg 6.1.1 and the fixture seeds.

Each invocation loads its own model. The first-process column contains one observation per configuration. The later median includes all subsequent invocations, potentially served by warm filesystem caches. Title p50/p95 cover the spoken trials across all splits. CPU is cumulative child CPU time across that condition. RSS is the maximum sampled child high-water mark. Temporary bytes are the largest observed final transcript file before cleanup. Model verification, fixture preparation and gate calibration occur outside the timed path. The historical benchmark used a different binary build. CI jobs may use different physical hosts.

## Verification and readiness

The Linux regression run passed 53 Python tests, three frontend tests, 64 fake-engine pipeline trials and the M2 packaging checks. The fake pipeline exercises cancellation, timeout, descendant termination, repeated cleanup and error handling. Only real whisper.cpp measurements appear in the recognition tables. [Regression evidence](https://github.com/Dukeraider2/rom-cli-sd/actions/runs/45288188730)

Independent review identified identical development and held-out non-speech waveforms in the first experiment. Commit `8b08d2a` corrected them and added a hash-disjointness check before measurement. Follow-up review found no critical or high-severity issue in the corrected CI path. It identified that CI uploads per-condition files and that the aggregator trusts some labels. The final verification separately checked every row's split, expected title, decoder, threads, gate state and model digests against the manifest and pinned definitions.

Human and physical Steam Deck evidence are both outstanding. The next qualification step calls for 12 consenting speakers, 96 utterances per speaker, two microphone types and quiet and game-background conditions. Set acceptance thresholds before examining held-out speakers. On the Deck, measure battery and AC behavior, title latency, frame-time impact under game load, memory recovery and cancellation. Controller and microphone lifecycle acceptance require a separately authorized pilot. M2 physical acceptance retains priority. [Offline reproduction command, human protocol and hardware matrix](m3a2-protocol.md)
