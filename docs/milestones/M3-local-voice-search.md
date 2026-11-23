# M3 decision — optional push-to-talk title search

**Decision, 2026-11-23.** Start with an offline transcription prototype using prerecorded title queries. Keep physical M2 acceptance as the release priority. Prototype work can proceed on a descendant feature branch while a Deck is unavailable. This decision allocates the first M3 increment to speech-to-text. Revisit optional speech playback after the search interaction is usable on hardware.

## Why this increment

M2 already accepts editable text in its search screen, returns opaque file IDs and binds installation to a separate destination preview and confirmation token. Speech can fill the existing title field without gaining authority to select a file, choose a suite or enqueue a job. Both platforms then use the same tested workflow. Device evidence for microphone access, focus, latency and memory under game load is still missing.

## Implementation order and exit criteria

1. **Offline experiment.** Compare small local whisper.cpp models on the same consented or redistributable clips. Include similar-sounding titles, numbers, silence and background noise. Record engine revision, model source, license and checksum, title accuracy, cold/warm latency, CPU time and peak RSS. Measure the complete transcription path. The upstream encoder benchmark measures only part of it. Select a default model after reviewing the measurements. [whisper.cpp tools and model documentation](https://github.com/ggml-org/whisper.cpp)
2. **Host-tested search integration.** Put transcription behind an optional adapter, disabled by default. Deliver editable text to the existing query field. The user activates Search, then separately selects and confirms any installation. Test successful transcription, cancellation, silence, missing model and engine failure. In each case assert zero enqueue calls from transcription and continued availability of typed search. Keep model installation opt-in and the standalone CLI independent of audio dependencies.
3. **Gaming Mode pilot.** Verify an unprivileged capture mechanism on the actual Deck. Capture only during intentional push-to-talk, show recording state, and release the microphone on button release, Back, focus loss, unload or timeout. Bound clip duration and bytes, discard temporary audio and unload idle models. Test built-in and headset microphones, background game audio, controller focus and memory recovery. Record release-to-editable-text latency alongside recognition results before choosing a shipping configuration.

**Release decision.** Ship optional voice search only after the core workflow passes the M2 hardware gate for both suites and the M3 pilot demonstrates reliable stop/cancel, editable results and acceptable measured resource use. If microphone access requires elevated privileges or continuous listening, retain keyboard search and defer capture integration. The host prototype remains independently testable.

[M2 progress and remaining gates](M2-gaming-mode-decky-integration.md) · [Physical test and rollback procedure](../../decky/README.md)

## M3A implementation checkpoint (2026-11-23)

The optional experiment lives in `experiments/m3a/` on `feature/m3a-offline-title-transcription`. The bounded offline adapter, reproducible fixture generator, two-model benchmark runner, fake-engine tests and independent CI workflow are implemented. No microphone capture, automatic search submission, download authority, or production plugin dependencies were introduced. See [M3A instructions](../../experiments/m3a/README.md).

**M3A remains INCOMPLETE: collect more evidence.** The deterministic fake-engine tests are pipeline verification, not model accuracy. A separate [real pinned whisper.cpp synthetic-speech comparison](../m3a-results.md) now provides 64 host inference runs, verified model hashes, raw transcripts and resource measurements. base.en retrieved 20/28 titles but hallucinated on both silence trials; tiny.en retrieved 18/28 with no silence false input. Consented human recordings and physical Deck microphone, power and controller measurements remain unavailable. Do not generalize synthetic host scores to real-user accuracy. M2 physical validation retains release priority. Do not advance a model to M3B until real reproducible results and raw transcripts are reviewed.
