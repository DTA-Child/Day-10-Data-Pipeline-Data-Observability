# TODO Audit

This audit covers `Guide.md`, `Rubric.md`, and the repository source tree. The explicit unfinished work is concentrated in student TODO stubs that raise `NotImplementedError`; these stubs currently block both runnable lab entrypoints.

## Summary

| Area | Status | Blocking components |
| --- | --- | --- |
| Raw data ingestion | Unfinished | `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` |
| Cleaning and data modeling | Unfinished | `build_clean_dataframe` |
| Evaluation set generation | Unfinished | `build_test_set` |
| Baseline pipeline orchestration | Unfinished | `pipelines.phase1.main` |
| Data quality and freshness | Unfinished | `run_data_quality_checks`, `build_freshness_report` |
| Markdown reporting | Unfinished | `generate_phase1_report`, `generate_corruption_report` |
| Corruption simulation | Unfinished | `corrupt_clean_dataframe` |
| Corruption/repair pipeline orchestration | Unfinished | `pipelines.corruption_flow.main` |
| Retrieval, embeddings, LLM provider, QA, metrics | Implemented enough for dependencies | No TODO stubs found |

## Unfinished Components

### `src/ingestion/crossref.py`

#### `parse_crossref_payload(payload: dict) -> list[PaperRecord]`

- **Missing logic:** Parse the Crossref REST API response into the local `PaperRecord` schema. The function currently contains only pseudo-code and raises `NotImplementedError`.
- **Expected inputs:** A Crossref payload dictionary, expected to contain `payload["message"]["items"]`.
- **Expected outputs:** A list of `PaperRecord` instances with `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, and `comment`.
- **Dependencies:** `PaperRecord`; Crossref item fields such as DOI, title, abstract, author list, subject/category values, publication/update dates, and links; text normalization/filtering rules required before records are accepted.

#### `fetch_source_records(settings: Settings) -> list[PaperRecord]`

- **Missing logic:** Fetch records from the configured external source, save the raw API response, parse records, and save parsed raw records. The function currently raises `NotImplementedError`.
- **Expected inputs:** `Settings` from `core.config.load_settings`, especially `settings.source_query`, `settings.source_filter`, `settings.max_results`, `settings.paths.raw_api_response`, and `settings.paths.raw_records_json`.
- **Expected outputs:** A list of parsed `PaperRecord` objects and persisted raw artifacts in `data/raw/`.
- **Dependencies:** External Crossref REST API access; retry/error handling for transient responses such as 429/503; `parse_crossref_payload`; JSON serialization helpers such as `core.utils.write_json`; parent directory creation via utility functions.

#### `load_raw_records(path: Path) -> list[PaperRecord]`

- **Missing logic:** Load a JSON snapshot of raw parsed records and convert it back into `PaperRecord` instances. The function currently raises `NotImplementedError`.
- **Expected inputs:** Path to a JSON file, normally `settings.paths.raw_records_json`.
- **Expected outputs:** A list of `PaperRecord` instances equivalent to the saved raw records.
- **Dependencies:** Raw record JSON schema produced by `fetch_source_records`; `PaperRecord`; JSON reading helper such as `core.utils.read_json`.

### `src/ingestion/cleaning.py`

#### `build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame`

- **Missing logic:** Convert raw records into a cleaned dataframe ready for embedding. The function currently raises `NotImplementedError`.
- **Expected inputs:** A list of `PaperRecord` values from `fetch_source_records` or `load_raw_records`; a `run_date` used to calculate freshness fields.
- **Expected outputs:** A pandas dataframe with normalized paper fields and helper columns required downstream, including `paper_id`, `title`, `summary`, `authors`, `categories`, `primary_category`, `published`, `updated`, `age_days`, `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`, `abs_url`, and `pdf_url`.
- **Dependencies:** `PaperRecord`; pandas; date parsing; text normalization rules; duplicate removal and invalid-row filtering; downstream schema expected by `LocalEmbeddingIndex._build_documents`, `build_test_set`, data quality checks, and corruption simulation.

### `src/evaluation/testset.py`

#### `build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]`

- **Missing logic:** Create and persist an evaluation set from the cleaned dataframe. The function currently raises `NotImplementedError`.
- **Expected inputs:** Cleaned dataframe from `build_clean_dataframe`; output path, normally `settings.paths.eval_testset`.
- **Expected outputs:** A list of evaluation samples written as JSON. Each sample should contain `id`, `question_type`, `question`, `ground_truth`, and `ground_truth_doc_ids`.
- **Dependencies:** Clean dataframe columns such as `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, and `published`; JSON writing helper; enough valid documents to create representative summary, authors, date, and category questions; downstream `evaluate_pipeline`, which expects these exact fields.

### `src/pipelines/phase1.py`

#### `main() -> None`

- **Missing logic:** Orchestrate the baseline pipeline end to end. The function currently raises `NotImplementedError`.
- **Expected inputs:** Environment/configuration loaded through `core.config.load_settings`; optional existing raw records and test set depending on `settings.refresh_source` and `settings.refresh_test_set`.
- **Expected outputs:** Baseline artifacts under `data/`, including raw records, clean CSV/JSON, embedding manifest/Chroma index, evaluation test set, baseline metrics, baseline answers, quality reports, freshness report, and `data/reports/phase1_report.md`.
- **Dependencies:** `load_settings`; `fetch_source_records` or `load_raw_records`; `build_clean_dataframe`; `core.utils.write_csv`/`write_json`; `LocalEmbeddingIndex.build`; `build_test_set`; `evaluate_pipeline`; `run_data_quality_checks`; `build_freshness_report`; `generate_phase1_report`; possibly `build_agent`/`run_agent_question` for demo answers.

### `src/observability/quality.py`

#### `run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]`

- **Missing logic:** Run data quality checks and persist a quality report. The function currently raises `NotImplementedError`.
- **Expected inputs:** Clean or corrupted/repaired dataframe; `Settings` with `quality_dir`, `gx_dir`, and freshness threshold paths; report name for the output artifact.
- **Expected outputs:** A dictionary summarizing quality check results and a persisted report under `data/quality/`.
- **Dependencies:** Clean dataframe schema from `build_clean_dataframe`; pandas; optional Great Expectations dependency listed in `pyproject.toml`; JSON writing helper; threshold rules for row count, non-null/unique `paper_id`, non-null `title`, summary length, and `age_days` freshness.

#### `build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]`

- **Missing logic:** Compute and persist freshness status for a dataset. The function currently raises `NotImplementedError`.
- **Expected inputs:** Dataframe with `published` and `age_days`; `Settings` with `freshness_threshold_days`; report path such as `settings.paths.freshness_report`.
- **Expected outputs:** A dictionary containing `latest_published`, `oldest_published`, `stale_rows`, `total_rows`, and `is_fresh`, also written to JSON.
- **Dependencies:** Clean dataframe date/freshness fields from `build_clean_dataframe`; pandas date handling; JSON writing helper; threshold from `Settings`.

### `src/observability/reporting.py`

#### `generate_phase1_report(report_path, source_summary, metrics, quality, freshness) -> None`

- **Missing logic:** Generate the baseline markdown report. The function currently raises `NotImplementedError`.
- **Expected inputs:** Output path, source summary, evaluation metrics, quality check result, and freshness result.
- **Expected outputs:** Markdown file at `report_path`, normally `data/reports/phase1_report.md`.
- **Dependencies:** Outputs from `phase1.main`, especially source fetch/load summary, `evaluate_pipeline`, `run_data_quality_checks`, and `build_freshness_report`; text writing helper.

#### `generate_corruption_report(report_path, baseline_metrics, corrupted_metrics, repaired_metrics, corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness) -> None`

- **Missing logic:** Generate the comparison markdown report for baseline, corrupted, and repaired runs. The function currently raises `NotImplementedError`.
- **Expected inputs:** Output path; baseline/corrupted/repaired metric dictionaries; quality dictionaries for corrupted and repaired datasets; freshness dictionaries for corrupted and repaired datasets.
- **Expected outputs:** Markdown file at `report_path`, normally `data/reports/corruption_report.md`, comparing retrieval, answer quality, data quality, and freshness.
- **Dependencies:** `evaluate_pipeline` outputs for baseline/corrupted/repaired runs; `run_data_quality_checks`; `build_freshness_report`; comparison data produced by `pipelines.corruption_flow.main`; text writing helper.

### `src/ingestion/corruption.py`

#### `corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame`

- **Missing logic:** Simulate multiple data corruption scenarios and persist a corruption log. The function currently raises `NotImplementedError`.
- **Expected inputs:** Baseline cleaned dataframe; output log path, normally `settings.paths.corruption_log`.
- **Expected outputs:** Corrupted dataframe with the same downstream schema as the baseline clean dataframe, plus a JSON log describing dropped records, blank summaries, noise injection, title truncation, stale dates, duplicates, and rebuilt embedding text.
- **Dependencies:** Clean dataframe columns from `build_clean_dataframe`; pandas; deterministic or documented sampling strategy; JSON writing helper; downstream `LocalEmbeddingIndex.build`, `evaluate_pipeline`, `run_data_quality_checks`, and `build_freshness_report`.

### `src/pipelines/corruption_flow.py`

#### `main() -> None`

- **Missing logic:** Orchestrate corruption, re-evaluation, repair, and comparison. The function currently raises `NotImplementedError`.
- **Expected inputs:** Existing baseline clean data, raw records, baseline metrics, and evaluation set; configuration loaded through `load_settings`.
- **Expected outputs:** Corrupted and repaired clean CSV/JSON files, corrupted and repaired embedding manifests/index collections, corrupted and repaired metrics/answers, corrupted and repaired quality/freshness reports, corruption log, and `data/reports/corruption_report.md`.
- **Dependencies:** `load_settings`; baseline artifacts from `phase1.main`; `corrupt_clean_dataframe`; `LocalEmbeddingIndex.build`; `evaluate_pipeline`; `run_data_quality_checks`; `build_freshness_report`; raw-record repair path through `load_raw_records` and `build_clean_dataframe`; `generate_corruption_report`.

## Dependency Map

```text
script/run_phase1.py
  -> pipelines.phase1.main
      -> core.config.load_settings
      -> ingestion.crossref.fetch_source_records
          -> external Crossref REST API
          -> ingestion.crossref.parse_crossref_payload
          -> data/raw/crossref_response.json
          -> data/raw/crossref_records.json
      -> ingestion.crossref.load_raw_records
          -> data/raw/crossref_records.json
      -> ingestion.cleaning.build_clean_dataframe
          -> PaperRecord schema
          -> clean dataframe schema expected by retrieval/evaluation/observability
      -> core.utils.write_csv / write_json
          -> data/clean/papers_clean.csv
          -> data/clean/papers_clean.json
      -> retrieval.index.LocalEmbeddingIndex.build
          -> text_for_embedding and metadata columns
          -> data/chroma/
          -> data/embeddings/papers_embeddings.json
      -> evaluation.testset.build_test_set
          -> data/eval/test_set.json
      -> evaluation.metrics.evaluate_pipeline
          -> retrieval.qa.answer_question
          -> retrieval.index.LocalEmbeddingIndex
          -> data/results/baseline_metrics.json
          -> data/results/baseline_answers.json
      -> observability.quality.run_data_quality_checks
          -> data/quality/
      -> observability.quality.build_freshness_report
          -> data/quality/freshness_report.json
      -> observability.reporting.generate_phase1_report
          -> data/reports/phase1_report.md
```

```text
script/run_corruption_flow.py
  -> pipelines.corruption_flow.main
      -> core.config.load_settings
      -> baseline artifacts from phase1
          -> data/clean/papers_clean.csv or .json
          -> data/results/baseline_metrics.json
          -> data/eval/test_set.json
      -> ingestion.corruption.corrupt_clean_dataframe
          -> data/results/corruption_log.json
          -> data/clean/papers_clean_corrupted.csv
          -> data/clean/papers_clean_corrupted.json
      -> retrieval.index.LocalEmbeddingIndex.build
          -> data/embeddings/papers_embeddings_corrupted.json
      -> evaluation.metrics.evaluate_pipeline
          -> data/results/corrupted_metrics.json
          -> data/results/corrupted_answers.json
      -> observability.quality.run_data_quality_checks
      -> observability.quality.build_freshness_report
      -> repair from raw source
          -> ingestion.crossref.load_raw_records
          -> ingestion.cleaning.build_clean_dataframe
          -> data/clean/papers_clean_repaired.csv
          -> data/clean/papers_clean_repaired.json
          -> data/embeddings/papers_embeddings_repaired.json
          -> data/results/repaired_metrics.json
          -> data/results/repaired_answers.json
      -> observability.reporting.generate_corruption_report
          -> data/reports/corruption_report.md
```

## Notes On Completed Supporting Code

- `src/retrieval/embeddings.py`, `src/retrieval/index.py`, `src/retrieval/llm.py`, `src/retrieval/agent.py`, and `src/retrieval/qa.py` do not contain TODO stubs. They depend on the cleaned dataframe schema being produced correctly.
- `src/evaluation/metrics.py` is implemented and depends on `build_test_set` producing the required sample fields.
- `script/run_phase1.py` and `script/run_corruption_flow.py` are thin entrypoints; they are blocked because the corresponding pipeline `main()` functions are unfinished.
