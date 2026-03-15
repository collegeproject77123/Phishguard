import json

with open("../classifier.js", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find("const SAFE_DATASET = [")
end = text.find("];", start)

js_array_str = text[start:end+2]

lines = js_array_str.split("\n")
domains = []

for line in lines[1:-1]:
    # Extract items between single quotes
    items = [x.strip("'") for x in line.split(",") if "'" in x]
    domains.extend(items)

domains.sort()

with open("../new_1000_safe_sites.txt", "w", encoding="utf-8") as f:
    for d in domains:
        f.write(f"{d}\n")

print(f"Successfully exported {len(domains)} domains")
