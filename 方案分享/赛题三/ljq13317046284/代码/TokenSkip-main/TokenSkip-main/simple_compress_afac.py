#!/usr/bin/env python3
"""
简化版AFAC数据集思维链压缩脚本
使用基于规则的方法进行压缩，不依赖外部模型
"""

import os
import json
import re
from typing import List, Dict, Any

def load_afac_dataset(file_path: str) -> List[Dict[str, Any]]:
    """加载AFAC数据集"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def save_compressed_dataset(data: List[Dict[str, Any]], output_path: str):
    """保存压缩后的数据集"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_cot_and_answer(output_text: str) -> tuple:
    """从output中提取思维链和答案"""
    # 查找思考过程部分
    cot_pattern = r'### 思考过程：(.*?)### 最终答案：'
    match = re.search(cot_pattern, output_text, re.DOTALL)
    
    if match:
        cot_content = match.group(1).strip()
        answer_part = output_text[match.end():].strip()
    else:
        # 如果没有明确标记，尝试提取整个output作为思维链
        cot_content = output_text
        answer_part = ""
    
    # 提取boxed答案
    boxed_pattern = r'\\boxed{([A-Z])}'
    boxed_match = re.search(boxed_pattern, output_text)
    answer = boxed_match.group(1) if boxed_match else None
    
    return cot_content, answer_part, answer

def simple_compress_cot(cot_text: str, compression_ratio: float) -> str:
    """
    基于规则的简单压缩方法
    
    策略：
    1. 移除冗余的连接词
    2. 合并相似的观点
    3. 保留关键推理步骤
    4. 简化长句
    """
    if not cot_text:
        return cot_text
    
    # 定义可以移除的冗余词汇
    redundant_phrases = [
        "首先，", "其次，", "然后，", "接着，", "最后，",
        "此外，", "而且，", "同时，", "另外，",
        "也就是说", "换句话说", "具体来说",
        "我们可以得出", "我们可以发现", "我们可以推断",
        "因此可以得出", "由此可以得出",
        "综上所述", "总的来说", "总体而言",
        "基于以上分析", "根据上述分析"
    ]
    
    # 定义可以简化的短语
    simplify_map = {
        "我们可以清楚地看到": "可见",
        "我们可以明确地得出": "得出",
        "我们可以很容易地发现": "发现",
        "我们可以直接得出": "得出",
        "我们可以简单地得出": "得出",
        "我们可以立即得出": "得出",
        "我们可以迅速得出": "得出",
        "我们可以直接推断": "推断",
        "我们可以明确地推断": "推断"
    }
    
    compressed = cot_text
    
    # 移除冗余短语
    for phrase in redundant_phrases:
        compressed = compressed.replace(phrase, "")
    
    # 简化短语
    for long_phrase, short_phrase in simplify_map.items():
        compressed = compressed.replace(long_phrase, short_phrase)
    
    # 移除多余的空格和换行
    compressed = re.sub(r'\n+', '\n', compressed)
    compressed = re.sub(r' +', ' ', compressed)
    compressed = compressed.strip()
    
    # 根据压缩比例进一步压缩
    target_length = int(len(compressed) * compression_ratio)
    
    # 如果仍然过长，保留关键句子
    if len(compressed) > target_length:
        sentences = re.split(r'[。！？.!?]', compressed)
        key_sentences = []
        current_length = 0
        
        # 优先保留包含关键信息的句子
        keywords = ['答案', '选项', '属于', '不属于', '正确', '错误', '因为', '所以', '因此', '但是']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 检查是否包含关键词
            has_keyword = any(keyword in sentence for keyword in keywords)
            
            if has_keyword or current_length < target_length * 0.8:
                if current_length + len(sentence) <= target_length:
                    key_sentences.append(sentence)
                    current_length += len(sentence)
        
        compressed = '。'.join(key_sentences) + '。'
    
    return compressed.strip()

def compress_afac_dataset_simple(
    input_path: str,
    output_dir: str,
    compression_ratios: List[float] = None
):
    """使用简化方法压缩AFAC数据集"""
    
    if compression_ratios is None:
        compression_ratios = [0.9, 0.8, 0.7, 0.6, 0.5]
    
    print("正在加载AFAC数据集...")
    afac_data = load_afac_dataset(input_path)
    print(f"加载完成，共{len(afac_data)}条数据")
    
    for ratio in compression_ratios:
        print(f"\n正在处理压缩比例: {ratio}")
        compressed_data = []
        
        for item in afac_data:
            original_output = item.get('output', '')
            
            # 提取思维链和答案
            cot_content, answer_part, answer = extract_cot_and_answer(original_output)
            
            # 压缩思维链
            compressed_cot = simple_compress_cot(cot_content, ratio)
            
            # 构建压缩后的输出
            compressed_output = f"### 思考过程：{compressed_cot}\n### 最终答案：{answer_part}"
            
            # 创建新的数据项
            compressed_item = {
                'instruction': item.get('instruction', ''),
                'input': item.get('input', ''),
                'original_output': original_output,
                'compressed_output': compressed_output,
                'original_cot': cot_content,
                'compressed_cot': compressed_cot,
                'original_length': len(cot_content),
                'compressed_length': len(compressed_cot),
                'compression_ratio': len(compressed_cot) / len(cot_content) if len(cot_content) > 0 else 0,
                'answer': answer,
                'dataset': 'afac-cot-simple-compressed'
            }
            
            compressed_data.append(compressed_item)
        
        # 保存压缩后的数据
        output_filename = f"fineval-train-ds-cot-simple-{int(ratio*100)}.json"
        output_path = os.path.join(output_dir, output_filename)
        save_compressed_dataset(compressed_data, output_path)
        
        # 计算统计信息
        total_original = sum(item['original_length'] for item in compressed_data)
        total_compressed = sum(item['compressed_length'] for item in compressed_data)
        avg_compression = total_compressed / total_original if total_original > 0 else 0
        
        print(f"压缩完成: {output_filename}")
        print(f"原始总长度: {total_original}字符")
        print(f"压缩后总长度: {total_compressed}字符")
        print(f"平均压缩比例: {avg_compression:.3f}")
        print(f"成功处理: {len(compressed_data)} 条数据")
    
    print("\n所有压缩任务完成！")

def create_sample_comparison(input_path: str, output_dir: str):
    """创建压缩前后对比样本"""
    print("创建对比样本...")
    
    afac_data = load_afac_dataset(input_path)
    
    if len(afac_data) > 0:
        sample = afac_data[0]
        original_output = sample.get('output', '')
        
        cot_content, answer_part, answer = extract_cot_and_answer(original_output)
        
        # 创建不同压缩比例的对比
        comparison = {
            'original': {
                'cot': cot_content,
                'length': len(cot_content)
            },
            'compressed_80': {
                'cot': simple_compress_cot(cot_content, 0.8),
                'length': len(simple_compress_cot(cot_content, 0.8))
            },
            'compressed_50': {
                'cot': simple_compress_cot(cot_content, 0.5),
                'length': len(simple_compress_cot(cot_content, 0.5))
            }
        }
        
        output_path = os.path.join(output_dir, "compression_sample.json")
        save_compressed_dataset(comparison, output_path)
        print(f"对比样本已保存: {output_path}")

if __name__ == "__main__":
    # 设置路径
    input_file = "datasets/afac/fineval-train-ds-cot.json"
    output_directory = "datasets/afac/simple_compressed"
    
    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"输入文件不存在: {input_file}")
        exit(1)
    
    # 执行压缩
    compress_afac_dataset_simple(
        input_path=input_file,
        output_dir=output_directory,
        compression_ratios=[0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    )
    
    # 创建对比样本
    create_sample_comparison(input_file, output_directory)