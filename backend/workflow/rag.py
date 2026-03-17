"""
RAG System using LangChain, AstraDB Vector Search, and Google Gemini.
"""

import os

from dotenv import load_dotenv
from langchain_astradb import AstraDBVectorStore
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()


class RAGSystem:
    """RAG system for answering eco-friendly construction material questions."""

    def __init__(self) -> None:
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.vector_store = AstraDBVectorStore(
            embedding=self.embeddings,
            collection_name="Eco_friendly",
            api_endpoint=os.getenv("ASTRA_DB_API_ENDPOINT"),
            token=os.getenv("ASTRA_DB_APPLICATION_TOKEN"),
            namespace=os.getenv("ASTRA_DB_KEYSPACE"),
        )

        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )

        template = """
        You are a retrieval specialist for eco-friendly building material advisory.
        Use only the supplied context to answer.
        If the context is insufficient, clearly state what is missing.
        Keep the answer concise, factual, and oriented to engineering and sustainability decisions.
        Prioritize signals that align with the merged retrieval query and engineering calculations.

        CONTEXT:
        {context}

        PROJECT CONTEXT:
        {project_context}

        MERGED QUERY:
        {question}

        ANSWER:
        """

        self.prompt = ChatPromptTemplate.from_template(template)

        self.rag_chain = (
            {
                "context": lambda x: self._retrieve_context(x["question"]),
                "project_context": lambda x: x.get("project_context", ""),
                "question": lambda x: x["question"],
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def _format_docs(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def _retrieve_context(self, question: str) -> str:
        docs = self.retriever.invoke(question)
        return self._format_docs(docs)

    def ask(self, question: str, project_context: str = "") -> dict:
        answer = self.rag_chain.invoke(
            {
                "question": question,
                "project_context": project_context,
            }
        )
        return {"answer": answer}


_rag_system = None


def get_rag_system() -> RAGSystem:
    """Get or create the RAG system singleton."""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system


if __name__ == "__main__":
    print("Starting RAG System Test...\n")

    rag = get_rag_system()

    print("Test 1: Basic Query")
    query1 = "Best sustainable material for load bearing walls"

    response1 = rag.ask(query1)

    print("Query:", query1)
    print("Answer:\n", response1["answer"])
    print("\n" + "=" * 80 + "\n")
