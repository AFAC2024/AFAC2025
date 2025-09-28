import csv
import json
import os

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
                # 手动读取第一行，确定列名
                header_line = next(csvfile).strip().split(',')
                
                # 根据新格式调整字段
                fieldnames = ['index', 'Question', 'A', 'B', 'C', 'D', 'Answer']
                reader = csv.DictReader(csvfile, fieldnames=fieldnames)
                
                # 跳过重复的表头行
                next(reader, None)
                
                for row in reader:
                    # 跳过空行
                    if not row.get('Question'):
                        continue
                    
                    # 校验答案格式
                    answer = row.get('Answer', '').strip().upper()
                    if not answer or answer not in ['A', 'B', 'C', 'D']:
                        print(f"  -> 跳过答案格式错误的行, 文件: {filename}, 问题: {row.get('Question', '')[:30]}..., 答案: '{answer}'")
                        continue

                    try:
                        # 构建input部分
                        input_text = (
                            f"{row['Question'].strip()}\n"
                            f"A,{row['A'].strip()}\n"
                            f"B,{row['B'].strip()}\n"
                            f"C,{row['C'].strip()}\n"
                            f"D,{row['D'].strip()}"
                        )
                        
                        # 构建output部分
                        output_text = f"\\boxed{{{answer}}}"
                        
                        # 构建JSON对象 (使用固定的instruction)
                        json_obj = {
                            "instruction": "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，请你使用一句话进行解释，然后向用户提供答案。例如：\n        input: 中国金融市场上现有的金融衍生产品不包括____。\nA,风险类\nB,利率类\nC,权益类\nD,货币类,\n        output: 按照利率类、权益类、货币类、商品类和信用类五个分类标准，中国现有的衍生产品包括以下几类。\\boxed{A}\n        input: ____不是金融衍生工具的特征之一。\nA,依赖于原生性金融工具\nB,表现为一种合约\nC,合约上载明交易品种、价格、数量、交割时间及地点等\nD,可以作为支付工具进行交易,\n        output: 金融衍生工具是指价值依赖于原生性金融工具的一类金融产品，在形式上均表现为一种合约，在合约上载明买卖双方同意的交易品种、价格、数量、交割时间及地点等。\\boxed{D}\n我保证问题有且只有唯一答案，能够基于规则客观评估正确性，最后，答案要用 \\boxed{A/B/C/D} 的形式输出。",
                            "input": input_text,
                            "output": output_text
                        }
                        
                        json_data.append(json_obj)

                    except Exception as e:
                        print(f"  -> 处理行时出错, 文件: {filename}, 问题: {row.get('Question', '')[:30]}..., 错误: {str(e)}")
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

# 设置输入和输出路径
input_directory = '/data/workspace/afac/FinanceIQ/test'  # CSV文件所在的目录
output_json_file = 'FinanceIQ-test2.json'  # 合并后的JSON文件

# 运行转换函数
merge_csv_to_json(input_directory, output_json_file)
