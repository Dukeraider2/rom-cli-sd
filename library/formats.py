"""Lightweight structural checks. Full emulation compatibility is tested on-device."""
import zipfile

SIGNATURES = {
    ".nes": (0,b"NES\x1a"), ".chd": (0,b"MComprHD"), ".cso": (0,b"CISO"),
    ".rvz": (0,b"RVZ\x01"), ".z64": (0,b"\x80\x37\x12\x40"),
    ".n64": (0,b"\x40\x12\x37\x80"), ".v64": (0,b"\x37\x80\x40\x12"),
    ".iso": (32769,b"CD001"),
}


def validate(stream, ext):
    stream.seek(0)
    head = stream.read(512)
    if (head.lstrip().lower().startswith((b"<!doctype", b"<html", b"<?xml"))
            or head.startswith((b"PK\x03\x04",b"7z\xbc\xaf\x27\x1c",b"Rar!",b"\x1f\x8b"))
            or zipfile.is_zipfile(stream)):
        raise ValueError("unexpected archive or document payload")
    if ext in SIGNATURES:
        offset, magic = SIGNATURES[ext]
        stream.seek(offset)
        if stream.read(len(magic)) != magic:
            raise ValueError(f"invalid {ext} header")

