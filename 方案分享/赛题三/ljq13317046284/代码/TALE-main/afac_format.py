import json

# Read the original JSON file
with open('./data/afac/afac.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Convert to JSONL format and write to a new file
with open('data/afac/afac.jsonl', 'w', encoding='utf-8') as f:
    for item in data:
        # Create a new dictionary structure
        new_item = {
            "question": item["input"],
            "answer": item["output"]
        }
        # Write one JSON line
        f.write(json.dumps(new_item, ensure_ascii=False) + '\n')

print("Conversion completed. Results saved to output.jsonl")