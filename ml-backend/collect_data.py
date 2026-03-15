"""
Step 1: Data Collection Script
This script collects features from URLs and saves them for training.
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from urllib.parse import urlparse
import json
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import multiprocessing

def extract_features(url, label):
    """
    Extract features from a webpage URL.
    Returns a dictionary of features + label.
    """
    features = {
        'url': url,
        'label': label,  # 1 for suspicious, 0 for safe
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
        
        # Fetch webpage (with timeout and size limit)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=(3.0, 3.0), stream=True, allow_redirects=True)
            html_raw = b""
            for chunk in response.iter_content(chunk_size=10240):
                html_raw += chunk
                if len(html_raw) > 100000:
                    break
            html_content = html_raw.decode('utf-8', errors='ignore').lower()
        except:
            html_content = ""
            
        # Parse HTML safely
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
        else:
            soup = BeautifulSoup("", 'html.parser')
        
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
        pass
        # Keep default values (0s)
    
    return features

def load_dataset_from_csv(csv_file, url_column='url', label_column='label', label_value=1):
    """
    Load URLs from a CSV file (from PhishTank, UCI, Kaggle, etc.)
    Handles datasets with both labeled and unlabeled URLs.
    
    Args:
        csv_file: Path to CSV file
        url_column: Name of column containing URLs (will try common variations)
        label_column: Name of column containing labels (or None if all same label)
        label_value: Label to assign if no label column found (0 for safe, 1 for suspicious)
    
    Returns:
        tuple: (legitimate_urls, suspicious_urls) - both lists of URLs
    """
    legitimate_urls = []
    suspicious_urls = []
    
    try:
        df = pd.read_csv(csv_file)
        
        # Try to find URL column (case-insensitive, common variations)
        possible_url_columns = ['url', 'URL', 'urls', 'URLs', 'website', 'Website', 
                               'domain', 'Domain', 'link', 'Link', 'address', 'Address']
        
        found_url_column = None
        if url_column in df.columns:
            found_url_column = url_column
        else:
            # Try case-insensitive match
            for col in df.columns:
                if col.lower() == url_column.lower():
                    found_url_column = col
                    break
            
            # Try common variations
            if not found_url_column:
                for possible in possible_url_columns:
                    if possible in df.columns:
                        found_url_column = possible
                        print(f"[INFO] Using column '{found_url_column}' for URLs")
                        break
        
        if not found_url_column:
            print(f"[ERROR] Could not find URL column in CSV.")
            print(f"   Looking for: '{url_column}' or common variations")
            print(f"   Available columns: {list(df.columns)}")
            print(f"   Tip: Rename your URL column to 'url' or edit collect_data.py")
            return legitimate_urls, suspicious_urls
        
        # Try to find label column
        found_label_column = None
        possible_label_columns = ['label', 'Label', 'labels', 'Labels', 'type', 'Type',
                                 'class', 'Class', 'category', 'Category', 'status', 'Status',
                                 'phishing', 'Phishing', 'is_phishing', 'is_phish', 'result']
        
        if label_column and label_column in df.columns:
            found_label_column = label_column
        else:
            # Try case-insensitive match
            for col in df.columns:
                if col.lower() in [l.lower() for l in possible_label_columns]:
                    found_label_column = col
                    print(f"[INFO] Using column '{found_label_column}' for labels")
                    break
        
        # Filter valid URLs
        valid_data = []
        for idx, row in df.iterrows():
            url = row[found_url_column]
            if pd.isna(url):
                continue
            
            url_str = str(url).strip()
            if not url_str or not (url_str.startswith('http://') or url_str.startswith('https://')):
                continue
            
            # Determine label
            if found_label_column and found_label_column in row.index:
                label_val = row[found_label_column]
                # Handle various label formats
                if pd.isna(label_val):
                    continue
                
                label_str = str(label_val).lower().strip()
                # Map common label values: 0/1, legitimate/phishing, benign/malicious, etc.
                if label_str in ['0', 'legitimate', 'benign', 'safe', 'good', 'false']:
                    label = 0
                elif label_str in ['1', 'phishing', 'malicious', 'suspicious', 'true', 'bad']:
                    label = 1
                else:
                    # Try numeric conversion
                    try:
                        label_num = int(float(label_str))
                        label = 0 if label_num == 0 else 1
                    except:
                        continue
            else:
                # No label column, use default
                label = label_value
            
            valid_data.append((url_str, label))
        
        # Separate by label
        for url, label in valid_data:
            if label == 0:
                legitimate_urls.append(url)
            else:
                suspicious_urls.append(url)
        
        print(f"[SUCCESS] Loaded {len(valid_data)} valid URLs from {csv_file}")
        print(f"   - Legitimate (0): {len(legitimate_urls)} URLs")
        print(f"   - Suspicious/Phishing (1): {len(suspicious_urls)} URLs")
        
    except Exception as e:
        print(f"[ERROR] Could not load {csv_file}: {e}")
        import traceback
        traceback.print_exc()
    
    return legitimate_urls, suspicious_urls

def collect_sample_data(use_datasets=False):
    """
    Collect data from a mix of legitimate and suspicious URLs.
    
    Args:
        use_datasets: If True, try to load from downloaded dataset files
    """
    
    # Sample legitimate sites (label = 0)
    legitimate_urls = [
        'https://www.google.com',
        'https://www.youtube.com',
        'https://www.wikipedia.org',
        'https://www.github.com',
        'https://www.linkedin.com',
        'https://www.reddit.com',
        'https://www.amazon.com',
        'https://www.netflix.com',
        'https://www.instagram.com',
        'https://www.facebook.com',
    ]
    
    # Sample suspicious/phishing URLs (label = 1)
    # Add real phishing URLs from PhishTank or other sources
    suspicious_urls = [
        'http://phishy-demo.test',
        'http://fraud-demo.test',
        'http://secure-verify.test',
        # Add more from PhishTank CSV or other sources
    ]
    
    all_data = []
    
    # Process hardcoded legitimate sites first (skip if using dataset)
    if not use_datasets or len(legitimate_urls) < 100:
        print("Collecting data from legitimate sites...")
        for url in legitimate_urls:
            print(f"Processing: {url}")
            features = extract_features(url, 0)  # 0 = safe/legitimate
            all_data.append(features)
            time.sleep(1)  # Be polite to servers
    
    print("\nCollecting data from suspicious sites...")
    
    suspicious_urls = []
    
    # Try to load from downloaded datasets
    if use_datasets:
        dataset_files = [
            'URLdataset.csv',     # Mendeley dataset with 450K+ URLs
            'URL dataset.csv',    # Alternative name
            'phishing_urls.csv',  # Put your downloaded phishing CSV here
            'phishTank_data.csv',
            'uci_phishing.csv',
        ]
        
        for dataset_file in dataset_files:
            if os.path.exists(dataset_file):
                legit_urls, phish_urls = load_dataset_from_csv(dataset_file, url_column='url', label_value=1)
                import sys
                use_all = '--use-all' in sys.argv
                
                # Check for --limit flag (e.g., --limit 50000 for 50K each)
                limit_each = None
                for arg in sys.argv:
                    if arg.startswith('--limit='):
                        try:
                            limit_each = int(arg.split('=')[1])
                            break
                        except:
                            pass
                
                if use_all:
                    legitimate_urls.extend(legit_urls)
                    suspicious_urls.extend(phish_urls)
                    print(f"[INFO] Using ALL URLs from dataset: {len(legit_urls)} legitimate, {len(phish_urls)} phishing")
                elif limit_each:
                    # Use specified limit for balanced training (e.g., 50K each = 100K total)
                    limit_legit = min(limit_each, len(legit_urls))
                    limit_phish = min(limit_each, len(phish_urls))
                    legitimate_urls.extend(legit_urls[:limit_legit])
                    suspicious_urls.extend(phish_urls[:limit_phish])
                    print(f"[INFO] Using {limit_legit} legitimate and {limit_phish} phishing URLs from dataset ({limit_legit + limit_phish} total)")
                    print(f"[INFO] 50/50 balanced split: {limit_legit} legitimate + {limit_phish} phishing")
                else:
                    # Default: 500 each for quick testing (1000 total)
                    legitimate_urls.extend(legit_urls[:500])
                    suspicious_urls.extend(phish_urls[:500])
                    print(f"[INFO] Added 500 legitimate and 500 phishing URLs from dataset (1000 total - quick test)")
                    print(f"[INFO] Options:")
                    print(f"   - For 50K/50K (100K total): python collect_data.py --use-datasets --limit=50000")
                    print(f"   - For all URLs: python collect_data.py --use-datasets --use-all")
                break
    
    # If no datasets found, use synthetic examples
    if not suspicious_urls:
        print("Note: No dataset files found. Using synthetic examples.")
        print("To use real datasets:")
        print("  1. Download phishing URLs CSV from: https://archive.ics.uci.edu/dataset/327/phishing")
        print("  2. Save it as 'phishing_urls.csv' in ml-backend folder")
        print("  3. Run this script again")
        
        synthetic_suspicious = [
            'https://example.com',
        ]
        
        for url in synthetic_suspicious:
            suspicious_urls.append(url)
        
        # Generate synthetic patterns
        print("Generating synthetic suspicious patterns...")
        for i in range(3):
            synthetic_url = f'http://suspicious-site-{i}.example.com/login/verify'
            parsed = urlparse(synthetic_url)
            hostname = parsed.netloc.lower()
            dot_count = hostname.count('.')
            
            synthetic = {
                'url': synthetic_url,
                'label': 1,
                'url_length': len(synthetic_url),
                'has_login_form': 1,
                'has_password_field': 1,
                'external_links_count': 0,
                'form_count': 2,
                'image_count': 1,
                'suspicious_keywords_html': 5 + i,
                'suspicious_keywords_url': 2,  # "login" and "verify" in URL
                'has_https': 0,
                'domain_length': len(hostname),
                'path_length': len(parsed.path),
                'query_length': 0,
                'is_ip_address': 0,
                'subdomain_count': dot_count,
                'has_many_subdomains': 1 if dot_count >= 3 else 0,
                'has_hyphen_in_domain': 1,  # "suspicious-site" has hyphen
                'has_punycode': 0,
                'has_at_symbol': 0,
            }
            all_data.append(synthetic)
            print(f"  Added synthetic suspicious sample {i+1}")
    
    # Check existing training_data.csv and skip already processed URLs
    existing_urls = set()
    csv_filename = 'training_data.csv'
    if os.path.exists(csv_filename):
        try:
            df_existing = pd.read_csv(csv_filename, on_bad_lines='skip', engine='python', usecols=['url'])
            existing_urls = set(df_existing['url'].tolist())
            print(f"\n[INFO] Found existing training_data.csv with {len(existing_urls)} URLs")
            print(f"[INFO] Will skip these URLs and only process new ones")
        except Exception as e:
            print(f"\n[WARNING] Could not read existing CSV: {e}")
    
    # Filter out URLs that are already in the CSV
    if existing_urls:
        legitimate_urls = [url for url in legitimate_urls if url not in existing_urls]
        suspicious_urls = [url for url in suspicious_urls if url not in existing_urls]
        print(f"[INFO] After filtering duplicates: {len(legitimate_urls)} legitimate, {len(suspicious_urls)} phishing URLs to process")
    
    # Process URLs in parallel for faster collection
    # Use ALL CPU cores for maximum speed
    cpu_count = multiprocessing.cpu_count()
    max_workers = min(cpu_count * 4, 32)  # Use 4x CPU cores, max 32 workers
    
    # Track incremental saves
    incremental_save_counter = {'count': 0}
    incremental_save_lock = Lock()
    
    def save_incrementally(new_data, all_data_list, csv_filename='training_data.csv', batch_size=100):
        """Save data incrementally so we can see progress"""
        with incremental_save_lock:
            incremental_save_counter['count'] += len(new_data)
            if incremental_save_counter['count'] >= batch_size:
                # Append to CSV file
                for attempt in range(5):
                    try:
                        df_new = pd.DataFrame(new_data)
                        file_exists = os.path.exists(csv_filename)
                        df_new.to_csv(csv_filename, mode='a', header=not file_exists, index=False)
                        incremental_save_counter['count'] = 0
                        break
                    except Exception as e:
                        if attempt == 4:
                            print(f"[WARNING] Failed to save incrementally: {e}")
                        else:
                            time.sleep(1.0)
                        # Continue processing - don't stop on save errors
    
    def process_urls_parallel(urls, label, workers=max_workers):
        """
        Process URLs in parallel using ThreadPoolExecutor.
        Uses multiple CPU cores to fetch URLs concurrently.
        """
        all_results = []
        lock = Lock()
        completed = 0
        
        # Load existing URLs to skip processing
        existing_urls = set()
        if os.path.exists('training_data.csv'):
            try:
                df_existing = pd.read_csv('training_data.csv', usecols=['url'], on_bad_lines='skip', engine='python')
                existing_urls = set(df_existing['url'].dropna().tolist())
                print(f"[SKIP] Found {len(existing_urls)} URLs already processed in training_data.csv")
            except Exception as e:
                print(f"[WARNING] Could not read existing URLs for skipping: {e}")
                
        # Filter urls
        original_count = len(urls)
        urls = [u for u in urls if u not in existing_urls]
        print(f"[INFO] Skipping {original_count - len(urls)} URLs. {len(urls)} remaining to fetch.")
        
        total = len(urls)
        if total == 0:
            return []
            
        batch_results = []  # For incremental saving
        start_time = time.time()
        
        def process_single_url(url):
            nonlocal completed, batch_results
            try:
                features = extract_features(url, label)
                
                features_to_save = None
                with lock:
                    completed += 1
                    batch_results.append(features)
                    
                    # Save incrementally every 100 URLs
                    if len(batch_results) >= 100:
                        features_to_save = list(batch_results)
                        batch_results.clear()
                    
                    if completed % 50 == 0 or completed == total:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0.01
                        remaining_secs = (total - completed) / rate
                        eta_mins = int(remaining_secs // 60)
                        eta_hrs = int(eta_mins // 60)
                        eta_mins = eta_mins % 60
                        print(f"Progress: {completed}/{total} URLs ({completed*100//total}%) | Speed: {rate:.1f} URLs/sec | ETA: {eta_hrs}h {eta_mins}m")
                        
                if features_to_save:
                    save_incrementally(features_to_save, all_results, batch_size=0)
                    
                return features
            except Exception as e:
                with lock:
                    completed += 1
                return None
        
        print(f"Processing {total} URLs in parallel (using {workers} workers)...")
        print("Using maximum CPU power for fastest processing!")
        print("Progress will be saved incrementally to training_data.csv")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_single_url, url): url for url in urls}
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_results.append(result)
        
        # Save any remaining batch
        if batch_results:
            save_incrementally(batch_results, all_results, batch_size=1)
        
        return all_results
    
    # Process legitimate URLs from dataset
    if legitimate_urls:
        print(f"\nProcessing {len(legitimate_urls)} legitimate URLs from dataset...")
        print(f"Using {max_workers} parallel workers for maximum speed!")
        results = process_urls_parallel(legitimate_urls, 0, workers=max_workers)
        all_data.extend(results)
    
    # Process suspicious URLs from dataset
    if suspicious_urls:
        print(f"\nProcessing {len(suspicious_urls)} suspicious/phishing URLs from dataset...")
        print(f"Using {max_workers} parallel workers for maximum speed!")
        results = process_urls_parallel(suspicious_urls, 1, workers=max_workers)
        all_data.extend(results)
    
    # Save to CSV (append mode if file exists for incremental saves)
    if all_data:
        csv_filename = 'training_data.csv'
        fieldnames = list(all_data[0].keys())
        
        # Always append to existing file if it exists (never overwrite)
        file_exists = os.path.exists(csv_filename)
        
        # Use pandas to save with proper CSV escaping (handles commas/special chars in URLs)
        valid_data = [row for row in all_data if row is not None]
        if valid_data:
            df_final = pd.DataFrame(valid_data)
            
            if file_exists:
                # Append mode: read existing and combine
                try:
                    df_existing = pd.read_csv(csv_filename, on_bad_lines='skip', engine='python')
                    df_final = pd.concat([df_existing, df_final], ignore_index=True)
                    print(f"[INFO] Appending to existing file ({len(df_existing)} existing + {len(valid_data)} new = {len(df_final)} total)")
                except Exception as e:
                    print(f"[WARNING] Could not read existing CSV, creating new: {e}")
            
            # Save with proper quoting to handle commas/special characters in URLs
            # Default quoting (QUOTE_MINIMAL) automatically escapes commas in URLs
            df_final.to_csv(csv_filename, index=False)
        
        print(f"\n[SUCCESS] Collected {len(all_data)} samples")
        print(f"[SUCCESS] Saved to {csv_filename}")
        return csv_filename
    
    return None

if __name__ == '__main__':
    print("=== PhishGuard ML Data Collection ===")
    print("\nOptions:")
    print("  1. Use downloaded datasets (if available): python collect_data.py --use-datasets")
    print("  2. Use sample data (default)")
    
    import sys
    use_datasets = '--use-datasets' in sys.argv
    
    csv_file = collect_sample_data(use_datasets=use_datasets)
    print(f"\nNext step: Train model with: python train_model.py")


