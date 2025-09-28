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
import re

def merge_csv_to_json(input_dir, output_file):
    """
    将多个特定格式的CSV文件合并并转换为一个JSON文件。
    - 跳过不符合格式的行（如重复的表头）。
    - 按照指定的 instruction, input, output 格式构建JSON对象。
    """
    json_data = []
    
    # 检查输入目录是否存在
    if not os.path.isdir(input_dir):
        print(f"错误：输入目录 '{input_dir}' 不存在。")
        return

    # 遍历目录中的所有CSV文件
    for filename in os.listdir(input_dir):
        if not filename.lower().endswith('.csv'):
            continue
            
        input_path = os.path.join(input_dir, filename)
        print(f"正在处理文件: {filename}...")
        
        try:
            # 使用 'utf-8-sig' 可以兼容带有BOM的UTF-8文件
            with open(input_path, 'r', encoding='utf-8-sig') as csvfile:
                # DictReader默认使用第一行作为表头
                reader = csv.DictReader(csvfile)
                
                # 检查表头是否符合预期
                required_fields = ['id', 'question', 'A', 'B', 'C', 'D', 'answer'] #, 'explanation'
                if not all(field in reader.fieldnames for field in required_fields):
                    print(f"  -> 警告: 文件 {filename} 的表头不完整，跳过该文件。")
                    continue

                for row in reader:
                    # **关键修改：跳过重复的表头行**
                    if row.get('id') == 'id' and row.get('question') == 'question':
                        continue

                    # 检查核心字段是否存在且不为空
                    if not all(row.get(field) for field in required_fields):
                        print(f"  -> 跳过不完整的行, 文件: {filename}, ID: {row.get('id', '未知')}")
                        continue
                    
                    # 校验答案格式
                    answer = row.get('answer', '').strip().upper()
                    if answer not in ['A', 'B', 'C', 'D']:
                        print(f"  -> 跳过答案格式错误的行, 文件: {filename}, ID: {row.get('id')}, 答案: '{answer}'")
                        continue

                    try:
                        # 构建input部分
                        input_text = (
                            f"{row['question'].strip()}\n"
                            f"A,{row['A'].strip()}\n"
                            f"B,{row['B'].strip()}\n"
                            f"C,{row['C'].strip()}\n"
                            f"D,{row['D'].strip()}"
                        )
                        
                        # **优化：清洗explanation并构建output部分**
                        # 1. 取出explanation，去除首尾空格
                        #explanation_raw = row['explanation'].strip()
                        explanation_raw = ''
                        # 2. 只取第一行内容（以防有多行解释）
                        first_line_explanation = explanation_raw.split('\n')[0]
                        # 3. 使用正则表达式去除行首的 "1. "、"2. " 等编号
                        cleaned_explanation = re.sub(r'^\d+\.\s*', '', first_line_explanation).strip()
                        
                        output_text = f"{cleaned_explanation}\\boxed{{{answer}}}"
                        
                        # 构建JSON对象 (使用你提供的更详细的instruction)
                        json_obj = {
                            "instruction": "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，你要给出解决问题的思考过程和最终答案。你要首先在头脑中思考推理过程，然后向用户提供答案。我保证问题有且只有唯一答案，能够基于规则客观评估正确性，最后，答案要用 \boxed{A/B/C/D} 的形式输出。",
                            "input": input_text,
                            "output": output_text
                        }
                        
                        json_data.append(json_obj)

                    except Exception as e:
                        print(f"  -> 处理行时出错, 文件: {filename}, ID: {row.get('id', '未知')}, 错误: {str(e)}")
                        continue
        
        except Exception as e:
            print(f"读取文件 {filename} 时发生错误: {str(e)}")

    # 写入合并后的JSON文件
    try:
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(json_data, jsonfile, ensure_ascii=False, indent=4)
        
        print(f"\n处理完成！共转换 {len(json_data)} 条记录，已保存到 {output_file}")
    
    except Exception as e:
        print(f"写入JSON文件 {output_file} 时发生错误: {str(e)}")


# --- 使用示例 ---
# 假设你的CSV文件都放在一个名为 'my_csv_files' 的文件夹里
# 请确保这个文件夹存在，并且里面有你的 a.csv 文件


# 设置输入和输出路径
input_directory = '/data/workspace/afac/fineval/val'  # CSV文件所在的目录
output_json_file = 'dineval-val.json'  # 合并后的JSON文件

# 运行转换函数
merge_csv_to_json(input_directory, output_json_file)
