from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def _load_or_fetch_records(settings):
    try:
        return fetch_source_records(settings), "fetched"
    except Exception:
        if not settings.paths.raw_records_json.exists():
            raise
        return load_raw_records(settings.paths.raw_records_json), "loaded_existing_after_fetch_failure"


def _write_compat_json(path, payload) -> None:
    write_json(path, payload)
    aliases = {
        "papers_clean.json": "cleaned_papers.json",
        "test_set.json": "testset.json",
    }
    alias_name = aliases.get(path.name)
    if alias_name:
        alias_path = path.with_name(alias_name)
        if alias_path != path:
            write_json(alias_path, payload)


def _write_report_alias(path) -> None:
    if path.name != "phase1_report.md":
        return
    alias_path = path.with_name("baseline_report.md")
    alias_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> None:
    """Run the baseline data, retrieval, evaluation, and observability pipeline."""
    settings = load_settings()

    records, source_mode = _load_or_fetch_records(settings)
    run_date = now_utc()

    clean_df = build_clean_dataframe(records, run_date)
    write_csv(clean_df, settings.paths.clean_csv)
    clean_payload = clean_df.to_dict(orient="records")
    _write_compat_json(settings.paths.clean_json, clean_payload)

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
    _write_compat_json(settings.paths.eval_testset, test_set)

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    quality = run_data_quality_checks(clean_df, settings, "quality_report")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "source_mode": source_mode,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "run_date": run_date.isoformat(),
        "raw_records_path": str(settings.paths.raw_records_json),
        "clean_json_path": str(settings.paths.clean_json),
        "embedding_manifest_path": str(settings.paths.embeddings_json),
        "test_set_path": str(settings.paths.eval_testset),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    _write_report_alias(settings.paths.baseline_report)

    print(
        "Phase 1 complete: "
        f"{len(records)} raw records, {len(clean_df)} clean records, "
        f"{len(test_set)} test samples."
    )
    print(f"Clean data: {settings.paths.clean_json}")
    print(f"Embeddings: {settings.paths.embeddings_json}")
    print(f"Metrics: {settings.paths.baseline_metrics}")
    print(f"Report: {settings.paths.baseline_report}")
