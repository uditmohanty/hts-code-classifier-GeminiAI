# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ---- API keys ----
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")  # e.g. "us-east1-gcp" / "gcp-starter"

    # ---- Data sources ----
    HTSUS_URL = "https://hts.usitc.gov/"
    CROSS_URL = "https://rulings.cbp.gov/home"

    # ---- Embeddings / Models ----
    # Using all-mpnet-base-v2 which produces 768-dimensional vectors
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ---- Vector DB (Pinecone) ----
    INDEX_NAME = os.getenv("PINECONE_INDEX", "hs-code-classifier")
    PINECONE_INDEX = INDEX_NAME
    # Set to 768 for all-mpnet-base-v2
    DIMENSION = int(os.getenv("EMBEDDING_DIM", "768"))

    # ---- Confidence threshold ----
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))

# handy instance (optional)
settings = Config()

# make sure the name is exported
__all__ = ["Config", "settings"]