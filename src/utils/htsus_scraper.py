import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
from tqdm import tqdm
import re

class HTSUScraper:
    def __init__(self, base_url="https://hts.usitc.gov"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def get_all_chapters(self):
        """Scrape all 99 chapters"""
        url = f"{self.base_url}/current"
        response = self.session.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        chapters = []
        # Find chapter links
        for link in soup.find_all('a', href=re.compile(r'/view/chapter')):
            chapter_num = re.search(r'chapter-(\d+)', link['href'])
            if chapter_num:
                chapters.append({
                    'chapter': chapter_num.group(1),
                    'title': link.text.strip(),
                    'url': self.base_url + link['href']
                })
        
        return chapters
    
    def scrape_chapter(self, chapter_url):
        """Scrape detailed chapter data"""
        response = self.session.get(chapter_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        entries = []
        
        # Find all HTS entries
        for row in soup.find_all('tr', class_='hts-row'):
            try:
                hs_code = row.find('td', class_='hts-code')
                description = row.find('td', class_='hts-description')
                duty_rate = row.find('td', class_='hts-duty')
                
                if hs_code and description:
                    entries.append({
                        'hs_code': hs_code.text.strip(),
                        'description': description.text.strip(),
                        'duty_rate': duty_rate.text.strip() if duty_rate else 'N/A',
                        'source_url': chapter_url
                    })
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
        
        return entries
    
    def scrape_all(self, output_file='data/htsus/htsus_complete.json'):
        """Scrape all 99 chapters"""
        chapters = self.get_all_chapters()
        all_data = []
        
        for chapter in tqdm(chapters, desc="Scraping HTSUS"):
            try:
                entries = self.scrape_chapter(chapter['url'])
                for entry in entries:
                    entry['chapter'] = chapter['chapter']
                    entry['chapter_title'] = chapter['title']
                all_data.extend(entries)
                time.sleep(1)  # Be respectful to the server
            except Exception as e:
                print(f"Error scraping chapter {chapter['chapter']}: {e}")
        
        # Save to JSON
        with open(output_file, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        # Also save as CSV
        df = pd.DataFrame(all_data)
        df.to_csv(output_file.replace('.json', '.csv'), index=False)
        
        print(f"Scraped {len(all_data)} HTSUS entries")
        return all_data

# Usage
if __name__ == "__main__":
    scraper = HTSUScraper()
    scraper.scrape_all()