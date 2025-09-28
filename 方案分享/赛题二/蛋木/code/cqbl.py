import json
import os

# 源文件路径 (包含所有应该存在的完整数据)
SOURCE_FILE_PATH = './测试 B 集/data.jsonl'
# 结果文件路径 (用于检查哪些数据已经存在)
RESULT_FILE_PATH = './results/result.jsonl'
# 输出文件路径 (用于保存缺失的完整数据行)
OUTPUT_FILE_PATH = './results/cqbl.jsonl'

def get_existing_pairs(file_path: str) -> set:
    """
    从结果文件中加载所有 (material_id, rule_id) 对。

    Args:
        file_path (str): 结果文件 (result.jsonl) 的路径。

    Returns:
        set: 一个包含 (material_id, rule_id) 元组的集合。如果文件不存在则返回 None。
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件未找到 '{file_path}'")
        return None
        
    pairs = set()
    print(f"正在从 '{os.path.basename(file_path)}' 加载已存在的 ID 对...")
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if 'material_id' in data and 'rule_id' in data:
                    pairs.add((data['material_id'], data['rule_id']))
                else:
                    print(f"警告: 文件 '{file_path}' 的第 {i} 行缺少 'material_id' 或 'rule_id'。")
            except json.JSONDecodeError:
                print(f"警告: 无法解析文件 '{file_path}' 的第 {i} 行。")
    print(f"加载完成，共找到 {len(pairs)} 个唯一的 ID 对。")
    return pairs

def extract_missing_data(source_path: str, existing_pairs: set, output_path: str):
    if not os.path.exists(source_path):
        print(f"错误: 源文件未找到 '{source_path}'")
        return

    print(f"\n正在扫描 '{os.path.basename(source_path)}' 并筛选缺失的数据...")
    missing_count = 0
    
    try:
        with open(source_path, 'r', encoding='utf-8') as source_file, \
             open(output_path, 'w', encoding='utf-8') as output_file:
            
            for i, line in enumerate(source_file, 1):
                # 我们需要保留原始行，所以先不 strip()
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                
                try:
                    data = json.loads(stripped_line)
                    current_pair = (data.get('material_id'), data.get('rule_id'))
                    
                    # 检查 ID 对是否在已存在的集合中
                    if current_pair not in existing_pairs:
                        # 如果不在，说明是缺失数据，将原始行写入输出文件
                        output_file.write(line) # 写入包含换行符的原始行
                        missing_count += 1

                except (json.JSONDecodeError, KeyError, TypeError):
                    print(f"警告: 无法处理源文件 '{source_path}' 的第 {i} 行，将跳过此行。")

        print("\n--- 操作完成 ---")
        if missing_count > 0:
            print(f"成功筛选出 {missing_count} 条缺失的数据。")
            print(f"结果已保存到文件: '{os.path.abspath(output_path)}'")
        else:
            print("数据完整！在 'data.jsonl' 中没有找到 'result.jsonl' 缺失的数据。")
            # 如果没有缺失数据，可以选择删除空的输出文件
            os.remove(output_path)
            print(f"已删除空的输出文件 '{output_path}'。")

    except IOError as e:
        print(f"错误: 读写文件时发生错误: {e}")


def main():
    existing_pairs = get_existing_pairs(RESULT_FILE_PATH)
    
    if existing_pairs is None:
        return
        
    extract_missing_data(SOURCE_FILE_PATH, existing_pairs, OUTPUT_FILE_PATH)


if __name__ == "__main__":
    main()