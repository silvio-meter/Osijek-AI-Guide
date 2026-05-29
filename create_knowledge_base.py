from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import os

load_dotenv()

print("Učitavanje dokumenata...")

loader = DirectoryLoader("data/", glob="**/*.pdf", loader_cls=PyPDFLoader)
documents = loader.load()

print(f"Učitano {len(documents)} dokumenata.")

if len(documents) == 0:
    print("⚠️ Nema dokumenata u data/ folderu. Dodaj PDF-ove pa pokreni ponovno.")
else:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = text_splitter.split_documents(documents)
    print(f"Podijeljeno na {len(docs)} dijelova.")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(
        docs, 
        embeddings, 
        persist_directory="vectorstore/chroma_db"
    )
    print("✅ Baza znanja uspješno kreirana!")