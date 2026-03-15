"""
Step 2: Train ML Model
This script loads collected data, trains a Random Forest model, and saves it.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os

def load_training_data(csv_file='training_data.csv'):
    """
    Load the CSV file created by collect_data.py
    Returns features (X) and labels (y) as pandas DataFrames/Series
    """
    if not os.path.exists(csv_file):
        print(f"[ERROR] {csv_file} not found!")
        print("   Run 'python collect_data.py' first to collect training data.")
        return None, None, None
    
    # Read CSV with error handling for malformed rows
    try:
        df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python')
    except:
        df = pd.read_csv(csv_file, on_bad_lines='skip', engine='c')
    
    print(f"[SUCCESS] Loaded {len(df)} samples from {csv_file}")
    
    # Separate features from label
    # We'll exclude 'url' and 'label' from features
    feature_columns = [col for col in df.columns if col not in ['url', 'label']]
    X = df[feature_columns]
    y = df['label']
    
    print(f"[SUCCESS] Using {len(feature_columns)} features: {', '.join(feature_columns)}")
    print(f"[SUCCESS] Class distribution:")
    print(f"   - Safe (0): {sum(y == 0)} samples")
    print(f"   - Suspicious (1): {sum(y == 1)} samples")
    
    return X, y, feature_columns

def train_model(X, y):
    """
    Train a Random Forest classifier on the data
    """
    print("\n[INFO] Splitting data into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"   Training set: {len(X_train)} samples")
    print(f"   Test set: {len(X_test)} samples")
    
    print("\n[INFO] Training Random Forest classifier...")
    # Random Forest is good for this because:
    # - Handles mixed feature types well
    # - Not too sensitive to feature scaling
    # - Provides feature importance
    model = RandomForestClassifier(
        n_estimators=100,      # Number of trees
        max_depth=10,          # Limit tree depth to prevent overfitting
        min_samples_split=5,   # Minimum samples to split a node
        min_samples_leaf=2,    # Minimum samples in a leaf
        random_state=42,
        class_weight='balanced', # Crucial: handles label imbalance (372k vs 10k)
        n_jobs=-1              # Use all CPU cores
    )
    
    model.fit(X_train, y_train)
    print("[SUCCESS] Training complete!")
    
    # Evaluate on test set
    print("\n[INFO] Evaluating model...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n[SUCCESS] Model Accuracy: {accuracy:.2%}")
    print("\n[INFO] Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Safe', 'Suspicious']))
    
    print("\n[INFO] Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Show feature importance
    print("\n[INFO] Top 10 Most Important Features:")
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(feature_importance.head(10).to_string(index=False))
    
    return model, accuracy

def save_model(model, filename='phishguard_model.pkl'):
    """
    Save the trained model to a file
    """
    joblib.dump(model, filename)
    file_size = os.path.getsize(filename) / 1024  # Size in KB
    print(f"\n[SUCCESS] Model saved to '{filename}' ({file_size:.1f} KB)")

def main():
    """
    Main training pipeline
    """
    print("=" * 50)
    print("PhishGuard ML Model Training")
    print("=" * 50)
    
    # Step 1: Load data
    X, y, feature_columns = load_training_data()
    if X is None:
        return
    
    # Check if we have enough data
    if len(X) < 10:
        print(f"\n[WARNING] Only {len(X)} samples. Model may not be accurate.")
        print("   Collect more data with 'python collect_data.py' for better results.")
    
    # Step 2: Train model
    model, accuracy = train_model(X, y)
    
    # Step 3: Save model
    save_model(model)
    
    print("\n" + "=" * 50)
    print("[SUCCESS] Training Complete!")
    print("=" * 50)
    print("\nNext Steps:")
    print("   1. Review the accuracy score above")
    print("   2. If accuracy is good (>80%), proceed to create Flask API")
    print("   3. Run: python app.py (we'll create this next)")
    print("   4. Test predictions with real URLs")
    print("=" * 50)

if __name__ == '__main__':
    main()

