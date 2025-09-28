from openai import OpenAI
from multiprocessing import Process, Queue
import csv
import re
from tqdm import tqdm
import time
from transformers import AutoTokenizer
import os
import random
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# client = OpenAI(api_key="0",base_url="http://0.0.0.0:8000/v1")
# def resres(query,temperature):
#     messages = [{"role": "user", "content": query}] # /no_think
#     result = client.chat.completions.create(messages=messages, temperature=temperature,model="/workspace/user_code/LLaMA-Factory-main/output/qwen3_4b_lora_sft3")
#     #print(result.choices[0].message.content)
#     return(result.choices[0].message.content[19:])# <think></think>的长度
# 1. 本地 tokenizer 只做一次，用来算 banned token ids
tok = AutoTokenizer.from_pretrained("/workspace/user_code/afac2025/Qwen3-4B-Chat")
banned_words = [
    # 确认类
    "好的", "好吧", "好", "好的呢", "好的呀", 
    "明白了", "我明白", "我理解了", "我知道了", "我懂了",
    "了解", "清楚了", "收到", "懂了",
    
    # 拖延/模糊类
    "让我想想", "我需要", "我现在", "这个嘛", 
    "其实", "一般来说", "通常情况下", "可能",
    
    # 无意义语气词
    "嗯", "呃", "啊", "哦", "诶", "呀",
    
    # 角色错位类
    "用户", "您", "你", "我们", "咱们",
    
    # 过度礼貌类
    "感谢您的提问", "很高兴为您解答", "非常乐意帮助您",
    
    # 重复问题类
    "您的问题是", "你想问的是", "你提到的",
    
    # 冗余前缀
    "关于这个问题", "针对这一点", "就这个问题而言"
]
logit_bias = {}
for w in banned_words:
    ids = tok.encode(w, add_special_tokens=False)
    for i in ids:
        logit_bias[i] = -100        # -100 足够让概率≈0
client = OpenAI(api_key="0", base_url="http://0.0.0.0:8000/v1")
def resres(query: str, temperature: float = 0.0) -> str:
    messages = [{"role": "user", "content": query}]
    resp = client.chat.completions.create(
        model="/workspace/user_code/LLaMA-Factory-main/output/qwen3_4b_lora_sft3",
        messages=messages,
        temperature=temperature,
        max_tokens=32768,
        logit_bias=logit_bias          # 关键：屏蔽指定 token
    )
    return(resp.choices[0].message.content[19:])# <think>\n</think>的长度
def extract_boxed_content(text):
    """
    从文本中提取最后一个\boxed{}内的内容
    """
    pattern = r'\\boxed{([^{}]+)}'
    matches = re.findall(pattern, text)
    return matches[-1] if matches else ""

# 定义温度列表和对应的提示词
temperatures = [0.1, 0.35, 0.8, 1.5, 2]
prompts = [
    "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题。你要首先在头脑中一步一步的思考并推理，但是不要输出具体思考过程，只需要输出经过思考后的总结结果。我保证问题有且只有唯一答案，能够基于规则客观评估正确性。用一句话指出问题的关键冲突，最后，答案要用 \\boxed{A/B/C/D} 的形式输出。",  # prompt1对应温度0.1
    "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题。你要首先在头脑中一步一步的思考并推理，但是不要输出具体思考过程，只需要输出经过思考后的总结结果。我保证问题有且只有唯一答案，能够基于规则客观评估正确性。对结果进行双重验证和一致性检查，最后，答案要用 \\boxed{A/B/C/D} 的形式输出。",         # prompt2对应温度0.35
    "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题。你要首先在头脑中一步一步的思考并推理，但是不要输出具体思考过程，只需要输出经过思考后的总结结果。我保证问题有且只有唯一答案，能够基于规则客观评估正确性。使用数据支撑关键结论，最后，答案要用 \\boxed{A/B/C/D} 的形式输出。",                # prompt3对应温度0.8
    "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题。你要首先在头脑中一步一步的思考并推理，但是不要输出具体思考过程，只需要输出经过思考后的总结结果。我保证问题有且只有唯一答案，能够基于规则客观评估正确性。用[电梯演讲]结构（30s），最后，答案要用 \\boxed{A/B/C/D} 的形式输出。",        # prompt4对应温度1.5
    "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题。你要首先在头脑中一步一步的思考并推理，但是不要输出具体思考过程，只需要输出经过思考后的总结结果。我保证问题有且只有唯一答案，能够基于规则客观评估正确性，最后，答案要用 \\boxed{A/B/C/D} 的形式输出。"            # prompt5对应温度2
]

def run_resres(question, temp, prompt, result_queue):
    full_question = prompt + question  # 将提示词和问题拼接
    response = resres(full_question, temperature=temp)
    result_queue.put(response)  # 将结果放入队列

# 读取输入文件并处理    input2.csv和训练的instruction一样
with open('/workspace/user_code/afac2025/data/input3.csv', 'r', encoding='utf-8') as infile, \
    open('output6.csv', 'w', newline='', encoding='utf-8') as outfile:

    # 首先计算总行数用于进度条
    total_rows = sum(1 for _ in open('/workspace/user_code/afac2025/data/input3.csv', 'r', encoding='utf-8'))
    
    reader = csv.reader(infile, delimiter='\t')
    writer = csv.writer(outfile, delimiter='\t')
    
    global_id = 0
    for row in tqdm(reader, total=total_rows, desc="处理进度"):
        if len(row) < 3:
            continue
        query_id = row[1]
        question = row[2]
        paired = list(zip(temperatures, prompts))
        random.shuffle(paired)
        for call_id, (temp, prompt) in enumerate(paired):
        #for call_id, (temp, prompt) in enumerate(zip(temperatures, prompts)):
            result_queue = Queue()
            p = Process(target=run_resres, args=(question, temp, prompt, result_queue))
            p.start()
            p.join(timeout=120)

            response = "TIMEOUT"  # 默认值
            if p.is_alive():
                p.terminate()
                p.join()  # 确保进程完全终止
                print(f"Timeout, skipping id={call_id}")
            else:
                try:
                    response = result_queue.get_nowait()  # 非阻塞获取
                    response = response.replace('\n', '')
                except:
                    response = "QUEUE_EMPTY"
            
            writer.writerow([
                global_id,
                query_id,
                call_id,
                response,
            ])
            
            global_id += 1
            time.sleep(1)

print("处理完成！结果已保存到output3.csv")