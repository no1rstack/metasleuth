# MetaSleuth

An offline, read-only metadata inspection CLI for local images, PDFs, and Office Open XML documents. Designed for OSINT, privacy reviews, and digital forensics education.

> **License:** Free-to-use proprietary, no modifications or redistribution without permission. Not open source.

## Install for development

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Usage

```bash
metasleuth inspect photo.jpg
metasleuth inspect document.pdf presentation.pptx --format json --output report.json
metasleuth inspect photo.jpg document.pdf --format csv --output report.csv
metasleuth inspect sample.docx --no-hash
pytest -q
```

## Supported formats

- JPEG, PNG, TIFF, WebP, BMP, GIF: dimensions, format, image info, EXIF and GPS tags when available.
- PDF: page count and document information metadata (unencrypted PDFs).
- DOCX, XLSX, PPTX: core OOXML properties, including creator, title and dates where present.
- Other files: filesystem metadata and optional SHA-256 hash.

## Privacy and security

All inspection runs locally, with no uploads or network calls. Results may contain names, locations, GPS coordinates, and other sensitive data; review reports before sharing. The program does not modify source files or run embedded macros. Treat untrusted or malformed files cautiously: metadata parsers may have vulnerabilities, and this tool is not a sandbox. The CLI processes explicitly named files only; it does not recursively crawl directories.

Filesystem `ctime` is not universally a creation time: on Unix-like systems it generally means inode change time.

## Limitations

- This is a metadata extractor, not an authenticity or attribution engine.
- It does not extract every proprietary EXIF sub-IFD, all PDF XMP metadata, or metadata embedded in document attachments.
- Encrypted PDFs may require passwords and may not expose page counts.
- No external enrichment or username/person identification.

## Publishing

Confirm the distribution name is available on PyPI and run `python -m build` before publishing. GitHub Actions CI is included; publishing is intentionally not automated until release ownership is finalized.

## License

Copyright © 2026 Noir Stack LLC. Licensed under the
[Proprietary Software License — Free Use, No Modification](LICENSE).
