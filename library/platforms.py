"""Read-only suite discovery. All paths originate in user configuration."""
import json
import os
import shlex
import subprocess
from pathlib import Path

APP = "net.retrodeck.retrodeck"
FORMATS = {
    "nes": (".nes",), "snes": (".sfc", ".smc"), "gb": (".gb",),
    "gbc": (".gbc",), "gba": (".gba",), "n64": (".z64", ".n64", ".v64"),
    "nds": (".nds",), "psx": (".chd",), "ps2": (".chd", ".iso"),
    "psp": (".iso", ".cso"), "gc": (".rvz",), "wii": (".rvz",),
    "dreamcast": (".chd",), "saturn": (".chd",), "genesis": (".md", ".gen"),
}
PLATFORMS = ("emudeck", "retrodeck")


def flatpak(*args):
    try:
        result = subprocess.run(["flatpak", "info", *args, APP], capture_output=True,
                                text=True, timeout=5, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def absolute(value, home):
    if not isinstance(value, str):
        raise ValueError("missing configured path")
    for prefix in ("~/", "$HOME/", "${HOME}/"):
        if value.startswith(prefix):
            value = str(home / value[len(prefix):])
            break
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or any(c in value for c in "$`\n\r\0"):
        raise ValueError("unsupported configured path")
    return path


def settings(path, keys):
    result = {}
    for line in path.read_text(encoding="utf8").splitlines():
        key, sep, raw = line.removeprefix("export ").partition("=")
        if sep and key.strip() in keys:
            # Only join shell-quoted text. No expansion, sourcing or subprocess.
            parts = shlex.split(raw, comments=True, posix=os.name != "nt")
            if len(parts) != 1:
                raise ValueError(f"invalid {key} assignment")
            result[key.strip()] = parts[0].strip('"') if os.name == "nt" else parts[0]
    return result


def discover(platform, home=None, probe=flatpak):
    home = Path(home or Path.home())
    row = dict(platform=platform, installed=False, root=None, userdata=None, status="absent")
    try:
        if platform == "emudeck":
            cfg = home / ".config/EmuDeck/settings.sh"
            if not cfg.is_file():
                return row
            row["installed"] = True
            root = absolute(settings(cfg, {"romsPath"}).get("romsPath"), home)
        elif platform == "retrodeck":
            if not probe("--show-ref"):
                return row
            row["installed"] = True
            folder = home / ".var/app" / APP / "config/retrodeck"
            if (folder/"retrodeck.json").exists():
                paths = json.loads((folder/"retrodeck.json").read_text(encoding="utf8"))["paths"]
                data, roms = paths["rd_home_path"], paths["roms_path"]
            else:
                paths = settings(folder/"retrodeck.cfg", {"rdhome", "roms_folder"})
                data, roms = paths["rdhome"], paths.get("roms_folder")
            userdata = absolute(data, home)
            row["userdata"] = str(userdata)
            root = absolute(roms, home) if roms else userdata / "roms"
        else:
            raise ValueError("unknown platform")
        row["root"] = str(root)
        if not root.is_dir():
            row["status"] = "storage-unavailable"
        elif not os.access(root, os.R_OK | os.X_OK):
            row["status"] = "inaccessible"
        else:
            row["status"] = "ready"
        row["writable"] = os.access(root, os.W_OK | os.X_OK)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        row.update(status="configuration-error", error=str(exc))
    return row


def destination(row, system, *, write=False, probe=flatpak):
    if system not in FORMATS or row["status"] != "ready":
        raise ValueError("unknown console or unavailable storage")
    folder = Path(row["root"]) / system
    if folder.resolve(strict=True) != folder or not folder.is_dir():
        raise ValueError("console directory missing or linked")
    if not os.access(folder, os.R_OK | os.X_OK | (os.W_OK if write else 0)):
        raise PermissionError(str(folder))
    if row["platform"] == "retrodeck" and probe("--file-access="+str(folder)) not in ("read-only","read-write"):
        raise PermissionError("RetroDECK cannot read console directory")
    return folder

