"""
Convert TALE-EP.py output JSONL format to structured JSON format.

This script transforms the raw model output into a standardized instruction-following format.
"""
import json
from typing import List, Dict, Any

# Path configurations
INPUT_FILE = "temp/gpt-4o-mini/afac/TALE.jsonl"
OUTPUT_FILE = "converted_output.json"


def convert_format(input_path: str, output_path: str) -> None:
    """
    Convert JSONL format to structured JSON format.
    
    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSON file
    """
    converted_data: List[Dict[str, Any]] = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            converted_item = {
                "instruction": "请你扮演一位金融和会计领域专家。"
                              "你会面临用户提出的一些问题，请你使用一句话进行解释，然后向用户提供答案。最后，答案要用 \boxed{A/B/C/D} 的形式输出。",
                "input": data["question"],
                "output": f"{data['reasoning']} \\boxed{{{data['ground truth']}}}"
            }
            converted_data.append(converted_item)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    convert_format(INPUT_FILE, OUTPUT_FILE)
    print(f"Conversion completed. Results saved to {OUTPUT_FILE}")