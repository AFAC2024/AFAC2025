import os
import re

def process_file(file_path):
    """
    处理单个文件：去除空行、行首尾空格，并将中间多余空格替换为单个。
    """
    try:
        # --- 步骤 1: 读取文件内容 ---
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        processed_lines = []
        # --- 步骤 2: 逐行处理 ---
        for line in lines:
            # 2.1 去除每行开头和结尾的空格
            stripped_line = line.strip()

            # 2.2 如果行处理后不为空，则继续处理
            if stripped_line:
                # 2.3 将中间的多个连续空格替换为单个空格
                # re.sub(r'\s+', ' ', stripped_line) 会将所有空白字符(包括空格、制表符等)替换为单个空格
                normalized_line = re.sub(r'\s+', ' ', stripped_line)
                processed_lines.append(normalized_line)
        
        # --- 步骤 3: 将处理后的内容写回原文件 ---
        # 使用 '\n'.join() 来确保行与行之间有换行符
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(processed_lines))
            
        print(f"处理完成: {file_path}")

    except Exception as e:
        print(f"处理文件时出错 {file_path}: {e}")

def main():
    root_dir = './测试 B 集/materials'

    if not os.path.isdir(root_dir):
        print(f"错误: 目录不存在 -> {root_dir}")
        return

    print(f"开始处理目录: {root_dir}")
    
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.md'):
                file_path = os.path.join(dirpath, filename)
                process_file(file_path)

    print("\n所有 .md 文件处理完毕！")

if __name__ == "__main__":
    main()