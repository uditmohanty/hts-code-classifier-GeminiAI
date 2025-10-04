from langchain.tools import Tool
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from config.settings import Config
from typing import List, Dict

class SearchTools:
    def __init__(self):
        self.pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        self.index = self.pc.Index(Config.INDEX_NAME)
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
    
    def search_hts_database(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search HTSUS database"""
        # Create query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Search Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter={"type": {"$eq": "htsus"}},
            include_metadata=True
        )
        
        candidates = []
        for match in results['matches']:
            candidates.append({
                'hs_code': match['metadata']['hs_code'],
                'description': match['metadata']['description'],
                'duty_rate': match['metadata']['duty_rate'],
                'chapter': match['metadata']['chapter'],
                'relevance_score': match['score']
            })
        
        return candidates
    
    def search_cross_rulings(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search CROSS rulings"""
        query_embedding = self.model.encode(query).tolist()
        
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter={"type": {"$eq": "cross"}},
            include_metadata=True
        )
        
        rulings = []
        for match in results['matches']:
            rulings.append({
                'ruling_number': match['metadata']['ruling_number'],
                'hs_code': match['metadata']['hs_code'],
                'description': match['metadata']['description'],
                'decision': match['metadata']['decision'],
                'date': match['metadata']['date'],
                'url': match['metadata']['url'],
                'relevance_score': match['score']
            })
        
        return rulings
    
    def lookup_duty_rate(self, hs_code: str) -> Dict:
        """Look up duty rate for specific HS code"""
        # Search for exact HS code
        results = self.index.query(
            vector=[0.0] * Config.DIMENSION,  # Dummy vector
            top_k=1,
            filter={
                "type": {"$eq": "htsus"},
                "hs_code": {"$eq": hs_code}
            },
            include_metadata=True
        )
        
        if results['matches']:
            match = results['matches'][0]
            return {
                'duty_rate': match['metadata']['duty_rate'],
                'description': match['metadata']['description']
            }
        
        return {'duty_rate': 'Not found', 'description': ''}

def create_langchain_tools(search_tools: SearchTools) -> List[Tool]:
    """Create LangChain tools"""
    return [
        Tool(
            name="HTSUS_Search",
            func=lambda q: str(search_tools.search_hts_database(q)),
            description="Search the Harmonized Tariff Schedule database for product classifications. Input should be a product description."
        ),
        Tool(
            name="CROSS_Rulings_Search",
            func=lambda q: str(search_tools.search_cross_rulings(q)),
            description="Search CBP classification rulings for precedent. Input should be a product description."
        ),
        Tool(
            name="Duty_Rate_Lookup",
            func=lambda code: str(search_tools.lookup_duty_rate(code)),
            description="Look up duty rate for a specific HS code. Input should be a 10-digit HS code."
        )
    ]