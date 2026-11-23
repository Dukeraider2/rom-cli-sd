# Recognition reliability protocol

## Reproducing the experiment

Target Linux, Python 3.10+, eSpeak and ffmpeg. Use the CPU-only upstream revision and the model hashes in the [audit](m3a2-audit.md). Explicit acquisition and exact CMake options appear in the [measurement workflow](../.github/workflows/m3a2-reliability.yml). The CLI is built once with native-host specialization disabled and shared libraries disabled so comparison jobs receive one identical executable. CPU model/host variability across CI shards remains a confound for timing comparisons with Phase 1 and between shards.

Prepare the nonprivate fixtures locally with `python3 -m experiments.m3a.reliability_fixtures --output experiments/m3a/local/phase2-fixtures`. After acquiring that directory, the verified executable and both models, this **single offline command** runs all eight conditions, two repetitions each, and writes every measured row:

```sh
python3 -m experiments.m3a.reliability --engine /path/to/whisper-cli --models-dir /path/to/models --fixtures experiments/m3a/local/phase2-fixtures --output experiments/m3a/local/phase2.json
```

The output includes generated inputs' SHA-256, titles and spoken renderings where they differ, voice, rate, gain, random seeds, actual SNR for mixed speech, generator versions, engine/model digests, thresholds and catalogs. The source defines procedural room hum, game-like tones and clicks. These are synthetic proxies. The manifest's original control clips use the original eSpeak en-us 155 wpm settings, plus the original deterministic noise and silence. Generated WAVs are excluded from Git and CI artifacts.

The benchmark tests the original decoder at four threads, greedy decoding at four, original decoding at two, and the actual pre-inference energy gate with original decoding at four. Every non-rejected trial starts a fresh process. Identical seeded trial order permits paired comparisons. Results separate recognition, catalog retrieval, ambiguous suggestions and non-speech transcription. The alternative matcher adds Roman numeral II–IV and brothers/bros equivalence. It returns candidates independently of editable text. Both catalog sizes contain the expected titles. The larger one adds explicitly listed collision candidates. Neither catalog represents a live provider search.

Gate score is the maximum RMS of 20 ms PCM frames, in integer sample units. The threshold selection prioritizes fewest rejected development speech clips, then fewest accepted development non-speech clips, then lowest threshold. Report held-out rejection/acceptance separately from engine output. Resource fields distinguish child CPU and sampled child RSS from gate CPU, elapsed time and separately measured Python heap. Gate disk writes are zero. Model verification, fixture generation, gate calibration and profiling precede timed trials. Temporary transcript bytes are measured before cleanup, not high-frequency filesystem write counters.

For the consolidated file run `python3 -m experiments.m3a.analysis.aggregate --output phase2.json.gz experiments/m3a/local/phase2.json` or pass all eight downloaded shard JSONs. The aggregator checks exact pairing, common corpus and identical executable before scoring. Keep the original [Phase 1 results](m3a-results.md) as a separate historical control.

## Consented human evidence — BLOCKED

Recruit a target of 12 consenting adults across different voices and accents. Explain purpose, retention, local processing, optional withdrawal and which deidentified results may be shared before capture. Keep consent and participant contact data separate from audio. Give each participant an opaque code. Obtain separate permission before sharing transcripts or audio; keep recordings out of Git, CI and public artifacts.

Use 12 queries per speaker including the five known speech failures, close franchise distractors, numerals, acronyms and short titles. Record two independently spoken repetitions per microphone with built-in and headset microphones, in quiet and with controlled game background for each microphone. This gives 96 title utterances per speaker. Randomize order and record input gain, microphone position, ambient condition, device, sample format and any pronunciation variants. Include non-speech periods from each environment. Score speaker-level accuracy and worst-condition false inputs; repeated engine runs do not increase the speaker count. Use disjoint speakers for development and held-out evaluation. Agree on acceptable false inputs, short-utterance rejection and latency before inspecting held-out human scores. Allow deletion of a participant's data and regenerate affected summaries.

## Steam Deck evidence — BLOCKED

| Device trial | Evidence to record before an M3B decision |
|---|---|
| Local prerecorded inference on battery and AC | Deck model, SteamOS, CPU allocation, temperature, energy use, latency p50/p95, RSS and CPU |
| Idle and representative game load | Frame-time degradation, competing CPU use and memory recovery for both thread counts |
| Actual built-in/headset recordings, with consent | Per-speaker retrieval and raw recognition; noise acceptance; missed low-energy and clipped speech |
| Controller interaction, future supervised pilot | Button release to editable text, cancellation, focus loss and unload; separate approval before capture integration |

A blocked device or human test never contributes to the synthetic denominator. M2 physical validation retains priority.
