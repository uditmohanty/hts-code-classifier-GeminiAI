import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.hs_code_agent import HSCodeAgent
import json

def main():
    print("Testing HS Code Classification Agent...\n")
    
    # Test product
    product_info = {
        'product_name': "Men's Cotton T-Shirt",
        'description': "Short sleeve, 100% cotton, knit fabric, crew neck",
        'material': "100% Cotton",
        'use': "Casual wear",
        'origin': "Bangladesh"
    }
    
    print("Product to classify:")
    print(json.dumps(product_info, indent=2))
    print("\nClassifying...\n")
    
    try:
        agent = HSCodeAgent()
        result = agent.classify_product(product_info)
        
        print("=" * 60)
        print("CLASSIFICATION RESULT")
        print("=" * 60)
        print(f"HS Code: {result.get('recommended_code')}")
        print(f"Duty Rate: {result.get('duty_rate')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"\nReasoning: {result.get('reasoning')}")
        print(f"\nAlternatives: {result.get('alternatives')}")
        
        if result.get('needs_review'):
            print("\nWARNING: Low confidence - needs review")
        
        print("\nTest successful!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()