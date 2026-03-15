# PhishGuard Testing Theory

## 5.3 Testing

### 5.3.1 Unit Testing

Unit testing involves verifying individual program components or functions in isolation from the rest of the system. For PhishGuard, this ensures that smaller sections of code work as intended, such as the URL feature extraction function (`extract_features_for_prediction()`), URL classification logic (`classifyQuick()`), or individual ML model prediction methods. Each function is tested independently with controlled inputs and expected outputs to detect early errors and ensure building blocks perform their specific tasks correctly before being combined into the larger system.

### 5.3.2 Integration Testing

Integration testing verifies that individual modules or components of the system work together cohesively. After unit tests, integration testing ensures that the Chrome extension's background script (`background.js`) interacts correctly with the Flask API server (`app.py`), and that the ML model can seamlessly receive feature vectors, process them, and return predictions. It also validates data flow between the extension popup (`popup.js`) and the background service worker, identifying interface issues, data mismatches, and communication failures between connected modules or external systems.

### 5.3.3 Blackbox Testing

Blackbox testing examines the overall system functionality without considering its internal code structure or implementation details. A tester provides input data (e.g., various URLs including safe, suspicious, and malicious sites) and evaluates if the system produces the expected outputs (e.g., correct icon color changes, accurate classification labels, appropriate ML probability scores). The focus is entirely on input-output behavior, ensuring the PhishGuard extension performs correctly from the user's perspective and meets the objective of reliably detecting phishing websites with high accuracy.

