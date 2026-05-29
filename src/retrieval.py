"""
Retrieval logika za Osijek AI Guide (Faza 2 - Napredna)
"""

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from config import VECTORSTORE_PATH, SIMILARITY_THRESHOLD, TOP_K
import os

def get_retriever():
    """Vraća retriever s postavljenim parametrima"""
    
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    vectorstore = Chroma(
        persist_directory=VECTORSTORE_PATH,
        embedding_function=embeddings
    )
    
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": SIMILARITY_THRESHOLD,
            "k": TOP_K
        }
    )
    
    return retriever

def get_relevant_documents(query: str):
    """Dohvaća relevantne dokumente s citation informacijama"""
    
    retriever = get_retriever()
    docs = retriever.invoke(query)
    
    enriched_docs = []
    for doc in docs:
        source = doc.metadata.get("source", "nepoznat")
        enriched_docs.append({
            "content": doc.page_content,
            "source": os.path.basename(source) if source else "nepoznat",
            "score": doc.metadata.get("score", 0.0)
        })
    
    return enriched_docs

def has_sufficient_context(docs, min_score=0.68):
    """Provjerava ima li dovoljno kvalitetnog konteksta"""
    if not docs:
        return False
    best_score = max(doc["score"] for doc in docs)
    return best_score >= min_score