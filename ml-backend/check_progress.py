"""
Quick script to check data collection progress
"""
import os
import pandas as pd

def check_progress():
    print("=" * 60)
    print("PhishGuard Data Collection Progress")
    print("=" * 60)
    
    csv_file = 'training_data.csv'
    
    if not os.path.exists(csv_file):
        print("\n[INFO] training_data.csv not found yet.")
        print("       Data collection may still be starting...")
        return
    
    try:
        # Try reading with error handling for malformed CSV rows
        try:
            df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python')
        except:
            # Fallback: try with C engine and skip bad lines
            try:
                df = pd.read_csv(csv_file, on_bad_lines='skip', engine='c')
            except:
                # Last resort: read with quote handling
                df = pd.read_csv(csv_file, quoting=1, on_bad_lines='skip', engine='python')
        
        total_samples = len(df)
        
        # Count by label
        if 'label' in df.columns:
            safe_count = len(df[df['label'] == 0])
            suspicious_count = len(df[df['label'] == 1])
            
            print(f"\n[PROGRESS] Total samples collected: {total_samples}")
            print(f"   - Safe/Legitimate (0): {safe_count}")
            print(f"   - Suspicious/Phishing (1): {suspicious_count}")
            
            # Estimate progress
            expected_total = 235795  # Total URLs in PhiUSIIL dataset
            progress_pct = min((total_samples / expected_total) * 100, 100)
            print(f"\n[ESTIMATE] Progress: ~{progress_pct:.2f}% complete")
            print(f"           ({total_samples} / ~{expected_total} expected)")
            
            # Check file modification time
            import datetime
            mod_time = os.path.getmtime(csv_file)
            mod_datetime = datetime.datetime.fromtimestamp(mod_time)
            time_diff = datetime.datetime.now() - mod_datetime
            
            if time_diff.total_seconds() < 60:
                print(f"\n[STATUS] File updated {time_diff.total_seconds():.0f} seconds ago - STILL RUNNING")
            else:
                minutes = time_diff.total_seconds() / 60
                print(f"\n[STATUS] File last updated {minutes:.1f} minutes ago")
                if minutes > 5:
                    print("         Collection may have finished or stalled")
        else:
            print(f"\n[PROGRESS] {total_samples} samples collected")
            print("           (Label column not found - cannot categorize)")
            
    except Exception as e:
        print(f"\n[ERROR] Could not read progress: {e}")

if __name__ == '__main__':
    check_progress()
    print("\n" + "=" * 60)
    print("Run this script again to see updated progress")
    print("=" * 60)


