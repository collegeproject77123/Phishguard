import os
import time
import pandas as pd
import sys

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def track_progress():
    csv_file = 'training_data.csv'
    total_phiusiil = 235795
    base_urls = 0  # To ignore previous datasets
    
    # Try to find the baseline of URLs before this session started
    try:
        df = pd.read_csv('phishing_urls.csv', usecols=['url'])
        phiusiil_urls = set(df['url'].tolist())
    except:
        phiusiil_urls = set()
        
    print("Initializing PhishGuard Training Tracker...")
    
    last_count = 0
    last_time = time.time()
    
    while True:
        try:
            if not os.path.exists(csv_file):
                print("Waiting for training_data.csv to be created...")
                time.sleep(2)
                continue
                
            # Read robustly, skipping lines being actively written
            try:
                df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python', usecols=['url', 'label'])
            except:
                time.sleep(0.5)
                continue
                
            current_total = len(df)
            
            # Total lines minus whatever we started the day with
            current_phiusiil_count = max(0, current_total - 31885)
            
            # Simple estimations since strict matching fails on formatted URLs
            safe_count = "N/A"
            phish_count = "N/A"

            current_time = time.time()
            
            # Calculate Speed and ETA
            if last_count == 0:
                last_count = current_phiusiil_count
                
            elapsed = current_time - last_time
            new_urls = current_phiusiil_count - last_count
            
            if elapsed >= 3.0: # Update speed every 3 seconds for stability
                speed = new_urls / elapsed if elapsed > 0 else 0
                
                # Smooth out wild speed fluctuations
                if speed > 200 or speed < 0: 
                    speed = 20.0
                    
                remaining_urls = total_phiusiil - current_phiusiil_count
                remaining_secs = remaining_urls / speed if speed > 0 else 999999
                
                eta_hrs = int(remaining_secs // 3600)
                eta_mins = int((remaining_secs % 3600) // 60)
                
                pct = min(100.0, (current_phiusiil_count / total_phiusiil) * 100)
                
                clear_console()
                print("="*50)
                print("  PHISHGUARD DATA COLLECTION DASHBOARD  ")
                print("="*50)
                print(f"Dataset: PhiUSIIL (235,795 Total URLs)\n")
                
                print(f"▶ Processed Today: {current_phiusiil_count:,} / {total_phiusiil:,}")
                print(f"▶ Progress:        [{'#' * int(pct // 5)}{'-' * (20 - int(pct // 5))}] {pct:.2f}%")
                
                if safe_count != "N/A":
                    print(f"\nDistribution:")
                    print(f"  - Safe Sites:      {safe_count:,}")
                    print(f"  - Phishing Sites:  {phish_count:,}")
                
                print(f"\nPerformance:")
                print(f"  - Current Speed:   {speed:.1f} websites/sec")
                print(f"  - Estimated ETA:   {eta_hrs}h {eta_mins}m remaining")
                print("="*50)
                print("Press Ctrl+C to exit dashboard. Training continues in background.")
                
                last_count = current_phiusiil_count
                last_time = current_time
                
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\nExiting tracker...")
            sys.exit(0)
        except Exception as e:
            # Silently ignore read errors caused by concurrent writing
            time.sleep(0.5)

if __name__ == '__main__':
    track_progress()
