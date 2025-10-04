import os

class GCPConfig:
    # Project settings - will be set from environment
    PROJECT_ID = os.getenv('GCP_PROJECT_ID')
    REGION = os.getenv('GCP_REGION', 'us-central1')
    
    # Vertex AI
    GEMINI_MODEL = "gemini-2.5-flash-002"
    EMBEDDING_MODEL = "text-embedding-004"
    
    # Vector Search
    INDEX_ENDPOINT = os.getenv('VERTEX_INDEX_ENDPOINT')
    DEPLOYED_INDEX_ID = "hs_classifier_deployed"
    
    # Storage buckets
    DATA_BUCKET = f"{PROJECT_ID}-data" if PROJECT_ID else None
    EMBEDDINGS_BUCKET = f"{PROJECT_ID}-embeddings" if PROJECT_ID else None
    REPORTS_BUCKET = f"{PROJECT_ID}-reports" if PROJECT_ID else None
    
    # Firestore
    FIRESTORE_DATABASE = 'firestore-database'
    
    # Confidence threshold
    CONFIDENCE_THRESHOLD = 0.80