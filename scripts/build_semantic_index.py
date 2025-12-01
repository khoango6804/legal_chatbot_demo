#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a lightweight semantic index for ND168 metadata so the RAG pipeline
can retrieve chunks by sentence similarity instead of relying solely on tags.

Usage:
    python scripts/build_semantic_index.py \
        --data nd168_metadata_clean.json \
        --output backend/semantic_index \
        --model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def load_records(data_path: Path) -> List[Dict[str, Any]]:
    with data_path.open("r", encoding="utf-8") as f:
        if data_path.suffix == ".jsonl":
            return [json.loads(line) for line in f if line.strip()]
        return json.load(f)


def extract_text(record: Dict[str, Any]) -> str:
    text_fields = [
        "content",
        "text",
        "diem_text",
        "khoan_intro",
        "full_text",
    ]
    for field in text_fields:
        value = record.get(field)
        if value and isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return ""


def build_index(records: List[Dict[str, Any]], model_name: str, output_dir: Path, batch_size: int = 64) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = []
    texts = []
    for idx, record in enumerate(records):
        text = extract_text(record)
        if not text:
            continue
        doc_id = record.get("doc_id") or f"chunk_{idx}"
        chunk = {
            "doc_id": doc_id,
            "article": record.get("article") or record.get("article_num"),
            "khoan": record.get("khoan") or record.get("khoan_num"),
            "diem": record.get("diem") or record.get("diem_letter"),
            "tags": record.get("tags", []),
        }
        chunks.append(chunk)
        texts.append(text)

    if not texts:
        raise ValueError("No valid chunks found to embed.")

    print(f"[semantic-index] Loaded {len(texts)} chunks. Encoding with {model_name} ...")
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    embeddings_path = output_dir / "embeddings.npy"
    metadata_path = output_dir / "metadata.json"
    config_path = output_dir / "config.json"

    np.save(embeddings_path, embeddings)
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "model_name": model_name,
                "normalize_embeddings": True,
                "chunk_count": len(chunks),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"[semantic-index] Saved embeddings to {embeddings_path}")
    print(f"[semantic-index] Saved metadata to  {metadata_path}")
    print(f"[semantic-index] Saved config to     {config_path}")


def main():
    parser = argparse.ArgumentParser(description="Build semantic index for traffic-law chunks.")
    parser.add_argument("--data", type=Path, default=Path("nd168_metadata_clean.json"), help="Path to ND168 metadata JSON/JSONL.")
    parser.add_argument("--output", type=Path, default=Path("backend/semantic_index"), help="Directory to store the index files.")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="SentenceTransformer model name.")
    parser.add_argument("--batch-size", type=int, default=64, help="Encoding batch size.")
    args = parser.parse_args()

    records = load_records(args.data)
    build_index(records, args.model, args.output, batch_size=args.batch_size)


if __name__ == "__main__":
    main()

