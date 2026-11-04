"""Offline metadata extraction without executing document contents."""
from __future__ import annotations

import hashlib
import mimetypes
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".gif"}
OFFICE_EXTS = {".docx", ".xlsx", ".pptx"}
MAX_PDF_BYTES = 100 * 1024 * 1024
MAX_OFFICE_ENTRIES = 10_000
MAX_CORE_PROPERTIES_BYTES = 2 * 1024 * 1024


def _safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"bytes_hex": value[:64].hex(), "truncated": len(value) > 64}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (tuple, list)):
        return [_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    return str(value)


def extract_metadata(path: str | Path, *, hash_file: bool = True) -> dict[str, Any]:
    """Extract filesystem and format metadata from a local regular file."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"Not a regular file: {p}")
    stat = p.stat()
    result: dict[str, Any] = {
        "path": str(p.resolve()),
        "filename": p.name,
        "extension": p.suffix.lower(),
        "mime_guess": mimetypes.guess_type(p.name)[0],
        "size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "created_or_changed_utc": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
        "metadata": {},
        "warnings": [],
    }
    if hash_file:
        h = hashlib.sha256()
        with p.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        result["sha256"] = h.hexdigest()
    suffix = p.suffix.lower()
    try:
        if suffix in IMAGE_EXTS:
            from PIL import ExifTags, Image
            with Image.open(p) as img:
                info = {str(k): _safe(v) for k, v in img.info.items() if k != "exif"}
                exif = img.getexif()
                exif_data = {ExifTags.TAGS.get(k, str(k)): _safe(v) for k, v in exif.items()}
                # GPSInfo is an EXIF sub-IFD in many images.
                gps_tag = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), None)
                if gps_tag is not None:
                    try:
                        gps = exif.get_ifd(gps_tag)
                        if gps:
                            exif_data["GPSInfo"] = {ExifTags.GPSTAGS.get(k, str(k)): _safe(v) for k, v in gps.items()}
                    except (AttributeError, KeyError, ValueError, TypeError):
                        pass
                result["metadata"] = {"format": img.format, "dimensions": list(img.size), "mode": img.mode, "image_info": info, "exif": exif_data}
        elif suffix == ".pdf":
            if stat.st_size > MAX_PDF_BYTES:
                raise ValueError(f"PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MiB inspection limit")
            from pypdf import PdfReader

            reader = PdfReader(str(p), strict=False)
            if reader.is_encrypted:
                result["metadata"] = {"encrypted": True}
                result["warnings"].append("Encrypted PDF metadata was not inspected")
            else:
                result["metadata"] = {
                    "page_count": len(reader.pages),
                    "document_info": {str(k): _safe(v) for k, v in (reader.metadata or {}).items()},
                    "encrypted": False,
                }
        elif suffix in OFFICE_EXTS:
            if not zipfile.is_zipfile(p):
                raise ValueError("Not a valid Office Open XML ZIP container")
            with zipfile.ZipFile(p) as archive:
                entries = archive.infolist()
                if len(entries) > MAX_OFFICE_ENTRIES:
                    raise ValueError("Office Open XML archive has too many entries")
                core = {}
                if "docProps/core.xml" in archive.namelist():
                    core_entry = archive.getinfo("docProps/core.xml")
                    if core_entry.file_size > MAX_CORE_PROPERTIES_BYTES:
                        raise ValueError("Core properties XML too large")
                    data = archive.read(core_entry)
                    root = ET.fromstring(data)
                    core = {node.tag.rsplit("}", 1)[-1]: (node.text or "") for node in root}
                result["metadata"] = {"core_properties": core, "archive_entries": len(entries)}
        else:
            result["warnings"].append("Unsupported format: filesystem metadata and optional SHA-256 only")
    except Exception as exc:  # noqa: BLE001 - parser failures must not abort a multi-file inspection
        result["warnings"].append(f"Format metadata could not be read: {type(exc).__name__}: {exc}")
    return result
