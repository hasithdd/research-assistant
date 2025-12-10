#!/usr/bin/env python3
"""Download embedding model during Docker build to avoid runtime delays."""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

if __name__ == "__main__":
    print(f"Downloading {MODEL_NAME}...")
    SentenceTransformer(MODEL_NAME)
    print("Model downloaded successfully!")
