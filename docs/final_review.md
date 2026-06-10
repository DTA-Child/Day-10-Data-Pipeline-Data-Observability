# Final Review — Day 10 Data Pipeline & Data Observability

**Review date:** 2026-06-10  
**Reviewer role:** Technical reviewer (pre-submission)  
**Reference:** [Rubric.md](../Rubric.md), [Guide.md](../Guide.md)

---

## Executive Summary

| Metric | Value |
| --- | --- |
| **Estimated base score** | **68 / 90** |
| **Bonus eligible (90+)?** | No |
| **Baseline pipeline (Phase 1)** | Runnable; artifacts present |
| **Corruption pipeline (Phase 2)** | Not runnable; artifacts missing |
| **End-to-end lab completion** | ~55% (Phase 1 only) |

The project delivers a solid baseline ETL → embedding → evaluation → observability flow. Raw ingestion, cleaning, vector indexing, test-set generation, and baseline reporting are implemented and backed by generated artifacts. The largest submission gaps are the **unfinished corruption/repair pipeline**, the **agent not being wired into evaluation**, and **missing comparison metrics** that the lab is designed to demonstrate.

---

## Score Breakdown

| # | Rubric area | Max | Score |
| --- | --- | ---: | ---: |
| 1 | Code structure | 10 | **8** |
| 2 | Raw ingestion | 15 | **13** |
| 3 | Cleaning | 15 | **13** |
| 4 | Embeddings | 10 | **9** |
| 5 | Agent & multi-provider LLM | 10 | **6** |
| 6 | Evaluation & scoring | 10 | **7** |
| 7 | Data observability | 10 | **8** |
| 8 | Corruption & comparison | 10 | **4** |
| | **Total (base)** | **90** | **68** |

---

## 1. Code Structure and Project Organization

**Score: 8 / 10**

### Reason

The repository follows the intended layout described in `README.md` and `Guide.md`:

- `src/core/` — configuration and shared utilities
- `src/ingestion/` — fetch, clean, corrupt
- `src/retrieval/` — embeddings, ChromaDB, LLM providers, agent, QA
- `src/evaluation/` — test set and metrics
- `src/observability/` — quality, freshness, reporting
- `src/pipelines/` — orchestration entrypoints
- `script/` — thin CLI wrappers

Module boundaries are clear, naming is consistent, and student TODO areas are mostly completed. `phase1.py` orchestrates the baseline flow in a readable sequence. Compatibility aliases (e.g. `raw_response.json`, `baseline_report.md`) show attention to artifact naming without breaking the configured paths.

### Missing work

- `src/pipelines/corruption_flow.py` still raises `NotImplementedError`.
- `docs/todo_audit.md` is outdated and still lists components as unfinished.
- No automated tests despite `pytest` in optional dev dependencies.
- `corruption.py` imports the private helper `_build_embedding_text` from `cleaning.py`, which couples modules unnecessarily.

### Improvement suggestions

1. Implement `corruption_flow.main()` following the pseudo-code already in the file and the dependency map in `todo_audit.md`.
2. Refresh or remove `docs/todo_audit.md` so it reflects the current codebase.
3. Add a small `tests/` suite for parsing, cleaning, and corruption logic to lock in schema contracts.
4. Export `build_embedding_text` as a public function in `cleaning.py` instead of importing a private symbol from corruption code.

---

## 2. Raw Data Ingestion

**Score: 13 / 15**

### Reason

`src/ingestion/crossref.py` is fully implemented:

- Calls the Crossref REST API with query, filter, pagination (`rows`), and sort order.
- Retries transient HTTP failures (429, 5xx) with exponential backoff.
- Persists the raw API payload to `data/raw/crossref_response.json` (alias: `raw_response.json`).
- Parses items into a consistent `PaperRecord` schema and saves `data/raw/crossref_records.json` (alias: `raw_records.json`).
- `load_raw_records()` correctly rehydrates records from disk.

Verified artifacts: **24 raw records** fetched and stored. Parsing handles DOI, title, abstract (HTML stripped), authors, dates, URLs, and deduplication by `paper_id`.

### Missing work

- Crossref keyword search is loose: the configured query targets RAG/LLM topics, but returned papers are largely unrelated (education, regional banking, etc.). `total-results: 105642` in the raw response suggests very broad matching.
- Many records have **empty `categories`** because Crossref `subject` is often absent for these works.
- No pagination beyond the first `max_results=24` page if a larger corpus is desired.
- Mailto in User-Agent is a placeholder (`example@example.com`).

### Improvement suggestions

1. Tighten the Crossref query/filter (e.g. `type:journal-article`, subject filters, or DOI prefix) so the corpus aligns with the lab's RAG theme.
2. Derive a fallback category from `container-title` / `comment` when `subject` is empty.
3. Document source parameters (query, filter, date window) in the phase-1 report findings section, not only in the summary table.
4. Use a real contact email in the Crossref polite-pool User-Agent string.

---

## 3. Cleaning and Data Modeling

**Score: 13 / 15**

### Reason

`build_clean_dataframe()` in `src/ingestion/cleaning.py` produces a well-defined schema:

- Filters invalid rows (missing id/title/summary, unparseable dates, short summaries &lt; 40 chars).
- Deduplicates by `paper_id`.
- Normalizes list fields (`authors`, `categories`) with de-duplication.
- Computes `age_days`, `authors_joined`, `categories_joined`, `summary_chars`.
- Builds structured `text_for_embedding` (title, abstract, authors, categories, published, DOI).

All **24 raw records** survived cleaning (**0% drop** in the current run). Outputs exist at `data/clean/papers_clean.csv` and `papers_clean.json`.

### Missing work

- **`age_days` is negative** for several rows because publication dates from Crossref are in the future (e.g. `2027-05-07`). Freshness logic treats negative values as "fresh" rather than flagging them as data anomalies.
- Empty categories propagate into downstream topic evaluation questions.
- No explicit validation that `text_for_embedding` length or content changed meaningfully after cleaning (only structural assembly).

### Improvement suggestions

1. Clamp or flag future publication dates during cleaning; set `age_days = 0` or mark rows with an `is_future_date` flag.
2. Populate `primary_category` from `comment` (journal name) when `categories` is empty.
3. Add a simple row-level quality flag column (e.g. `has_categories`, `summary_ok`) for easier observability downstream.
4. Log/filter statistics (dropped count, drop reasons) to the phase-1 report.

---

## 4. Embedding and Vector Store

**Score: 9 / 10**

### Reason

The retrieval stack is complete and functioning:

- `MiniLMEmbeddings` wraps `sentence-transformers/all-MiniLM-L6-v2` with normalized embeddings.
- `LocalEmbeddingIndex.build()` creates a ChromaDB persistent collection (`papers-baseline`), stores embeddings + metadata, and writes a manifest to `data/embeddings/papers_embeddings.json`.
- Separate collection names are configured for baseline, corrupted, and repaired runs.
- `search()` and `lookup()` support semantic and exact retrieval.

Evidence of correct operation: **retrieval hit rate = 1.0** on 96 evaluation samples; Chroma artifacts exist under `data/chroma/`.

### Missing work

- Embedding manifest stores an **absolute Windows path** in `persist_path`, which reduces portability across machines.
- Corrupted/repaired embedding manifests were never generated (blocked by corruption flow).
- No standalone script or notebook demonstrating ad-hoc query against the index outside evaluation.

### Improvement suggestions

1. Store paths relative to `project_dir` in the manifest and resolve at load time.
2. After implementing corruption flow, verify all three collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) build without collision.
3. Add a minimal `script/query_index.py` CLI for manual retrieval smoke tests.

---

## 5. Agent and Multi-Provider LLM

**Score: 6 / 10**

### Reason

Provider abstraction in `src/retrieval/llm.py` supports the required providers: OpenAI, Gemini, Anthropic, OpenRouter, Ollama, and custom OpenAI-compatible endpoints. Credential checks in `require_llm_credentials()` are explicit.

`src/retrieval/agent.py` defines a LangChain agent with two tools (`semantic_search_papers`, `lookup_paper`) and a sensible system prompt.

However, **the agent is not used in the baseline pipeline or evaluation**. `evaluate_pipeline()` calls `answer_question()` from `qa.py`, which uses rule-based answer extraction from retrieved metadata—not the LLM agent. All 96 baseline answers used the **fallback heuristic judge** because the structured LLM judge was unavailable (likely missing/invalid API key).

### Missing work

- No `data/results/agent_demo_answers.json` or other artifact showing the agent answering questions.
- LLM judge never ran; metrics rely on token-overlap heuristics.
- Agent capabilities (tool use, reasoning) are not demonstrated end-to-end.

### Improvement suggestions

1. Wire `build_agent()` into evaluation (or add a separate agent evaluation mode) so submission reflects the RAG agent, not only the QA shortcut.
2. Ensure `.env` has a valid `GOOGLE_API_KEY` (or chosen provider) and confirm structured judge output before final metrics run.
3. Add a short agent demo step in `phase1.main()` that writes `agent_demo_answers.json` for a few sample questions.
4. Document which code path is used for scoring (`qa.py` vs `agent.py`) in the report to avoid reviewer confusion.

---

## 6. Evaluation and Scoring

**Score: 7 / 10**

### Reason

Evaluation infrastructure is in place:

- `build_test_set()` generates **96 samples** across four question types (author, summary, publication, topic) with required fields.
- `evaluate_pipeline()` computes retrieval hit rate, token F1, judge accuracy/score, and optionally Ragas.
- Artifacts exist: `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`.

Baseline metrics:

| Metric | Value |
| --- | ---: |
| Samples | 96 |
| Retrieval hit rate | 1.0 |
| Mean token F1 | 0.75 |
| Judge accuracy | 0.75 |
| Mean judge score | 4.0 |
| Ragas | Skipped |

Metrics are internally consistent (24/96 incorrect ≈ 25% error rate). Failures cluster around **topic** questions where `categories_joined` is empty and the QA layer returns the first sentence of the summary instead.

### Missing work

- Ragas evaluation disabled (`RUN_RAGAS=1` not set).
- LLM judge unavailable for all samples; scoring depends on fallback heuristics.
- Evaluation does not use the LangChain agent (see Section 5).
- No corrupted/repaired metrics for comparison.

### Improvement suggestions

1. Fix LLM credentials and re-run evaluation so judge scores reflect actual model judgment.
2. Run with `RUN_RAGAS=1` for at least a subset if runtime is a concern; report results or explain skip in findings.
3. Improve topic question ground truth when categories are empty (use journal/comment field consistently in both test set and QA extraction).
4. Complete Phase 2 evaluation to produce `corrupted_metrics.json` and `repaired_metrics.json`.

---

## 7. Data Observability

**Score: 8 / 10**

### Reason

Observability requirements for Phase 1 are met:

- `run_data_quality_checks()` validates missing title, missing summary, duplicate `paper_id`, and stale `age_days`.
- `build_freshness_report()` reports latest/oldest published dates, stale row count, and `is_fresh`.
- `generate_phase1_report()` writes readable markdown with dataset summary, metrics, quality table, freshness, and findings.
- JSON reports: `data/quality/quality_report.json`, `data/quality/freshness_report.json`.
- Markdown: `data/reports/phase1_report.md` (mirrored as `baseline_report.md`).

Current baseline observability results: **100% quality pass rate**, **0 stale rows**, **is_fresh: true**.

### Missing work

- **Great Expectations** is listed in `pyproject.toml` and `settings.paths.gx_dir` exists, but no GX expectations suite is implemented or executed.
- Quality checks do not flag negative `age_days` or future publication dates as anomalies.
- Reports are factual summaries, not analytical write-ups (no interpretation of metric weaknesses, no before/after narrative).
- No observability artifacts for corrupted/repaired datasets.

### Improvement suggestions

1. Either integrate a minimal Great Expectations checkpoint or remove the unused dependency/path to avoid implied but missing functionality.
2. Add checks for future dates, empty categories, and summary length outliers.
3. Expand the findings section with actionable insights (e.g. "topic questions fail when categories empty").
4. After corruption flow, generate separate quality/freshness reports and include them in `corruption_report.md`.

---

## 8. Corruption and Comparison

**Score: 4 / 10**

### Reason

`corrupt_clean_dataframe()` in `src/ingestion/corruption.py` implements all six corruption scenarios from the guide:

1. Drop latest records (top 3 by published date)
2. Blank summaries
3. Inject noise into summaries
4. Truncate titles
5. Stale publication dates and `age_days`
6. Duplicate rows  
7. Rebuilds `text_for_embedding` and writes a JSON corruption log

`generate_corruption_report()` in `reporting.py` is also implemented and ready to compare baseline vs corrupted vs repaired runs.

**Critical gap:** `src/pipelines/corruption_flow.py` is still a stub (`NotImplementedError`). As a result, none of the Phase 2 artifacts exist:

| Expected artifact | Status |
| --- | --- |
| `data/clean/papers_clean_corrupted.*` | Missing |
| `data/clean/papers_clean_repaired.*` | Missing |
| `data/embeddings/papers_embeddings_corrupted.json` | Missing |
| `data/embeddings/papers_embeddings_repaired.json` | Missing |
| `data/results/corruption_log.json` | Missing |
| `data/results/corrupted_metrics.json` | Missing |
| `data/results/repaired_metrics.json` | Missing |
| `data/reports/corruption_report.md` | Missing |

This is the **primary blocker** for demonstrating that bad data degrades agent performance and that repair restores it—the core learning objective of the lab's second phase.

### Missing work

- Entire corruption → evaluate → repair → compare orchestration.
- No measured impact of corruption on retrieval, F1, or quality pass rates.
- No comparison report proving repair recovery.

### Improvement suggestions

1. **Priority:** Implement `corruption_flow.main()` using the pseudo-code in the file:
   - Load baseline clean data and metrics
   - Run `corrupt_clean_dataframe()`, save corrupted artifacts
   - Rebuild index with `corrupted_embeddings_json`
   - Evaluate on the **same** test set
   - Run quality/freshness on corrupted data
   - Repair from raw records via `load_raw_records()` + `build_clean_dataframe()`
   - Rebuild index, re-evaluate, generate `corruption_report.md`
2. Ensure corruption scenarios affect evaluation meaningfully (dropped records should remove ground-truth docs for some test questions).
3. In the comparison report, explicitly state metric deltas (baseline → corrupted → repaired) and tie them to corruption log entries.
4. Run `uv run python script/run_corruption_flow.py` and verify all output paths under `data/`.

---

## Bonus (90–100)

**Estimated bonus: 0** (base score below 90)

Potential bonus items from the rubric once base work is complete:

| Bonus criterion | Current status |
| --- | --- |
| Clear markdown report with metric change analysis | Partial — baseline report only; no comparison narrative |
| Meaningful corruption scenario | Code exists; not executed |
| Visualization or comparison tables | Basic tables in report template; no charts |
| Additional tests/validation | None |
| Reproducible CLI/use case | Phase 1 CLI works; Phase 2 CLI fails |

---

## Deduction Risks

| Risk | Severity | Notes |
| --- | --- | --- |
| Cannot run end-to-end | **High** | `run_corruption_flow.py` fails immediately |
| Artifacts not committed | **Medium** | `data/` outputs are untracked in git; reviewers may not reproduce without running locally |
| Report vs artifact mismatch | **Low** | Phase 1 report matches current baseline metrics |
| Hard-coded paths/keys | **Low** | Absolute path in embedding manifest; no secrets in repo; `.env` gitignored |
| Outdated documentation | **Low** | `todo_audit.md` contradicts actual implementation state |

---

## Pre-Submission Checklist

### Done

- [x] Modular project structure
- [x] Crossref fetch, parse, raw artifact persistence
- [x] Cleaning pipeline with `text_for_embedding`
- [x] ChromaDB + MiniLM index built
- [x] Evaluation test set (96 samples)
- [x] Baseline metrics and answers
- [x] Quality checks and freshness report
- [x] Phase 1 markdown report
- [x] Corruption simulation function (code only)

### Not done (must fix before submission)

- [ ] Implement and run `corruption_flow.main()`
- [ ] Generate corrupted/repaired datasets, embeddings, metrics, and answers
- [ ] Generate `data/reports/corruption_report.md` with baseline vs corrupted vs repaired comparison
- [ ] Demonstrate agent or document/evaluate via agent path
- [ ] Configure LLM API key and re-run evaluation with real judge (not 100% fallback)
- [ ] Update stale project documentation (`docs/todo_audit.md`)
- [ ] Commit or document how reviewers should reproduce artifacts (`data/` currently untracked)

### Recommended polish

- [ ] Enable Ragas (`RUN_RAGAS=1`) or document why it was skipped
- [ ] Fix future-date / negative `age_days` handling
- [ ] Use relative paths in embedding manifest
- [ ] Add minimal automated tests
- [ ] Improve Crossref query relevance or document corpus limitations

---

## Recommended Path to ~85+ Points

Estimated effort and impact if the remaining work is completed:

| Action | Points recovered (approx.) |
| --- | ---: |
| Complete corruption flow + all Phase 2 artifacts + comparison report | +18–22 |
| Wire agent into evaluation or provide agent demo artifacts | +2–3 |
| Fix LLM judge + re-run metrics | +1–2 |
| Observability polish (future-date checks, analytical findings) | +1 |

Completing Phase 2 alone would likely raise the total from **68** to the **mid-80s**. Adding agent integration and a proper LLM judge run could approach **90** and unlock bonus consideration.

---

## Conclusion

This is a **strong Phase 1 submission** with clean module design, working ingestion/cleaning/indexing, and credible baseline evaluation artifacts. It is **not yet a complete lab submission** because the corruption/repair experiment—the section weighted equally with other major components and central to the learning goals—is unimplemented at the pipeline level despite the corruption function being ready.

**Realistic current grade: 68/90.**  
**Highest-impact next step:** implement `src/pipelines/corruption_flow.py` and run `script/run_corruption_flow.py` to produce the missing comparison artifacts before submission.
