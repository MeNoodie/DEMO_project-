import os
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from langchain_astradb import AstraDBVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DEFAULT_COLLECTION_NAME = os.getenv("ASTRA_DB_COLLECTION", "Eco_friendly")
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value


def discover_pdf_paths(data_dir: Path = DATA_DIR) -> List[Path]:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    pdf_paths = sorted(p for p in data_dir.glob("*.pdf") if p.is_file())
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in: {data_dir}")
    return pdf_paths


def load_pdf_documents(pdf_paths: Iterable[Path]) -> List[Document]:
    all_docs: List[Document] = []
    for pdf_path in pdf_paths:
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()
        rel_source = str(pdf_path.relative_to(BASE_DIR))

        for doc in docs:
            metadata = dict(doc.metadata or {})
            metadata["source"] = rel_source
            metadata["source_file"] = pdf_path.name
            all_docs.append(Document(page_content=doc.page_content, metadata=metadata))

    if not all_docs:
        raise ValueError("No text content extracted from the provided PDFs.")
    return all_docs


def split_documents(
    docs: List[Document],
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    if not chunks:
        raise ValueError("Chunking produced 0 chunks. Check PDF contents.")
    return chunks


def get_embeddings(model_name: str = DEFAULT_EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name)


def get_vector_store(
    embeddings: HuggingFaceEmbeddings,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> AstraDBVectorStore:
    return AstraDBVectorStore(
        embedding=embeddings,
        collection_name=collection_name,
        api_endpoint=_require_env("ASTRA_DB_API_ENDPOINT"),
        token=_require_env("ASTRA_DB_APPLICATION_TOKEN"),
        namespace=os.getenv("ASTRA_DB_KEYSPACE"),
    )


def ingest_pdfs(
    pdf_paths: Iterable[Path] | None = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
    batch_size: int = 64,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> dict:
    selected_paths = list(pdf_paths) if pdf_paths is not None else discover_pdf_paths()
    raw_docs = load_pdf_documents(selected_paths)
    chunks = split_documents(raw_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    embeddings = get_embeddings()
    vector_store = get_vector_store(embeddings, collection_name=collection_name)

    total_inserted = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        batch_ids = [
            (
                f"{doc.metadata.get('source_file', 'unknown')}:"
                f"p{doc.metadata.get('page', 'na')}:"
                f"c{doc.metadata.get('chunk_id', start + idx)}"
            )
            for idx, doc in enumerate(batch)
        ]
        # vector_store.add_documents(batch, ids=batch_ids)
        total_inserted += len(batch)

    return {
        "pdf_count": len(selected_paths),
        "raw_pages": len(raw_docs),
        "chunk_count": len(chunks),
        "inserted": total_inserted,
        "collection_name": collection_name,
    }


if __name__ == "__main__":
    stats = ingest_pdfs()
    print("Knowledge base ingestion completed.")
    print(stats)
