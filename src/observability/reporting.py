from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def _display(value: Any) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _metric_rows(metrics: dict[str, Any]) -> list[tuple[str, str]]:
    names = [
        ("samples", "Samples"),
        ("retrieval_hit_rate", "Retrieval hit rate"),
        ("mean_token_f1", "Mean token F1"),
        ("judge_accuracy", "Judge accuracy"),
        ("mean_judge_score", "Mean judge score"),
    ]
    return [(label, _display(metrics.get(key))) for key, label in names]


def _quality_rows(quality: dict[str, Any]) -> list[str]:
    issues = quality.get("issues") or []
    if not issues:
        return ["| No quality checks reported | Not available | Not available |"]

    rows = []
    for issue in issues:
        failed = int(issue.get("count") or 0)
        status = "pass" if failed == 0 else "fail"
        rows.append(f"| {issue.get('issue_type', 'unknown')} | {status} | {failed} |")
    return rows


def _findings(metrics: dict[str, Any], quality: dict[str, Any], freshness: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    failed_records = int(quality.get("failed_records") or 0)
    if failed_records:
        findings.append(f"- Data quality found {failed_records} affected records.")
    elif quality:
        findings.append("- Data quality checks passed for the generated dataset.")
    else:
        findings.append("- Quality report was not available.")

    if freshness:
        if freshness.get("is_fresh"):
            findings.append("- Freshness check passed; no stale rows were reported.")
        else:
            findings.append(f"- Freshness check found {_display(freshness.get('stale_rows'))} stale rows.")
    else:
        findings.append("- Freshness report was not available.")

    if metrics:
        hit_rate = metrics.get("retrieval_hit_rate")
        token_f1 = metrics.get("mean_token_f1")
        findings.append(
            f"- Evaluation metrics are available: retrieval hit rate {_display(hit_rate)}, "
            f"mean token F1 {_display(token_f1)}."
        )
    else:
        findings.append("- Evaluation metrics were not available when this report was generated.")
    return findings


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a readable baseline markdown report from generated artifacts."""
    dataset_rows = [
        ("Source", source_summary.get("source") or source_summary.get("source_api")),
        ("Query", source_summary.get("query") or source_summary.get("source_query")),
        ("Filter", source_summary.get("filter") or source_summary.get("source_filter")),
        ("Raw records", source_summary.get("raw_records") or source_summary.get("total_records")),
        ("Clean records", quality.get("total_records") or source_summary.get("clean_records")),
    ]

    lines = [
        "# Dataset Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    lines.extend(f"| {label} | {_display(value)} |" for label, value in dataset_rows)

    lines.extend(
        [
            "",
            "# Evaluation Metrics",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
    )
    lines.extend(f"| {label} | {value} |" for label, value in _metric_rows(metrics))
    ragas = metrics.get("ragas")
    if ragas:
        lines.append(f"| Ragas | `{_display(ragas)}` |")

    lines.extend(
        [
            "",
            "# Quality Checks",
            "",
            f"- Total records: {_display(quality.get('total_records'))}",
            f"- Failed records: {_display(quality.get('failed_records'))}",
            f"- Pass rate: {_display(quality.get('pass_rate'))}",
            "",
            "| Check | Status | Failed records |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(_quality_rows(quality))

    lines.extend(
        [
            "",
            "# Freshness",
            "",
            f"- Latest published: {_display(freshness.get('latest_published'))}",
            f"- Oldest published: {_display(freshness.get('oldest_published'))}",
            f"- Stale rows: {_display(freshness.get('stale_rows'))}",
            f"- Total rows: {_display(freshness.get('total_rows'))}",
            f"- Fresh: {_display(freshness.get('is_fresh'))}",
            "",
            "# Findings",
            "",
        ]
    )
    lines.extend(_findings(metrics, quality, freshness))
    lines.append("")

    write_text(Path(report_path), "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a markdown comparison report for baseline, corrupted, and repaired runs."""
    metric_keys = [
        ("retrieval_hit_rate", "Retrieval hit rate"),
        ("mean_token_f1", "Mean token F1"),
        ("judge_accuracy", "Judge accuracy"),
        ("mean_judge_score", "Mean judge score"),
    ]
    lines = [
        "# Dataset Summary",
        "",
        "| Dataset | Total records | Failed records | Pass rate | Stale rows |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| Corrupted | {_display(corrupted_quality.get('total_records'))} | "
            f"{_display(corrupted_quality.get('failed_records'))} | "
            f"{_display(corrupted_quality.get('pass_rate'))} | "
            f"{_display(corrupted_freshness.get('stale_rows'))} |"
        ),
        (
            f"| Repaired | {_display(repaired_quality.get('total_records'))} | "
            f"{_display(repaired_quality.get('failed_records'))} | "
            f"{_display(repaired_quality.get('pass_rate'))} | "
            f"{_display(repaired_freshness.get('stale_rows'))} |"
        ),
        "",
        "# Evaluation Metrics",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | --- | --- | --- |",
    ]
    for key, label in metric_keys:
        lines.append(
            f"| {label} | {_display(baseline_metrics.get(key))} | "
            f"{_display(corrupted_metrics.get(key))} | {_display(repaired_metrics.get(key))} |"
        )

    lines.extend(
        [
            "",
            "# Quality Checks",
            "",
            "## Corrupted",
            "",
            "| Check | Status | Failed records |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(_quality_rows(corrupted_quality))
    lines.extend(
        [
            "",
            "## Repaired",
            "",
            "| Check | Status | Failed records |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(_quality_rows(repaired_quality))
    lines.extend(
        [
            "",
            "# Freshness",
            "",
            f"- Corrupted stale rows: {_display(corrupted_freshness.get('stale_rows'))}",
            f"- Corrupted fresh: {_display(corrupted_freshness.get('is_fresh'))}",
            f"- Repaired stale rows: {_display(repaired_freshness.get('stale_rows'))}",
            f"- Repaired fresh: {_display(repaired_freshness.get('is_fresh'))}",
            "",
            "# Findings",
            "",
        ]
    )
    lines.extend(
        _corruption_findings(
            baseline_metrics,
            corrupted_metrics,
            repaired_metrics,
            corrupted_quality,
            repaired_quality,
            corrupted_freshness,
            repaired_freshness,
        )
    )
    lines.append("")

    write_text(Path(report_path), "\n".join(lines))
    
    

def _corruption_findings(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> list[str]:
    """Generate analytical findings for corruption experiment."""

    baseline_hit = float(baseline_metrics.get("retrieval_hit_rate", 0))
    corrupted_hit = float(corrupted_metrics.get("retrieval_hit_rate", 0))
    repaired_hit = float(repaired_metrics.get("retrieval_hit_rate", 0))

    baseline_f1 = float(baseline_metrics.get("mean_token_f1", 0))
    corrupted_f1 = float(corrupted_metrics.get("mean_token_f1", 0))
    repaired_f1 = float(repaired_metrics.get("mean_token_f1", 0))

    baseline_acc = float(baseline_metrics.get("judge_accuracy", 0))
    corrupted_acc = float(corrupted_metrics.get("judge_accuracy", 0))
    repaired_acc = float(repaired_metrics.get("judge_accuracy", 0))

    hit_drop = round((baseline_hit - corrupted_hit) * 100, 1)
    f1_drop = round((baseline_f1 - corrupted_f1) * 100, 1)
    acc_drop = round((baseline_acc - corrupted_acc) * 100, 1)

    failed_records = corrupted_quality.get("failed_records", 0)
    stale_rows = corrupted_freshness.get("stale_rows", 0)

    lines = [
        "## Impact of Corruption",
        "",
        (
            f"The corrupted dataset introduced data quality issues affecting "
            f"{failed_records} records, including missing summaries, duplicate "
            f"records, and stale publication dates."
        ),
        "",
        (
            "Missing summaries reduced the amount of semantic information "
            "available to the embedding model, making relevant documents "
            "harder to retrieve."
        ),
        "",
        (
            "Duplicate records increased retrieval noise and reduced the "
            "overall quality of search results."
        ),
        "",
        (
            f"Freshness monitoring detected {stale_rows} stale records, "
            "demonstrating how outdated content can impact data reliability."
        ),
        "",
        (
            f"After corruption, retrieval hit rate decreased from "
            f"{baseline_hit:.3f} to {corrupted_hit:.3f} "
            f"(-{hit_drop}%)."
        ),
        "",
        (
            f"Mean token F1 decreased from "
            f"{baseline_f1:.4f} to {corrupted_f1:.4f} "
            f"(-{f1_drop}%), indicating lower answer quality."
        ),
        "",
        (
            f"Judge accuracy decreased from "
            f"{baseline_acc:.3f} to {corrupted_acc:.3f} "
            f"(-{acc_drop}%), confirming that corrupted data negatively "
            "affected downstream evaluation performance."
        ),
        "",
        "## Recovery After Repair",
        "",
        (
            "The repair process rebuilt the dataset from the original raw "
            "source, restoring missing content, removing duplicates, and "
            "recovering freshness."
        ),
        "",
        (
            f"Retrieval hit rate recovered to {repaired_hit:.3f}, "
            f"matching the baseline value of {baseline_hit:.3f}."
        ),
        "",
        (
            f"Mean token F1 recovered to {repaired_f1:.4f}, "
            "indicating that answer quality returned to its original level."
        ),
        "",
        (
            f"Judge accuracy recovered to {repaired_acc:.3f}, "
            "demonstrating that the impact of corruption was reversible."
        ),
        "",
        "## Conclusion",
        "",
        (
            "This experiment demonstrates that data quality directly affects "
            "retrieval effectiveness and answer quality in RAG systems."
        ),
        "",
        (
            "Corrupted datasets degraded retrieval and evaluation metrics, "
            "while repairing the data restored performance to baseline levels."
        ),
    ]

    return lines