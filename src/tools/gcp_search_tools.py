from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndexEndpoint
from sentence_transformers import SentenceTransformer
from google.cloud import firestore
from typing import List, Dict
from config.gcp_settings import GCPConfig

class GCPSearchTools:
    def __init__(self):
        # Initialize Vertex AI
        aiplatform.init(
            project=GCPConfig.PROJECT_ID, 
            location=GCPConfig.REGION
        )
        
        # Initialize embedding model
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Initialize Firestore with specific database
        self.db = firestore.Client(
            project=GCPConfig.PROJECT_ID,
            database=GCPConfig.FIRESTORE_DATABASE
        )
        
        # Initialize endpoint (if available)
        try:
            if GCPConfig.INDEX_ENDPOINT:
                self.endpoint = MatchingEngineIndexEndpoint(
                    GCPConfig.INDEX_ENDPOINT
                )
            else:
                self.endpoint = None
        except Exception as e:
            print(f"Vector Search not initialized: {e}")
            self.endpoint = None
    
    def search_hts_database(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search HTSUS using Vertex AI Vector Search"""
        
        if not self.endpoint:
            return self._fallback_search(query, 'htsus', top_k)
        
        try:
            # Create query embedding
            query_embedding = self.model.encode(query).tolist()
            
            # Query Vertex AI Vector Search
            response = self.endpoint.find_neighbors(
                deployed_index_id=GCPConfig.DEPLOYED_INDEX_ID,
                queries=[query_embedding],
                num_neighbors=top_k
            )
            
            # Parse results
            candidates = []
            for neighbor in response[0]:
                metadata = self._get_metadata(neighbor.id)
                if metadata.get('type') == 'htsus':
                    candidates.append({
                        'hs_code': metadata.get('hs_code', 'Unknown'),
                        'description': metadata.get('description', ''),
                        'duty_rate': metadata.get('duty_rate', 'N/A'),
                        'chapter': metadata.get('chapter', ''),
                        'relevance_score': float(neighbor.distance)
                    })
            
            return candidates
            
        except Exception as e:
            print(f"Vector search error: {e}")
            return self._fallback_search(query, 'htsus', top_k)
    
    def search_cross_rulings(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search CROSS rulings"""
        
        if not self.endpoint:
            return self._fallback_search(query, 'cross', top_k)
        
        try:
            query_embedding = self.model.encode(query).tolist()
            
            response = self.endpoint.find_neighbors(
                deployed_index_id=GCPConfig.DEPLOYED_INDEX_ID,
                queries=[query_embedding],
                num_neighbors=top_k
            )
            
            rulings = []
            for neighbor in response[0]:
                metadata = self._get_metadata(neighbor.id)
                if metadata.get('type') == 'cross':
                    rulings.append({
                        'ruling_number': metadata.get('ruling_number', ''),
                        'hs_code': metadata.get('hs_code', ''),
                        'description': metadata.get('description', ''),
                        'decision': metadata.get('decision', ''),
                        'date': metadata.get('date', ''),
                        'url': metadata.get('url', ''),
                        'relevance_score': float(neighbor.distance)
                    })
            
            return rulings
            
        except Exception as e:
            print(f"Vector search error: {e}")
            return self._fallback_search(query, 'cross', top_k)
    
    def _get_metadata(self, record_id: str) -> Dict:
        """Fetch metadata from Firestore"""
        try:
            doc_ref = self.db.collection('embeddings_metadata').document(record_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            print(f"Metadata fetch error: {e}")
        
        return {}
    
    def _fallback_search(self, query: str, data_type: str, top_k: int) -> List[Dict]:
        """Fallback to Firestore text search if vector search unavailable"""
        try:
            results = []
            query_lower = query.lower()
            
            # Query Firestore
            docs = self.db.collection('embeddings_metadata')\
                .where('type', '==', data_type)\
                .limit(100)\
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                description = data.get('description', '').lower()
                
                # Simple text matching
                if any(word in description for word in query_lower.split()):
                    if data_type == 'htsus':
                        results.append({
                            'hs_code': data.get('hs_code', 'Unknown'),
                            'description': data.get('description', ''),
                            'duty_rate': data.get('duty_rate', 'N/A'),
                            'chapter': data.get('chapter', ''),
                            'relevance_score': 0.5
                        })
                    else:
                        results.append({
                            'ruling_number': data.get('ruling_number', ''),
                            'hs_code': data.get('hs_code', ''),
                            'description': data.get('description', ''),
                            'decision': data.get('decision', ''),
                            'date': data.get('date', ''),
                            'url': data.get('url', ''),
                            'relevance_score': 0.5
                        })
            
            return results[:top_k]
            
        except Exception as e:
            print(f"Fallback search error: {e}")
            return []
    
    def lookup_duty_rate(self, hs_code: str) -> Dict:
        """Look up duty rate for specific HS code"""
        try:
            # Query Firestore for exact match
            docs = self.db.collection('embeddings_metadata')\
                .where('hs_code', '==', hs_code)\
                .where('type', '==', 'htsus')\
                .limit(1)\
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                return {
                    'duty_rate': data.get('duty_rate', 'Not found'),
                    'description': data.get('description', '')
                }
        except Exception as e:
            print(f"Duty lookup error: {e}")
        
        return {'duty_rate': 'Not found', 'description': ''}