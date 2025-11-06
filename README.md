# Mike Virtual Coach RAG System

This project provides a complete Retrieval-Augmented Generation (RAG) pipeline for the **Mike Virtual Coach**.

## Overview

The system ingests documents from two sources:

1. **Exercices JSON** – 3,333 JSON files describing individual exercises. These files live in `data/raw/exercises_json/`.
2. **Training Program PDFs** – A handful of PDF documents containing meso- and micro‑cycle descriptions. Place them in `data/raw/pdfs/`.

The pipeline cleans and normalizes the raw data, chunks long documents into semantic segments, embeds the chunks with a Sentence Transformer, and indexes them in Qdrant. A hybrid retriever combines dense vector search with sparse BM25 retrieval. An answer generator packages the retrieved context, calls an LLM, and returns a citation‑rich response.

## Usage

1. **Install dependencies** (preferably in a virtual environment):

```bash
pip install -r requirements.txt
```

2. **Prepare raw data**: Copy your 3,333 exercise JSON files into `data/raw/exercises_json/`. Copy your PDF documents into `data/raw/pdfs/`.

3. **Run Phase I – Data cleaning & chunking**:

```bash
python scripts/clean_exercises.py
python scripts/pdf_semantic_chunker.py
```

These scripts generate the normalized JSONL files in `data/processed/`:

- `exercises.jsonl` – One exercise per line with canonicalised metadata.
- `microcycles.jsonl` and `mesocycles.jsonl` – Semantic chunks extracted from the PDFs.

4. **Run Phase II – Ingestion into Qdrant**:

Ensure Qdrant is running locally (default port 6333) or adjust the host/port. Then:

```bash
python scripts/qdrant_ingest.py
```

This script creates (or recreates) the collection `coach_mike` and ingests all chunks with their embeddings.

5. **Integrate with your API**:

The retrieval, generation and monitoring services are implemented in `app/services/`. See the comments in each file for usage details. You can import these classes into your FastAPI app or any backend.

## Notes

- Only the core functionality from CodeOrbit’s “100 K documents” architecture is implemented here: semantic chunking, hybrid retrieval with RRF fusion, optional cross‑encoder reranking, and basic monitoring.
- Features such as quantization and semantic caching are omitted because they are unnecessary for a dataset of this size.
- Modify the system prompt in `app/services/generator.py` to suit your domain.