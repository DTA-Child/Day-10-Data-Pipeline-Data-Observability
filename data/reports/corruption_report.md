# Dataset Summary

| Dataset | Total records | Failed records | Pass rate | Stale rows |
| --- | --- | --- | --- | --- |
| Corrupted | 23 | 6 | 0.7391 | 2 |
| Repaired | 24 | 0 | 1 | 0 |

# Evaluation Metrics

| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Retrieval hit rate | 1 | 0.875 | 1 |
| Mean token F1 | 0.75 | 0.6277 | 0.75 |
| Judge accuracy | 0.75 | 0.625 | 0.75 |
| Mean judge score | 4 | 3.5 | 4 |

# Quality Checks

## Corrupted

| Check | Status | Failed records |
| --- | --- | --- |
| missing_title | pass | 0 |
| missing_summary | fail | 2 |
| duplicate_records | fail | 4 |
| stale_records | fail | 2 |

## Repaired

| Check | Status | Failed records |
| --- | --- | --- |
| missing_title | pass | 0 |
| missing_summary | pass | 0 |
| duplicate_records | pass | 0 |
| stale_records | pass | 0 |

# Freshness

- Corrupted stale rows: 2
- Corrupted fresh: no
- Repaired stale rows: 0
- Repaired fresh: yes

# Findings

## Impact of Corruption

The corrupted dataset introduced data quality issues affecting 6 records, including missing summaries, duplicate records, and stale publication dates.

Missing summaries reduced the amount of semantic information available to the embedding model, making relevant documents harder to retrieve.

Duplicate records increased retrieval noise and reduced the overall quality of search results.

Freshness monitoring detected 2 stale records, demonstrating how outdated content can impact data reliability.

After corruption, retrieval hit rate decreased from 1.000 to 0.875 (-12.5%).

Mean token F1 decreased from 0.7500 to 0.6277 (-12.2%), indicating lower answer quality.

Judge accuracy decreased from 0.750 to 0.625 (-12.5%), confirming that corrupted data negatively affected downstream evaluation performance.

## Recovery After Repair

The repair process rebuilt the dataset from the original raw source, restoring missing content, removing duplicates, and recovering freshness.

Retrieval hit rate recovered to 1.000, matching the baseline value of 1.000.

Mean token F1 recovered to 0.7500, indicating that answer quality returned to its original level.

Judge accuracy recovered to 0.750, demonstrating that the impact of corruption was reversible.

## Conclusion

This experiment demonstrates that data quality directly affects retrieval effectiveness and answer quality in RAG systems.

Corrupted datasets degraded retrieval and evaluation metrics, while repairing the data restored performance to baseline levels.
