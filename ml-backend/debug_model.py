
import joblib
import pandas as pd
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import warnings

warnings.filterwarnings("ignore")

def extract_features_debug(url):
    # print(f"Analyzing {url}...")
    features = {
        'url_length': len(url),
        'has_login_form': 0,
        'has_password_field': 0,
        'external_links_count': 0,
        'form_count': 0,
        'image_count': 0,
        'suspicious_keywords_html': 0,
        'suspicious_keywords_url': 0,
        'has_https': 1 if url.startswith('https://') else 0,
        'domain_length': 0,
        'path_length': 0,
        'query_length': 0,
        'is_ip_address': 0,
        'subdomain_count': 0,
        'has_many_subdomains': 0,
        'has_hyphen_in_domain': 0,
        'has_punycode': 0,
        'has_at_symbol': 0,
    }
    
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        features['domain_length'] = len(hostname)
        features['path_length'] = len(parsed.path)
        features['query_length'] = len(parsed.query)
        
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            features['is_ip_address'] = 1
        
        dot_count = hostname.count('.')
        features['subdomain_count'] = dot_count
        features['has_many_subdomains'] = 1 if dot_count >= 3 else 0
        features['has_hyphen_in_domain'] = 1 if '-' in hostname else 0
        features['has_punycode'] = 1 if 'xn--' in hostname.lower() else 0
        features['has_at_symbol'] = 1 if '@' in url else 0
        
        url_text = (hostname + parsed.path).lower()
        suspicious_words = ['login', 'verify', 'update', 'secure', 'account', 'password', 'confirm', 'suspended', 'locked', 'urgent']
        url_keyword_count = sum(1 for word in suspicious_words if word in url_text)
        features['suspicious_keywords_url'] = url_keyword_count
        
        # Light mock of getting webpage to avoid network in debug
        # We assume benign sites don't have login forms for this test unless specified
        features['form_count'] = 0
        features['has_login_form'] = 0
        features['has_password_field'] = 0
        
    except Exception as e:
        print(f"Error extracting features: {e}")
        
    return features

def check_urls():
    try:
        model = joblib.load('phishguard_model.pkl')
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    test_urls = [
        'https://www.etherscan.io',
        'https://www.neocities.org',
        'https://www.projecteuler.net',
        'http://info.cern.ch',
        'https://www.lichess.org',
        'https://www.example.com'
    ]

    with open('results.csv', 'w') as f:
        f.write("url,score,hyphen,dots\n")
        for url in test_urls:
            try:
                feats = extract_features_debug(url)
                df = pd.DataFrame([feats])
                ordered_keys = [
                    'url_length', 'has_login_form', 'has_password_field', 'external_links_count',
                    'form_count', 'image_count', 'suspicious_keywords_html', 'suspicious_keywords_url',
                    'has_https', 'domain_length', 'path_length', 'query_length',
                    'is_ip_address', 'subdomain_count', 'has_many_subdomains',
                    'has_hyphen_in_domain', 'has_punycode', 'has_at_symbol'
                ]
                df = df[ordered_keys]
                probs = model.predict_proba(df)[0]
                suspicious_prob = probs[1]
                f.write(f"{url},{suspicious_prob:.4f},{feats['has_hyphen_in_domain']},{feats['subdomain_count']}\n")
            except Exception as e:
                f.write(f"{url},ERROR,{e}\n")
    print("Results written to results.csv")

if __name__ == "__main__":
    check_urls()
