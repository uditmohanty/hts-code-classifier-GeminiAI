import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from tqdm import tqdm
import time

class CROSSScraper:
    def __init__(self, base_url="https://rulings.cbp.gov"):
        self.base_url = base_url
        self.session = requests.Session()
        self.api_url = f"{base_url}/api/search"
    
    def search_rulings(self, query="", page=1, per_page=100):
        """Search CROSS database"""
        params = {
            'q': query,
            'page': page,
            'per_page': per_page
        }
        
        response = self.session.get(self.api_url, params=params)
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_ruling_detail(self, ruling_id):
        """Get detailed ruling information"""
        url = f"{self.base_url}/ruling/{ruling_id}"
        response = self.session.get(url)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        ruling = {
            'ruling_id': ruling_id,
            'url': url
        }
        
        # Extract fields
        for field in ['ruling_number', 'date', 'hs_code', 'description', 'decision']:
            element = soup.find('div', class_=f'ruling-{field}')
            ruling[field] = element.text.strip() if element else ''
        
        return ruling
    
    def scrape_all_rulings(self, max_pages=100, output_file='data/cross/cross_rulings.json'):
        """Scrape multiple pages of rulings"""
        all_rulings = []
        
        for page in tqdm(range(1, max_pages + 1), desc="Scraping CROSS"):
            try:
                results = self.search_rulings(page=page)
                
                if not results or 'rulings' not in results:
                    break
                
                for ruling in results['rulings']:
                    ruling_id = ruling.get('id')
                    if ruling_id:
                        detailed = self.get_ruling_detail(ruling_id)
                        if detailed:
                            all_rulings.append(detailed)
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error on page {page}: {e}")
                continue
        
        # Save
        with open(output_file, 'w') as f:
            json.dump(all_rulings, f, indent=2)
        
        df = pd.DataFrame(all_rulings)
        df.to_csv(output_file.replace('.json', '.csv'), index=False)
        
        print(f"Scraped {len(all_rulings)} CROSS rulings")
        return all_rulings

# Usage
if __name__ == "__main__":
    scraper = CROSSScraper()
    scraper.scrape_all_rulings()