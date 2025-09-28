# 导入所需的库
import pandas as pd
import json
import glob
import traceback
import os
import pickle
import time
from itertools import combinations
# 从自定义模块导入函数
from data_process import extract_module_raw_text, analysis_conflict, get_chunk_list
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 初始化冲突记录列表
conflict_records = []

# 读取规则配置文件，建立规则与文件类型的映射关系
rule_config = pd.read_excel(r"config/规则文件映射.xlsx")
cols = rule_config.columns
rule_map = {}
# 遍历规则配置表，构建规则到文件类型的映射字典
for index, row in rule_config.iterrows():
    files = []
    for col in cols:
        if row[col] == 1:  # 如果该列值为1，表示该规则适用于此文件类型
            files.append(col)
    rule_map[row['规则']] = files  # 建立规则与文件列表的映射


def process_row(row):
    """
    处理单条数据记录的核心函数
    参数:
        row: 包含material_id和rule信息的数据行
    """
    try:
        # 从规则描述中提取模块名称，进行文本清理
        module_name = row.rule.replace("该产品的与", "").replace("该产品的", "") \
            .replace("在各材料中的定义没有冲突", "") \
            .replace("保障相关的时间", "保障相关时间")

        # 记录处理开始时间
        start = time.time()
        start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start))
        # print(f"{start_str} Processing: {row.material_id} - {row.rule_id} - {module_name}")

        # 设置缓存目录并创建（如果不存在）
        cache_dir = "module_content_cache"
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{row.rule_id}.pkl")

        # 检查是否有缓存文件，如果有则直接加载，避免重复处理
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                module_content_list = pickle.load(f)
            # print(f"Loaded from cache: {cache_file}")
        else:
            # 没有缓存则进行正常处理
            module_content_list = []
            # 遍历指定材料目录下的所有文件
            for path in glob.glob(f"测试 B 集/materials/{row.material_id}/*/*"):
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                file_type = Path(path).parent.name  # 获取文件类型（父目录名）

                # 初始化用于存储模块内容的列表
                module_lines_parts = []

                # 使用线程池并行处理文件内容块
                with ThreadPoolExecutor() as executor:
                    # 将文件内容分割成块并提交给线程池处理
                    future_to_chunk = {
                        executor.submit(extract_module_raw_text, module_name, chunk_lines, path): chunk_lines
                        for chunk_lines in get_chunk_list(lines)
                    }

                    # 处理完成的线程结果
                    for future in as_completed(future_to_chunk):
                        try:
                            llm_result = future.result()
                            res_list = []
                            # 处理结果可能是列表或单个结果
                            if isinstance(llm_result, list):
                                res_list = llm_result
                            else:
                                res_list = [llm_result]

                            # 收集有效的结果（长度大于10）
                            for res in res_list:
                                if len(res) > 10:
                                    module_lines_parts.append(res)
                                    # 当累积内容超过8000字符时，保存为一个条目
                                    if sum(len(part) for part in module_lines_parts) > 8000:
                                        module_content_list.append([str(path), file_type, ''.join(module_lines_parts)])
                                        module_lines_parts = []
                        except Exception as e:
                            print(f"Error processing chunk: {e}")

                # 处理剩余的内容块
                if module_lines_parts and len(module_lines_parts) > 0:
                    module_content_list.append([str(path), file_type, ''.join(module_lines_parts)])

            # 将处理结果保存到缓存文件
            with open(cache_file, 'wb') as f:
                pickle.dump(module_content_list, f)
            # print(f"Saved to cache: {cache_file}")

        # 初始化一致性检查结果为True（一致）
        result = True
        valid_files = rule_map.get(module_name)  # 获取该模块适用的文件类型列表

        # 对提取的内容进行两两比较
        for content_i, content_j in combinations(module_content_list, 2):
            # 检查两个内容项是否都属于有效的文件类型
            is_valid = False
            if content_i[1] in valid_files and content_j[1] in valid_files:
                is_valid = True

            # 对于特定模块，跳过同类型文件之间的比较
            if module_name in ['基础产品销售信息', '出险条款', '附加条款', '术语解释', '续保条款', '保障相关时间',
                               '责任免除'] and \
                    (content_i[1] == content_j[1] or not is_valid):
                continue

            # 调用冲突分析函数进行一致性检查
            if isinstance(content_i[1], list):
                conflict_result = analysis_conflict(module_name, [content_i[2], content_j[2]])
            else:
                conflict_result = analysis_conflict(module_name, [content_i, content_j])

            # 如果发现不一致情况
            if conflict_result and conflict_result.find('不一致') > -1:
                # 记录冲突详情
                conflict_records.append({
                    "rule_id": row.rule_id,
                    "content_i": content_i,
                    "content_j": content_j,
                    "conflict_result": conflict_result
                })
                # print(conflict_records)
                result = False
                break  # 发现不一致立即退出循环

        # 返回处理结果
        return {
            "material_id": row.material_id,
            "rule_id": row.rule_id,
            "result": result
        }

    except Exception as e:
        # 异常处理
        print(f"Error processing {row.material_id}: {e}")
        print(traceback.format_exc())

        # 异常时返回默认结果（False表示不一致）
        return {
            "material_id": row.material_id,
            "rule_id": row.rule_id,
            "result": False
        }


def main():
    """
    主函数：读取数据并启动多线程处理
    """
    # 读取待处理的数据文件
    df = pd.read_json("测试 B 集/data.jsonl", lines=True)

    # 记录开始处理时间
    start = time.time()
    start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start))
    print(f"开始处理: {start_str}")

    results = []

    # 使用线程池并发处理数据行
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        # 提交所有任务到线程池
        for idx, row in df.iterrows():
            # if idx == 2:
            # if row.rule.find('退保条款') > -1:
            future = executor.submit(process_row, row)
            futures.append((future, idx))

        # 收集处理结果
        for future, idx in futures:
            try:
                result_item = future.result()
                start = time.time()
                start_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start))
                print(f"{start_str} Got result: {result_item}")
                # print(result_item['result'])
                results.append(result_item)
            except Exception as e:
                print(f"Task at index {idx} failed: {e}")
                # 出错时默认返回一致结果
                results.append({
                    "material_id": row.material_id,
                    "rule_id": row.rule_id,
                    "result": True
                })

    print(f"Collected {len(results)} results to write")

    # 将结果写入提交文件
    with open("submit.jsonl", "w", encoding="utf-8") as f:
        for item in results:
            if item is not None:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                # print(item['result'])

    # 如果有冲突记录，则保存到CSV文件
    if conflict_records:
        conflict_df = pd.DataFrame(conflict_records)
        conflict_df.to_csv("conflict_results.csv", index=False, encoding="utf-8-sig")
        print(f"已保存 {len(conflict_records)} 条冲突记录到 conflict_results.csv")
    else:
        print("未检测到冲突。")


# 程序入口点
if __name__ == "__main__":
    main()
