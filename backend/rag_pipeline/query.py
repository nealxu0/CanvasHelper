# backend/query.py
"""
RAG query utilities: load Chroma vectorstore, create a Retriever + LLM chain (LangChain),
and provide a simple function to run a query and return answer + source documents.

Designed to work with:
- backend/config.py for paths and settings
- backend/ingest.py that persisted a Chroma vectorstore to VECTORSTORE_DIR
- a local Ollama server (or other LangChain-compatible LLM) for generation

Functions:
- load_vectorstore(persist_dir, emb_model) -> Chroma vectorstore
- build_retriever(vectordb, top_k) -> Retriever
- build_qa_chain(llm, retriever, return_sources) -> RetrievalQA
- query_rag(question, top_k=4, model="llama3", return_sources=True) -> dict(answer, sources)

Example (CLI):
    python backend/query.py "Summarize my upcoming assignments"
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.llms import Ollama
from langchain.schema import Document

from .config import get_vectorstore_config, get_ollama_config, VECTORSTORE_DIR

# setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_vectorstore(
    persist_dir: Optional[str] = None,
    emb_model: Optional[str] = None,
) -> Chroma:
    """
    Load an existing Chroma vectorstore from disk.
    Raises RuntimeError if store doesn't exist or is empty.
    """
    cfg = get_vectorstore_config()
    persist_dir = str(persist_dir or cfg.persist_dir)
    emb_model = emb_model or cfg.embedding_model

    # Create the embedding wrapper
    embeddings = HuggingFaceEmbeddings(model_name=emb_model)

    # Load Chroma (will open an existing persisted DB)
    vectordb = Chroma(embedding_function=embeddings, persist_directory=persist_dir)

    # Quick sanity check: try to retrieve a small number of docs
    try:
        retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 1})
        docs = retriever.get_relevant_documents("test")
        # docs might be empty if collection is empty
        if docs is None or len(docs) == 0:
            logger.warning("Chroma vectorstore loaded but returned no documents. "
                           "Did you run ingest.py and persist the vectorstore?")
    except Exception as e:
        logger.exception("Failed to probe Chroma vectorstore: %s", e)
        raise RuntimeError(f"Could not load Chroma vectorstore at {persist_dir}: {e}")

    return vectordb


def build_retriever(vectordb: Chroma, top_k: int = 4):
    """
    Return a LangChain retriever from the vectorstore.
    """
    return vectordb.as_retriever(search_type="similarity", search_kwargs={"k": top_k})


def build_llm(model: str = "llama3"):
    """
    Build and return an LLM wrapper. Currently uses local Ollama by default.
    """
    ollama_cfg = get_ollama_config()
    # Ollama wrapper in LangChain accepts model name; base url can be configured via env or passed here
    try:
        llm = Ollama(model=model)  # if LangChain Ollama wrapper picks up base URL from env
    except TypeError:
        # older/newer signatures may require base_url keyword
        llm = Ollama(model=model, base_url=ollama_cfg.url)
    return llm


def build_qa_chain(llm, retriever, return_source_documents: bool = True):
    """
    Create a RetrievalQA chain using the provided llm and retriever.
    """
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",  # simple chain_type; can switch to 'map_reduce' or others
        retriever=retriever,
        return_source_documents=return_source_documents,
    )
    return chain


def query_rag(
    question: str,
    top_k: int = 4,
    llm_model: str = "llama3",
    return_sources: bool = True,
    persist_dir: Optional[str] = None,
    emb_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    High-level helper: load vectorstore, build retriever + LLM chain, and run the question.
    Returns a dict:
      {
        "answer": "<generated text>",
        "sources": [ { "content": "...", "metadata": {...} }, ... ]  # if return_sources True
      }
    """
    # Load vectorstore
    vectordb = load_vectorstore(persist_dir=persist_dir, emb_model=emb_model)
    retriever = build_retriever(vectordb, top_k=top_k)

    # Build LLM and chain
    llm = build_llm(model=llm_model)
    chain = build_qa_chain(llm=llm, retriever=retriever, return_source_documents=return_sources)

    # Run the chain
    try:
        # `chain.run` returns a text string when return_source_documents=False.
        # When return_source_documents=True, call chain() with a dict to get both.
        if return_sources:
            result = chain({"query": question})
            # result is typically a dict with keys: "result" (or "answer") and "source_documents"
            # LangChain variants differ: check common keys
            answer = result.get("result") or result.get("answer") or result.get("output_text") or ""
            source_docs = result.get("source_documents") or result.get("source_documents", []) or []
            # Normalize sources to simple dicts
            sources_out = []
            for d in source_docs:
                if isinstance(d, Document):
                    sources_out.append({
                        "content": d.page_content,
                        "metadata": dict(getattr(d, "metadata", {}) or {})
                    })
                elif isinstance(d, dict):
                    sources_out.append({
                        "content": d.get("page_content") or d.get("text") or "",
                        "metadata": d.get("metadata") or {}
                    })
                else:
                    # fallback: string or unknown object
                    sources_out.append({"content": str(d), "metadata": {}})
            return {"answer": answer, "sources": sources_out}
        else:
            answer = chain.run(question)
            return {"answer": answer, "sources": []}
    except Exception as e:
        logger.exception("RAG query failed: %s", e)
        raise RuntimeError(f"RAG query failed: {e}")


# -----------------------
# Optional CLI for quick testing
# -----------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Query the local RAG index and LLM")
    parser.add_argument("question", type=str, help="Question to ask the RAG system")
    parser.add_argument("--top_k", type=int, default=4, help="Number of retrievals to use")
    parser.add_argument("--model", type=str, default="llama3", help="LLM model name for Ollama")
    parser.add_argument("--no_sources", dest="sources", action="store_false", help="Do not return source documents")
    args = parser.parse_args()

    out = query_rag(
        question=args.question,
        top_k=args.top_k,
        llm_model=args.model,
        return_sources=args.sources,
    )

    # minimal CLI output
    print("ANSWER\n------")
    print(out["answer"])
    if out.get("sources"):
        print("\nSOURCES\n-------")
        for i, s in enumerate(out["sources"][:5], 1):
            meta = s.get("metadata") or {}
            title = meta.get("assignment") or meta.get("source_file") or f"source_{i}"
            print(f"[{i}] {title} — {len(s['content'])} chars")
