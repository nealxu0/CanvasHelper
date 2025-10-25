# backend/config.py
"""
Central configuration for CanvasHelper backend.

Place environment-specific secrets in backend/.env:
  - CANVAS_BASE_URL
  - CANVAS_API_TOKEN
  - OLLAMA_URL            (optional, default http://localhost:11434)
  - EMBEDDING_MODEL      (optional, default sentence-transformers/all-MiniLM-L6-v2)
  - CHROMA_PERSIST_DIR   (optional)
  - MODEL_DIR            (optional)
  - VECTORSTORE_DIR      (optional)
  - RANDOM_SEED          (optional)

This module exposes simple functions/values to import from other modules, and
a helper to ensure the expected directories exist.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env (if present)
# Note: calling load_dotenv() here makes config importable and environment-aware.
load_dotenv(dotenv_path=Path(__file__).resolve().parents[0] / ".env")

# Project root (assumes config.py lives in backend/)
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Default directories (relative to project root)
DEFAULT_TRAINING_DATA_DIR = BACKEND_DIR / "training_data"
DEFAULT_VECTORSTORE_DIR = BACKEND_DIR / "vectorstore"
DEFAULT_MODELS_DIR = BACKEND_DIR / "models"
DEFAULT_TMP_DIR = BACKEND_DIR / "tmp"

# Environment-driven settings with fallbacks
CANVAS_BASE_URL: str = os.getenv("CANVAS_BASE_URL", "").rstrip("/")  # e.g. https://canvas.instructure.com
CANVAS_API_TOKEN: str = os.getenv("CANVAS_API_TOKEN", "")

OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Vectorstore / persistence
VECTORSTORE_DIR: Path = Path(os.getenv("VECTORSTORE_DIR", DEFAULT_VECTORSTORE_DIR))
TRAINING_DATA_DIR: Path = Path(os.getenv("TRAINING_DATA_DIR", DEFAULT_TRAINING_DATA_DIR))
MODELS_DIR: Path = Path(os.getenv("MODEL_DIR", DEFAULT_MODELS_DIR))
TMP_DIR: Path = Path(os.getenv("TMP_DIR", DEFAULT_TMP_DIR))

# LangChain / ingest defaults
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBED_BATCH_SIZE: int = int(os.getenv("EMBED_BATCH_SIZE", "128"))

# Model training defaults
RANDOM_SEED: int = int(os.getenv("RANDOM_SEED", "42"))
RF_N_ESTIMATORS: int = int(os.getenv("RF_N_ESTIMATORS", "200"))
RF_MAX_DEPTH: Optional[int] = (None if os.getenv("RF_MAX_DEPTH", "").strip() == "" else int(os.getenv("RF_MAX_DEPTH")))

# Persistence locations
SCHEDULE_MODEL_PATH: Path = MODELS_DIR / "schedule_model.pkl"
TRAINING_METRICS_PATH: Path = MODELS_DIR / "training_metrics.json"

# Small dataclass wrappers for structured access (optional)
@dataclass(frozen=True)
class CanvasConfig:
    base_url: str
    token: str

@dataclass(frozen=True)
class OllamaConfig:
    url: str

@dataclass(frozen=True)
class VectorstoreConfig:
    persist_dir: Path
    embedding_model: str
    chunk_size: int
    chunk_overlap: int

def get_canvas_config() -> CanvasConfig:
    """Return Canvas API configuration (may be empty strings if not set)."""
    return CanvasConfig(base_url=CANVAS_BASE_URL, token=CANVAS_API_TOKEN)

def get_ollama_config() -> OllamaConfig:
    """Return Ollama configuration."""
    return OllamaConfig(url=OLLAMA_URL)

def get_vectorstore_config() -> VectorstoreConfig:
    """Return vectorstore/ingest related configuration."""
    return VectorstoreConfig(
        persist_dir=VECTORSTORE_DIR,
        embedding_model=EMBEDDING_MODEL,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

def ensure_dirs():
    """Create required directories if they don't exist yet."""
    for p in (TRAINING_DATA_DIR, VECTORSTORE_DIR, MODELS_DIR, TMP_DIR):
        try:
            Path(p).mkdir(parents=True, exist_ok=True)
        except Exception:
            # silent safe-guard; callers can handle if creation fails
            pass

# Ensure directories on import so other modules can rely on them immediately
ensure_dirs()
