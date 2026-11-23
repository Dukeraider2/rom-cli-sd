"""Generate explicitly labeled synthetic speech or mock-only fixture WAVs locally.

No recordings are committed. Real mode needs locally installed espeak and ffmpeg.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import wave

TITLES = [
    ("mario-2", "Super Mario Bros. 2"),
    ("mario-3", "Super Mario Bros. 3"),
    ("metroid-prime", "Metroid Prime"),
    ("metroid-prime-2", "Metroid Prime 2: Echoes"),
    ("mega-man-2", "Mega Man 2"),
    ("mega-man-3", "Mega Man 3"),
    ("zelda", "The Legend of Zelda"),
    ("zelda-past", "The Legend of Zelda: A Link to the Past"),
    ("sonic", "Sonic the Hedgehog"),
    ("sonic-2", "Sonic the Hedgehog 2"),
    ("chrono", "Chrono Trigger"),
    ("street-fighter-2", "Street Fighter II"),
]
SAMPLE_RATE = 16000


def save_wav(path: Path, samples: list[int]) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def read_wav(path: Path) -> list[int]:
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, SAMPLE_RATE):
            raise ValueError("Expected 16k mono PCM16")
        data = wav.readframes(wav.getnframes())
    return list(struct.unpack("<" + "h" * (len(data) // 2), data))


def noise(count: int, seed: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.randint(-1800, 1800) for _ in range(count)]


def synthesize(title: str, destination: Path, voice="en-us", rate=155) -> None:
    espeak = shutil.which("espeak")
    ffmpeg = shutil.which("ffmpeg")
    if not espeak or not ffmpeg:
        raise RuntimeError("Speech fixtures require local espeak and ffmpeg")
    with tempfile.TemporaryDirectory(prefix="m3a-speech-") as folder:
        original = Path(folder) / "speech.wav"
        subprocess.run([espeak, "-v", voice, "-s", str(rate), "-w", str(original), title],
                       check=True, stdout=subprocess.DEVNULL, timeout=30)
        subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-y", "-i", str(original), "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", str(destination)],
                       check=True, timeout=30)


def generate(output: Path, mock: bool) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    clips = []
    for index, (fixture_id, title) in enumerate(TITLES):
        path = output / (fixture_id + ".wav")
        if mock:
            # Non-speech tone: only valid for fake-engine pipeline tests.
            import math
            samples = [int(3000 * math.sin(2 * math.pi * (180 + index * 13) * i / SAMPLE_RATE))
                       for i in range(SAMPLE_RATE)]
            save_wav(path, samples)
            generator = "test_tone"
        else:
            synthesize(title, path)
            generator = "espeak_en_us_155wpm"
        clips.append({"id": fixture_id, "kind": "synthetic", "expected_title": title,
                      "provenance": {"generator": generator, "generated_locally": True},
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for fixture_id in ("mario-2-noisy", "metroid-prime-noisy"):
        title = dict(TITLES)[fixture_id.removesuffix("-noisy")]
        path = output / (fixture_id + ".wav")
        if mock:
            save_wav(path, noise(SAMPLE_RATE, 123))
            generator = "test_tone"
        else:
            clean = output / (fixture_id.removesuffix("-noisy") + ".wav")
            samples = read_wav(clean)
            background = noise(len(samples), 123)
            save_wav(path, [max(-32768, min(32767, x + n)) for x, n in zip(samples, background)])
            generator = "espeak_plus_deterministic_noise"
        clips.append({"id": fixture_id, "kind": "synthetic", "expected_title": title,
                      "provenance": {"generator": generator, "seed": 123, "generated_locally": True},
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for fixture_id, samples in (("silence", [0] * SAMPLE_RATE * 2),
                                ("noise-only", noise(SAMPLE_RATE * 2, 17))):
        path = output / (fixture_id + ".wav")
        save_wav(path, samples)
        clips.append({"id": fixture_id, "kind": "silence" if fixture_id == "silence" else "noise",
                      "expected_title": None,
                      "provenance": {"generator": "python_stdlib", "seed": 17 if fixture_id == "noise-only" else None},
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"schema": 1, "language": "en", "fixture_mode": "mock" if mock else "synthetic_speech",
                "clips": clips}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="experiments/m3a/local/fixtures")
    parser.add_argument("--mock", action="store_true", help="Generate non-speech CI fixtures only")
    args = parser.parse_args()
    manifest = generate(Path(args.output), args.mock)
    print(f"Generated {len(manifest['clips'])} local fixtures at {args.output}")


if __name__ == "__main__":
    main()
