import os
from openai import OpenAI
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


# 只调用一次
import json
import re

def extract_boxed_answer(text):
    """从文本中提取\boxed{}中的答案"""
    match = re.search(r'\\boxed\{([A-D])\}', text)
    return match.group(1) if match else None

from tqdm import tqdm
import json

def process_json_file(input_file, output_file):
    """
    处理JSON文件，为每个条目添加模型生成的output，并显示进度条
    
    参数:
        input_file: 输入的JSON文件路径
        output_file: 输出的JSON文件路径
    """
    # 读取原始JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 使用tqdm显示进度条
    for item in tqdm(data, desc="处理进度", unit="条"):
        try:
            # 拼接instruction和input作为输入
            text_input = f"{item['instruction']}\n{item['input']}"
            # 调用模型获取响应
            model_response = resres(text_input+'\n值得注意的是，思考过程应该简洁，不要复述输入和条件，不要进行反思', 0.25)
            model_response = model_response.replace("\n", "")
            # 提取模型回答的答案
            item['output'] = model_response
            
        except Exception as e:
            print(f"\n处理条目时出错: {str(e)}")
            item['output'] = ""  # 出错时设为空字符串
            continue

    # 保存处理后的JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"\n处理完成！结果已保存到 {output_file}")

# 使用示例
process_json_file('finbenchmark.json', 'finbenchmark-cot.json')



# import json
# import re

# def extract_boxed_answer(text):
#     """从文本中提取\boxed{}中的答案"""
#     match = re.search(r'\\boxed\{([A-D])\}', text)
#     return match.group(1) if match else None

# def process_json_file(input_file, output_file):
#     # 读取原始JSON文件
#     with open(input_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     # 处理每个条目
#     for item in data:
#         original_output = item['output']  # 保存原始正确答案
#         correct_answered = False
        
#         # 第一次尝试：使用默认温度0.25
#         text_input1 = f"{item['instruction']}\n{item['input']}"
#         model_response1 = resres(text_input1, 0.25)
#         model_response1 = model_response1.replace("\n", "")
#         model_answer1 = extract_boxed_answer(model_response1)
        
#         if model_answer1 == original_output:
#             item['output'] = model_response1
#             continue  # 答对了，直接进入下一个条目
        
#         # 第二次尝试：使用更高温度0.8
#         text_input2 = f"{item['instruction']}\n{item['input']}"
#         model_response2 = resres(text_input2, 1)
#         model_response2 = model_response2.replace("\n", "")
#         model_answer2 = extract_boxed_answer(model_response2)
        
#         if model_answer2 == original_output:
#             item['output'] = model_response2
#             continue  # 答对了，进入下一个条目
        
#         # 第三次尝试：提供正确答案并要求解释
#         text_input3 = f'''{item['instruction']}\n{item['input']}\n\n现在我告诉你，答案是 {original_output}，请你使用一句话帮我解释为什么答案是这个，并给出你的最终答案，答案仍然要用 \boxed{{}} 的形式输出。'''
#         model_response3 = resres(text_input3, 0.25)
#         model_response3 = model_response3.replace("\n", "")
#         model_answer3 = extract_boxed_answer(model_response3)
        
#         if model_answer3 == original_output:
#             # 虽然解释正确，但仍标记为错误（根据要求）
#             item['output'] = model_response3
#         else:
#             # 即使提供了答案仍回答错误
#             item['output'] = f"{original_output}（回答错误）"
    
#     # 保存处理后的JSON文件
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)

# # 使用示例
# process_json_file('dineval-val.json', 'dineval-val-cot.json')
