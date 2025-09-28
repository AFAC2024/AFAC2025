import os
import re
import logging
import shutil
from collections import defaultdict, deque
from typing import List, Dict, Any
import tiktoken

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
BASE_DIR = os.path.expanduser("./测试 B 集")
SOURCE_MATERIALS_DIR = os.path.join(BASE_DIR, "materials")
TARGET_CHUNK_DIR = os.path.join(BASE_DIR, "chunck_data")
MAX_TOKENS = 2000

try:
    tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    tokenizer = tiktoken.encoding_for_model("gpt-4")
logging.info(f"Tokenizer initialized. MAX_TOKENS set to {MAX_TOKENS}.")

SUBFOLDER_NAMES = {
    "CLAUSE", "INSURE_NOTICE", "HEALTH_INFORM", "HEAD_IMG", "INTRODUCE_IMG",
    "H5", "INSURANCE_POLICY", "PRODUCT_MANUAL", "ADDITIONAL_AGREEMENT",
    "LIABILITY_EXCLUSION"
}

# --- 2. 辅助函数  ---

def estimate_token_count(text: str) -> int:
    """估算文本的token数量"""
    return len(tokenizer.encode(text, disallowed_special=()))

def get_subfolder_from_path(relative_path: str) -> str:
    """从相对路径中提取出定义的子文件夹名称"""
    parts = relative_path.split(os.sep)
    for part in parts:
        if part in SUBFOLDER_NAMES:
            return part
    return "UNKNOWN"

def get_paragraphs_with_source(material_dir: str) -> List[Dict[str, str]]:
    """读取文件并创建带来源信息的段落列表"""
    logging.info(f"Reading files and creating paragraph-source list from: {material_dir}")
    md_files = []
    for root, _, files in os.walk(material_dir):
        for file in sorted(files):
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))

    all_paragraphs_with_source = []
    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                relative_path = os.path.relpath(file_path, BASE_DIR)
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                for p in paragraphs:
                    all_paragraphs_with_source.append({'text': p, 'source': relative_path})
        except Exception as e:
            logging.error(f"Failed to read file {file_path}: {e}")
    return all_paragraphs_with_source

def write_chunk_to_file(m_id: str, subfolder: str, chunk_index: int, content: str):
    """将分块内容写入文件，并放入对应的子文件夹"""
    try:
        # 构建目标路径
        target_dir = os.path.join(TARGET_CHUNK_DIR, m_id, subfolder)
        os.makedirs(target_dir, exist_ok=True)

        target_filename = f"batch_{chunk_index:03d}.md"
        target_filepath = os.path.join(target_dir, target_filename)
        with open(target_filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        final_token_count = estimate_token_count(content)
        log_level = logging.WARNING if final_token_count > MAX_TOKENS else logging.INFO
        logging.log(log_level, f"Successfully wrote chunk to: {target_filepath} (Token count: {final_token_count})")
    except Exception as e:
        # 增加日志信息，便于调试
        logging.error(f"Failed to write file for m_id {m_id} in subfolder {subfolder}: {e}")

def split_giant_paragraph(text: str, max_tokens: int) -> List[str]:
    """
    将巨型段落分割成小于 max_tokens 的块。
    新策略：优先按句子分割，然后组合，对超长句子再进行硬分割。
    """
    logging.info(f"Splitting a giant paragraph of {estimate_token_count(text)} tokens...")

    # 1. 按句子（或换行符）分割，这是更自然的边界
    # 使用正则表达式匹配句子结束符或连续的换行符作为分隔符
    sentences = re.split(r'([。！？\.\?!]|\n{2,})', text)
    
    # 将分隔符重新附加到句子末尾
    temp_sentences = []
    if sentences:
        temp_sentences.append(sentences[0])
        for i in range(1, len(sentences) - 1, 2):
            temp_sentences[-1] += sentences[i] # 将分隔符加到前一个句子
            if sentences[i+1]:
                temp_sentences.append(sentences[i+1]) # 添加下一个句子
    
    # 过滤掉可能产生的空字符串
    sentences = [s.strip() for s in temp_sentences if s.strip()]

    final_chunks = []
    current_chunk_sentences = []
    current_token_count = 0
    joiner_tokens = estimate_token_count("\n\n")

    # 2. 贪心组合句子成块
    for sentence in sentences:
        sentence_token_count = estimate_token_count(sentence)
        
        # 如果单个句子就超长，直接处理它
        if sentence_token_count > max_tokens:
            # 先将当前已组合的块保存起来
            if current_chunk_sentences:
                final_chunks.append("\n\n".join(current_chunk_sentences))
                current_chunk_sentences = []
                current_token_count = 0
            
            # 对这个超长的句子进行递归硬分割
            # 这是唯一需要硬分割的地方，风险可控
            logging.warning(f"A single sentence of {sentence_token_count} tokens exceeds max_tokens. Hard splitting it.")
            # 使用一个简单的、确保能前进的硬分割
            sub_chunks = []
            remaining_text = sentence
            while estimate_token_count(remaining_text) > max_tokens:
                # 估算一个安全的切分点（字符数）
                # 确保 split_pos > 0
                chars_per_token = len(remaining_text) / (estimate_token_count(remaining_text) + 1e-5)
                split_pos = max(1, int(max_tokens * chars_per_token * 0.9))
                
                # 寻找附近最近的换行符或空格，使分割更自然
                best_split = remaining_text.rfind(' ', 0, split_pos)
                if best_split == -1:
                    best_split = remaining_text.rfind('\n', 0, split_pos)
                
                split_point = best_split if best_split != -1 else split_pos

                sub_chunks.append(remaining_text[:split_point].strip())
                remaining_text = remaining_text[split_point:].strip()

            if remaining_text:
                sub_chunks.append(remaining_text)
            final_chunks.extend(sub_chunks)
            continue

        # 检查加入新句子后是否超长
        if current_chunk_sentences and (current_token_count + sentence_token_count + joiner_tokens) > max_tokens:
            # 当前块已满，保存并开始新块
            final_chunks.append("\n\n".join(current_chunk_sentences))
            current_chunk_sentences = [sentence]
            current_token_count = sentence_token_count
        else:
            # 继续向当前块添加句子
            if current_chunk_sentences:
                current_token_count += joiner_tokens
            current_chunk_sentences.append(sentence)
            current_token_count += sentence_token_count

    if current_chunk_sentences:
        final_chunks.append("\n\n".join(current_chunk_sentences))

    logging.info(f"Giant paragraph split into {len(final_chunks)} smaller chunks.")
    return final_chunks

# --- 4. 核心分块逻辑 ---

def process_single_material_dir(material_dir: str):
    m_id = os.path.basename(material_dir)
    logging.info(f"--- Starting processing for m_id: {m_id} with subfolder grouping ---")

    paragraphs_with_source = get_paragraphs_with_source(material_dir)
    processed_paragraphs = []
    for para_info in paragraphs_with_source:
        para_text = para_info['text']
        para_source = para_info['source']
        if estimate_token_count(para_text) > MAX_TOKENS:
            sub_chunks = split_giant_paragraph(para_text, MAX_TOKENS)
            for sub_chunk in sub_chunks:
                processed_paragraphs.append({'text': sub_chunk, 'source': para_source})
        else:
            processed_paragraphs.append(para_info)

    if not processed_paragraphs:
        logging.warning(f"No content found for m_id: {m_id}. Skipping.")
        return

    grouped_paragraphs = defaultdict(list)
    for para_info in processed_paragraphs:
        subfolder = get_subfolder_from_path(para_info['source'])
        grouped_paragraphs[subfolder].append(para_info)
    
    logging.info(f"Grouped paragraphs into {len(grouped_paragraphs)} subfolders: {list(grouped_paragraphs.keys())}")

    chunk_index = 1
    for subfolder in sorted(grouped_paragraphs.keys()):
        paragraphs_in_group = grouped_paragraphs[subfolder]
        logging.info(f"Processing group '{subfolder}' with {len(paragraphs_in_group)} paragraphs...")
        
        current_chunk_parts = []
        current_token_count = 0
        last_source_path = None

        for para_info in paragraphs_in_group:
            para_text = para_info['text']
            para_source = para_info['source']
            header_to_add = ""
            if para_source != last_source_path:
                header_to_add = f"## 文档: {para_source}\n\n"
            
            content_to_add = header_to_add + para_text
            token_count_to_add = estimate_token_count(content_to_add)
            joiner_tokens = estimate_token_count("\n\n") if current_chunk_parts else 0

            if current_chunk_parts and (current_token_count + token_count_to_add + joiner_tokens) > MAX_TOKENS:
                final_chunk_content = "\n\n".join(current_chunk_parts)
                write_chunk_to_file(m_id, subfolder, chunk_index, final_chunk_content)
                chunk_index += 1
                
                new_header = f"## 文档: {para_source}\n\n"
                current_chunk_parts = [new_header + para_text]
                current_token_count = estimate_token_count(new_header + para_text)
            else:
                current_chunk_parts.append(content_to_add)
                current_token_count += token_count_to_add + joiner_tokens
            
            last_source_path = para_source
            
        if current_chunk_parts:
            final_chunk_content = "\n\n".join(current_chunk_parts)
            write_chunk_to_file(m_id, subfolder, chunk_index, final_chunk_content)
            chunk_index += 1

    logging.info(f"--- Finished processing for m_id: {m_id} ---")


def main():
    logging.info("--- Starting Intelligent Chunking Process with Subfolder Grouping ---")
    if os.path.exists(TARGET_CHUNK_DIR):
        shutil.rmtree(TARGET_CHUNK_DIR)
        logging.info(f"Cleared old target directory: {TARGET_CHUNK_DIR}")
    os.makedirs(TARGET_CHUNK_DIR)

    if not os.path.isdir(SOURCE_MATERIALS_DIR):
        logging.error(f"Source directory not found: {SOURCE_MATERIALS_DIR}")
        return

    material_dirs = sorted([os.path.join(SOURCE_MATERIALS_DIR, entry) for entry in os.listdir(SOURCE_MATERIALS_DIR) if entry.startswith("m_") and os.path.isdir(os.path.join(SOURCE_MATERIALS_DIR, entry))])
    logging.info(f"Found {len(material_dirs)} material directories to process.")

    for dir_path in material_dirs:
        process_single_material_dir(dir_path)

    logging.info("--- All materials have been processed successfully. ---")

if __name__ == "__main__":
    main()