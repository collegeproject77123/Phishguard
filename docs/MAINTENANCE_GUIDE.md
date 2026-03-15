# PhishGuard Maintenance Guide

## How to Manual Update Site Lists
Currently, the "Database" of known Safe and Malicious sites is stored in **hardcoded arrays** within the extension files.

Because the extension runs in different contexts (Popup vs Background), these lists are currently **duplicated** in two files. You must update **BOTH** locations to ensure consistency.

### 1. Adding a Malicious Site (Blocklist)
Add the domain (e.g., `'example-phish.com'`) to the `MALICIOUS_DATASET` array in both:

1.  **`phish-guard/classifier.js`** (~Line 60)
    ```javascript
    const MALICIOUS_DATASET = [
      'purplehoodie.com',
      'apunkagames.net',
      'YOUR-NEW-SITE.COM', // <--- Add here
      ...
    ];
    ```

2.  **`phish-guard/background.js`** (Inside `classifyQuick` function, ~Line 622)
    *   *Note: This is an inline backup list.*
    ```javascript
    const inMaliciousDataset = (self._PG_MALICIOUS_DATASET || [..., 'apunkagames.net', 'YOUR-NEW-SITE.COM', ...]).some(...)
    ```

---

### 2. Adding a Safe Site (Whitelist)
Add the domain to the `SAFE_DATASET` array in both:

1.  **`phish-guard/background.js`** (~Line 74)
    ```javascript
    const SAFE_DATASET = [
      'google.com',
      'YOUR-SAFE-SITE.COM', // <--- Add here
      ...
    ];
    ```

2.  **`phish-guard/classifier.js`** (~Line 5)
    ```javascript
    const SAFE_DATASET = [
      'google.com',
      'YOUR-SAFE-SITE.COM', // <--- Add here
      ...
    ];
    ```

### 3. Updating the ML Model (Advanced)
If you want the AI to learn new patterns, you need to:
1.  Add the URL and label (`good` or `bad`) to `ml-backend/datasets/training_data.csv` (if it exists) or `URLDataset.csv`.
2.  Run `python train_model.py` to regenerate the `phishguard_model.pkl`.
3.  Redeploy the backend (Railway automatically handles this when you push).
