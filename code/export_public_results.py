"""Create machine-independent public CSVs from frozen local experiment outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable


SCORE_VERSION = "structural_compliance_v1.1"


def fnum(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def portable_basename(value: object) -> str:
    """Return a filename from either Windows- or POSIX-style archived paths."""
    return str(value or "").replace("\\", "/").rsplit("/", 1)[-1]


def write_rows(path: Path, fields: list[str], rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def export_path_redacted(source: Path, output: Path, path_field: str, file_field: str) -> None:
    with source.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or path_field not in reader.fieldnames:
            raise ValueError(f"Missing {path_field!r} in {source}")
        fields = [file_field if field == path_field else field for field in reader.fieldnames]

        def rows() -> Iterable[Dict[str, object]]:
            for source_row in reader:
                row = dict(source_row)
                local_path = row.pop(path_field, "")
                row[file_field] = portable_basename(local_path)
                yield {field: row.get(field, "") for field in fields}

        write_rows(output, fields, rows())


def export_ablation(source: Path, output: Path) -> None:
    with source.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"fallback_count", "response_midi_path", "tonality_score", "rhythm_score"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required ablation fields: {sorted(missing)}")
        removed = {"fallback_used", "fallback_count", "response_midi_path"}
        fields = [field for field in reader.fieldnames or [] if field not in removed]
        fields.extend(
            [
                "score_version",
                "style_compliance_score",
                "non_style_structural_score",
                "event_repair_used",
                "event_repair_count",
                "motif_fallback_used",
                "motif_fallback_count",
                "response_midi_file",
            ]
        )

        def rows() -> Iterable[Dict[str, object]]:
            for source_row in reader:
                row: Dict[str, object] = {
                    field: source_row.get(field, "") for field in fields if field in source_row
                }
                event_repairs = int(fnum(source_row.get("fallback_count")))
                style = (
                    0.22 * fnum(source_row.get("tonality_score"))
                    + 0.20 * fnum(source_row.get("rhythm_score"))
                ) / 0.42
                non_style = (
                    0.18 * fnum(source_row.get("interval_score"))
                    + 0.16 * fnum(source_row.get("repetition_score"))
                    + 0.14 * fnum(source_row.get("pitch_diversity_score"))
                    + 0.10 * fnum(source_row.get("compression_score"))
                ) / 0.58
                row.update(
                    {
                        "score_version": SCORE_VERSION,
                        "style_compliance_score": f"{style:.6f}",
                        "non_style_structural_score": f"{non_style:.6f}",
                        "event_repair_used": int(event_repairs > 0),
                        "event_repair_count": event_repairs,
                        "motif_fallback_used": 0,
                        "motif_fallback_count": 0,
                        "response_midi_file": portable_basename(source_row.get("response_midi_path")),
                    }
                )
                yield {field: row.get(field, "") for field in fields}

        write_rows(output, fields, rows())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    redact = subparsers.add_parser("redact-path", help="replace one absolute-path column by filenames")
    redact.add_argument("--source", type=Path, required=True)
    redact.add_argument("--output", type=Path, required=True)
    redact.add_argument("--path-field", required=True)
    redact.add_argument("--file-field", required=True)

    ablation = subparsers.add_parser("ablation", help="standardize fallback semantics and redact MIDI paths")
    ablation.add_argument("--source", type=Path, required=True)
    ablation.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "ablation":
        export_ablation(args.source, args.output)
    else:
        export_path_redacted(args.source, args.output, args.path_field, args.file_field)


if __name__ == "__main__":
    main()
