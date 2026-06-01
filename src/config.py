"""
Konfiguracija za Osijek AI Guide (Lega)
"""

import os

# LLM settings
LLM_MODEL = "grok-3-mini"
TEMPERATURE = 0.7
MAX_TOKENS = 800

# RAG settings
SIMILARITY_THRESHOLD = 0.72
TOP_K = 5

VECTORSTORE_PATH = "../vectorstore/chroma_db"
DATA_PATH = "../data"

DEFAULT_LANGUAGE = "hr"

# ==========================================
# Authentication / JWT settings
# ==========================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-only-super-secret-key-change-me-in-production-please-1234567890"
)

if JWT_SECRET_KEY.startswith("dev-only"):
    import warnings
    warnings.warn(
        "Using default JWT_SECRET_KEY. This is insecure for production. "
        "Please set JWT_SECRET_KEY in your environment.",
        UserWarning
    )

JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7