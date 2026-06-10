from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _record_id(row: pd.Series, fallback_index: int) -> str:
    paper_id = _clean_text(row.get("paper_id"))
    return paper_id or f"row-{fallback_index}"


def _issue_payload(issue_type: str, description: str, record_ids: list[str]) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "description": description,
        "count": len(record_ids),
        "record_ids": record_ids,
    }


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    filename = report_name if report_name.endswith(".json") else f"{report_name}.json"
    return settings.paths.quality_dir / filename


def _write_quality_report(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)
    alias_path = path.with_name("quality_report.json")
    if alias_path != path:
        write_json(alias_path, payload)


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run core data quality checks and persist a JSON report."""
    total_records = int(len(df))
    missing_title_ids: list[str] = []
    missing_summary_ids: list[str] = []
    stale_record_ids: list[str] = []

    for index, row in df.iterrows():
        record_id = _record_id(row, int(index))
        if not _clean_text(row.get("title")):
            missing_title_ids.append(record_id)
        if not _clean_text(row.get("summary")):
            missing_summary_ids.append(record_id)
        age_days = pd.to_numeric(row.get("age_days"), errors="coerce")
        if pd.isna(age_days) or int(age_days) > settings.freshness_threshold_days:
            stale_record_ids.append(record_id)

    if "paper_id" in df.columns:
        duplicate_mask = df["paper_id"].astype(str).str.strip().duplicated(keep=False)
        duplicate_ids = [
            _record_id(row, int(index))
            for index, row in df.loc[duplicate_mask].iterrows()
        ]
    else:
        duplicate_ids = []

    issues = [
        _issue_payload("missing_title", "Records with missing or blank title.", missing_title_ids),
        _issue_payload("missing_summary", "Records with missing or blank summary.", missing_summary_ids),
        _issue_payload("duplicate_records", "Records with duplicate paper_id values.", duplicate_ids),
        _issue_payload(
            "stale_records",
            f"Records with age_days greater than {settings.freshness_threshold_days}, or missing age_days.",
            stale_record_ids,
        ),
    ]

    failed_record_ids = sorted(
        set(missing_title_ids) | set(missing_summary_ids) | set(duplicate_ids) | set(stale_record_ids)
    )
    failed_records = len(failed_record_ids)
    passed_records = max(total_records - failed_records, 0)
    pass_rate = (passed_records / total_records) if total_records else 0.0

    report = {
        "total_records": total_records,
        "failed_records": failed_records,
        "passed_records": passed_records,
        "pass_rate": round(pass_rate, 4),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "failed_record_ids": failed_record_ids,
        "issues": issues,
        "checks": {
            issue["issue_type"]: {
                "passed": issue["count"] == 0,
                "failed_records": issue["count"],
            }
            for issue in issues
        },
    }

    _write_quality_report(_quality_report_path(settings, report_name), report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist a focused freshness report."""
    total_rows = int(len(df))
    published = pd.to_datetime(df.get("published"), errors="coerce") if "published" in df else pd.Series(dtype="datetime64[ns]")
    age_days = pd.to_numeric(df.get("age_days"), errors="coerce") if "age_days" in df else pd.Series(dtype="float64")
    stale_mask = age_days.isna() | (age_days > settings.freshness_threshold_days)
    stale_rows = int(stale_mask.sum()) if len(age_days) else total_rows

    report = {
        "latest_published": published.max().date().isoformat() if not published.dropna().empty else None,
        "oldest_published": published.min().date().isoformat() if not published.dropna().empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0,
    }
    write_json(Path(report_path), report)
    return report
