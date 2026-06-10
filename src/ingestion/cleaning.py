from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


MIN_SUMMARY_CHARS = 40


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return normalize_whitespace(str(value))


def _clean_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        key = text.lower()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _record_to_dict(record: PaperRecord | dict[str, Any]) -> dict[str, Any]:
    if isinstance(record, dict):
        return record
    if is_dataclass(record):
        return asdict(record)
    return {
        "paper_id": getattr(record, "paper_id", ""),
        "title": getattr(record, "title", ""),
        "summary": getattr(record, "summary", ""),
        "authors": getattr(record, "authors", []),
        "categories": getattr(record, "categories", []),
        "primary_category": getattr(record, "primary_category", ""),
        "published": getattr(record, "published", ""),
        "updated": getattr(record, "updated", ""),
        "abs_url": getattr(record, "abs_url", ""),
        "pdf_url": getattr(record, "pdf_url", ""),
        "comment": getattr(record, "comment", ""),
        "doi": getattr(record, "doi", ""),
    }


def _parse_date(value: Any) -> date | None:
    text = _clean_text(value)
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _run_date_value(run_date: datetime) -> date:
    if run_date.tzinfo is None:
        return run_date.date()
    return run_date.astimezone(UTC).date()


def _build_embedding_text(row: dict[str, Any]) -> str:
    parts = [
        f"Title: {row['title']}",
        f"Abstract: {row['summary']}",
    ]
    if row["authors_joined"]:
        parts.append(f"Authors: {row['authors_joined']}")
    if row["categories_joined"]:
        parts.append(f"Categories: {row['categories_joined']}")
    if row["published"]:
        parts.append(f"Published: {row['published']}")
    if row["doi"]:
        parts.append(f"DOI: {row['doi']}")
    return normalize_whitespace("\n".join(parts))


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw paper records into a dataframe ready for embedding."""
    run_day = _run_date_value(run_date)
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for record in records:
        raw = _record_to_dict(record)
        doi = _clean_text(raw.get("doi") or raw.get("paper_id")).lower()
        paper_id = _clean_text(raw.get("paper_id") or doi).lower()
        title = _clean_text(raw.get("title"))
        summary = _clean_text(raw.get("summary"))
        published_date = _parse_date(raw.get("published"))

        if not paper_id or not title or not summary or published_date is None:
            continue
        if len(summary) < MIN_SUMMARY_CHARS:
            continue
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        authors = _clean_list(raw.get("authors"))
        categories = _clean_list(raw.get("categories"))
        primary_category = _clean_text(raw.get("primary_category"))
        if not primary_category and categories:
            primary_category = categories[0]

        updated_date = _parse_date(raw.get("updated"))
        published = published_date.isoformat()
        updated = updated_date.isoformat() if updated_date else ""
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)

        row = {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": primary_category,
            "published": published,
            "updated": updated,
            "age_days": (run_day - published_date).days,
            "doi": doi,
            "abs_url": _clean_text(raw.get("abs_url")),
            "pdf_url": _clean_text(raw.get("pdf_url")),
            "comment": _clean_text(raw.get("comment")),
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
        }
        row["text_for_embedding"] = _build_embedding_text(row)
        rows.append(row)

    columns = [
        "paper_id",
        "title",
        "summary",
        "authors",
        "categories",
        "primary_category",
        "published",
        "updated",
        "age_days",
        "doi",
        "abs_url",
        "pdf_url",
        "comment",
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "text_for_embedding",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns).sort_values(
        by=["published", "paper_id"],
        ascending=[False, True],
        ignore_index=True,
    )
