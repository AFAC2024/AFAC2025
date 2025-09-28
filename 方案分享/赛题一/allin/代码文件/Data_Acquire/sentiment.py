from transformers import AutoModel, AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os
import pandas as pd
import re
from tqdm import tqdm

def extract_answer(text):
    """
    从模型输出文本中提取情感标签
    参数:
        text (str): 模型生成的完整文本
    返回:
        MatchObject: 正则表达式匹配结果对象
    """
    sentiment = re.search(r'<情感标签>\s*([^<]+?)\s*</情感标签>', text)
    return sentiment
def text_to_int(text):
    """
    将情感标签文本转换为数值
    参数:
        text (str): 情感标签文本 (positive/negative/neutral)
    返回:
        int: 对应的数值 (1:积极, 0:中性, -1:消极)
    """
    if 'positive' in text:
        return 1
    elif 'neutral' in text:
        return 0
    elif 'negative' in text:
        return -1

# 基础模型和微调模型文件路径配置
base_model = "Qwen3-4B" 
peft_model = "LLM_Train/cot_ouput/checkpoint"
# 加载分词器和模型
tokenizer = AutoTokenizer.from_pretrained(base_model)
tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(base_model, device_map = "cuda:0")
# 加载微调模型权重
model = PeftModel.from_pretrained(model, peft_model)
# 设置模型为eval模式
model = model.eval()


def get_sentiment(cot = True):
    """
    获取基金新闻的情感分析结果
    参数:
        cot (bool): 是否启用Chain-of-Thought思维链推理，默认为True
    """
    # 系统提示词，定义模型角色
    SYSTEM_PROMPT = """你是一个金融新闻情感分析专家"""
    # 读取的摘要数据根路径
    root_path = "Data/summary_data"
    # 获取所有摘要数据文件列表
    file_lists = os.listdir(root_path)
    # 创建情感分析结果保存目录
    if not os.path.exists("Data/sentiment_results"):
        os.mkdir("Data/sentiment_results")
    # 遍历处理每个基金的摘要数据文件
    for file in file_lists:
        # 输出当前正在处理的文件
        print(file)
        # 读取基金摘要数据
        data = pd.read_csv(os.path.join(root_path,file))
        sentiment_results = []
        # 对每条摘要数据进行情感分析
        for i in tqdm(range(len(data))):
            row = data.iloc[i]
            date = row['date']
            # 用户提示词前缀，包含具体的分析任务和要求
            USER_PROMPT_PREFIX = f"""你的任务是对给定的金融新闻进行情感分析，并输出相应的情感标签。
请仔细阅读以下金融新闻：
<金融新闻>
{row["response"]}
</金融新闻>
情感标签分为以下三种类型：积极、消极、中性，分别对应positive、negative、neutral。
请在<情感标签>标签中输出相应的情感标签(positive、negative、neutral中的一个)。
<情感标签>[positive/negative/neutral]</情感标签>"""
            # 可以关闭思维链，大大提高推理速度
            if cot == False:
                USER_PROMPT_PREFIX = USER_PROMPT_PREFIX + "/no_think"
            # 构建对话消息
            messages = [
                {"role":"system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_PREFIX}
            ]
            # 应用聊天模板
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=True
            )
            # 编码输入并生成响应
            model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
            generated_ids = model.generate(
                **model_inputs,
                max_new_tokens=32768
            )
            output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 
            try:
                index = len(output_ids) - output_ids[::-1].index(151668)
            except ValueError:
                index = 0
            # 解码生成的内容
            thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
            content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
            print(thinking_content)
            print(content)
            # 提取情感标签并转换为数值
            sentiment_text = extract_answer(content).group(1)
            sentiment = text_to_int(sentiment_text)
            # 保存结果
            sentiment_results.append({"date":date,"sentiment":sentiment})
        # 将情感分析结果保存为CSV文件
        df = pd.DataFrame(sentiment_results)
        df.to_csv(f"Data/sentiment_results/{file}")
