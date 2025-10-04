# Test what's actually available
import sys
print("Python:", sys.version)

# Test google-cloud-aiplatform
try:
    import google.cloud.aiplatform as aiplatform
    print("✓ google.cloud.aiplatform imported")
    
    # Try to initialize
    aiplatform.init(project="test-project", location="us-central1")
    print("✓ aiplatform.init works")
    
    # Check for language models
    from google.cloud.aiplatform import language_models
    print("✓ language_models available")
    
    # Try text-bison
    model = language_models.TextGenerationModel.from_pretrained("text-bison")
    print("✓ text-bison model available")
    
except Exception as e:
    print(f"✗ Error: {e}")

# Test google-generativeai (if installed)
try:
    import google.generativeai as genai
    print("✓ google.generativeai available")
except ImportError:
    print("✗ google.generativeai not installed")
    print("  Install with: pip install google-generativeai")