import json
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.settings import Config

class DataProcessor:
    def __init__(self, model_name="sentence-transformers/all-mpnet-base-v2"):
        self.model = SentenceTransformer(model_name)
        print(f"Using embedding model: {model_name}")
    
    def load_htsus_data(self, file_path='data/htsus/htsus_complete.json'):
        """Load and preprocess HTSUS data"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # Create combined text for embedding
        df['combined_text'] = (
            "Chapter " + df['chapter'].astype(str) + ": " + df['chapter_title'] + " | " +
            "HTS Code: " + df['hs_code'] + " | " +
            "Description: " + df['description']
        )
        
        return df
    
    def load_cross_data(self, file_path='data/cross/cross_rulings.json'):
        """Load and preprocess CROSS data"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # Create combined text
        df['combined_text'] = (
            "Ruling: " + df['ruling_number'].fillna('') + " | " +
            "Date: " + df['date'].fillna('') + " | " +
            "HTS Code: " + df['hs_code'].fillna('') + " | " +
            "Description: " + df['description'].fillna('') + " | " +
            "Decision: " + df['decision'].fillna('')
        )
        
        return df
    
    def create_embeddings(self, texts, batch_size=32):
        """Generate embeddings for texts"""
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Creating embeddings"):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_embeddings)
        
        return np.array(embeddings)
    
    def process_all_data(self):
        """Process both HTSUS and CROSS data"""
        # Create output directory
        os.makedirs('data/processed', exist_ok=True)
        
        # Load data
        print("Loading HTSUS data...")
        htsus_df = self.load_htsus_data()
        
        print("Loading CROSS data...")
        cross_df = self.load_cross_data()
        
        # Create embeddings
        print("Creating HTSUS embeddings...")
        htsus_embeddings = self.create_embeddings(htsus_df['combined_text'].tolist())
        htsus_df['embedding'] = htsus_embeddings.tolist()
        
        print("Creating CROSS embeddings...")
        cross_embeddings = self.create_embeddings(cross_df['combined_text'].tolist())
        cross_df['embedding'] = cross_embeddings.tolist()
        
        # Save processed data
        print("Saving processed data...")
        htsus_df.to_pickle('data/processed/htsus_with_embeddings.pkl')
        cross_df.to_pickle('data/processed/cross_with_embeddings.pkl')
        
        print(f"✅ Processed {len(htsus_df)} HTSUS entries and {len(cross_df)} CROSS rulings")
        print(f"✅ Files saved to data/processed/")
        
        return htsus_df, cross_df

# Usage
if __name__ == "__main__":
    processor = DataProcessor()
    processor.process_all_data()