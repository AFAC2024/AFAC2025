# from transformers import AutoModelForCausalLM, AutoTokenizer

# model_name = "/workspace/user_code/afac2025/Qwen3-4B-Chat"

# # load the tokenizer and the model
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# model = AutoModelForCausalLM.from_pretrained(
#     model_name,
#     torch_dtype="auto",
#     device_map="auto"
# )

# # prepare the model input
# prompt = "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，你要向用户提供答案。我保证问题有且只有唯一答案，是单选。最后，答案要用 \boxed{A/B/C/D} 的形式输出。\n问题：\n甲公司和乙公司均为增值税一般纳税人，适用的增值税税率为13%。2×19年6月10日，甲公司以一台生产设备换入乙公司的一项专利权（符合免征增值税条件）。交换日，甲公司换出设备的账面原价为1 000万元，已计提折旧250万元，计提减值准备50万元，公允价值为800万元，换出该设备应缴纳的增值税税额为104万元，甲公司另向乙公司支付银行存款46万元。假定该交易具有商业实质，不考虑其他因素的影响，甲公司该项非货币性资产交换对当期损益的影响金额为（　　）万元。\nA.100\nB.150\nC.0\nD.250 \n\n不要反思，不要检查，只需要使用一句话进行解释"
# messages = [
#     {"role": "user", "content": prompt}
# ]
# text = tokenizer.apply_chat_template(
#     messages,
#     tokenize=False,
#     add_generation_prompt=True,
#     enable_thinking=True # Switches between thinking and non-thinking modes. Default is True.
# )
# model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

# # conduct text completion
# generated_ids = model.generate(
#     **model_inputs,
#     max_new_tokens=32768
# )
# output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 

# # parsing thinking content
# try:
#     # rindex finding 151668 (</think>)
#     index = len(output_ids) - output_ids[::-1].index(151668)
# except ValueError:
#     index = 0

# thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
# content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

# print("thinking content:", thinking_content)
# print("content:", content)

from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "/workspace/user_code/afac2025/Qwen3-4B-Chat"

# 加载 tokenizer 和模型
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)


# 准备模型输入
prompt = "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，你要向用户提供答案。我保证问题有且只有唯一答案，是单选。最后，答案要用 \\boxed{A/B/C/D} 的形式输出。\n问题：\n甲公司和乙公司均为增值税一般纳税人，适用的增值税税率为13%。2×19年6月10日，甲公司以一台生产设备换入乙公司的一项专利权（符合免征增值税条件）。交换日，甲公司换出设备的账面原价为1 000万元，已计提折旧250万元，计提减值准备50万元，公允价值为800万元，换出该设备应缴纳的增值税税额为104万元，甲公司另向乙公司支付银行存款46万元。假定该交易具有商业实质，不考虑其他因素的影响，甲公司该项非货币性资产交换对当期损益的影响金额为（　　）万元。\nA.100\nB.150\nC.0\nD.250 \n\n不要进行反思，不要进行检查，只需要使用一句话进行解释"
messages = [
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=True  # 切换思考/非思考模式，默认为 True
)


model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
# 定义要禁止输出的词列表
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
# 1. 保持每个词是一个子列表
banned_word_ids = [tokenizer.encode(w, add_special_tokens=False) for w in banned_words]

# 2. 直接传 banned_word_ids
generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=32768,
    bad_words_ids=banned_word_ids   
)
# 解析输出
output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()

try:
    # 查找 </think> (151668) 的位置
    index = len(output_ids) - output_ids[::-1].index(151668)
except ValueError:
    index = 0

thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

print("thinking content:", thinking_content)
print("content:", content)
