# Test the classifier directly
from src.agents.gcp_gemini_classifier import GCPGeminiClassifier

# Initialize classifier
print("Initializing classifier...")
classifier = GCPGeminiClassifier()

# Test product
test_product = {
    'product_name': 'Cotton T-Shirt',
    'description': 'Men\'s cotton t-shirt with crew neck, short sleeves',
    'material': '100% Cotton',
    'use': 'Casual wear',
    'origin': 'Bangladesh'
}

print("\nClassifying product...")
result = classifier.classify_product(test_product, [], [])

print("\nClassification Result:")
print(f"HS Code: {result.get('recommended_code')}")
print(f"Confidence: {result.get('confidence')}")
print(f"Duty Rate: {result.get('duty_rate')}")
print(f"Status: {result.get('status')}")
print(f"Reasoning: {result.get('reasoning')}")