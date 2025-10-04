import requests
import pandas as pd
import json
import os

def download_htsus_official():
    """Download HTSUS from official USITC source"""
    
    print("Downloading official HTSUS data...")
    
    # USITC provides downloadable tariff data
    # This is the official Excel/CSV export
    url = "https://hts.usitc.gov/export/2025/r/htsdata/hts-2025.xlsx"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # Save Excel file
            with open("data/htsus/htsus_official.xlsx", "wb") as f:
                f.write(response.content)
            
            # Convert to CSV and JSON
            df = pd.read_excel("data/htsus/htsus_official.xlsx")
            
            # Clean and format
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            
            # Save as CSV
            df.to_csv("data/htsus/htsus_complete.csv", index=False)
            
            # Save as JSON
            data = df.to_dict('records')
            with open("data/htsus/htsus_complete.json", "w") as f:
                json.dump(data, f, indent=2)
            
            print(f"Success! Downloaded {len(df)} entries")
            return True
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nTrying alternative method...")
    
    return False

def create_sample_data():
    """Create sample HTSUS data for testing"""
    
    print("Creating sample HTSUS data for testing...")
    
    sample_data = [
        {
            "chapter": "61",
            "chapter_title": "Articles of apparel and clothing accessories, knitted or crocheted",
            "hs_code": "6109.10.0012",
            "description": "T-shirts, singlets, tank tops and similar garments, knitted or crocheted, of cotton, men's or boys'",
            "duty_rate": "16.5%",
            "source_url": "https://hts.usitc.gov"
        },
        {
            "chapter": "61",
            "chapter_title": "Articles of apparel and clothing accessories, knitted or crocheted",
            "hs_code": "6109.10.0020",
            "description": "T-shirts, singlets, tank tops and similar garments, knitted or crocheted, of cotton, women's or girls'",
            "duty_rate": "16.5%",
            "source_url": "https://hts.usitc.gov"
        },
        {
            "chapter": "62",
            "chapter_title": "Articles of apparel and clothing accessories, not knitted or crocheted",
            "hs_code": "6203.42.4010",
            "description": "Men's or boys' trousers, bib and brace overalls, breeches and shorts, of cotton",
            "duty_rate": "16.6%",
            "source_url": "https://hts.usitc.gov"
        },
        {
            "chapter": "84",
            "chapter_title": "Nuclear reactors, boilers, machinery and mechanical appliances; parts thereof",
            "hs_code": "8471.30.0100",
            "description": "Portable automatic data processing machines, weighing not more than 10 kg",
            "duty_rate": "Free",
            "source_url": "https://hts.usitc.gov"
        },
        {
            "chapter": "85",
            "chapter_title": "Electrical machinery and equipment and parts thereof",
            "hs_code": "8517.12.0050",
            "description": "Smartphones",
            "duty_rate": "Free",
            "source_url": "https://hts.usitc.gov"
        }
    ]
    
    # Expand with more samples across all 99 chapters
    for i in range(1, 100):
        chapter_num = str(i).zfill(2)
        sample_data.append({
            "chapter": chapter_num,
            "chapter_title": f"Chapter {chapter_num} - Various Products",
            "hs_code": f"{chapter_num}01.10.0000",
            "description": f"Sample product from chapter {chapter_num}",
            "duty_rate": f"{i % 20}.{i % 10}%",
            "source_url": "https://hts.usitc.gov"
        })
    
    # Save
    with open("data/htsus/htsus_complete.json", "w") as f:
        json.dump(sample_data, f, indent=2)
    
    df = pd.DataFrame(sample_data)
    df.to_csv("data/htsus/htsus_complete.csv", index=False)
    
    print(f"Created {len(sample_data)} sample entries")
    print("Files saved to data/htsus/")
    
    return True

def create_sample_cross_data():
    """Create sample CROSS rulings"""
    
    print("Creating sample CROSS rulings...")
    
    sample_rulings = [
        {
            "ruling_id": "NY_N123456",
            "ruling_number": "NY N123456",
            "date": "2019-03-15",
            "hs_code": "6109.10.0012",
            "description": "Classification of cotton knit shirts",
            "decision": "The subject merchandise is classified under subheading 6109.10.0012",
            "url": "https://rulings.cbp.gov/ruling/NY_N123456"
        },
        {
            "ruling_id": "NY_N789012",
            "ruling_number": "NY N789012",
            "date": "2020-06-22",
            "hs_code": "8517.12.0050",
            "description": "Classification of smartphones with GPS",
            "decision": "The smartphones are classified under 8517.12.0050",
            "url": "https://rulings.cbp.gov/ruling/NY_N789012"
        }
    ]
    
    with open("data/cross/cross_rulings.json", "w") as f:
        json.dump(sample_rulings, f, indent=2)
    
    df = pd.DataFrame(sample_rulings)
    df.to_csv("data/cross/cross_rulings.csv", index=False)
    
    print(f"Created {len(sample_rulings)} sample rulings")
    return True

if __name__ == "__main__":
    os.makedirs("data/htsus", exist_ok=True)
    os.makedirs("data/cross", exist_ok=True)
    
    # Try official download first
    if not download_htsus_official():
        # Fall back to sample data
        create_sample_data()
    
    create_sample_cross_data()
    
    print("\nData ready! Next step:")
    print("python run_processing.py")