import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.htsus_scraper import HTSUScraper
from utils.cross_scraper import CROSSScraper

def main():
    print("=" * 60)
    print("HS CODE CLASSIFIER - DATA COLLECTION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Step 1: HTSUS Scraping
    print("\n[STEP 1/2] Scraping HTSUS Database...")
    print("-" * 60)
    
    try:
        htsus_scraper = HTSUScraper()
        print("Connecting to https://hts.usitc.gov/...")
        htsus_data = htsus_scraper.scrape_all()
        
        print(f"\nSuccess! Scraped {len(htsus_data)} HTSUS entries")
        print(f"Saved to: data/htsus/htsus_complete.json")
        print(f"Saved to: data/htsus/htsus_complete.csv")
        
    except Exception as e:
        print(f"\nError in HTSUS scraper: {e}")
        print("This might be due to website changes or network issues.")
        return
    
    # Step 2: CROSS Scraping
    print("\n[STEP 2/2] Scraping CROSS Rulings...")
    print("-" * 60)
    
    try:
        cross_scraper = CROSSScraper()
        print("Connecting to https://rulings.cbp.gov/...")
        cross_data = cross_scraper.scrape_all_rulings(max_pages=10)
        
        print(f"\nSuccess! Scraped {len(cross_data)} CROSS rulings")
        print(f"Saved to: data/cross/cross_rulings.json")
        print(f"Saved to: data/cross/cross_rulings.csv")
        
    except Exception as e:
        print(f"\nError in CROSS scraper: {e}")
        print("Continuing anyway - CROSS data is supplementary.")
    
    # Summary
    print("\n" + "=" * 60)
    print("DATA COLLECTION COMPLETE")
    print("=" * 60)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nNext step: Run data processing")
    print("Command: python run_processing.py")

if __name__ == "__main__":
    main()