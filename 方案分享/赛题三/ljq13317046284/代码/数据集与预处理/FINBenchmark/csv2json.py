# import csv
# import json
# import os

# def merge_csv_to_json(input_dir, output_file):
#     json_data = []
    
#     # 遍历目录中的所有CSV文件
#     for filename in os.listdir(input_dir):
#         if not filename.endswith('.csv'):
#             continue
            
#         input_path = os.path.join(input_dir, filename)
        
#         with open(input_path, 'r', encoding='utf-8') as csvfile:
#             reader = csv.DictReader(csvfile)
#             for row in reader:
#                 # 检查行是否符合格式要求
#                 required_fields = ['id', 'question', 'A', 'B', 'C', 'D', 'answer', 'explanation']
#                 if not all(field in row for field in required_fields):
#                     print(f"跳过不符合格式的行，文件: {filename}, ID: {row.get('id', '未知')}")
#                     continue
                
#                 try:
#                     # 构建input部分
#                     input_text = f"{row['question']}\nA,{row['A']}\nB,{row['B']}\nC,{row['C']}\nD,{row['D']}"
                    
#                     # 构建output部分
#                     explanation = row['explanation'].split('\n')[0].strip()  # 取第一行解释
#                     output_text = f"{explanation}\\boxed{{{row['answer']}}}"
                    
#                     # 构建JSON对象
#                     json_obj = {
#                         "instruction": "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，你要给出解决问题的思考过程和最终答案。你要首先在头脑中思考推理过程，然后向用户提供答案。我保证问题有且只有唯一答案，能够基于规则客观评估正确性，最后，答案要用 \boxed{A/B/C/D} 的形式输出。",
#                         "input": input_text,
#                         "output": output_text
#                     }
                    
#                     json_data.append(json_obj)
#                 except Exception as e:
#                     print(f"处理行时出错，文件: {filename}, ID: {row['id']}, 错误: {str(e)}")
#                     continue
    
#     # 写入合并后的JSON文件
#     with open(output_file, 'w', encoding='utf-8') as jsonfile:
#         json.dump(json_data, jsonfile, ensure_ascii=False, indent=4)
    
#     print(f"合并完成，共处理 {len(json_data)} 条记录，已保存到 {output_file}")

# # 使用示例
# input_directory = '/data/workspace/afac/fineval/dev'  # CSV文件所在的目录
# output_file = 'dineval-dev.json'  # 合并后的JSON文件
# merge_csv_to_json(input_directory, output_file)


import csv
import json
import os

def convert_csv_to_json(input_dir, output_file):
    """
    将目录中的所有CSV文件转换为指定的JSON格式
    
    参数:
        input_dir: 包含CSV文件的目录路径
        output_file: 输出的JSON文件路径
    """
    # 定义固定的instruction文本
    instruction_text = """请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，请你使用一句话进行解释，然后向用户提供答案。最后，答案要用 \\boxed{A/B/C/D} 的形式输出。"""
    
    json_data = []
    
    # 遍历目录中的所有CSV文件
    for filename in os.listdir(input_dir):
        if not filename.endswith('.csv'):
            continue
            
        filepath = os.path.join(input_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # 检查CSV文件是否包含必需的列
                required_columns = ['id', 'question', 'A', 'B', 'C', 'D']
                if not all(col in reader.fieldnames for col in required_columns):
                    print(f"跳过文件 {filename}，因为它缺少必需的列")
                    continue
                
                for row in reader:
                    # 构建input部分
                    input_text = f"{row['question']}\nA,{row['A']}\nB,{row['B']}\nC,{row['C']}\nD,{row['D']}"
                    
                    # 创建JSON对象
                    json_obj = {
                        "instruction": instruction_text,
                        "input": input_text,
                        "output": ""  # 留空，因为原始CSV中没有答案
                    }
                    
                    json_data.append(json_obj)
                    
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            continue
    
    # 将结果写入JSON文件
    try:
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, ensure_ascii=False, indent=4)
        print(f"转换完成！结果已保存到 {output_file}")
    except Exception as e:
        print(f"写入JSON文件时出错: {str(e)}")

# 使用示例
input_directory = '/data/workspace/afac/FINBenchmark'  # 替换为你的CSV文件目录
output_json_file = 'finbenchmark.json'  # 输出的JSON文件名

convert_csv_to_json(input_directory, output_json_file)
