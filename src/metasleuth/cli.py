"""Command line interface."""
import csv
import json
from pathlib import Path

import typer

from .extract import extract_metadata

app = typer.Typer(help="Read-only, offline metadata extraction for local files.")


def _csv_cell(value: object) -> object:
    """Prevent spreadsheet formulas when a report is opened in a spreadsheet app."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


@app.command()
def inspect(
    paths: list[Path] = typer.Argument(..., help="One or more local files"),
    format: str = typer.Option("json", "--format", "-f", help="json or csv"),
    output: Path | None = typer.Option(None, "--output", "-o"),
    no_hash: bool = typer.Option(False, "--no-hash", help="Skip SHA-256 calculation"),
):
    if format not in ("json", "csv"):
        raise typer.BadParameter("Choose json or csv")
    try:
        records = [extract_metadata(p, hash_file=not no_hash) for p in paths]
    except (OSError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    if format == "json":
        rendered = json.dumps(records, indent=2, ensure_ascii=False)
    else:
        import io
        buffer = io.StringIO()
        fields = ["path", "filename", "extension", "mime_guess", "size_bytes", "modified_utc", "created_or_changed_utc", "sha256", "metadata", "warnings"]
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    k: _csv_cell(json.dumps(record.get(k)))
                    if k in ("metadata", "warnings")
                    else _csv_cell(record.get(k, ""))
                    for k in fields
                }
            )
        rendered = buffer.getvalue()
    if output:
        output.write_text(rendered + ("\n" if not rendered.endswith("\n") else ""), encoding="utf-8")
        typer.echo(f"Saved {len(records)} record(s) to {output}")
    else:
        typer.echo(rendered)


if __name__ == "__main__":
    app()
