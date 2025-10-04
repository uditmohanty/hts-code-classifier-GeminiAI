import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.data_processor import DataProcessor

def main():
    print("=" * 60)
    print("HS CODE CLASSIFIER - DATA PROCESSING")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("Loading data and creating embeddings...")
    print("This will take 10-30 minutes depending on data size.\n")
    
    try:
        processor = DataProcessor()
        htsus_df, cross_df = processor.process_all_data()
        
        print("\n" + "=" * 60)
        print("DATA PROCESSING COMPLETE")
        print("=" * 60)
        print(f"HTSUS entries processed: {len(htsus_df)}")
        print(f"CROSS rulings processed: {len(cross_df)}")
        print(f"\nSaved to:")
        print("- data/processed/htsus_with_embeddings.pkl")
        print("- data/processed/cross_with_embeddings.pkl")
        print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nNext step: Setup vector database")
        print("Command: python run_vector_setup.py")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nMake sure you ran: python quick_setup_data.py")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()