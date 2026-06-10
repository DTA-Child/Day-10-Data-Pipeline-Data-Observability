from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


QUESTION_TYPES = ("author", "summary", "publication", "topic")
MIN_SAMPLES = 20


def _clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return normalize_whitespace(str(value))


def _clean_doc_id(value: Any) -> str:
    return _clean_text(value).lower()


def _question_anchor(row: pd.Series) -> str:
    title = _clean_text(row.get("title"))
    return title.replace("'", "")


def _topic_ground_truth(row: pd.Series) -> str:
    topic = _clean_text(row.get("categories_joined"))
    if topic:
        return topic
    topic = _clean_text(row.get("primary_category"))
    if topic:
        return topic
    topic = _clean_text(row.get("comment"))
    if topic:
        return topic
    return _question_anchor(row)


def _sample_for_type(row: pd.Series, question_type: str, sample_id: int) -> dict[str, Any] | None:
    title = _question_anchor(row)
    paper_id = _clean_doc_id(row.get("paper_id"))
    if not title or not paper_id:
        return None

    if question_type == "author":
        ground_truth = _clean_text(row.get("authors_joined"))
        question = f"Who authored '{title}'?"
    elif question_type == "summary":
        summary = _clean_text(row.get("summary"))
        ground_truth = first_sentence(summary)
        question = f"What is the main summary of '{title}'?"
    elif question_type == "publication":
        ground_truth = _clean_text(row.get("published"))
        question = f"When was '{title}' published?"
    elif question_type == "topic":
        ground_truth = _topic_ground_truth(row)
        question = f"What categories or topic describe '{title}'?"
    else:
        return None

    if not ground_truth:
        return None

    return {
        "id": f"eval-{sample_id:03d}",
        "question_type": question_type,
        "question": question,
        "ground_truth": ground_truth,
        "ground_truth_doc_ids": [paper_id],
    }


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic evaluation set from a cleaned papers dataframe."""
    required_columns = {"paper_id", "title", "summary", "published"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Cleaned dataframe is missing required columns: {sorted(missing)}")

    if df.empty:
        raise ValueError("Cannot build an evaluation set from an empty dataframe.")

    working = df.copy()
    for optional_column in ["authors_joined", "categories_joined"]:
        if optional_column not in working.columns:
            working[optional_column] = ""

    working = working.sort_values(by=["paper_id", "title"], kind="stable").reset_index(drop=True)

    samples: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    sample_id = 1

    for question_type in QUESTION_TYPES:
        for _, row in working.iterrows():
            sample = _sample_for_type(row, question_type, sample_id)
            if sample is None or sample["question"] in seen_questions:
                continue
            samples.append(sample)
            seen_questions.add(sample["question"])
            sample_id += 1

    if len(samples) < MIN_SAMPLES:
        raise ValueError(
            f"Need at least {MIN_SAMPLES} valid evaluation samples, but only generated {len(samples)}."
        )

    samples = samples[: max(MIN_SAMPLES, len(samples))]
    write_json(Path(output_path), samples)
    return samples
