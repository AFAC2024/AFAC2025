#!/usr/bin/env python3
"""
AFAC数据集验证和测试脚本
用于验证数据集格式并测试压缩功能
"""

import os
import json
import sys
from pathlib import Path

def validate_dataset(file_path):
    """验证数据集格式"""
    print(f"正在验证数据集: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ 成功加载数据，共{len(data)}条记录")
        
        if len(data) == 0:
            print("❌ 数据集为空")
            return False
        
        # 检查第一条记录的格式
        first_item = data[0]
        required_keys = ['instruction', 'input', 'output']
        
        for key in required_keys:
            if key not in first_item:
                print(f"❌ 缺少必要字段: {key}")
                return False
        
        print("✅ 数据格式验证通过")
        
        # 显示样本信息
        print("\n样本信息:")
        print(f"  instruction长度: {len(first_item['instruction'])}字符")
        print(f"  input长度: {len(first_item['input'])}字符")
        print(f"  output长度: {len(first_item['output'])}字符")
        
        # 检查是否包含思维链格式
        output = first_item['output']
        if '### 思考过程：' in output and '### 最终答案：' in output:
            print("✅ 检测到标准思维链格式")
            
            # 提取思维链部分
            import re
            cot_pattern = r'### 思考过程：(.*?)### 最终答案：'
            match = re.search(cot_pattern, output, re.DOTALL)
            if match:
                cot_content = match.group(1).strip()
                print(f"  思维链长度: {len(cot_content)}字符")
                
                # 检查答案格式
                boxed_pattern = r'\\boxed{([A-Z])}'
                boxed_match = re.search(boxed_pattern, output)
                if boxed_match:
                    print(f"  检测到标准答案格式: {boxed_match.group(1)}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def test_compression():
    """测试压缩功能"""
    print("\n" + "="*50)
    print("测试压缩功能")
    print("="*50)
    
    try:
        from llmlingua import PromptCompressor
        print("✅ LLMLingua库导入成功")
        
        # 测试压缩器初始化
        compressor = PromptCompressor(
            model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
            use_llmlingua2=True
        )
        print("✅ 压缩器初始化成功")
        
        # 测试简单压缩
        test_text = "这是一个测试文本，用于验证压缩功能是否正常工作。"
        compressed = compressor.compress_prompt(test_text, rate=0.8)
        
        if compressed and 'compressed_prompt' in compressed:
            print("✅ 压缩功能测试成功")
            print(f"  原始长度: {len(test_text)}字符")
            print(f"  压缩后长度: {len(compressed['compressed_prompt'])}字符")
            print(f"  压缩比例: {compressed['rate']}")
        else:
            print("❌ 压缩功能测试失败")
            
    except ImportError as e:
        print(f"❌ LLMLingua库导入失败: {e}")
        print("请运行: pip install llmlingua")
    except Exception as e:
        print(f"❌ 压缩测试失败: {e}")

def check_dependencies():
    """检查依赖项"""
    print("\n" + "="*50)
    print("检查依赖项")
    print("="*50)
    
    dependencies = [
        'llmlingua',
        'tqdm',
        'torch',
        'transformers'
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} (需要安装)")

def main():
    """主函数"""
    print("AFAC数据集验证和测试工具")
    print("="*50)
    
    # 设置路径
    dataset_path = "datasets/afac/fineval-train-ds-cot.json"
    
    # 验证数据集
    is_valid = validate_dataset(dataset_path)
    
    # 检查依赖
    check_dependencies()
    
    # 测试压缩
    test_compression()
    
    print("\n" + "="*50)
    if is_valid:
        print("✅ 数据集验证完成，可以开始压缩")
        print("运行: python compress_afac_cot.py")
    else:
        print("❌ 数据集验证失败，请检查文件")
    
    print("="*50)

if __name__ == "__main__":
    main()