import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.vector_db import VectorDatabase

def main():
    print("=" * 60)
    print("HS CODE CLASSIFIER - VECTOR DATABASE SETUP")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("Connecting to Pinecone and uploading data...")
    print("This will take 10-20 minutes.\n")
    
    try:
        db = VectorDatabase()
        db.setup_complete_db()
        
        print("\n" + "=" * 60)
        print("VECTOR DATABASE SETUP COMPLETE")
        print("=" * 60)
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nYour Pinecone index is ready!")
        print("Index name: hs-code-classifier")
        print("\nNext step: Create agent files and run application")
        print("Command: streamlit run app.py")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nCheck your Pinecone API key in .env file")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    