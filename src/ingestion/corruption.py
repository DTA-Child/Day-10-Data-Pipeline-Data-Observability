from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

from ingestion.cleaning import _build_embedding_text


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate multiple data corruption scenarios and write a log.

    1. Drop some latest records.
    2. Blank summary of some rows.
    3. Inject noise into text (summary).
    4. Truncate titles.
    5. Make published dates stale.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Write corruption log to output_log_path.
    """
    corrupted_df = df.copy()

    # 1. Drop some latest records.
    # df is sorted by published descending, so the top records are the latest.
    dropped_df = corrupted_df.iloc[:3]
    dropped_ids = dropped_df["paper_id"].tolist()
    corrupted_df = corrupted_df.iloc[3:].reset_index(drop=True)

    log_data = {
        "dropped_records": dropped_ids,
        "blanked_summaries": [],
        "injected_noise": [],
        "truncated_titles": [],
        "stale_dates": [],
        "duplicates": []
    }

    n = len(corrupted_df)
    if n > 0:
        # 2. Blank summary in a few rows.
        blank_indices = [0, 1]
        for idx in blank_indices:
            if idx < n:
                paper_id = corrupted_df.at[idx, "paper_id"]
                corrupted_df.at[idx, "summary"] = ""
                corrupted_df.at[idx, "summary_chars"] = 0
                log_data["blanked_summaries"].append(paper_id)

        # 3. Inject noise into text.
        noise_indices = [2, 3]
        for idx in noise_indices:
            if idx < n:
                paper_id = corrupted_df.at[idx, "paper_id"]
                original_summary = corrupted_df.at[idx, "summary"]
                corrupted_df.at[idx, "summary"] = original_summary + " !!!NOISE!!!"
                corrupted_df.at[idx, "summary_chars"] = len(corrupted_df.at[idx, "summary"])
                log_data["injected_noise"].append(paper_id)

        # 4. Make title truncated.
        truncate_indices = [4, 5]
        for idx in truncate_indices:
            if idx < n:
                paper_id = corrupted_df.at[idx, "paper_id"]
                original_title = corrupted_df.at[idx, "title"]
                corrupted_df.at[idx, "title"] = original_title[:15]
                log_data["truncated_titles"].append(paper_id)

        # 5. Make published date old (stale) and age_days stale.
        stale_indices = [6, 7]
        for idx in stale_indices:
            if idx < n:
                paper_id = corrupted_df.at[idx, "paper_id"]
                corrupted_df.at[idx, "published"] = "2000-01-01"
                corrupted_df.at[idx, "age_days"] = 10000
                log_data["stale_dates"].append(paper_id)

        # 6. Add duplicate rows.
        dup_indices = []
        if n > 9:
            dup_indices = [8, 9]
        elif n > 1:
            dup_indices = [0, 1]

        dup_rows = []
        for idx in dup_indices:
            if idx < n:
                paper_id = corrupted_df.at[idx, "paper_id"]
                dup_rows.append(corrupted_df.iloc[idx])
                log_data["duplicates"].append(paper_id)

        if dup_rows:
            dup_df = pd.DataFrame(dup_rows)
            corrupted_df = pd.concat([corrupted_df, dup_df], ignore_index=True)

    # 7. Rebuild text_for_embedding.
    for idx, row in corrupted_df.iterrows():
        row_dict = row.to_dict()
        for col in ["authors_joined", "categories_joined"]:
            if col not in row_dict:
                row_dict[col] = ""
        corrupted_df.at[idx, "text_for_embedding"] = _build_embedding_text(row_dict)

    # 8. Write corruption log to output_log_path.
    log_path = Path(output_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)

    return corrupted_df

