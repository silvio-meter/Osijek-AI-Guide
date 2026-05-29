"""
Konfiguracija za Osijek AI Guide (Lega)
"""

LLM_MODEL = "grok-2"
TEMPERATURE = 0.7
MAX_TOKENS = 800

SIMILARITY_THRESHOLD = 0.72
TOP_K = 5

VECTORSTORE_PATH = "../vectorstore/chroma_db"
DATA_PATH = "../data"

DEFAULT_LANGUAGE = "hr"