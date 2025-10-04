import pinecone
from pinecone import Pinecone, ServerlessSpec
import pandas as pd
from tqdm import tqdm
from config.settings import Config

class VectorDatabase:
    def __init__(self):
        self.pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        self.index_name = Config.INDEX_NAME
        
    def create_index(self):
        """Create Pinecone index"""
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=Config.DIMENSION,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=Config.PINECONE_ENVIRONMENT
                )
            )
        
        self.index = self.pc.Index(self.index_name)
    
    def upsert_htsus_data(self, df, batch_size=100):
        """Upload HTSUS data to Pinecone"""
        vectors = []
        
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Upserting HTSUS"):
            vector = {
                'id': f"htsus_{idx}",
                'values': row['embedding'],
                'metadata': {
                    'type': 'htsus',
                    'hs_code': row['hs_code'],
                    'description': row['description'],
                    'duty_rate': row['duty_rate'],
                    'chapter': row['chapter'],
                    'chapter_title': row['chapter_title'],
                    'text': row['combined_text']
                }
            }
            vectors.append(vector)
            
            if len(vectors) >= batch_size:
                self.index.upsert(vectors=vectors)
                vectors = []
        
        if vectors:
            self.index.upsert(vectors=vectors)
    
    def upsert_cross_data(self, df, batch_size=100):
        """Upload CROSS rulings to Pinecone"""
        vectors = []
        
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Upserting CROSS"):
            vector = {
                'id': f"cross_{idx}",
                'values': row['embedding'],
                'metadata': {
                    'type': 'cross',
                    'ruling_id': row['ruling_id'],
                    'ruling_number': row['ruling_number'],
                    'date': row['date'],
                    'hs_code': row['hs_code'],
                    'description': row['description'],
                    'decision': row['decision'],
                    'text': row['combined_text'],
                    'url': row['url']
                }
            }
            vectors.append(vector)
            
            if len(vectors) >= batch_size:
                self.index.upsert(vectors=vectors)
                vectors = []
        
        if vectors:
            self.index.upsert(vectors=vectors)
    
    def setup_complete_db(self):
        """Complete database setup"""
        self.create_index()
        
        # Load processed data
        htsus_df = pd.read_pickle('data/processed/htsus_with_embeddings.pkl')
        cross_df = pd.read_pickle('data/processed/cross_with_embeddings.pkl')
        
        # Upsert data
        self.upsert_htsus_data(htsus_df)
        self.upsert_cross_data(cross_df)
        
        print("Vector database setup complete!")

# Usage
if __name__ == "__main__":
    db = VectorDatabase()
    db.setup_complete_db()