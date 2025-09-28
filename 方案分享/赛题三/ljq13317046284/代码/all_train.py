# import json
# import os
# import random
# from glob import glob

# def merge_and_shuffle_json_files(output_file='all_train_cot.json'):
#     # 收集所有JSON文件路径
#     json_files = [
#         '/data/workspace/afac/FinanceIQ/dev/FinanceIQ-dev-cot.json',
#         '/data/workspace/afac/FinanceIQ/test/FinanceIQ-test-cot.json',
#         '/data/workspace/afac/fineval/dev/dineval-dev.json',
#         '/data/workspace/afac/fineval/val/dineval-val-cot.json',
#         '/data/workspace/afac/input2train.json'
#     ]
#     all_data=[]
#     # 读取所有JSON文件内容
#     for json_file in json_files:
#         try:
#             with open(json_file, 'r', encoding='utf-8') as f:
#                 data = json.load(f)
#                 if isinstance(data, list):
#                     all_data.extend(data)
#                 else:
#                     all_data.append(data)
#             print(f"已读取: {json_file}")
#         except Exception as e:
#             print(f"读取文件 {json_file} 时出错: {e}")
    
#     # 打乱顺序
#     random.shuffle(all_data)
    
#     # 写入合并后的文件
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(all_data, f, ensure_ascii=False, indent=2)
    
#     print(f"合并完成！共合并了 {len(all_data)} 条数据，输出文件: {output_file}")

# if __name__ == '__main__':
#     merge_and_shuffle_json_files()


import json
import os
import random
from glob import glob

def merge_and_shuffle_json_files(output_file='all_train_cot2.json'):
    # 收集所有JSON文件路径
    json_files = [
        '/data/workspace/afac/FinanceIQ/dev/FinanceIQ-dev-cot.json',
        '/data/workspace/afac/FinanceIQ/test/FinanceIQ-test-cot.json',
        '/data/workspace/afac/fineval/dev/dineval-dev.json',
        '/data/workspace/afac/fineval/val/dineval-val-cot.json',
        '/data/workspace/afac/FINBenchmark/finbenchmark-cot.json',
        '/data/workspace/afac/output1.json',
        '/data/workspace/afac/output2.json',
        '/data/workspace/afac/output3.json',
        '/data/workspace/afac/output4.json',
        '/data/workspace/afac/output5.json'
    ]
    all_data=[]
    # 读取所有JSON文件内容
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
                else:
                    all_data.append(data)
            print(f"已读取: {json_file}")
        except Exception as e:
            print(f"读取文件 {json_file} 时出错: {e}")
    
    # 打乱顺序
    random.shuffle(all_data)
    
    # 写入合并后的文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"合并完成！共合并了 {len(all_data)} 条数据，输出文件: {output_file}")

if __name__ == '__main__':
    merge_and_shuffle_json_files()
