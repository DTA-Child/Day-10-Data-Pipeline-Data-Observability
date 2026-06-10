# Day 10 - Data Pipeline And Data Observability
# 2A202600978

End-to-end RAG data pipeline using Crossref data, ChromaDB, MiniLM embeddings, evaluation metrics, data observability, corruption simulation, and repair analysis.

## Features

* Crossref API ingestion
* Data cleaning & modeling
* MiniLM embeddings
* ChromaDB vector store
* Retrieval evaluation
* Quality & freshness monitoring
* Data corruption simulation
* Data repair and recovery analysis

## Run

### Phase 1

```bash
uv run python script/run_phase1.py
```

### Phase 2

```bash
uv run python script/run_corruption_flow.py
```

### Dashboard

```bash
streamlit run dashboard/app.py
```

### Link deploy

```bash
https://day-10-2a202600978-data-pipeline-data-observability.streamlit.app/
```

## Results

| Metric             | Baseline | Corrupted | Repaired |
| ------------------ | -------- | --------- | -------- |
| Retrieval Hit Rate | 1.000    | 0.875     | 1.000    |
| Mean Token F1      | 0.750    | 0.628     | 0.750    |
| Judge Accuracy     | 0.750    | 0.625     | 0.750    |
| Mean Judge Score   | 4.000    | 3.500     | 4.000    |

## Project Structure

```text
src/
├── ingestion/
├── retrieval/
├── evaluation/
├── observability/
└── pipelines/

script/
├── run_phase1.py
└── run_corruption_flow.py

data/
├── raw/
├── clean/
├── embeddings/
├── chroma/
├── quality/
├── results/
└── reports/
```

## Key Finding

Corrupted data reduced retrieval and answer quality. Repairing the dataset restored metrics back to baseline levels, demonstrating the importance of data quality and observability in RAG systems.
