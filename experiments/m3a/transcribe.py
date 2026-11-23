"""Bounded, CPU-only whisper.cpp CLI adapter for local WAV files.

M3A is a standalone development experiment. It has no Decky or library imports.
Each call launches a new engine process; it is NOT a resident-model benchmark.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import resource
import signal
import subprocess
import tempfile
import threading
import time
import wave

ENGINE_REVISION = "96ec4d9823e9d0211944172da35f9f29134af990"
# SHA-1 hashes published in whisper.cpp/models/README.md at ENGINE_REVISION.
MODELS = {
    "tiny.en": "c78c86eb1a8faa21b369bcd33207cc90d64ae9df",
    "base.en": "137c40403d78fd54d454da0f9bd998f78703390c",
}
MAX_AUDIO_BYTES = 512 * 1024
MAX_DURATION_SECONDS = 10
MAX_OUTPUT_BYTES = 4096


class TranscriptionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def digest(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_audio(path: Path) -> dict:
    try:
        if path.is_symlink() or not path.is_file():
            raise TranscriptionError("invalid_audio", "Audio must be a regular local file")
        size = path.stat().st_size
        if size > MAX_AUDIO_BYTES:
            raise TranscriptionError("oversized_audio", "WAV exceeds the 512 KiB limit")
        with wave.open(str(path), "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, "NONE"):
                raise TranscriptionError("invalid_audio", "Expected mono 16 kHz 16-bit PCM WAV")
            frames = wav.getnframes()
        if frames < 1 or frames > MAX_DURATION_SECONDS * 16000:
            raise TranscriptionError("invalid_audio", "WAV duration must be >0 and <=10 seconds")
        return {"bytes": size, "duration_seconds": frames / 16000}
    except (wave.Error, EOFError, OSError) as exc:
        raise TranscriptionError("invalid_audio", "Unreadable PCM WAV") from exc


def _rss_bytes(pid: int) -> int | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


class WhisperAdapter:
    def __init__(self, engine: Path, models_dir: Path, *, threads: int = 4,
                 timeout_seconds: float = 45, strict_hashes: bool = True):
        if not isinstance(threads, int) or not 1 <= threads <= 8:
            raise ValueError("threads must be 1..8")
        if not 0 < timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be >0 and <=120")
        self.engine = Path(engine).resolve()
        self.models_dir = Path(models_dir)
        self.threads = threads
        self.timeout_seconds = timeout_seconds
        self.strict_hashes = strict_hashes
        self._verified = {}
        self._lock = threading.Lock()

    def _model(self, model_id: str) -> tuple[Path, dict]:
        if model_id not in MODELS:
            raise TranscriptionError("invalid_model", "Model is not allowlisted")
        path = self.models_dir / f"ggml-{model_id}.bin"
        if path.is_symlink() or not path.is_file():
            raise TranscriptionError("missing_model", "Model file is missing or linked")
        st = path.stat()
        identity = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
        cached = self._verified.get(model_id)
        if cached and cached[0] == identity:
            return path, cached[1]
        if self.strict_hashes and digest(path, "sha1") != MODELS[model_id]:
            raise TranscriptionError("invalid_model", "Model SHA-1 does not match pinned upstream artifact")
        metadata = {"size_bytes": st.st_size, "sha1": digest(path, "sha1"),
                    "sha256": digest(path, "sha256")}
        self._verified[model_id] = (identity, metadata)
        return path, metadata

    def transcribe(self, clip: Path, model_id: str, cancel: threading.Event | None = None) -> dict:
        """Return editable text only; no search, source selection or enqueue side effects."""
        with self._lock:
            try:
                if model_id not in MODELS:
                    raise TranscriptionError("invalid_model", "Model is not allowlisted")
                if not self.engine.is_file() or not os.access(self.engine, os.X_OK):
                    raise TranscriptionError("missing_engine", "whisper-cli executable not found")
                audio = validate_audio(Path(clip))
                model, metadata = self._model(model_id)
                if cancel is not None and cancel.is_set():
                    raise TranscriptionError("cancelled", "Transcription cancelled")
                return self._run(Path(clip), model, model_id, audio, metadata, cancel)
            except TranscriptionError as exc:
                return {"ok": False, "error": {"code": exc.code, "message": str(exc)}}
            except (OSError, ValueError) as exc:
                return {"ok": False, "error": {"code": "unavailable", "message": str(exc)[:200]}}

    def _run(self, clip, model, model_id, audio, metadata, cancel):
        with tempfile.TemporaryDirectory(prefix="rom-m3a-") as folder:
            temp = Path(folder)
            stem = temp / "transcript"
            output = temp / "transcript.txt"
            log = temp / "engine.log"
            args = [str(self.engine), "-m", str(model.resolve()), "-f", str(clip.resolve()),
                    "-l", "en", "-t", str(self.threads), "-ng", "-nf", "-sns",
                    "-tp", "0", "-tpi", "0", "-bs", "5", "-bo", "5",
                    "-otxt", "-of", str(stem)]
            start = time.monotonic()
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            peak = None
            with log.open("wb") as stream:
                try:
                    process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                               stdout=stream, stderr=subprocess.STDOUT,
                                               start_new_session=(os.name == "posix"))
                except OSError as exc:
                    raise TranscriptionError("engine_failure", "Unable to launch engine") from exc
                reason = None
                try:
                    while True:
                        peak_now = _rss_bytes(process.pid)
                        if peak_now is not None:
                            peak = max(peak or 0, peak_now)
                        if cancel is not None and cancel.is_set():
                            reason = "cancelled"
                            break
                        if time.monotonic() - start >= self.timeout_seconds:
                            reason = "timeout"
                            break
                        try:
                            process.wait(timeout=0.025)
                            break
                        except subprocess.TimeoutExpired:
                            pass
                finally:
                    if reason or process.poll() is None:
                        _terminate(process)
            elapsed = time.monotonic() - start
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu = (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime)
            temp_bytes = sum(p.stat().st_size for p in temp.rglob("*") if p.is_file())
            metrics = {"elapsed_ms": round(elapsed * 1000, 3),
                       "cpu_seconds": round(max(0.0, cpu), 6),
                       "peak_rss_bytes_sampled": peak, "temporary_disk_bytes": temp_bytes,
                       "audio_bytes": audio["bytes"], "audio_seconds": audio["duration_seconds"],
                       "model_size_bytes": metadata["size_bytes"], "model_sha256": metadata["sha256"]}
            if reason:
                return {"ok": False, "error": {"code": reason, "message": "Transcription " + reason}, "metrics": metrics}
            if process.returncode != 0 or not output.is_file():
                return {"ok": False, "error": {"code": "engine_failure", "message": "Engine failed or produced no transcript file"}, "metrics": metrics}
            if output.stat().st_size > MAX_OUTPUT_BYTES:
                return {"ok": False, "error": {"code": "invalid_output", "message": "Transcript exceeds output limit"}, "metrics": metrics}
            try:
                text = output.read_text(encoding="utf-8").strip()
            except UnicodeError:
                return {"ok": False, "error": {"code": "invalid_output", "message": "Transcript is not UTF-8"}, "metrics": metrics}
            return {"ok": True, "text": text, "model": model_id, "metrics": metrics}
