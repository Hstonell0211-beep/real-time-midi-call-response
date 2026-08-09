from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


QUESTIONS = ["q1", "q2", "q3", "q4"]
RNG_SEED = 20260809


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze the frozen blind-listening study.")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--answer-key", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def unwrap_extended_json(value):
    if isinstance(value, dict) and len(value) == 1:
        key, raw = next(iter(value.items()))
        if key in {"$numberInt", "$numberLong"}:
            return int(raw)
        if key in {"$numberDouble", "$numberDecimal"}:
            return float(raw)
    return value


def load_snapshot(path: Path) -> pd.DataFrame:
    records = json.loads(path.read_text(encoding="utf-8"))
    normalized = [
        {key: unwrap_extended_json(value) for key, value in record.items()}
        for record in records
    ]
    return pd.DataFrame(normalized)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normal_two_sided_p(z_value: float) -> float:
    return math.erfc(abs(z_value) / math.sqrt(2.0))


def build_design(
    frame: pd.DataFrame,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> tuple[np.ndarray, list[str]]:
    columns = [np.ones(len(frame), dtype=float)]
    names = ["intercept"]
    for column in numeric_columns:
        columns.append(frame[column].to_numpy(dtype=float))
        names.append(column)
    for column in categorical_columns:
        levels = sorted(frame[column].astype(str).unique())
        for level in levels[1:]:
            columns.append((frame[column].astype(str) == level).to_numpy(dtype=float))
            names.append(f"{column}={level}")
    return np.column_stack(columns), names


def fit_clustered_ols(
    frame: pd.DataFrame,
    outcome: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
    cluster_column: str,
) -> dict:
    design, names = build_design(frame, numeric_columns, categorical_columns)
    target = frame[outcome].to_numpy(dtype=float)
    inverse = np.linalg.pinv(design.T @ design)
    coefficients = inverse @ design.T @ target
    residuals = target - design @ coefficients
    meat = np.zeros((design.shape[1], design.shape[1]), dtype=float)
    groups = frame[cluster_column].astype(str).to_numpy()
    unique_groups = np.unique(groups)
    for group in unique_groups:
        mask = groups == group
        score = design[mask].T @ residuals[mask]
        meat += np.outer(score, score)
    covariance = inverse @ meat @ inverse
    n_rows, n_parameters = design.shape
    n_groups = len(unique_groups)
    if n_groups > 1 and n_rows > n_parameters:
        covariance *= (n_groups / (n_groups - 1)) * ((n_rows - 1) / (n_rows - n_parameters))
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    return {
        "names": names,
        "coefficients": coefficients,
        "standard_errors": standard_errors,
        "n_rows": n_rows,
        "n_clusters": n_groups,
    }


def coefficient_summary(model: dict, name: str) -> dict:
    index = model["names"].index(name)
    estimate = float(model["coefficients"][index])
    standard_error = float(model["standard_errors"][index])
    z_value = estimate / standard_error if standard_error > 0 else float("nan")
    return {
        "estimate": estimate,
        "standard_error": standard_error,
        "ci_low": estimate - 1.96 * standard_error,
        "ci_high": estimate + 1.96 * standard_error,
        "z_value": z_value,
        "p_value_normal": normal_two_sided_p(z_value),
        "n_rows": model["n_rows"],
        "n_clusters": model["n_clusters"],
    }


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator, draws: int = 50000) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    batch_size = 2000
    means = []
    remaining = draws
    while remaining > 0:
        current = min(batch_size, remaining)
        indices = rng.integers(0, len(values), size=(current, len(values)))
        means.append(values[indices].mean(axis=1))
        remaining -= current
    distribution = np.concatenate(means)
    return tuple(float(value) for value in np.quantile(distribution, [0.025, 0.975]))


def sign_flip_p(values: np.ndarray, rng: np.random.Generator, draws: int = 200000) -> float:
    values = np.asarray(values, dtype=float)
    observed = abs(values.mean())
    extreme = 0
    processed = 0
    batch_size = 5000
    while processed < draws:
        current = min(batch_size, draws - processed)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(current, len(values)))
        permuted = np.abs((signs * values).mean(axis=1))
        extreme += int(np.count_nonzero(permuted >= observed - 1e-12))
        processed += current
    return (extreme + 1) / (draws + 1)


def paired_summary(
    item_scores: pd.DataFrame,
    family: str,
    controlled_variants: set[str],
    comparator_variants: set[str],
    rng: np.random.Generator,
    question_id: str | None = None,
) -> dict:
    subset = item_scores[item_scores["comparison_family"] == family].copy()
    if question_id is not None:
        subset = subset[subset["question_id"] == question_id]
    subset["arm"] = np.where(
        subset["variant_key"].isin(controlled_variants),
        "controlled",
        np.where(subset["variant_key"].isin(comparator_variants), "comparator", "other"),
    )
    subset = subset[subset["arm"] != "other"]
    participant_arm = (
        subset.groupby(["submission_id", "arm"], as_index=False)["score"]
        .mean()
        .pivot(index="submission_id", columns="arm", values="score")
        .dropna()
    )
    differences = (participant_arm["controlled"] - participant_arm["comparator"]).to_numpy()
    ci_low, ci_high = bootstrap_ci(differences, rng)
    standard_deviation = float(np.std(differences, ddof=1))
    return {
        "family": family,
        "question_id": question_id or "aggregate",
        "n_participants": int(len(participant_arm)),
        "controlled_mean": float(participant_arm["controlled"].mean()),
        "comparator_mean": float(participant_arm["comparator"].mean()),
        "mean_difference": float(differences.mean()),
        "bootstrap_ci_low": ci_low,
        "bootstrap_ci_high": ci_high,
        "sign_flip_p": sign_flip_p(differences, rng),
        "cohens_dz": float(differences.mean() / standard_deviation) if standard_deviation > 0 else float("nan"),
    }


def prepare_cleaning(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    submission_start = rows.groupby("submission_id")["received_at"].min().sort_values()
    item_rows = rows.sort_values("row_index").drop_duplicates(["submission_id", "item_id"])
    zero_playback_ids = set(
        item_rows.loc[item_rows["played_clip_count"].fillna(0).eq(0), "submission_id"]
    )

    later_duplicate_ids: set[str] = set()
    for _, group in rows[["submission_id", "session_id"]].drop_duplicates().groupby("session_id"):
        submission_ids = list(group["submission_id"])
        if len(submission_ids) > 1:
            ordered = sorted(submission_ids, key=lambda item: submission_start[item])
            later_duplicate_ids.update(ordered[1:])

    records = []
    for submission_id in submission_start.index:
        reasons = []
        if submission_id in zero_playback_ids:
            reasons.append("any_item_played_clip_count_zero")
        if submission_id in later_duplicate_ids:
            reasons.append("later_submission_in_repeated_session")
        submission_rows = rows[rows["submission_id"] == submission_id]
        unique_scores = submission_rows["score"].nunique()
        records.append(
            {
                "submission_id": submission_id,
                "session_id": submission_rows["session_id"].iloc[0],
                "received_at": submission_start[submission_id],
                "included_primary": not reasons,
                "exclusion_reasons": ";".join(reasons),
                "duration_seconds": submission_rows["duration_seconds"].iloc[0],
                "unique_score_values": unique_scores,
                "straightline_all_same": unique_scores == 1,
                "zero_playback_items": int(
                    item_rows[
                        (item_rows["submission_id"] == submission_id)
                        & item_rows["played_clip_count"].fillna(0).eq(0)
                    ].shape[0]
                ),
            }
        )
    manifest = pd.DataFrame(records)
    included_ids = set(manifest.loc[manifest["included_primary"], "submission_id"])
    return rows[rows["submission_id"].isin(included_ids)].copy(), manifest


def validate_grain(rows: pd.DataFrame) -> dict:
    rows_per_submission = rows.groupby("submission_id").size()
    items_per_submission = rows.groupby("submission_id")["item_id"].nunique()
    cells_per_submission = rows.groupby("submission_id").apply(
        lambda frame: frame[["item_id", "question_id"]].drop_duplicates().shape[0],
        include_groups=False,
    )
    return {
        "rows": int(len(rows)),
        "submissions": int(rows["submission_id"].nunique()),
        "all_submissions_have_32_rows": bool(rows_per_submission.eq(32).all()),
        "all_submissions_have_8_items": bool(items_per_submission.eq(8).all()),
        "all_submissions_have_32_unique_rating_cells": bool(cells_per_submission.eq(32).all()),
        "duplicate_dedupe_keys": int(rows["dedupe_key"].duplicated().sum()),
        "nonzero_fallback_rows": int(rows["fallback_count"].fillna(0).ne(0).sum()),
        "nonzero_motif_fallback_rows": int(rows["motif_fallback_used"].fillna(0).ne(0).sum()),
        "study_ids": sorted(rows["study_id"].dropna().astype(str).unique().tolist()),
    }


def scale_alpha(clean_rows: pd.DataFrame) -> float:
    matrix = clean_rows.pivot_table(
        index=["submission_id", "item_id"],
        columns="question_id",
        values="score",
        aggfunc="first",
    )[QUESTIONS]
    item_variances = matrix.var(ddof=1).sum()
    total_variance = matrix.sum(axis=1).var(ddof=1)
    return float((len(QUESTIONS) / (len(QUESTIONS) - 1)) * (1 - item_variances / total_variance))


def add_answer_key(clean_rows: pd.DataFrame, answer_key: pd.DataFrame) -> pd.DataFrame:
    metadata_columns = [
        "item_id",
        "condition_code",
        "condition_label",
        "variant_key",
        "comparison_family",
        "analysis_pair",
        "objective_score",
        "origin",
        "source_dataset",
    ]
    metadata = answer_key[metadata_columns].copy()
    response_columns = [
        "submission_id",
        "item_id",
        "question_id",
        "score",
        "presentation_index",
        "item_duration_seconds",
    ]
    responses = clean_rows[response_columns].copy()
    return responses.merge(metadata, on="item_id", how="left", validate="many_to_one")


def position_model(unblinded: pd.DataFrame) -> dict:
    item_means = (
        unblinded.groupby(
            ["submission_id", "item_id", "presentation_index"], as_index=False
        )["score"]
        .mean()
        .rename(columns={"score": "item_mean"})
    )
    model = fit_clustered_ols(
        item_means,
        "item_mean",
        ["presentation_index"],
        ["submission_id", "item_id"],
        "submission_id",
    )
    return coefficient_summary(model, "presentation_index")


def adjusted_family_model(
    unblinded: pd.DataFrame,
    family: str,
    controlled_variants: set[str],
    comparator_variants: set[str],
) -> dict:
    subset = unblinded[unblinded["comparison_family"] == family].copy()
    subset["controlled"] = subset["variant_key"].isin(controlled_variants).astype(float)
    item_means = (
        subset.groupby(
            ["submission_id", "item_id", "analysis_pair", "controlled", "presentation_index"],
            as_index=False,
        )["score"]
        .mean()
        .rename(columns={"score": "item_mean"})
    )
    model = fit_clustered_ols(
        item_means,
        "item_mean",
        ["controlled", "presentation_index"],
        ["submission_id", "analysis_pair"],
        "submission_id",
    )
    return coefficient_summary(model, "controlled")


def item_summary(unblinded: pd.DataFrame) -> pd.DataFrame:
    grouped = unblinded.groupby(
            [
                "item_id",
                "condition_code",
                "condition_label",
                "variant_key",
                "comparison_family",
                "analysis_pair",
                "objective_score",
                "origin",
                "source_dataset",
            ],
            as_index=False,
        ).agg(count=("score", "count"), mean=("score", "mean"), std=("score", "std"))
    grouped["standard_error"] = grouped["std"] / np.sqrt(grouped["count"])
    grouped["ci_low"] = grouped["mean"] - 1.96 * grouped["standard_error"]
    grouped["ci_high"] = grouped["mean"] + 1.96 * grouped["standard_error"]
    return grouped.sort_values("item_id")


def demographics(clean_rows: pd.DataFrame) -> dict:
    participants = clean_rows.sort_values("received_at").drop_duplicates("submission_id")
    return {
        "instrument_experience": participants["instrument_experience"].value_counts().to_dict(),
        "improv_familiarity": participants["improv_familiarity"].value_counts().to_dict(),
        "listening_setup": participants["listening_setup"].value_counts().to_dict(),
        "recruitment_source": participants["recruitment_source"].replace("", "(blank)").value_counts().to_dict(),
        "deployment_variant": participants["deployment_variant"].replace("", "(blank)").value_counts().to_dict(),
        "duration_seconds": {
            "median": float(participants["duration_seconds"].median()),
            "mean": float(participants["duration_seconds"].mean()),
            "min": float(participants["duration_seconds"].min()),
            "max": float(participants["duration_seconds"].max()),
        },
    }


def objective_human_alignment(items: pd.DataFrame) -> dict:
    pearson = float(items[["objective_score", "mean"]].corr(method="pearson").iloc[0, 1])
    spearman = float(items[["objective_score", "mean"]].corr(method="spearman").iloc[0, 1])
    return {"n_items": int(len(items)), "pearson_r": pearson, "spearman_rho": spearman}


def format_float(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def write_latex_table(path: Path, comparison: pd.DataFrame, adjusted: dict) -> None:
    labels = {
        "ablation_a0_vs_a4": ("Raw AMT", "Controlled AMT (A4)"),
        "baseline_motif_vs_a6": ("Motif baseline", "Controlled AMT (A6)"),
    }
    rows = []
    for record in comparison.to_dict(orient="records"):
        comparator, controlled = labels[record["family"]]
        adjusted_effect = adjusted[record["family"]]["estimate"]
        rows.append(
            f"{comparator} vs. {controlled} & "
            f"{format_float(record['comparator_mean'])} & "
            f"{format_float(record['controlled_mean'])} & "
            f"{format_float(record['mean_difference'])} "
            f"[{format_float(record['bootstrap_ci_low'])}, {format_float(record['bootstrap_ci_high'])}] & "
            f"{format_float(record['sign_flip_p'], 4)} & "
            f"{format_float(adjusted_effect)} \\\\"
        )
    table = "\n".join(
        [
            r"\begin{table*}[t]",
            r"\centering",
            r"\caption{Blind-listening results on a four-point Likert scale. Differences are controlled minus comparator. The primary confidence intervals use participant bootstrap resampling; the final column adjusts for presentation index, participant fixed effects, and call-pair fixed effects.}",
            r"\label{tab:blind-listening-results}",
            r"\small",
            r"\begin{tabular}{lccccc}",
            r"\hline",
            r"Comparison & Comparator & Controlled & Paired difference (95\% CI) & $p_{\mathrm{perm}}$ & Adjusted effect \\ ",
            r"\hline",
            *rows,
            r"\hline",
            r"\end{tabular}",
            r"\end{table*}",
            "",
        ]
    )
    path.write_text(table, encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_snapshot(args.snapshot)
    answer_key = pd.read_csv(args.answer_key)
    quality = validate_grain(rows)
    clean_rows, manifest = prepare_cleaning(rows)
    unblinded = add_answer_key(clean_rows, answer_key)
    rng = np.random.default_rng(RNG_SEED)

    families = {
        "ablation_a0_vs_a4": ({"A4_fallback"}, {"A0_raw_amt"}),
        "baseline_motif_vs_a6": ({"A6_full_controlled"}, {"motif_transform_baseline"}),
    }
    comparisons = []
    question_comparisons = []
    adjusted = {}
    for family, (controlled, comparator) in families.items():
        comparisons.append(paired_summary(unblinded, family, controlled, comparator, rng))
        adjusted[family] = adjusted_family_model(unblinded, family, controlled, comparator)
        for question_id in QUESTIONS:
            question_comparisons.append(
                paired_summary(
                    unblinded,
                    family,
                    controlled,
                    comparator,
                    rng,
                    question_id=question_id,
                )
            )

    comparison_frame = pd.DataFrame(comparisons)
    question_frame = pd.DataFrame(question_comparisons)
    items = item_summary(unblinded)
    straightline_ids = set(
        manifest.loc[
            manifest["included_primary"] & manifest["straightline_all_same"], "submission_id"
        ]
    )
    sensitivity_rows = unblinded[~unblinded["submission_id"].isin(straightline_ids)]
    sensitivity = []
    for family, (controlled, comparator) in families.items():
        sensitivity.append(paired_summary(sensitivity_rows, family, controlled, comparator, rng))

    summary = {
        "frozen_snapshot": str(args.snapshot.resolve()),
        "snapshot_sha256": sha256(args.snapshot),
        "answer_key": str(args.answer_key.resolve()),
        "quality": quality,
        "cleaning": {
            "raw_submissions": int(rows["submission_id"].nunique()),
            "included_submissions": int(clean_rows["submission_id"].nunique()),
            "excluded_submissions": int((~manifest["included_primary"]).sum()),
            "exclusion_reason_counts": (
                manifest.loc[~manifest["included_primary"], "exclusion_reasons"]
                .value_counts()
                .to_dict()
            ),
            "included_straightliners": int(
                (manifest["included_primary"] & manifest["straightline_all_same"]).sum()
            ),
        },
        "demographics": demographics(clean_rows),
        "cronbach_alpha": scale_alpha(clean_rows),
        "presentation_order_model": position_model(unblinded),
        "primary_comparisons": comparisons,
        "position_adjusted_comparisons": adjusted,
        "straightliner_exclusion_sensitivity": sensitivity,
        "objective_human_alignment": objective_human_alignment(items),
    }

    manifest.to_csv(
        args.output_dir / "exclusion_manifest.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    comparison_frame.to_csv(
        args.output_dir / "comparison_summary.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    question_frame.to_csv(
        args.output_dir / "question_comparison_summary.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    items.to_csv(
        args.output_dir / "item_summary.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    pd.DataFrame(sensitivity).to_csv(
        args.output_dir / "straightliner_sensitivity.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    (args.output_dir / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_latex_table(args.output_dir / "blind_listening_results_table.tex", comparison_frame, adjusted)
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
