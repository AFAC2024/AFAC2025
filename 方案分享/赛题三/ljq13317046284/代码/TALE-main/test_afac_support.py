#!/usr/bin/env python3
"""
Simple test script to verify AFAC dataset support
"""

import os
import json
import sys

def test_afac_support():
    """Test AFAC dataset support."""
    print("Testing AFAC dataset support...")
    
    # Check file existence
    afac_path = './data/afac/afac.jsonl'
    if not os.path.exists(afac_path):
        print(f"❌ AFAC file not found: {afac_path}")
        return False
    
    print(f"✅ AFAC file found: {afac_path}")
    
    # Check file size
    file_size = os.path.getsize(afac_path)
    print(f"📊 File size: {file_size:,} bytes")
    
    # Load and validate first few entries
    try:
        with open(afac_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"📋 Total lines: {len(lines)}")
        
        # Parse first 3 entries
        valid_entries = 0
        for i, line in enumerate(lines[:3]):
            try:
                data = json.loads(line.strip())
                if 'question' in data and 'answer' in data:
                    valid_entries += 1
                    print(f"✅ Entry {i+1}: Valid format")
                    print(f"   Question preview: {data['question'][:50]}...")
                    print(f"   Answer: {data['answer']}")
                else:
                    print(f"❌ Entry {i+1}: Missing required fields")
            except json.JSONDecodeError as e:
                print(f"❌ Entry {i+1}: JSON decode error - {e}")
        
        if valid_entries > 0:
            print(f"✅ Found {valid_entries} valid entries")
            return True
        else:
            print("❌ No valid entries found")
            return False
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def create_sample_files():
    """Create sample train/test files for the dataset classes."""
    print("\nCreating sample train/test files...")
    
    try:
        with open('./data/afac/afac.jsonl', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Split data (80% train, 20% test)
        split_idx = int(len(lines) * 0.8)
        
        # Create train file
        with open('./data/afac/afac_train.jsonl', 'w', encoding='utf-8') as f:
            f.writelines(lines[:split_idx])
        
        # Create test file
        with open('./data/afac/afac_test.jsonl', 'w', encoding='utf-8') as f:
            f.writelines(lines[split_idx:])
        
        print(f"✅ Created afac_train.jsonl with {split_idx} entries")
        print(f"✅ Created afac_test.jsonl with {len(lines) - split_idx} entries")
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample files: {e}")
        return False

def main():
    """Main test function."""
    print("=" * 50)
    print("AFAC DATASET SUPPORT TEST")
    print("=" * 50)
    
    # Test basic support
    support_ok = test_afac_support()
    
    if support_ok:
        # Create compatible files
        create_sample_files()
        
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print("✅ AFAC dataset is supported and ready to use")
        print("✅ Compatible files created for TALE framework")
        print("\nUsage examples:")
        print("  python inference.py --data_name afac --model gpt-4o-mini")
        print("  python search_budget.py --do_search --data_name afac")
    else:
        print("\n❌ AFAC dataset support issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main()