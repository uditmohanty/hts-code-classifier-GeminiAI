#!/bin/bash

echo "Deploying HS Code Classifier..."

# Install dependencies
pip install -r requirements.txt

# Download and process data
echo "Setting up data..."
python quick_setup_data.py

# Process data and create embeddings
echo "Processing data and creating embeddings..."
python run_processing.py

# Setup vector database
echo "Initializing vector database..."
python run_vector_setup.py

# Start application
echo "Starting Streamlit app..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0