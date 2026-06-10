# Dataset Summary

| Field | Value |
| --- | --- |
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2025-12-12,has-abstract:true |
| Raw records | 24 |
| Clean records | 24 |

# Evaluation Metrics

| Metric | Value |
| --- | --- |
| Samples | 96 |
| Retrieval hit rate | 1 |
| Mean token F1 | 0.75 |
| Judge accuracy | 0.75 |
| Mean judge score | 4 |
| Ragas | `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}` |

# Quality Checks

- Total records: 24
- Failed records: 0
- Pass rate: 1

| Check | Status | Failed records |
| --- | --- | --- |
| missing_title | pass | 0 |
| missing_summary | pass | 0 |
| duplicate_records | pass | 0 |
| stale_records | pass | 0 |

# Freshness

- Latest published: 2027-05-07
- Oldest published: 2026-12-01
- Stale rows: 0
- Total rows: 24
- Fresh: yes

# Findings

- Data quality checks passed for the generated dataset.
- Freshness check passed; no stale rows were reported.
- Evaluation metrics are available: retrieval hit rate 1, mean token F1 0.75.
