import pandas as pd

print('Loading PhiUSIIL dataset...')
df = pd.read_csv('PhiUSIIL_Phishing_URL_Dataset.csv', usecols=['URL', 'label'])

# In PhiUSIIL: 1 = legitimate, 0 = phishing
# In PhishGuard: 0 = safe, 1 = suspicious (phishing)
print('Remapping labels...')
df['label'] = df['label'].map({1: 0, 0: 1})

# Rename URL column to url for collect_data.py
df.rename(columns={'URL': 'url'}, inplace=True)

print(df.head())
print(df['label'].value_counts())

print('Saving as phishing_urls.csv...')
df.to_csv('phishing_urls.csv', index=False)
print('Done! Ready for collect_data.py')
