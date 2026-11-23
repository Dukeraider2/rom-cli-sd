import re
import unicodedata
from pathlib import Path
from .platforms import FORMATS


def basename(value):
    if (not value or value.startswith(".") or value.endswith((" ", "."))
            or any(c in '/\\:*?"<>|' or unicodedata.category(c).startswith("C") for c in value)
            or len(value.encode("utf8")) > 240):
        raise ValueError("invalid filename or metadata component")
    return value


def identify(name, system=None):
    ext = Path(basename(name)).suffix.lower()
    candidates = [key for key, values in FORMATS.items() if ext in values]
    if system is None and len(candidates) == 1:
        return candidates[0]
    if system not in candidates:
        raise ValueError("unsupported format or ambiguous system")
    return system


def names(original, title=None, region="", revision="", disc=0):
    basename(original)
    display = basename(title or Path(original).stem)
    if disc < 0:
        raise ValueError("disc must be positive when supplied")
    labels = [basename(region)] if region else []
    if revision:
        labels.append("Rev "+basename(revision))
    if disc:
        labels.append(f"Disc {disc}")
    filename = display + "".join(f" ({label})" for label in labels) + Path(original).suffix.lower()
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFC", display)).strip().casefold()
    return display, normalized, basename(filename) if title or labels else original

