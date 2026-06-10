from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import html
import re
from pathlib import Path
import time
from typing import Any

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json
import requests


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    doi: str
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item)
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        return _clean_text(value[0] if value else "")
    return _clean_text(value)


def _date_from_parts(value: Any) -> str:
    parts = value.get("date-parts") if isinstance(value, dict) else None
    if not parts or not isinstance(parts, list) or not parts[0]:
        return ""
    year_month_day = [str(part).zfill(2) for part in parts[0]]
    if not year_month_day:
        return ""
    year_month_day[0] = year_month_day[0].zfill(4)
    return "-".join(year_month_day)


def _best_date(item: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = _date_from_parts(item.get(key))
        if value:
            return value
    return ""


def _parse_authors(item: dict[str, Any]) -> list[str]:
    authors = []
    for author in item.get("author") or []:
        if not isinstance(author, dict):
            continue
        given = _clean_text(author.get("given"))
        family = _clean_text(author.get("family"))
        name = _clean_text(author.get("name"))
        full_name = normalize_whitespace(" ".join(part for part in [given, family] if part)) or name
        if full_name:
            authors.append(full_name)
    return authors


def _parse_pdf_url(item: dict[str, Any]) -> str:
    for link in item.get("link") or []:
        if not isinstance(link, dict):
            continue
        url = _clean_text(link.get("URL"))
        content_type = _clean_text(link.get("content-type")).lower()
        if url and ("pdf" in content_type or url.lower().endswith(".pdf")):
            return url
    return ""


def _record_to_dict(record: PaperRecord) -> dict[str, Any]:
    return asdict(record)


def _write_json_with_requested_alias(path: Path, requested_name: str, payload: Any) -> None:
    write_json(path, payload)
    alias_path = path.with_name(requested_name)
    if alias_path != path:
        write_json(alias_path, payload)


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into normalized paper records."""
    items = payload.get("message", {}).get("items", [])
    if not isinstance(items, list):
        raise ValueError("Crossref payload is missing message.items.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _clean_text(item.get("DOI"))
        title = _first_text(item.get("title"))
        summary = _clean_text(item.get("abstract"))
        if not doi or not title or not summary:
            continue

        paper_id = doi.lower()
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        categories = [_clean_text(subject) for subject in item.get("subject") or []]
        categories = [category for category in categories if category]
        published = _best_date(item, ["published-print", "published-online", "published", "created", "deposited"])
        updated = _best_date(item, ["updated", "deposited", "indexed"])
        abs_url = _clean_text(item.get("URL")) or f"https://doi.org/{doi}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_parse_authors(item),
                categories=categories,
                doi=doi,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=_parse_pdf_url(item),
                comment=_first_text(item.get("container-title")),
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref works, persist the raw payload, and persist parsed records."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "sort": "published",
        "order": "desc",
    }
    headers = {"User-Agent": "day10-data-observability-lab/0.1 (mailto:example@example.com)"}

    last_error: Exception | None = None
    response: requests.Response | None = None
    for attempt in range(4):
        try:
            response = requests.get(CROSSREF_WORKS_URL, params=params, headers=headers, timeout=30)
            if response.status_code not in RETRY_STATUS_CODES:
                response.raise_for_status()
                break
            last_error = RuntimeError(f"Crossref returned retryable status {response.status_code}.")
        except requests.RequestException as exc:
            last_error = exc

        if attempt < 3:
            time.sleep(2**attempt)
    else:
        if last_error:
            raise RuntimeError(f"Failed to fetch Crossref records: {last_error}") from last_error

    if response is None:
        raise RuntimeError("Failed to fetch Crossref records: no response returned.")

    payload = response.json()
    _write_json_with_requested_alias(settings.paths.raw_api_response, "raw_response.json", payload)

    records = parse_crossref_payload(payload)
    _write_json_with_requested_alias(
        settings.paths.raw_records_json,
        "raw_records.json",
        [_record_to_dict(record) for record in records],
    )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load parsed raw records from disk."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected raw records list in {path}.")

    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        doi = _clean_text(item.get("doi") or item.get("DOI") or item.get("paper_id"))
        categories = item.get("categories") if isinstance(item.get("categories"), list) else []
        authors = item.get("authors") if isinstance(item.get("authors"), list) else []
        records.append(
            PaperRecord(
                paper_id=_clean_text(item.get("paper_id") or doi).lower(),
                title=_clean_text(item.get("title")),
                summary=_clean_text(item.get("summary")),
                authors=[_clean_text(author) for author in authors if _clean_text(author)],
                categories=[_clean_text(category) for category in categories if _clean_text(category)],
                doi=doi,
                primary_category=_clean_text(item.get("primary_category") or (categories[0] if categories else "")),
                published=_clean_text(item.get("published")),
                updated=_clean_text(item.get("updated")),
                abs_url=_clean_text(item.get("abs_url")),
                pdf_url=_clean_text(item.get("pdf_url")),
                comment=_clean_text(item.get("comment")),
            )
        )
    return records
