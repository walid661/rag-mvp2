all-phase1:
	python scripts/clean_exercises.py
	python scripts/pdf_semantic_chunker.py

ingest:
	python scripts/qdrant_ingest.py