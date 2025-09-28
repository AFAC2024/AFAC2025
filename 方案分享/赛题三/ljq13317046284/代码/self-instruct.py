import csv

import os
from openai import OpenAI
import time
os.environ['OPENAI_API_KEY'] = ""
client = OpenAI(base_url="http://v2.open.venus.oa.com/llmproxy")
def res(text):
    response = client.chat.completions.create(
    model="deepseek-v3-local-II",
    temperature=1.2,
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

# # 你的示例题目
# examples = [
#     "下列各项关于变更记账本位币会计处理的表述中，正确的是（      ）。\\nA.记账本位币变更日，所有者权益项目按照历史汇率折算为变更后的记账本位币\\nB.记账本位币变更日，资产负债项目按照当日的即期汇率折算为变更后的记账本位币\\nC.记账本位币变更当年年初至变更日的利润表项目按照交易发生日的即期汇率折算为变更后的记账本位币\\nD.记账本位币变更当年年初至变更日的现金流量表项目按照与交易发生日即期汇率近似的汇率折算为变更后的记账本位币",
#     "下列各项中，应在资产负债表“应付账款”项目列示的有（ ）。\\nA.“应付票据”科目所属明细科目的贷方余额\\nB.“预付账款”科目所属明细科目的贷方余额\\nC.“应付账款”科目所属明细科目的贷方余额\\nD.“应付账款”科目所属明细科目的借方余额",
#     "经海公司2021年11月发生消费税10万元，实际缴纳消费税10万元，缴纳增值税20万元，已知城市维护建设税的征收比率为7%，教育费附加的征收比率为3%。经海公司本月应当计入税金及附加的金额为（ ）万元。\\nA.20\\nB.13\\nC.3\\nD.33",
#     "2×20年，甲公司发生的有关交易或事项如下：（1）甲公司以其生产的产品作为奖品，奖励给20名当年度被评为优秀的生产工人。上述产品的销售价格总额为500万元，销售成本为420万元；（2）根据甲公司确定的利润分享计划，以当年度实现的利润总额为基础，计算的应支付给管理人员利润分享金额为280万元；（3）甲公司于当年起对150名管理人员实施累积带薪年休假制度，每名管理人员每年可享受7个工作日的带薪年休假，未使用的年休假只能向后结转一个日历年度，超过1年未使用的权利作废，也不能得到任何现金补偿。2×20年，有10名管理人员每人未使用带薪年休假2天，预计2×21年该10名管理人员将每人休假9天。甲公司平均每名管理人员每个工作日的工资为300元。不考虑相关税费及其他因素，下列各项关于甲公司上述职工薪酬会计处理的表述中，正确的是（　　）。\\nA.将自产的产品作为奖品发放应按420万元确认应付职工薪酬\\nB.2×20年应确认10名管理人员未使用带薪年休假费用0.6万元并计入管理费用\\nC.根据利润分享计划计算的2×20年应支付给管理人员的280万元款项应作为利润分配处理\\nD.2×20年应从工资费用中扣除已享受带薪年休假权利的140名管理人员的工资费用29.4万元"
# ]

# # Prompt模板
# prompt_template = """
# 你是一名金融领域的高级出题专家。请根据以下要求，生成一道全新的金融推理选择题，题目难度适中，题干包含必要的背景知识、定义、数据和规则，题目长度不超过1000 token，答案唯一且不在题干中，题型为表格推理、计算推理或逻辑推理。请严格按照如下格式输出：

# ####题目开始####
# 【题目】{example}
# ####题目结束####

# 请仿照上述格式，再生成一道全新的题目（不要与示例重复），并严格按照如下格式输出：

# ####题目开始####
# 【题目】（请在此处生成题目，带A/B/C/D四个选项，每个选项单独一行）
# A. 
# B. 
# C. 
# D. 
# ####题目结束####
# """

# def extract_question(text):
#     # 提取####题目开始####和####题目结束####之间的内容
#     start = text.find("####题目开始####")
#     end = text.find("####题目结束####")
#     if start != -1 and end != -1:
#         return text[start+len("####题目开始####"):end].strip()
#     else:
#         return None

# def generate_questions(n, examples):
#     questions = []
#     for i in range(n):
#         # 随机选一个示例
#         import random
#         example = random.choice(examples)
#         prompt = prompt_template.format(example=example)
#         output = res(prompt)
#         time.sleep(1)
#         question = extract_question(output)
#         if question:
#             questions.append(question)
#         else:
#             print(f"第{i}题生成失败，输出为：{output}")
#     return questions

# def save_to_csv(questions, filename):
#     with open(filename, 'w', encoding='utf-8', newline='') as f:
#         writer = csv.writer(f, delimiter='\t')
#         for idx, q in enumerate(questions):
#             writer.writerow([idx, idx, q])

# if __name__ == "__main__":
#     num_questions = 5
#     questions = generate_questions(num_questions, examples)
#     save_to_csv(questions, "self-instruct.csv")

import csv
import random
import time
import re
import os



# ==============================================================================
# 步骤 2: 准备您的初始种子数据集 (保持不变)
# ==============================================================================
# seed_data = [
#     "下列各项关于变更记账本位币会计处理的表述中，正确的是（      ）。\\nA.记账本位币变更日，所有者权益项目按照历史汇率折算为变更后的记账本位币\\nB.记账本位币变更日，资产负债项目按照当日的即期汇率折算为变更后的记账本位币\\nC.记账本位币变更当年年初至变更日的利润表项目按照交易发生日的即期汇率折算为变更后的记账本位币\\nD.记账本位币变更当年年初至变更日的现金流量表项目按照与交易发生日即期汇率近似的汇率折算为变更后的记账本位币",
#     "下列各项中，应在资产负债表“应付账款”项目列示的有（ ）。\\nA.“应付票据”科目所属明细科目的贷方余额\\nB.“预付账款”科目所属明细科目的贷方余额\\nC.“应付账款”科目所属明细科目的贷方余额\\nD.“应付账款”科目所属明细科目的借方余额",
#     "2×18年1月1日，甲公司从非关联方购入乙公司60%股权，能够对乙公司的财务和经营决策实施控制。除乙公司外，甲公司无其他子公司。2×18年度，乙公司按照购买日可辨认净资产公允价值为基础计算实现的本年净利润为2 400万元，无其他所有者权益变动。2×18年末，甲公司合并财务报表中少数股东权益为960万元。2×19年度，乙公司按购买日可辨认净资产公允价值为基础计算的净亏损为5 400万元，无其他所有者权益变动。2×19年末，甲公司个别财务报表中所有者权益总额为9 600万元。不考虑其他因素，下列各项关于合并财务报表列报的表述中，正确的有（　　）。\\nA.2×18年度少数股东损益为960万元\\nB.2×19年度少数股东损益为－2 160万元\\nC.2×19年12月31日少数股东权益为0\\nD.2×19年12月31日归属于母公司股东权益为7 800万元",
#     "2×20年，甲公司发生的有关交易或事项如下：（1）甲公司以其生产的产品作为奖品，奖励给20名当年度被评为优秀的生产工人。上述产品的销售价格总额为500万元，销售成本为420万元；（2）根据甲公司确定的利润分享计划，以当年度实现的利润总额为基础，计算的应支付给管理人员利润分享金额为280万元；（3）甲公司于当年起对150名管理人员实施累积带薪年休假制度，每名管理人员每年可享受7个工作日的带薪年休假，未使用的年休假只能向后结转一个日历年度，超过1年未使用的权利作废，也不能得到任何现金补偿。2×20年，有10名管理人员每人未使用带薪年休假2天，预计2×21年该10名管理人员将每人休假9天。甲公司平均每名管理人员每个工作日的工资为300元。不考虑相关税费及其他因素，下列各项关于甲公司上述职工薪酬会计处理的表述中，正确的是（　　）。\\nA.将自产的产品作为奖品发放应按420万元确认应付职工薪酬\\nB.2×20年应确认10名管理人员未使用带薪年休假费用0.6万元并计入管理费用\\nC.根据利润分享计划计算的2×20年应支付给管理人员的280万元款项应作为利润分配处理\\nD.2×20年应从工资费用中扣除已享受带薪年休假权利的140名管理人员的工资费用29.4万元"
#     "2018年1月1日，甲公司为乙公司的1 000万元债务中的60％提供担保。2018年6月1日，乙公司因无力偿还到期债务被债权人起诉。至2018年12月31日，法院尚未作出判决。经咨询律师，甲公司认为有60％的可能性需要承担全部保证责任并承担诉讼费用４万元。2019年2月10日，法院作出判决，甲公司需要承担全部的担保责任和诉讼费用。甲公司表示服从法院判决，于当日履行了担保责任，并支付了4万元的诉讼费用。甲公司2018年财务报告于2019年2月20日经董事会批准报出。不考虑其他因素，下列关于甲公司对该事项的会计处理中，正确的有（　　）。\\nA.在2019年实际支付担保款项时才需进行会计处理\\nB.在2018年的利润表中将预计的诉讼费用4万元确认为管理费用\\nC.在2018年的利润表中确认营业外支出600万元\\nD.在2018年的财务报表附注中披露或有负债600万元",
#     "甲公司2018年1月1日，从银行借入100万元的短期借款，以满足季节性生产对资金的需求，该借款期限为6个月，年利率为3.6%（与实际利率一致），月末计息，分季付息。下列各项中，该公司会计处理正确的是（      ）。\\nA.2018年1月31日计提利息时，借记“财务费用”0.3  贷记“短期借款”0.3\\nB.2018年6月30日计提利息时，借记“财务费用”0.9  贷记“应付利息”0.9\\nC.2018年1月1日从银行借入短期借款时，借记“银行存款”100  贷记“短期借款”100\\nD.2018年1月31日，计提利息时，借记“管理费用”0.3  贷记“应付利息”0.3",
#     "20×1年度，甲公司发生的相关交易或事项如下：(1)4月1日，甲公司收到先征后返的增值税600万元。(2)6月30日，甲公司以8 000万元的拍卖价格取得一栋已达到预定可使用状态的房屋，该房屋的预计使用年限为50年。当地政府为鼓励甲公司在当地投资，于同日拨付甲公司2 000万元，作为对甲公司取得房屋的补偿。(3)8月1日，甲公司收到政府拨付的300万元款项，用于正在建造的新型设备。至12月31日，该设备仍处于建造过程中。(4)10月10日，甲公司收到当地政府追加的投资500万元。甲公司按年限平均法对固定资产计提折旧。已知甲公司对取得的政府补助采用总额法核算。下列各项关于甲公司上述交易或事项会计处理的表述中，正确的是(　　)。\\nA.收到政府拨付的房屋补助款应冲减所取得房屋的成本\\nB.收到先征后返的增值税应确认为与收益相关的政府补助\\nC.收到政府追加的投资应确认为递延收益并分期计入损益\\nD.收到政府拨付用于新型设备的款项应冲减设备的建造成本"
#     "下列各项中，通常不属于出租人应当分类为融资租赁的情形是（　　）。\\nA.在租赁期届满时，租赁资产的所有权转移给承租人\\nB.承租人有购买租赁资产的选择权，且购买价预计远低于将行使购买选择权时租赁资产的公允价值\\nC.租赁期占租赁资产使用寿命的80％以上\\nD.在租赁开始日，租赁收款额的现值相当于租赁资产的公允价值的75％以上"
# ]
def extract_questions_from_csv(csv_file):
    seed_data = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        
        for row in reader:
            if len(row) >= 3:  # 确保行有足够列
                # 提取问题部分（第三列）
                full_text = row[2]
                
                # 查找"问题："的位置
                question_start = full_text.find("问题：")
                
                if question_start != -1:
                    # 提取"问题："之后的内容
                    question = full_text[question_start + 3:].strip()
                    seed_data.append(question)
                else:
                    # 如果没有"问题："标记，直接使用整个文本
                    seed_data.append(full_text.strip())
    
    return seed_data

# 使用示例
csv_file = "input.csv"  # 替换为你的CSV文件路径
seed_data = extract_questions_from_csv(csv_file)


def create_prompt(examples: list) -> str:
    """
    根据随机抽取的示例，构建高质量的Prompt。
    """
    # 将示例格式化，注意这里的示例已经是单行带\n的格式
    formatted_examples = ""
    for i, q in enumerate(examples):
        # 在Prompt中展示的示例也应该是理想的格式
        formatted_examples += f"--- 示例问题 {i+1} ---\n{q}\n\n"

    # 这是核心的 "meta-instruction"
    prompt = f"""
你是一位顶级的金融与会计领域的出题专家，精通CPA、CFA等专业考试的命题规律。你的任务是根据我提供的几个示例，创作一个高质量的金融领域问题。

请严格遵守以下所有要求：
1.  **问题类型**: 创作一道金融领域常见的问题。问题应围绕会计、税法、公司金融、投资学等核心主题。
2.  **包含上下文**: 问题描述中必须包含解决问题所需的全部额外信息，如背景知识、关键概念定义、计算规则、具体数据（如利率、税率、金额、日期等）。确保问题本身是自包含的。
3.  **唯一确定答案**: 问题必须有且仅有一个逻辑上或计算上明确的、唯一的正确答案。答案不能模棱两可。
4.  **难度适中**: 问题的难度应设计为金融专业学生或从业者需要思考和计算才能解决，但不是无法解答的难题。
5.  **原创性**: 生成的问题必与我提供的示例在主题、数字或逻辑上有所不同，但风格和难度保持一致。不要直接复制或简单改写示例。不要直接复制或简单改写示例。
6.  **分隔符**: 在四个选项结束后，另起一行，使用 `####` 作为唯一的分隔符。在 `####` 之后，另起一行，只写出正确答案的字母和解析。
7.  **【最重要】输出格式**:
    - 从问题描述到最后一个选项的全部内容，必须合并成一个**单行字符串**。
    - 所有的换行必须用显式的 `\\n` 字符来表示。
    - **绝对不要**包含任何Markdown标记（如 `**` 或 `---`）或任何多余的说明性文字（如“好的，这是一个...”或“问题描述”）。直接开始输出问题正文。

以下是一些符合要求的示例，请学习它们的风格和结构：

{formatted_examples}

现在，请根据以上所有要求，创作一个全新的问题。
"""
    return prompt

def parse_llm_output(response: str) -> str or None:
    """
    从模型的完整输出中解析出 "问题+选项" 部分的原始文本。
    """
    if '####' not in response:
        print("[警告] 模型输出格式不正确，缺少 '####' 分隔符。")
        return None
    
    question_part = response.split('####')[0]
    return question_part

def clean_and_format_question(text: str) -> str or None:
    """
    对提取出的问题文本进行清洗和格式化，以满足最终要求。
    """
    # 1. 移除可能存在的前导说明性文字，如 "好的，这是一个问题：" 或 "**问题描述**" 等
    # 使用正则表达式，非贪婪地匹配从开头到 "问题描述" 或第一个换行符（如果它看起来像引言）
    text = re.sub(r'^\s*.*?(问题描述|题目：|以下是|为你创作)\s*', '', text, count=1, flags=re.IGNORECASE)
    
    # 2. 移除Markdown的粗体标记 `**`
    text = text.replace('**', '')

    # 3. 按行分割，并去除每行前后的空白字符
    lines = [line.strip() for line in text.splitlines()]
    
    # 4. 过滤掉空行
    non_empty_lines = [line for line in lines if line]
    
    if not non_empty_lines:
        print(f"[警告] 清洗后没有有效内容。")
        return None

    # 5. 使用 `\n` 将所有有效行连接成一个单行字符串
    final_question = r'\n'.join(non_empty_lines)
    
    # 6. 最终验证，确保问题看起来是合理的
    if len(final_question) < 50 or not any(opt in final_question for opt in ['A.', 'B.', 'C.', 'D.']):
        print(f"[警告] 清洗后的问题部分似乎不完整或格式错误: {final_question[:100]}...")
        return None
        
    return final_question


# ==============================================================================
# 步骤 4: 主执行循环 (已更新)
# ==============================================================================
def main():
    # --- 配置参数 ---
    num_questions_to_generate = 2000  # 增加生成数量以更好地测试
    output_filename = "self-instruct2.csv"  # 使用 .tsv 扩展名更准确
    # 从种子池中随机抽取k个作为in-context learning的示例
    num_examples_for_prompt = 3
    
    # --- 初始化 ---
    # 使用 all_questions 作为动态更新的指令池
    all_questions = list(seed_data)
    generated_questions = []
    
    print(f"初始化完成，已有 {len(all_questions)} 条种子问题。")
    print(f"目标：生成 {num_questions_to_generate} 条新问题。")
    
    # 提前打开文件，使用追加模式
    try:
        f = open(output_filename, 'w', newline='', encoding='utf-8')
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        
        # 先写入已有的种子问题
        for i, question_text in enumerate(all_questions):
            writer.writerow([i, i, question_text])
            f.flush()  # 确保立即写入磁盘
        
        # --- 生成循环 ---
        while len(generated_questions) < num_questions_to_generate:
            print(f"\n--- 开始生成第 {len(generated_questions) + 1} 条新问题 ---")
            
            # 1. 从当前所有问题池中随机抽取示例
            examples = random.sample(all_questions, min(len(all_questions), num_examples_for_prompt))
            
            # 2. 创建Prompt
            prompt = create_prompt(examples)
            
            # 3. 调用大模型API
            try:
                llm_response = res(prompt)
                # 4. 解析原始问题部分
                raw_question_part = parse_llm_output(llm_response)
                
                if raw_question_part:
                    # 5. 清洗和格式化问题
                    cleaned_question = clean_and_format_question(raw_question_part)
                    
                    if cleaned_question:
                        # 6. 如果成功，将新问题加入池中并立即写入文件
                        generated_questions.append(cleaned_question)
                        all_questions.append(cleaned_question)
                        
                        # 立即写入文件
                        current_id = len(all_questions) - 1
                        writer.writerow([current_id, current_id, cleaned_question])
                        f.flush()  # 确保立即写入磁盘
                        
                        print(f"[成功] 已生成 {len(generated_questions)}/{num_questions_to_generate} 条新问题。问题池总量: {len(all_questions)}")
                        # 打印一两条看看效果
                        if len(generated_questions) <= 2:
                            print(f"预览生成的问题: {cleaned_question[:150]}...")
                    else:
                        print("[失败] 清洗后内容不合格，本次生成失败，将重试。")
                else:
                    print("[失败] 模型输出不含分隔符，本次生成失败，将重试。")

            except Exception as e:
                print(f"[错误] 调用API或处理时发生异常: {e}")
                print("等待5秒后重试...")
                time.sleep(5)
                
            time.sleep(1)

        print(f"\n--- 生成完成！总共生成了 {len(generated_questions)} 条新问题。---")
        print(f"所有 {len(all_questions)} 条问题已实时保存到 {output_filename}")
        
    except IOError as e:
        print(f"[错误] 无法写入文件: {e}")
    finally:
        # 确保文件被正确关闭
        if 'f' in locals() and not f.closed:
            f.close()
# def main():
#     # --- 配置参数 ---
#     num_questions_to_generate = 2000 # 增加生成数量以更好地测试
#     output_filename = "self-instruct.csv" # 使用 .tsv 扩展名更准确
#     # 从种子池中随机抽取k个作为in-context learning的示例
#     num_examples_for_prompt = 4
    
#     # --- 初始化 ---
#     # 使用 all_questions 作为动态更新的指令池
#     all_questions = list(seed_data)
#     generated_questions = []
    
#     print(f"初始化完成，已有 {len(all_questions)} 条种子问题。")
#     print(f"目标：生成 {num_questions_to_generate} 条新问题。")
    
#     # --- 生成循环 ---
#     while len(generated_questions) < num_questions_to_generate:
#         print(f"\n--- 开始生成第 {len(generated_questions) + 1} 条新问题 ---")
        
#         # 1. 从当前所有问题池中随机抽取示例
#         examples = random.sample(all_questions, min(len(all_questions), num_examples_for_prompt))
        
#         # 2. 创建Prompt
#         prompt = create_prompt(examples)
        
#         # 3. 调用大模型API
#         try:
#             llm_response = res(prompt)
#             # 4. 解析原始问题部分
#             raw_question_part = parse_llm_output(llm_response)
            
#             if raw_question_part:
#                 # 5. 清洗和格式化问题
#                 cleaned_question = clean_and_format_question(raw_question_part)
                
#                 if cleaned_question:
#                     # 6. 如果成功，将新问题加入池中
#                     generated_questions.append(cleaned_question)
#                     all_questions.append(cleaned_question)
#                     print(f"[成功] 已生成 {len(generated_questions)}/{num_questions_to_generate} 条新问题。问题池总量: {len(all_questions)}")
#                     # 打印一两条看看效果
#                     if len(generated_questions) <= 2:
#                         print(f"预览生成的问题: {cleaned_question[:150]}...")
#                 else:
#                     print("[失败] 清洗后内容不合格，本次生成失败，将重试。")
#             else:
#                 print("[失败] 模型输出不含分隔符，本次生成失败，将重试。")

#         except Exception as e:
#             print(f"[错误] 调用API或处理时发生异常: {e}")
#             print("等待5秒后重试...")
#             time.sleep(5)
            
#         time.sleep(1) 

#     print(f"\n--- 生成完成！总共生成了 {len(generated_questions)} 条新问题。---")
    
#     # --- 步骤 5: 保存到文件 ---
#     print(f"正在将所有 {len(all_questions)} 条问题保存到 {output_filename}...")
    
#     try:
#         # 使用 tsv 格式，即制表符分隔
#         with open(output_filename, 'w', newline='', encoding='utf-8') as f:
#             writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            
#             for i, question_text in enumerate(all_questions):
#                 # 写入三列：ID, ID, 问题文本
#                 writer.writerow([i, i, question_text])
                
#         print(f"文件 {output_filename} 保存成功！")
        
#     except IOError as e:
#         print(f"[错误] 无法写入文件: {e}")


if __name__ == "__main__":
    main()
