import zipfile
from pathlib import Path

import pytest

from metasleuth import extract_metadata


def test_text_file(tmp_path: Path):
    file = tmp_path / "note.txt"
    file.write_text("hello", encoding="utf-8")
    result = extract_metadata(file)
    assert result["size_bytes"] == 5
    assert len(result["sha256"]) == 64
    assert result["warnings"]


def test_no_hash(tmp_path: Path):
    file = tmp_path / "note.txt"
    file.write_text("hello", encoding="utf-8")
    assert "sha256" not in extract_metadata(file, hash_file=False)


def test_missing_file(tmp_path: Path):
    with pytest.raises(ValueError):
        extract_metadata(tmp_path / "missing.pdf")


def test_image(tmp_path: Path):
    from PIL import Image
    file = tmp_path / "test.png"
    Image.new("RGB", (12, 8)).save(file)
    assert extract_metadata(file)["metadata"]["dimensions"] == [12, 8]


def test_office(tmp_path: Path):
    file = tmp_path / "test.docx"
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("docProps/core.xml", '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>Analyst</dc:creator></cp:coreProperties>')
    assert extract_metadata(file)["metadata"]["core_properties"]["creator"] == "Analyst"


def test_large_office_core_properties_are_not_read(tmp_path: Path):
    file = tmp_path / "large.docx"
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("docProps/core.xml", "x" * (2 * 1024 * 1024 + 1))
    result = extract_metadata(file)
    assert any("Core properties XML too large" in warning for warning in result["warnings"])
