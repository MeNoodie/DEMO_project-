import os
from dotenv import load_dotenv
import json
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_astradb import AstraDBVectorStore
from langchain_community.document_loaders import PyPDFLoader
load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
PDF_PATH = BASE_DIR / "data" / "booklet- energy eff buildings.pdf"

if not PDF_PATH.is_file():
    raise FileNotFoundError(f"PDF not found at: {PDF_PATH}")

loader = PyPDFLoader(str(PDF_PATH))

def extract_documents(docs: list[Document], source_file: str) -> list[Document]:
    documents = []

    for doc in docs:
        metadata = doc.metadata or {}
        metadata["source"] = source_file

        documents.append(
            Document(
                page_content=doc.page_content,
                metadata=metadata
            )
        )
    return documents

docs = loader.load()
DOCUMENT = extract_documents(docs, "backend/data/booklet- energy eff buildings.pdf")
print("PDF loaded.")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=100
    )

chunked_docs = text_splitter.split_documents(DOCUMENT)

print("Docs loaded and splitterd.")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vstore = AstraDBVectorStore(
    embedding=embeddings,
    collection_name="Eco_friendly",
    api_endpoint=os.getenv("ASTRA_DB_API_ENDPOINT"),
    token=os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
    namespace=os.getenv("ASTRA_DB_KEYSPACE")
)

print("AstraDB Vector Store connected.")
# vstore.add_documents(docs)

print("Documents added to AstraDB Vector Store.")
