import re
import json
from pathlib import Path
import fitz  # PyMuPDF

# Regular expressions to detect meso- and micro-cycle headers.
# These patterns can be adapted as needed.
MESO_HEADER_RE = re.compile(r"^MC\d+(?:\.\d+)?\s*[-–]\s*.*", re.IGNORECASE)
MICRO_HEADER_RE = re.compile(r"^mc[A-Z]\d{2}\s*[-–]\s*.*", re.IGNORECASE)

def pdf_to_text(path: Path) -> str:
    doc = fitz.open(path.as_posix())
    texts = []
    for page in doc:
        texts.append(page.get_text())
    return "\n".join(texts)

def split_blocks(text: str, header_re: re.Pattern) -> list:
    lines = text.split("\n")
    blocks = []
    current_block = []
    for line in lines:
        if header_re.match(line.strip()):
            if current_block:
                blocks.append("\n".join(current_block).strip())
                current_block = []
            current_block.append(line.strip())
        else:
            current_block.append(line.strip())
    if current_block:
        blocks.append("\n".join(current_block).strip())
    return blocks

def parse_micro_block(block: str) -> dict:
    # Parse a micro-cycle block into metadata fields.
    lines = block.split("\n")
    name = lines[0]
    body = "\n".join(lines[1:])
    parts = [part.strip() for part in re.split(r"\|", body) if part.strip()]
    keys = ["focus", "objectif", "methode", "format", "mouvements_cles", "progression", "intensite"]
    meta = {"cycle_type": "micro", "name": name}
    for key, value in zip(keys, parts):
        meta[key] = value
    return {
        "doc_id": name,
        "chunk_id": f"{name}#0001",
        "text": block,
        "meta": meta,
    }

def parse_meso_block(block: str) -> dict:
    # For meso cycles we keep the entire block. Extract the first line as the name.
    lines = block.split("\n")
    name = lines[0]
    meta = {"cycle_type": "meso", "name": name}
    return {
        "doc_id": name,
        "chunk_id": f"{name}#0001",
        "text": block,
        "meta": meta,
    }

def process_pdf_dir(in_dir="data/raw/pdfs", out_micro="data/processed/microcycles.jsonl", out_meso="data/processed/mesocycles.jsonl"):
    in_path = Path(in_dir)
    out_micro_path = Path(out_micro)
    out_meso_path = Path(out_meso)
    out_micro_path.parent.mkdir(parents=True, exist_ok=True)
    out_meso_path.parent.mkdir(parents=True, exist_ok=True)
    with out_micro_path.open("w", encoding="utf-8") as f_micro, out_meso_path.open("w", encoding="utf-8") as f_meso:
        for pdf_file in in_path.glob("*.pdf"):
            text = pdf_to_text(pdf_file)
            # Extract micro cycles
            micro_blocks = split_blocks(text, MICRO_HEADER_RE)
            for block in micro_blocks:
                row = parse_micro_block(block)
                f_micro.write(json.dumps(row, ensure_ascii=False) + "\n")
            # Extract meso cycles
            meso_blocks = split_blocks(text, MESO_HEADER_RE)
            for block in meso_blocks:
                row = parse_meso_block(block)
                f_meso.write(json.dumps(row, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    process_pdf_dir()