from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _require_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def _load_clean_dataframe(csv_path: Path, json_path: Path) -> pd.DataFrame:
    if json_path.exists():
        df = pd.DataFrame(read_json(json_path))
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        raise FileNotFoundError(f"Missing baseline clean dataset: {csv_path} or {json_path}")

    text_columns = [
        "paper_id",
        "title",
        "summary",
        "primary_category",
        "published",
        "updated",
        "doi",
        "abs_url",
        "pdf_url",
        "comment",
        "authors_joined",
        "categories_joined",
        "text_for_embedding",
    ]
    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    return df


def _print_metric_comparison(
    baseline_metrics: dict,
    corrupted_metrics: dict,
    repaired_metrics: dict,
) -> None:
    keys = [
        ("retrieval_hit_rate", "Retrieval hit rate"),
        ("mean_token_f1", "Mean token F1"),
        ("judge_accuracy", "Judge accuracy"),
        ("mean_judge_score", "Mean judge score"),
    ]
    print("\nMetric comparison (baseline -> corrupted -> repaired):")
    for key, label in keys:
        baseline = baseline_metrics.get(key)
        corrupted = corrupted_metrics.get(key)
        repaired = repaired_metrics.get(key)
        print(f"  {label}: {baseline} -> {corrupted} -> {repaired}")


def main() -> None:
    """Run corruption, re-evaluation, repair, and comparison against baseline."""
    settings = load_settings()
    paths = settings.paths

    _require_path(paths.clean_csv, "baseline clean CSV")
    _require_path(paths.baseline_metrics, "baseline metrics")
    _require_path(paths.eval_testset, "evaluation test set")
    _require_path(paths.raw_records_json, "raw records")

    baseline_df = _load_clean_dataframe(paths.clean_csv, paths.clean_json)
    baseline_metrics = read_json(paths.baseline_metrics)

    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=paths.corrupted_embeddings_json,
    )
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "quality_report_corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        paths.quality_dir / "freshness_report_corrupted.json",
    )

    records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(records, now_utc())
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=paths.repaired_embeddings_json,
    )
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "quality_report_repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        paths.quality_dir / "freshness_report_repaired.json",
    )

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    _print_metric_comparison(
        baseline_metrics,
        corrupted_evaluation.summary,
        repaired_evaluation.summary,
    )

    print(
        "\nCorruption flow complete: "
        f"{len(baseline_df)} baseline rows, "
        f"{len(corrupted_df)} corrupted rows, "
        f"{len(repaired_df)} repaired rows."
    )
    print(f"Corruption log: {paths.corruption_log}")
    print(f"Corrupted metrics: {paths.corrupted_metrics}")
    print(f"Repaired metrics: {paths.repaired_metrics}")
    print(f"Comparison report: {paths.comparison_report}")
