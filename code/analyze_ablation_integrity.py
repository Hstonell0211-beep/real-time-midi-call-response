"""Audit Call100 ablation comparability, fallback activation, and score decomposition."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List, Sequence, Tuple

import evaluate_melody_metrics as evaluator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ABLATION_DIR = ROOT / "ab_tests" / "objective_ablation_call100_trials15_latency"
DEFAULT_LEGACY_RESULTS = ROOT / "ab_tests" / "objective_search_call100_trials15" / "all_objective_results.csv"
DEFAULT_OUTPUT_DIR = ROOT / "ab_tests" / "evaluation_integrity_audit"


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: List[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def fnum(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def answer_metadata(ablation_dir: Path) -> Dict[Tuple[str, str, str, int], Dict[str, str]]:
    output: Dict[Tuple[str, str, str, int], Dict[str, str]] = {}
    for path in sorted(ablation_dir.glob("*__A*/answer_key.csv")):
        run_name = path.parent.name
        preset, variant = run_name.split("__", 1)
        for row in read_csv(path):
            key = (preset, variant, row["call_id"], int(fnum(row["trial"])))
            output[key] = row
    return output


def enrich(rows: Sequence[Dict[str, str]], answers: Dict[Tuple[str, str, str, int], Dict[str, str]]) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    for row in rows:
        key = (row["preset"], row["ablation_variant"], row["call_id"], int(fnum(row["trial"])))
        answer = answers.get(key)
        if answer is None:
            raise KeyError(f"Missing answer row for {key}")
        motif_used = int(fnum(answer.get("motif_fallback_used"), 0))
        legacy_fallback_count = int(fnum(answer.get("fallback_count"), 0))
        event_repairs = int(fnum(answer.get("event_repair_count"), max(0, legacy_fallback_count - motif_used)))
        item: Dict[str, object] = dict(row)
        item["event_repair_count"] = event_repairs
        item["event_repair_used"] = int(event_repairs > 0)
        item["motif_fallback_used"] = motif_used
        item["empty_output_before_fallback"] = int(fnum(answer.get("empty_output_before_fallback"), 0))
        item["fallback_enabled"] = int(fnum(answer.get("fallback_enabled"), 0))
        style = (
            evaluator.OBJECTIVE_WEIGHTS["tonality_score"] * fnum(row.get("tonality_score"))
            + evaluator.OBJECTIVE_WEIGHTS["rhythm_score"] * fnum(row.get("rhythm_score"))
        ) / evaluator.STYLE_COMPLIANCE_WEIGHT
        non_style = (
            evaluator.OBJECTIVE_WEIGHTS["interval_score"] * fnum(row.get("interval_score"))
            + evaluator.OBJECTIVE_WEIGHTS["repetition_score"] * fnum(row.get("repetition_score"))
            + evaluator.OBJECTIVE_WEIGHTS["pitch_diversity_score"] * fnum(row.get("pitch_diversity_score"))
            + evaluator.OBJECTIVE_WEIGHTS["compression_score"] * fnum(row.get("compression_score"))
        ) / evaluator.NON_STYLE_STRUCTURAL_WEIGHT
        item["style_compliance_score"] = style
        item["non_style_structural_score"] = non_style
        output.append(item)
    return output


def variant_summaries(rows: Sequence[Dict[str, object]]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["variant_short"])].append(row)
    activation: List[Dict[str, object]] = []
    decomposition: List[Dict[str, object]] = []
    for variant in sorted(grouped):
        items = grouped[variant]
        repair_samples = sum(int(row["event_repair_used"]) for row in items)
        motif_samples = sum(int(row["motif_fallback_used"]) for row in items)
        empty_samples = sum(int(row["empty_output_before_fallback"]) for row in items)
        activation.append(
            {
                "variant": variant,
                "sample_count": len(items),
                "event_repair_sample_count": repair_samples,
                "event_repair_sample_rate": f"{repair_samples / len(items):.6f}",
                "event_repair_total_count": sum(int(row["event_repair_count"]) for row in items),
                "empty_output_before_fallback_count": empty_samples,
                "motif_fallback_used_count": motif_samples,
                "motif_fallback_used_rate": f"{motif_samples / len(items):.6f}",
            }
        )
        decomposition.append(
            {
                "variant": variant,
                "sample_count": len(items),
                "mean_structural_compliance_composite": f"{mean(fnum(row['objective_score']) for row in items):.6f}",
                "mean_style_compliance_score": f"{mean(fnum(row['style_compliance_score']) for row in items):.6f}",
                "mean_non_style_structural_score": f"{mean(fnum(row['non_style_structural_score']) for row in items):.6f}",
            }
        )
    return activation, decomposition


def stratified_scores(rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, int], List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["variant_short"] in {"A3", "A4"}:
            grouped[(str(row["variant_short"]), int(row["event_repair_used"]))].append(row)
    output: List[Dict[str, object]] = []
    for (variant, repair_used), items in sorted(grouped.items()):
        output.append(
            {
                "variant": variant,
                "event_repair_used": repair_used,
                "sample_count": len(items),
                "mean_objective_score": f"{mean(fnum(row['objective_score']) for row in items):.6f}",
                "mean_style_compliance_score": f"{mean(fnum(row['style_compliance_score']) for row in items):.6f}",
                "mean_non_style_structural_score": f"{mean(fnum(row['non_style_structural_score']) for row in items):.6f}",
            }
        )
    return output


def a3_a4_audit(rows: Sequence[Dict[str, object]], hash_midis: bool) -> Dict[str, object]:
    buckets: Dict[Tuple[str, str, int], Dict[str, Dict[str, object]]] = defaultdict(dict)
    for row in rows:
        if row["variant_short"] in {"A3", "A4"}:
            key = (str(row["preset"]), str(row["call_id"]), int(fnum(row["trial"])))
            buckets[key][str(row["variant_short"])] = row
    diffs: List[float] = []
    identical_midis = 0
    for values in buckets.values():
        if set(values) != {"A3", "A4"}:
            continue
        left, right = values["A3"], values["A4"]
        diffs.append(fnum(right["objective_score"]) - fnum(left["objective_score"]))
        if hash_midis:
            identical_midis += int(
                sha256(Path(str(left["response_midi_path"]))) == sha256(Path(str(right["response_midi_path"])))
            )
    return {
        "paired_sample_count": len(diffs),
        "negative_difference_count": sum(value < 0 for value in diffs),
        "zero_difference_count": sum(value == 0 for value in diffs),
        "positive_difference_count": sum(value > 0 for value in diffs),
        "mean_difference": mean(diffs) if diffs else 0.0,
        "min_difference": min(diffs) if diffs else 0.0,
        "max_difference": max(diffs) if diffs else 0.0,
        "byte_identical_response_midi_count": identical_midis if hash_midis else None,
    }


def legacy_audit(legacy_path: Path, rows: Sequence[Dict[str, object]]) -> Dict[str, object]:
    legacy = read_csv(legacy_path)
    legacy_raw = [fnum(row["objective_score"]) for row in legacy if row["candidate"] == "amt_small_raw"]
    legacy_controlled = [row for row in legacy if row["candidate"] == "amt_small_controlled"]
    a0 = [fnum(row["objective_score"]) for row in rows if row["variant_short"] == "A0"]
    event_repair_samples = sum(str(row.get("fallback_used", "")).lower() in {"true", "1"} for row in legacy_controlled)
    return {
        "legacy_raw_label": "style-projected raw path; superseded",
        "legacy_raw_mean": mean(legacy_raw),
        "true_a0_raw_mean": mean(a0),
        "difference": mean(legacy_raw) - mean(a0),
        "legacy_controlled_event_repair_sample_count": event_repair_samples,
        "legacy_controlled_event_repair_sample_rate": event_repair_samples / len(legacy_controlled),
        "legacy_controlled_motif_fallback_rate_claim_valid": False,
    }


def write_report(output_dir: Path, activation: Sequence[Dict[str, object]], decomposition: Sequence[Dict[str, object]], pair_audit: Dict[str, object], legacy: Dict[str, object]) -> None:
    a3 = next(row for row in activation if row["variant"] == "A3")
    a4 = next(row for row in activation if row["variant"] == "A4")
    lines = [
        "# Evaluation Integrity Audit",
        "",
        "## Raw-AMT comparability",
        "",
        f"The legacy `amt_small_raw` path has mean `{legacy['legacy_raw_mean']:.6f}` because it applied style projection. True A0 raw has mean `{legacy['true_a0_raw_mean']:.6f}`. The legacy label is superseded by the harmonized evaluation.",
        "",
        "## Fallback semantics",
        "",
        f"A3 empty outputs: `{a3['empty_output_before_fallback_count']}`. A4 empty outputs eligible for motif fallback: `{a4['empty_output_before_fallback_count']}`. A4 motif fallback activations: `{a4['motif_fallback_used_count']}`.",
        f"The A3-A4 comparison has `{pair_audit['zero_difference_count']}` exact zero differences among `{pair_audit['paired_sample_count']}` pairs. This is nonactivation, not evidence that replacement output was ineffective.",
        f"The previously reported 41.46% value is an event-repair sample rate (`{legacy['legacy_controlled_event_repair_sample_rate']:.6f}`), not a phrase-level motif-fallback rate.",
        "",
        "## Score decomposition",
        "",
        "| variant | composite | style compliance | non-style structural |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in decomposition:
        lines.append(
            f"| {row['variant']} | {row['mean_structural_compliance_composite']} | "
            f"{row['mean_style_compliance_score']} | {row['mean_non_style_structural_score']} |"
        )
    (output_dir / "integrity_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ablation-dir", type=Path, default=DEFAULT_ABLATION_DIR)
    parser.add_argument("--legacy-results", type=Path, default=DEFAULT_LEGACY_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-midi-hashes", action="store_true")
    args = parser.parse_args()

    source_path = args.ablation_dir / "ablation_all_results.csv"
    source = read_csv(source_path)
    if len(source) != 63000:
        raise RuntimeError(f"Expected 63,000 ablation rows, found {len(source)}")
    enriched = enrich(source, answer_metadata(args.ablation_dir))
    activation, decomposition = variant_summaries(enriched)
    stratified = stratified_scores(enriched)
    pair_audit = a3_a4_audit(enriched, not args.skip_midi_hashes)
    legacy = legacy_audit(args.legacy_results, enriched)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "fallback_activation_by_variant.csv", activation)
    write_csv(output_dir / "fallback_stratified_scores.csv", stratified)
    write_csv(output_dir / "ablation_score_decomposition.csv", decomposition)
    (output_dir / "a3_a4_pairwise_audit.json").write_text(json.dumps(pair_audit, indent=2) + "\n", encoding="utf-8")
    (output_dir / "legacy_label_audit.json").write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "ablation_results": str(source_path),
        "ablation_results_sha256": sha256(source_path),
        "legacy_results": str(args.legacy_results),
        "legacy_results_sha256": sha256(args.legacy_results),
        "evaluator_score_version": evaluator.SCORE_VERSION,
        "empty_output_objective_score": evaluator.evaluate_notes([], 480, evaluator.build_parser().parse_args([]))["objective_score"],
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    write_report(output_dir, activation, decomposition, pair_audit, legacy)
    print(f"[done] output={output_dir}")


if __name__ == "__main__":
    main()
