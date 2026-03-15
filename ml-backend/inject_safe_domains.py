import urllib.request
import zipfile
import io
import os
import re

print('Downloading top domains...')
url = 'http://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip'
response = urllib.request.urlopen(url)
with zipfile.ZipFile(io.BytesIO(response.read())) as z:
    with z.open(z.namelist()[0]) as f:
        lines = f.readlines()

top_domains = [line.decode('utf-8').strip().split(',')[1] for line in lines[:890]]

indian_gov_edu = [
    'india.gov.in', 'uidai.gov.in', 'incometaxindia.gov.in', 'mca.gov.in', 
    'gst.gov.in', 'epfindia.gov.in', 'passportindia.gov.in', 'rbi.org.in',
    'irctc.co.in', 'indianrailways.gov.in', 'nvsp.in', 'cowin.gov.in',
    'mygov.in', 'digitalindia.gov.in', 'parivahan.gov.in', 'echs.gov.in',
    'joinindianarmy.nic.in', 'indianairforce.nic.in', 'joinindiannavy.gov.in',
    'ugc.ac.in', 'aicte-india.org', 'nta.ac.in', 'cbse.gov.in', 'ncert.nic.in',
    'mu.ac.in', 'du.ac.in', 'jnu.ac.in', 'bhu.ac.in', 'amu.ac.in', 'ignou.ac.in',
    'annauniv.edu', 'vtu.ac.in', 'sppu.ac.in', 'caluniv.ac.in', 'osmania.ac.in',
    'iitb.ac.in', 'iitd.ac.in', 'iitm.ac.in', 'iitk.ac.in', 'iitkgp.ac.in',
    'nic.in', 'gov.in', 'ac.in', 'edu.in', 'res.in', 'mahait.org', 'maharashtra.gov.in',
    'kerala.gov.in', 'tn.gov.in', 'up.gov.in', 'ap.gov.in', 'gui.gov.in',
    'karnataka.gov.in', 'rajasthan.gov.in', 'wb.gov.in', 'punjab.gov.in',
    'haryana.gov.in', 'bihar.gov.in', 'assam.gov.in', 'odisha.gov.in', 'mponline.gov.in',
    'ssc.nic.in', 'upsc.gov.in', 'ibps.in', 'rrbcdg.gov.in', 'drdo.gov.in',
    'isro.gov.in', 'barc.gov.in', 'bhel.com', 'ntpc.co.in', 'ongcindia.com',
    'gailonline.com', 'iocl.com', 'bpcl.in', 'hpcl.co.in', 'powergrid.in',
    'sbi.co.in', 'pnbindia.in', 'bankofbaroda.in', 'canarabank.com', 'unionbankofindia.co.in',
    'licindia.in', 'nabard.org', 'sidbi.in', 'bseindia.com', 'nseindia.com',
    'sebi.gov.in', 'irdaionline.org', 'pfrda.org.in', 'fssai.gov.in', 'bis.gov.in',
    'trai.gov.in', 'cpcb.nic.in', 'ndma.gov.in', 'niti.gov.in', 'pmindia.gov.in',
    'presidentofindia.nic.in', 'vicepresidentofindia.nic.in', 'loksabha.nic.in',
    'rajyasabha.nic.in', 'supremecourtofindia.nic.in', 'sci.gov.in', 'highcourt.cg.gov.in',
    'bombayhighcourt.nic.in', 'delhihighcourt.nic.in', 'keralahighcourt.nic.in',
    'madras.nic.in', 'tnhighcourt.nic.in', 'mphc.gov.in', 'cghighcourt.nic.in',
    'patnahighcourt.gov.in', 'allahabadhighcourt.in', 'hcraj.nic.in', 'gujarathighcourt.nic.in',
    'kar.nic.in', 'hck.gov.in', 'kdhc.nic.in', 'wbhealth.gov.in', 'nrhm.gov.in',
    'mohfw.gov.in', 'ayush.gov.in', 'education.gov.in', 'mha.gov.in', 'mea.gov.in',
    'mof.gov.in', 'mod.gov.in', 'wcd.nic.in', 'tribal.nic.in', 'minorityaffairs.gov.in',
    'socialjustice.gov.in', 'labour.gov.in', 'dgt.gov.in', 'skilldevelopment.gov.in',
    'msme.gov.in', 'commerce.gov.in', 'dpiit.gov.in', 'dgft.gov.in', 'mca.gov.in',
    'nclt.gov.in', 'nclat.nic.in', 'cci.gov.in', 'ibbi.gov.in', 'nfsa.gov.in',
    'fcamin.nic.in', 'rural.nic.in', 'mord.gov.in', 'panchayat.gov.in', 'drinkingwater.nic.in',
    'swachhbharatmission.gov.in', 'moud.gov.in', 'mohousingandurbanaffairs.gov.in',
    'smartcities.gov.in', 'amrut.gov.in', 'hridayindia.in', 'nhai.gov.in',
    'morth.nic.in', 'civilaviation.gov.in', 'dgca.gov.in', 'aai.aero',
    'shipping.nic.in', 'railways.gov.in', 'coal.nic.in', 'mines.gov.in',
    'steel.gov.in', 'petroleum.nic.in', 'power.gov.in', 'mnre.gov.in',
    'dae.gov.in', 'dos.gov.in', 'dst.gov.in', 'dbtindia.gov.in', 'dsir.gov.in',
    'moes.gov.in', 'moef.gov.in', 'cpcb.nic.in', 'nctc.gov.in', 'ncrpb.nic.in'
]

combined = list(set(top_domains + indian_gov_edu))
combined.sort()

# Generate the JS array text
js_lines = ["const SAFE_DATASET = ["]
chunk_size = 5
for i in range(0, len(combined), chunk_size):
    chunk = combined[i:i+chunk_size]
    line = "  " + ", ".join([f"'{d}'" for d in chunk])
    if i + chunk_size < len(combined):
        line += ","
    js_lines.append(line)
js_lines.append("];")

js_array_text = "\n".join(js_lines)

# Inject into classifier.js
with open('../classifier.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace const SAFE_DATASET = [ ... ];
text = re.sub(r'const SAFE_DATASET = \[\s*.*?\s*\];', js_array_text, text, flags=re.DOTALL)

with open('../classifier.js', 'w', encoding='utf-8') as f:
    f.write(text)

# Inject into background.js
with open('../background.js', 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = re.sub(r'const SAFE_DATASET = \[\s*.*?\s*\];', js_array_text, text2, flags=re.DOTALL)

with open('../background.js', 'w', encoding='utf-8') as f:
    f.write(text2)

print(f"Successfully injected {len(combined)} domains into classifier.js and background.js!")
