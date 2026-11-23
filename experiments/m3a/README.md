# M3A — Offline game-title transcription experiment

**Status: benchmark harness implemented; real model comparison NOT RUN. Decision: COLLECT MORE EVIDENCE.** M2 Steam Deck physical acceptance remains the release priority. This optional development-only directory is not imported by the CLI, Decky backend or frontend, and is not packaged in the plugin ZIP.

## Verified upstream baseline (2026-11-23)

- Engine: [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp), MIT license, pinned commit **96ec4d9823e9d0211944172da35f9f29134af990**.
- Models: [upstream ggml model table](https://github.com/ggml-org/whisper.cpp/blob/96ec4d9823e9d0211944172da35f9f29134af990/models/README.md). Original OpenAI Whisper source is MIT licensed. Preconverted artifacts come from [ggerganov/whisper.cpp on Hugging Face](https://huggingface.co/ggerganov/whisper.cpp/tree/main).
- English-only first pass. tiny.en: approximately 75 MiB, **SHA-1 c78c86eb1a8faa21b369bcd33207cc90d64ae9df**. base.en: approximately 142 MiB, **SHA-1 137c40403d78fd54d454da0f9bd998f78703390c**. These are **SHA-1**, not SHA-256. The runner also records locally calculated SHA-256 identities.
- [Upstream CLI options](https://github.com/ggml-org/whisper.cpp/blob/96ec4d9823e9d0211944172da35f9f29134af990/examples/cli/README.md): whisper-cli supports -m, -f, -l, -t, -ng, -nf, -sns, -tp, -tpi, -bs, -bo, -otxt, -of. Input here is mono 16 kHz 16-bit PCM WAV.

## Explicit setup, once, on a Linux host

These commands download engine source and model weights. **They are not run by the benchmark** and are not part of CI. No Docker or elevated SteamOS modification is needed. Install build tools only through a user-approved method.

~~~sh
git clone https://github.com/ggml-org/whisper.cpp.git /path/to/whisper.cpp
git -C /path/to/whisper.cpp checkout 96ec4d9823e9d0211944172da35f9f29134af990
cmake -S /path/to/whisper.cpp -B /path/to/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build /path/to/whisper.cpp/build --config Release -j 4
sh /path/to/whisper.cpp/models/download-ggml-model.sh tiny.en
sh /path/to/whisper.cpp/models/download-ggml-model.sh base.en
sha1sum /path/to/whisper.cpp/models/ggml-tiny.en.bin /path/to/whisper.cpp/models/ggml-base.en.bin
~~~

Verify the two SHA-1 values against the pinned hashes above before proceeding. Check the CLI executable and SHA-256 with sha256sum. Never add downloaded binaries to Git.

## Fixture provenance and generation

The fixed catalog is [catalog.json](catalog.json). Fixture generator creates twelve game-title utterances, two noisy title utterances, silence and noise-only clips. Similar-sounding names and numerals are deliberately represented. It uses local eSpeak English US speech (155 wpm), ffmpeg PCM16 conversion, and seeded additive noise. All speech is **synthesized**, not human. No audio is downloaded or included in Git.

~~~sh
python3 -m experiments.m3a.fixtures --output experiments/m3a/local/fixtures
~~~

Install eSpeak and ffmpeg locally before running that command. Record their versions in your device report. For human clips, obtain explicit consent or redistributable material, transcode to the same WAV format, and add manifest entries with id, kind=human, expected_title, permission=consented or redistributable, provenance, and SHA-256. Keep private recordings outside Git. Report human and synthetic scores separately.

The alternative --mock generator makes non-speech test tones and is **only** for deterministic CI. The real benchmark refuses mock fixtures.

## Run real comparison completely offline

After obtaining the engine, both models and fixtures, disconnect networking if desired and run from the repository root:

~~~sh
python3 -m experiments.m3a.benchmark \
  --engine /path/to/whisper.cpp/build/bin/whisper-cli \
  --models-dir /path/to/whisper.cpp/models \
  --fixtures experiments/m3a/local/fixtures \
  --catalog experiments/m3a/catalog.json \
  --threads 4 --repeats 3 \
  --output experiments/m3a/local/results.json
~~~

The runner rejects missing or mismatched model SHA-1, mismatched fixture SHA-256, and wrong engine revision declaration. It does not fetch files. The executable binary SHA-256, model SHA-1/SHA-256, fixture manifest digest, environment, settings, all expected/raw transcripts, exact/normalized/retrieval counts, false input, timings, CPU, sampled RSS, and temporary disk are written to JSON.

Normalization is defined before scoring: Unicode NFKC, casefold, & to "and", number words zero through ten to digits, punctuation/underscore removal, and whitespace collapse. Roman numerals remain literal. Search usefulness is a **fixed local catalog simulation**, not a claim about Internet Archive provider ranking: exact normalized match wins, otherwise Python SequenceMatcher ratio >=0.82 and a >=0.08 margin over runner-up; ambiguity means no match.

Every clip uses a **fresh CLI process**. First and later process timings may differ due to filesystem cache; neither is a genuinely resident model. Time includes CLI startup, model loading, inference, and transcript publication, but not one-time model integrity hashing or fixture generation. CPU time is a process-child rusage delta; peak RSS is sampled from Linux /proc VmHWM and may underestimate very short peaks. Temporary disk measures output/log files before cleanup. All models use CPU-only, four threads, English, no fallback, suppressed non-speech tokens, zero temperature and fixed beam/best-of settings. The runner does not claim Steam Deck power or in-game performance.

## CI-only pipeline smoke

~~~sh
python3 -m experiments.m3a.fixtures --mock --output experiments/m3a/local/mock-fixtures
mkdir -p experiments/m3a/local/mock-models
printf mock > experiments/m3a/local/mock-models/ggml-tiny.en.bin
printf mock > experiments/m3a/local/mock-models/ggml-base.en.bin
python3 -m experiments.m3a.benchmark \
  --engine experiments/m3a/fake_engine.py \
  --models-dir experiments/m3a/local/mock-models \
  --fixtures experiments/m3a/local/mock-fixtures \
  --mock --repeats 2 \
  --output experiments/m3a/local/mock-results.json
python3 -B -m unittest discover -s tests -v
~~~

The fake engine validates subprocess lifecycle, result serialization and scoring only. Its transcripts are fixture-ID lookups, **not** recognition results. Never use mock accuracy numbers to select a model.

## Isolation and release gate

The current Decky search field in decky/src/index.tsx is editable state query; Search is a separate button calling the validated search RPC. A future M3B transcript can setQuery(text) without invoking search. File selection, suite choice and confirmation/enqueue remain separate M2 actions. M3A does **not** modify this UI, the RPC allowlist, the SQLite schema, the package builder, or downloader behavior. M2 device testing and ordinary typed search remain independent.

**Decision: COLLECT MORE EVIDENCE.** The model weights and whisper-cli executable are not available in this development environment, so there are no real ASR accuracy or resource measurements. Required next evidence: real tiny.en/base.en runs on the same human and synthetic clips, review of raw transcripts and false inputs, then Steam Deck controller/microphone/power measurements during M3B. Do not mark M3A complete until another developer reproduces the real comparison.
