"""
backend/ingest.py

Ingests documents from backend/training_data and builds a Chroma vectorstore using
LangChain HuggingFace embeddings.

Usage (from project root, in your backend venv):
    python backend/ingest.py

Optional arguments are available via CLI flags:
    --source_dir PATH          (default: backend/training_data)
    --persist_dir PATH         (default: backend/vectorstore)
    --emb_model MODEL_NAME     (default: sentence-transformers/all-MiniLM-L6-v2)
    --chunk_size INT           (default: 800)
    --chunk_overlap INT        (default: 200)
"""

import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema import Document

# --------- helpers ---------
def find_files(source_dir: Path) -> List[Path]:
    """Return list of candidate files (csv, json, txt) in source_dir."""
    exts = (".csv", ".json", ".txt")
    files = []
    if not source_dir.exists():
        return files
    for p in source_dir.iterdir():
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return sorted(files)

def build_doc_from_csv_row(row: pd.Series) -> Dict[str, Any]:
    """
    Build a structured doc dict from a CSV row. We try common column names
    that Canvas parser or our scraping might produce.
    Expected keys: course_name, assignment_name, description, due_date, id
    """
    keys = row.index.str.lower().tolist()
    d = {}

    # try various common column names
    def try_get(*candidates, default=""):
        for c in candidates:
            if c in keys:
                return str(row[c]).strip() if pd.notna(row[c]) else ""
        return default

    d["course_name"] = try_get("course_name", "course", "code_module", default="")
    d["assignment_name"] = try_get("assignment_name", "name", "title", "id_assessment", default="")
    d["description"] = try_get("description", "instructions", "task", "details", default="")
    d["due_date"] = try_get("due_date", "date", "due_at", default="")
    d["id"] = try_get("id", "id_assessment", "assignment_id", default="")
    return d

def build_doc_from_json(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Extract fields from a JSON-like Canvas assignment object or our parsed dict."""
    # direct keys often used by our parser
    res = {
        "course_name": obj.get("course") or obj.get("course_name") or obj.get("code_module") or "",
        "assignment_name": obj.get("name") or obj.get("assignment_name") or obj.get("title") or str(obj.get("id", "")),
        "description": obj.get("description") or obj.get("instructions") or obj.get("details") or "",
        "due_date": obj.get("due_date") or obj.get("due_at") or obj.get("date") or "",
        "id": obj.get("id") or obj.get("assignment_id") or ""
    }
    # If description contains HTML, strip basic tags (light)
    if res["description"] and "<" in res["description"]:
        import re
        res["description"] = re.sub(r"<.*?>", "", res["description"])
    return res

def load_documents_from_source(source_dir: Path) -> List[Document]:
    """Scan the source_dir and return a list of LangChain Documents with metadata."""
    docs: List[Document] = []
    files = find_files(source_dir)
    for f in files:
        if f.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(f, low_memory=False)
            except Exception:
                # try fallback with latin-1
                df = pd.read_csv(f, low_memory=False, encoding="latin-1")
            for _, row in df.iterrows():
                meta = build_doc_from_csv_row(row)
                text = "\n".join(
                    part for part in (meta.get("course_name"), meta.get("assignment_name"), meta.get("due_date"), meta.get("description")) if part
                )
                if not text.strip():
                    continue
                docs.append(Document(page_content=text, metadata={
                    "source_file": str(f.name),
                    "course": meta.get("course_name"),
                    "assignment": meta.get("assignment_name"),
                    "due_date": meta.get("due_date"),
                    "assignment_id": meta.get("id")
                }))
        elif f.suffix.lower() == ".json":
            try:
                data = json.load(open(f, "r"))
            except Exception:
                data = []
            # if the file is a dict with a top-level list called 'assignments' or similar
            if isinstance(data, dict):
                # try common keys
                if "assignments" in data and isinstance(data["assignments"], list):
                    items = data["assignments"]
                else:
                    # treat dict as single object
                    items = [data]
            elif isinstance(data, list):
                items = data
            else:
                items = []
            for obj in items:
                md = build_doc_from_json(obj)
                text = "\n".join(
                    part for part in (md.get("course_name"), md.get("assignment_name"), md.get("due_date"), md.get("description")) if part
                )
                if not text.strip():
                    continue
                docs.append(Document(page_content=text, metadata={
                    "source_file": str(f.name),
                    "course": md.get("course_name"),
                    "assignment": md.get("assignment_name"),
                    "due_date": md.get("due_date"),
                    "assignment_id": md.get("id")
                }))
        elif f.suffix.lower() == ".txt":
            content = f.read_text(encoding="utf-8", errors="ignore")
            if content.strip():
                docs.append(Document(page_content=content, metadata={"source_file": str(f.name)}))
    return docs

# --------- main ingest function ---------
def run_ingest(
    source_dir: str = "backend/training_data",
    persist_dir: str = "backend/vectorstore",
    emb_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    chunk_size: int = 800,
    chunk_overlap: int = 200,
):
    source = Path(source_dir)
    persist = Path(persist_dir)
    persist.mkdir(parents=True, exist_ok=True)

    # Load documents from disk
    documents = load_documents_from_source(source)

    if not documents:
        raise RuntimeError(f"No documents found in {source}. Put CSV/JSON/TXT files there (e.g., parsed Canvas assignments or course notes).")

    # Chunk documents
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    split_docs: List[Document] = []
    for doc in documents:
        pieces = splitter.split_text(doc.page_content)
        for i, p in enumerate(pieces):
            md = dict(doc.metadata) if doc.metadata else {}
            md.update({"chunk_index": i})
            split_docs.append(Document(page_content=p, metadata=md))

    # Create embeddings
    embeddings = HuggingFaceEmbeddings(model_name=emb_model)

    # Persist with Chroma
    vectordb = Chroma.from_documents(documents=split_docs, embedding=embeddings, persist_directory=str(persist))
    vectordb.persist()
    # Optionally: you can call vectordb._collection.count() or similar depending on chroma version

    # Return summary info
    return {
        "n_raw_docs": len(documents),
        "n_chunks": len(split_docs),
        "persist_directory": str(persist),
        "embedding_model": emb_model,
    }

# --------- CLI ---------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_dir", type=str, default="backend/training_data")
    parser.add_argument("--persist_dir", type=str, default="backend/vectorstore")
    parser.add_argument("--emb_model", type=str, default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--chunk_size", type=int, default=800)
    parser.add_argument("--chunk_overlap", type=int, default=200)

    args = parser.parse_args()
    info = run_ingest(
        source_dir=args.source_dir,
        persist_dir=args.persist_dir,
        emb_model=args.emb_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    # Minimal console feedback
    print(f"Ingest complete — {info['n_raw_docs']} source docs -> {info['n_chunks']} chunks")
    print(f"Chroma persisted at: {info['persist_directory']}")
    print(f"Embedding model: {info['embedding_model']}")
