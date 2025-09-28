#!/usr/bin/env python3
"""
AFAC数据集思维链压缩脚本
用于压缩fineval-train-ds-cot.json中的思维链内容
"""

import os
import json
import re
from tqdm import tqdm
from llmlingua import PromptCompressor


def load_afac_dataset(file_path):
    """加载AFAC数据集"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def save_compressed_dataset(data, output_path):
    """保存压缩后的数据集"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_cot_from_output(output_text):
    """从output中提取思维链部分"""
    # 查找思考过程部分
    cot_pattern = r'### 思考过程：(.*?)### 最终答案：'
    match = re.search(cot_pattern, output_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # 如果没有明确标记，尝试提取整个output作为思维链
    return output_text


def compress_afac_cot(input_path, output_dir, compression_ratios=None, model_path="microsoft/llmlingua-2-xlm-roberta-large-meetingbank"):
    """
    压缩AFAC数据集中的思维链
    
    Args:
        input_path: 输入数据集路径
        output_dir: 输出目录
        compression_ratios: 压缩比例列表，如[0.9, 0.8, 0.7, 0.6, 0.5]
        model_path: LLMLingua模型路径
    """
    if compression_ratios is None:
        compression_ratios = [0.9, 0.8, 0.7, 0.6, 0.5]
    
    print("正在加载AFAC数据集...")
    afac_data = load_afac_dataset(input_path)
    print(f"加载完成，共{len(afac_data)}条数据")
    
    # 初始化压缩器
    print("正在初始化LLMLingua压缩器...")
    try:
        compressor = PromptCompressor(
            model_name=model_path,
            use_llmlingua2=True
        )
    except Exception as e:
        print(f"初始化压缩器失败: {e}")
        print("尝试使用默认模型...")
        compressor = PromptCompressor(
            model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
            use_llmlingua2=True
        )
    
    # 为每个压缩比例处理数据
    for ratio in compression_ratios:
        print(f"\n正在处理压缩比例: {ratio}")
        compressed_data = []
        
        # 处理每条数据
        for item in tqdm(afac_data, desc=f"压缩思维链 (比例={ratio})"):
            original_output = item.get('output', '')
            
            # 提取思维链部分
            cot_content = extract_cot_from_output(original_output)
            
            if cot_content:
                try:
                    # 压缩思维链
                    compressed_cot = compressor.compress_prompt(
                        cot_content,
                        rate=ratio,
                        force_tokens=['思考', '过程', '因为', '所以', '因此', '但是', '然而'],
                        force_reserve_digit=True
                    )
                    
                    # 构建压缩后的输出
                    compressed_output = original_output.replace(
                        cot_content, 
                        compressed_cot['compressed_prompt']
                    )
                    
                    # 创建新的数据项
                    compressed_item = {
                        'instruction': item.get('instruction', ''),
                        'input': item.get('input', ''),
                        'original_output': original_output,
                        'compressed_output': compressed_output,
                        'original_cot': cot_content,
                        'compressed_cot': compressed_cot['compressed_prompt'],
                        'original_tokens': compressed_cot['origin_tokens'],
                        'compressed_tokens': compressed_cot['compressed_tokens'],
                        'compression_ratio': compressed_cot['rate'],
                        'dataset': 'afac-cot-compressed'
                    }
                    
                    compressed_data.append(compressed_item)
                    
                except Exception as e:
                    print(f"压缩失败，跳过该条数据: {e}")
                    # 如果压缩失败，保留原始内容
                    compressed_item = {
                        'instruction': item.get('instruction', ''),
                        'input': item.get('input', ''),
                        'original_output': original_output,
                        'compressed_output': original_output,
                        'original_cot': cot_content,
                        'compressed_cot': cot_content,
                        'original_tokens': len(cot_content),
                        'compressed_tokens': len(cot_content),
                        'compression_ratio': 1.0,
                        'dataset': 'afac-cot-compressed',
                        'error': str(e)
                    }
                    compressed_data.append(compressed_item)
        
        # 保存压缩后的数据
        output_filename = f"fineval-train-ds-cot-compressed-{int(ratio*100)}.json"
        output_path = os.path.join(output_dir, output_filename)
        save_compressed_dataset(compressed_data, output_path)
        
        # 计算统计信息
        total_original = sum(item['original_tokens'] for item in compressed_data)
        total_compressed = sum(item['compressed_tokens'] for item in compressed_data)
        avg_compression = total_compressed / total_original if total_original > 0 else 0
        
        print(f"压缩完成: {output_filename}")
        print(f"原始总token数: {total_original}")
        print(f"压缩后总token数: {total_compressed}")
        print(f"平均压缩比例: {avg_compression:.3f}")
        print(f"成功处理: {len(compressed_data)} 条数据")
    
    print("\n所有压缩任务完成！")


def create_compression_report(input_path, output_dir):
    """创建压缩报告"""
    report_path = os.path.join(output_dir, "compression_report.json")
    
    report = {
        "input_file": input_path,
        "output_dir": output_dir,
        "compression_ratios": [0.9, 0.8, 0.7, 0.6, 0.5],
        "model": "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
        "description": "AFAC数据集思维链压缩报告",
        "created_at": "2025-07-31"
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"压缩报告已保存: {report_path}")


if __name__ == "__main__":
    # 设置路径
    input_file = "datasets/afac/fineval-train-ds-cot.json"
    output_directory = "datasets/afac/compressed"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"输入文件不存在: {input_file}")
        print("请检查路径是否正确")
        exit(1)
    
    # 执行压缩
    compress_afac_cot(
        input_path=input_file,
        output_dir=output_directory,
        compression_ratios=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    )
    
    # 创建压缩报告
    create_compression_report(input_file, output_directory)