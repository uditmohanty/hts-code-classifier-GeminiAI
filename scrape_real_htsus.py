import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import time
from tqdm import tqdm
import re

class RealHTSUScraper:
    def __init__(self):
        self.base_url = "https://hts.usitc.gov"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_chapter_list(self):
        """Get list of all 99 chapters"""
        url = f"{self.base_url}/current"
        print(f"Fetching chapter list from {url}...")
        
        response = self.session.get(url, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        chapters = []
        
        # Method 1: Look for chapter links
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Pattern: /view/chapter-XX or similar
            match = re.search(r'chapter[/-](\d+)', href.lower())
            if match:
                chapter_num = match.group(1).zfill(2)
                if chapter_num not in [c['number'] for c in chapters]:
                    chapters.append({
                        'number': chapter_num,
                        'url': href if href.startswith('http') else f"{self.base_url}{href}",
                        'title': link.get_text(strip=True)
                    })
        
        # If no chapters found, try alternative structure
        if not chapters:
            # Look for numbered sections (01-99)
            for i in range(1, 100):
                chapter_num = str(i).zfill(2)
                # Try common URL patterns
                possible_urls = [
                    f"{self.base_url}/view/chapter-{i}",
                    f"{self.base_url}/chapters/{chapter_num}",
                    f"{self.base_url}/current/chapter-{i}"
                ]
                
                for test_url in possible_urls:
                    try:
                        test_response = self.session.head(test_url, timeout=5)
                        if test_response.status_code == 200:
                            chapters.append({
                                'number': chapter_num,
                                'url': test_url,
                                'title': f"Chapter {chapter_num}"
                            })
                            break
                    except:
                        continue
                
                if i == 1 and not chapters:
                    print("Warning: Could not find chapters using standard methods")
                    break
        
        return sorted(chapters, key=lambda x: x['number'])
    
    def scrape_chapter_data(self, chapter_url, chapter_num):
        """Scrape a single chapter"""
        entries = []
        
        try:
            response = self.session.get(chapter_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple table structures
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) < 2:
                        continue
                    
                    # Extract text from cells
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # Look for HS code pattern (XXXX.XX.XXXX or similar)
                    hs_code = None
                    for text in cell_texts:
                        if re.match(r'\d{4}\.?\d{2}\.?\d{4}', text.replace(' ', '')):
                            hs_code = text.strip()
                            break
                    
                    if hs_code:
                        # Find description and duty rate
                        description = ""
                        duty_rate = ""
                        
                        for text in cell_texts:
                            if text != hs_code:
                                if '%' in text or 'Free' in text or 'cents' in text.lower():
                                    duty_rate = text
                                elif len(text) > 10:
                                    description = text
                        
                        entries.append({
                            'chapter': chapter_num,
                            'hs_code': hs_code,
                            'description': description or 'No description available',
                            'duty_rate': duty_rate or 'N/A'
                        })
        
        except Exception as e:
            print(f"Error scraping chapter {chapter_num}: {e}")
        
        return entries
    
    def scrape_all_chapters(self):
        """Scrape all 99 chapters"""
        all_data = []
        
        # Get chapters
        chapters = self.get_chapter_list()
        
        if not chapters:
            print("Could not find chapters. Using API method...")
            return self.scrape_via_api()
        
        print(f"Found {len(chapters)} chapters. Starting scrape...")
        
        for chapter in tqdm(chapters, desc="Scraping chapters"):
            entries = self.scrape_chapter_data(chapter['url'], chapter['number'])
            
            for entry in entries:
                entry['chapter_title'] = chapter['title']
                entry['source_url'] = chapter['url']
            
            all_data.extend(entries)
            time.sleep(0.5)  # Be polite
        
        return all_data
    
    def scrape_via_api(self):
        """Alternative: Use USITC DataWeb API if available"""
        print("Attempting to use USITC DataWeb API...")
        
        all_data = []
        
        # The USITC provides a DataWeb query system
        api_url = "https://dataweb.usitc.gov/api/tariff/hts"
        
        for chapter in tqdm(range(1, 100), desc="Fetching via API"):
            try:
                params = {'chapter': str(chapter).zfill(2)}
                response = self.session.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        all_data.extend(data)
                
                time.sleep(0.3)
                
            except Exception as e:
                continue
        
        return all_data
    
    def save_data(self, data, filename='data/htsus/htsus_complete'):
        """Save scraped data"""
        if not data:
            print("No data to save!")
            return
        
        # Save JSON
        with open(f"{filename}.json", 'w') as f:
            json.dump(data, f, indent=2)
        
        # Save CSV
        df = pd.DataFrame(data)
        df.to_csv(f"{filename}.csv", index=False)
        
        print(f"\nSaved {len(data)} entries to:")
        print(f"  - {filename}.json")
        print(f"  - {filename}.csv")
        
        # Show statistics
        if 'chapter' in df.columns:
            print(f"\nChapters covered: {df['chapter'].nunique()}/99")
            print("\nEntries per chapter:")
            print(df['chapter'].value_counts().sort_index().head(10))

def main():
    scraper = RealHTSUScraper()
    
    print("=" * 70)
    print("REAL HTSUS DATA SCRAPER")
    print("=" * 70)
    
    # Scrape
    data = scraper.scrape_all_chapters()
    
    # Save
    scraper.save_data(data)
    
    print("\nDone! If data is incomplete, the website structure may have changed.")
    print("Check the saved files to see what was collected.")

if __name__ == "__main__":
    main()