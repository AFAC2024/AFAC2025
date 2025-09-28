import os
from openai import OpenAI
import time
os.environ['OPENAI_API_KEY'] = ""
client = OpenAI(base_url="http://v2.open.venus.oa.com/llmproxy")
def resres(text,temperature):
    response = client.chat.completions.create(
    model="deepseek-v3-local-II",
    temperature=temperature,
    messages=[{"role": "user", "content": text}]
    )
    result = {
        'content': '',
        'reasoning': ''
    }
    
    if hasattr(response, 'choices'):
        for choice in response.choices:
            if hasattr(choice, 'message'):
                result['content'] = getattr(choice.message, 'content', '')
                result['reasoning'] = getattr(choice.message, 'reasoning_content', '')
    
    return result['content']
# prompt='''请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，你要给出解决问题的思考过程和最终答案。你要首先在头脑中思考推理过程，然后向用户提供答案。我保证问题有且只有唯一答案，能够基于规则客观评估正确性，最后，答案要用 \boxed{A/B/C/D} 的形式输出。下列不属于我国商业银行业务范围的是____。\nA,发行金融债券\nB,监管其他金融机构\nC,买卖政府债券\nD,买卖外汇'''
# print(resres(prompt,0.8))
import csv
prompt='''"以下是一个分步推理过程，请你在内部理解并整合所有逻辑，你应该在头脑中一步一步的思考，但不要输出任何中间步骤和具体思考过程。在潜在空间完成所有计算后，对该思维链进行总结即可。  
需要总结的思维链内容如下(直接返回利用Latent Space Reasoning总结后的内容)：
'''
#3.最后的\\boxed{{A\B\C\D}}应该保留
import csv
def process_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')
        
        for row in reader:
            if len(row) >= 4:  # 确保有第四列
                original_text = row[3]
                
                # 提取\boxed{...}部分
                boxed_part = ""
                if r'\boxed{' in original_text:
                    start_idx = original_text.index(r'\boxed{')
                    boxed_part = original_text[start_idx:]
                
                # 调用resres函数处理文本（不包括boxed部分）
                text_to_process = original_text.replace(boxed_part, "")
                processed_text = resres(prompt + text_to_process, 0.25).replace("\n", "")
                time.sleep(1)
                # 将处理后的文本与boxed部分合并
                new_text = processed_text + boxed_part
                
                # 更新第四列
                row[3] = new_text
            
            # 立即写入当前行
            writer.writerow(row)
            outfile.flush()  # 确保立即写入磁盘

# 使用示例
input_filename = 'input-ds-output.csv'
output_filename = 'input-ds-output-sub.csv'
process_file(input_filename, output_filename)

print(f"处理完成，结果已保存到 {output_filename}")
