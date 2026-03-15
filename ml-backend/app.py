"""
Step 3: Flask API Server
This server accepts URLs from the Chrome extension and returns ML predictions.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pandas as pd
import re
from datetime import datetime
import json

app = Flask(__name__)
# Allow Chrome extension to make requests (extensions have chrome-extension:// origin)
CORS(app, resources={
    r"/predict": {"origins": "*", "methods": ["POST", "OPTIONS"]},
    r"/report": {"origins": "*", "methods": ["POST", "OPTIONS"]},
    r"/health": {"origins": "*", "methods": ["GET", "OPTIONS"]},
    r"/api/datasets": {"origins": "*", "methods": ["GET", "OPTIONS"]}
})

# Global variable to store the model
model = None
feature_columns = None

# Load model when app starts (for gunicorn/production)
def initialize_model():
    global model, feature_columns
    if load_model():
        print("[SUCCESS] Model loaded on startup")
    else:
        print("[WARNING] Model failed to load on startup - will retry on first request")

def extract_features_for_prediction(url):
    """
    Extract the same features we used during training.
    This must match extract_features() from collect_data.py exactly.
    """
    features = {
        'url_length': len(url),
        'has_login_form': 0,
        'has_password_field': 0,
        'external_links_count': 0,
        'form_count': 0,
        'image_count': 0,
        'suspicious_keywords_html': 0,  # Keywords in webpage HTML
        'suspicious_keywords_url': 0,   # Keywords in URL (hostname + path)
        'has_https': 1 if url.startswith('https://') else 0,
        'domain_length': 0,
        'path_length': 0,
        'query_length': 0,
        # URL heuristic features (matching classifier.js)
        'is_ip_address': 0,           # IP address instead of domain
        'subdomain_count': 0,         # Number of dots (subdomains)
        'has_many_subdomains': 0,     # >= 3 dots (4+ labels)
        'has_hyphen_in_domain': 0,    # Hyphen in hostname
        'has_punycode': 0,            # Punycode/IDN (xn--)
        'has_at_symbol': 0,           # @ symbol in URL
    }
    
    try:
        # Parse URL
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        features['domain_length'] = len(hostname)
        features['path_length'] = len(parsed.path)
        features['query_length'] = len(parsed.query)
        
        # URL heuristic features (before fetching webpage)
        # Check if IP address (IPv4)
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            features['is_ip_address'] = 1
        
        # Count subdomains (number of dots)
        dot_count = hostname.count('.')
        features['subdomain_count'] = dot_count
        features['has_many_subdomains'] = 1 if dot_count >= 3 else 0
        
        # Hyphen in domain
        features['has_hyphen_in_domain'] = 1 if '-' in hostname else 0
        
        # Punycode detection
        features['has_punycode'] = 1 if 'xn--' in hostname.lower() else 0
        
        # @ symbol in URL
        features['has_at_symbol'] = 1 if '@' in url else 0
        
        # Suspicious keywords in URL (hostname + pathname)
        url_text = (hostname + parsed.path).lower()
        suspicious_words = ['login', 'verify', 'update', 'secure', 'account', 
                          'password', 'confirm', 'suspended', 'locked', 'urgent']
        url_keyword_count = sum(1 for word in suspicious_words if word in url_text)
        features['suspicious_keywords_url'] = url_keyword_count
        
        # Fetch webpage (with timeout)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        html_content = response.text.lower()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for login forms
        forms = soup.find_all('form')
        features['form_count'] = len(forms)
        for form in forms:
            if 'login' in form.get('action', '').lower() or 'login' in form.get('id', '').lower():
                features['has_login_form'] = 1
        
        # Check for password fields
        password_inputs = soup.find_all('input', {'type': 'password'})
        features['has_password_field'] = 1 if len(password_inputs) > 0 else 0
        
        # Count images
        images = soup.find_all('img')
        features['image_count'] = len(images)
        
        # Count external links
        links = soup.find_all('a', href=True)
        domain = parsed.netloc
        external_count = 0
        for link in links:
            href = link.get('href', '')
            if href.startswith('http') and domain not in href:
                external_count += 1
        features['external_links_count'] = external_count
        
        # Check for suspicious keywords in HTML content
        suspicious_words = ['verify', 'update', 'secure', 'account', 'password', 
                          'login', 'confirm', 'suspended', 'locked', 'urgent']
        html_keyword_count = sum(1 for word in suspicious_words if word in html_content)
        features['suspicious_keywords_html'] = html_keyword_count
        
    except Exception as e:
        # If we can't fetch the page, use default values (0s)
        # This handles errors gracefully
        print(f"[WARNING] Could not extract features from {url}: {str(e)[:100]}")
    
    return features

def load_model():
    """
    Load the trained model from disk.
    """
    global model, feature_columns
    
    model_path = 'phishguard_model.pkl'
    
    if not os.path.exists(model_path):
        print(f"[ERROR] Model file '{model_path}' not found!")
        print("   Run 'python train_model.py' first to train the model.")
        return False
    
    try:
        model = joblib.load(model_path)
        
        # We need to know the feature order from training
        # Check if we have a training CSV to infer feature columns
        if os.path.exists('training_data.csv'):
            df = pd.read_csv('training_data.csv', nrows=1)
            feature_columns = [col for col in df.columns if col not in ['url', 'label']]
        else:
            # Default feature order (must match training)
            # This list is only used if training_data.csv doesn't exist
            # It should match the features in extract_features_for_prediction()
            feature_columns = [
                'url_length', 'has_login_form', 'has_password_field',
                'external_links_count', 'form_count', 'image_count',
                'suspicious_keywords_html', 'suspicious_keywords_url', 'has_https',
                'domain_length', 'path_length', 'query_length',
                'is_ip_address', 'subdomain_count', 'has_many_subdomains',
                'has_hyphen_in_domain', 'has_punycode', 'has_at_symbol'
            ]
        
        print(f"[SUCCESS] Model loaded from '{model_path}'")
        print(f"[SUCCESS] Using {len(feature_columns)} features")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return False

# Initialize model after function definition (for gunicorn/production)
initialize_model()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })

@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    """Serves the central safe and malicious datasets to the extension."""
    safe_domains = []
    malicious_domains = []
    
    try:
        if os.path.exists('safe_domains.json'):
            with open('safe_domains.json', 'r', encoding='utf-8') as f:
                safe_domains = json.load(f)
                
        if os.path.exists('malicious_domains.json'):
            with open('malicious_domains.json', 'r', encoding='utf-8') as f:
                malicious_domains = json.load(f)
                
    except Exception as e:
        print(f"[API] Error loading datasets: {e}")
        
    return jsonify({
        'safe_dataset': safe_domains,
        'malicious_dataset': malicious_domains
    })

@app.route('/predict', methods=['POST'])
def predict():
    """
    Main prediction endpoint.
    
    Expected JSON:
    {
        "url": "https://example.com"
    }
    
    Returns:
    {
        "suspicious": true/false,
        "probability": 0.0-1.0,
        "features": {...}
    }
    """
    print(f"\n[API] Received prediction request from {request.remote_addr}")
    
    if model is None:
        print("[API] ERROR: Model not loaded")
        return jsonify({
            'error': 'Model not loaded. Server may still be starting.'
        }), 503
    
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            print("[API] ERROR: Missing 'url' parameter")
            return jsonify({
                'error': 'Missing "url" parameter'
            }), 400
        
        url = data['url']
        print(f"[API] Predicting URL: {url}")
        
        # Extract features
        features = extract_features_for_prediction(url)
        
        # Convert to DataFrame with same column order as training
        feature_vector = pd.DataFrame([features], columns=feature_columns)
        
        # Make prediction
        prediction = model.predict(feature_vector)[0]
        probabilities = model.predict_proba(feature_vector)[0]
        
        # Get probability of being suspicious (class 1)
        suspicious_prob = probabilities[1] if len(probabilities) > 1 else probabilities[0]
        
        # Convert numpy types to native Python types for JSON serialization
        prediction_int = int(prediction)
        suspicious_prob_float = float(suspicious_prob)
        
        # Determine if suspicious (Strict threshold: 80% confidence)
        is_suspicious = suspicious_prob_float >= 0.8
        
        result = {
            'suspicious': bool(is_suspicious),  # Ensure Python bool, not numpy.bool_
            'probability': suspicious_prob_float,
            'prediction': prediction_int,
            'features': features,
            'url': url
        }
        
        print(f"[API] Result: suspicious={result['suspicious']}, probability={result['probability']:.3f}")
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Prediction failed: {e}")
        print(error_trace)
        return jsonify({
            'error': str(e),
            'traceback': error_trace if app.debug else None
        }), 500

@app.route('/report', methods=['POST'])
def report_site():
    """
    Report a suspicious/malicious site.
    Saves the report to reports.md file locally AND syncs to GitHub if configured.
    """
    print(f"\n[API] Received report request from {request.remote_addr}")
    
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" parameter'}), 400
        
        url = data.get('url', '')
        label = data.get('label', 'unknown')
        reasons = data.get('reasons', [])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Local Save (Standard)
        reports_file = os.path.join(os.path.dirname(__file__), 'reports.md')
        
        repo_update_status = "Skipped (No Token)"
        
        # Prepare content
        report_block = f"""
## {timestamp}

- **URL**: `{url}`
- **Classification**: `{label}`
- **Reasons**: {', '.join(reasons) if reasons else 'None provided'}
- **Timestamp**: {timestamp}

---
"""
        # Append locally
        with open(reports_file, 'a', encoding='utf-8') as f:
            f.write(report_block)
            
        # 2. GitHub Sync (New Feature)
        github_token = os.environ.get('GITHUB_TOKEN')
        repo_name = os.environ.get('GITHUB_REPO') # e.g. "G-man312/Phishguard-"
        
        if github_token and repo_name:
            try:
                from github import Github
                g = Github(github_token)
                repo = g.get_repo(repo_name)
                
                # Path to reports.md in the repo (adjust if inside a subdir)
                # Assumes reports.md is in ml-backend/reports.md based on repo structure
                file_path = "ml-backend/reports.md" 
                
                try:
                    contents = repo.get_contents(file_path)
                    existing_data = contents.decoded_content.decode("utf-8")
                    new_data = existing_data + report_block
                    repo.update_file(contents.path, f"Add report for {url}", new_data, contents.sha)
                    repo_update_status = "Success"
                    print(f"[GITHUB] Successfully updated {file_path}")
                except Exception as gh_e:
                    print(f"[GITHUB] Error updating file: {gh_e}")
                    repo_update_status = f"Failed: {str(gh_e)}"
                    
            except Exception as e:
                print(f"[GITHUB] Integration error: {e}")
                repo_update_status = f"Error: {str(e)}"
        
        return jsonify({
            'success': True,
            'message': 'Report processed',
            'github_sync': repo_update_status
        })
        
    except Exception as e:
        print(f"[ERROR] Report failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API info"""
    return jsonify({
        'name': 'PhishGuard ML API',
        'version': '1.0',
        'endpoints': {
            '/health': 'GET - Health check',
            '/predict': 'POST - Predict if URL is suspicious',
            '/report': 'POST - Report a suspicious/malicious site'
        },
        'model_loaded': model is not None
    })

if __name__ == '__main__':
    print("=" * 50)
    print("PhishGuard ML API Server")
    print("=" * 50)
    
    # Load model on startup
    if load_model():
        print("\n[INFO] Starting Flask server...")
        print("[INFO] API will be available at: http://localhost:5000")
        print("\nEndpoints:")
        print("  GET  /           - API info")
        print("  GET  /health     - Health check")
        print("  POST /predict    - Predict URL")
        print("  POST /report     - Report suspicious/malicious site")
        print("\n[INFO] Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Run the server
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("[ERROR] Failed to load model. Server will not start.")
        print("   Run 'python train_model.py' first to train the model.")

