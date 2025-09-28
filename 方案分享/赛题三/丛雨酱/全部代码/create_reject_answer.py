import pandas as pd
import re
from typing import Dict, List, Set
import json
import time
import concurrent.futures
from threading import Lock
import os

try:
    from openai import OpenAI
except ImportError:
    print("错误: 请安装 openai 库: pip install openai")
    exit(1)


class DeepSeekAPIProcessor:
    def __init__(self, api_key: str = "none"):
        self.api_key = api_key
        try:
            self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        except Exception as e:
            print(f"初始化API客户端失败: {e}")
            self.client = None
        self.lock = Lock()
    
    def call_deepseek_chat_for_analysis(self, question: str, answer: str, attempt: int = 1) -> str:
        """调用DeepSeek Chat API进行问题分析，生成更详细的回答"""
        
        if self.client is None:
            return f"API客户端未初始化，无法生成回答（尝试 {attempt}）"
        
        prompt = f"""
{question}

该题目的正确答案：{answer}

根据已知的答案，对原问题以及问题对应的四个选项进行分析：

问题分析：
[分析题目的关键信息、涉及的知识点、解题思路等]

选项分析：
[如果是选择题，分析各个选项的正确性；如果是计算题，分析计算步骤]

注意事项：
1. 选项和问题的分析尽量内容充实完整，任何步骤都不能省略，最终的文本内容至少要超过2000字
2. 详细说明其他选项的错误之处，详细说明一切
3. 最终答案请用 $\\boxed{{答案}}$ 的形式输出
4. 请提供不同的分析角度和思路（第{attempt}次生成）
"""
        
        try:
            with self.lock:
                time.sleep(1)
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=min(0.7 + (attempt * 0.1), 1.0),  # 限制温度最大值
                max_tokens=2000
            )
            
            return response.choices[0].message.content
                
        except Exception as e:
            return f"API调用异常（尝试 {attempt}）: {str(e)}"

def parse_correct_answers(file_path: str) -> Dict[int, str]:
    """解析正确答案文件"""
    answers = {}
    
    if not os.path.exists(file_path):
        print(f"警告: 正确答案文件 {file_path} 不存在")
        return answers
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        parts = line.split(': ')
                        if len(parts) == 2:
                            range_part = parts[0]
                            answers_part = parts[1]
                            
                            start, end = map(int, range_part.split('-'))
                            answer_list = [ans.strip() for ans in answers_part.split(', ')]
                            
                            for i, answer in enumerate(answer_list):
                                question_id = start + i
                                answers[question_id] = answer
                    except Exception as e:
                        print(f"解析第 {line_num} 行时出错: {e}")
                        continue
    except Exception as e:
        print(f"读取正确答案文件时出错: {e}")
    
    return answers

def extract_final_answer(content: str) -> str:
    """从回答内容中提取最终答案"""
    if not content or pd.isna(content):
        return ""
    
    content = str(content)
    patterns = [
        r'### 最终答案[：:]*\s*([A-D]+)',
        r'最终答案[：:]*\s*([A-D]+)',
        r'答案[：:]*\s*([A-D]+)',
        r'\$\\boxed\{([A-D]+)\}',
        r'\$\\boxed\{([A-D]+)\}\$',
        r'\$\s*\\boxed\{([A-D]+)\}\s*\$',
        r'\$\$\s*\\boxed\{([A-D]+)\}\s*\$\$',
        r'选择[：:]*\s*([A-D]+)',
        r'正确答案[：:]*\s*([A-D]+)',
        r'答案是[：:]*\s*([A-D]+)',
        r'选项\s*([A-D]+)',
        r'([A-D]+)\s*是正确的',
        r'应该选择\s*([A-D]+)',
        r'因此.*?([A-D]+)',
        r'所以.*?([A-D]+)',
    ]
    
    for pattern in patterns:
        try:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                return matches[-1].upper()
        except Exception:
            continue
    
    return ""

def create_standardized_dataset(csv_file: str, correct_answers_file: str, input_csv: str, output_file: str):
    """创建标准化的数据集，确保每个问题都有5条记录，格式统一"""
    
    # 检查文件是否存在
    required_files = [csv_file, input_csv]
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"错误: 必需文件 {file_path} 不存在")
            return
    
    # 解析正确答案
    correct_answers = parse_correct_answers(correct_answers_file)
    print(f"加载了 {len(correct_answers)} 个正确答案")
    
    # 读取input.csv获取所有问题
    try:
        input_df = pd.read_csv(input_csv, sep='\t', header=None)
        questions = {}
        for _, row in input_df.iterrows():
            try:
                question_id = int(row[0])
                question_content = str(row[1]) if len(row) > 1 else ""
                questions[question_id] = question_content
            except (ValueError, IndexError) as e:
                print(f"跳过无效行: {row.tolist()}, 错误: {e}")
                continue
    except Exception as e:
        print(f"读取 {input_csv} 时出错: {e}")
        return
    
    print(f"需要处理 {len(questions)} 个问题")
    
    # 读取现有的CSV文件，筛选正确但冗长的答案
    try:
        df = pd.read_csv(csv_file)
        print(f"原始数据: {len(df)} 行")
    except Exception as e:
        print(f"读取 {csv_file} 时出错: {e}")
        return
    
    # 按问题ID分组收集现有的有效回答
    existing_responses = {}
    
    for _, row in df.iterrows():
        try:
            question_id = int(row.iloc[0])
            response_content = str(row.iloc[2]) if len(row) > 2 else ""
            
            # 检查是否为有效回答（非nan且内容充实）
            if (response_content and 
                response_content != 'nan' and 
                not pd.isna(response_content) and 
                len(response_content.strip()) > 100):  # 最少100字符
                
                # 如果有正确答案，检查答案是否正确
                if question_id in correct_answers:
                    expected_answer = correct_answers[question_id]
                    extracted_answer = extract_final_answer(response_content)
                    
                    # 只保留答案正确的回答
                    if extracted_answer == expected_answer:
                        if question_id not in existing_responses:
                            existing_responses[question_id] = []
                        existing_responses[question_id].append(response_content)
                else:
                    # 对于没有正确答案的问题，保留内容充实的回答
                    if question_id not in existing_responses:
                        existing_responses[question_id] = []
                    existing_responses[question_id].append(response_content)
        except (ValueError, IndexError) as e:
            print(f"跳过无效行: {row.tolist()}, 错误: {e}")
            continue
    
    # 生成标准化数据集
    api_processor = DeepSeekAPIProcessor()
    final_data = []
    
    for question_id in sorted(questions.keys()):
        question_content = questions[question_id]
        correct_answer = correct_answers.get(question_id, "未知")
        
        # 获取现有的有效回答
        current_responses = existing_responses.get(question_id, [])
        
        # 确保每个问题都有5条不同的回答
        responses_needed = 5
        
        # 如果现有回答超过5条，只取前5条
        if len(current_responses) >= responses_needed:
            selected_responses = current_responses[:responses_needed]
        else:
            # 需要生成额外的回答
            selected_responses = current_responses.copy()
            additional_needed = responses_needed - len(current_responses)
            
            print(f"为问题 {question_id} 生成 {additional_needed} 个额外回答...")
            
            # 生成额外回答
            for attempt in range(additional_needed):
                try:
                    new_response = api_processor.call_deepseek_chat_for_analysis(
                        question_content, correct_answer, attempt + len(current_responses) + 1
                    )
                    selected_responses.append(new_response)
                    time.sleep(1)  # 避免API限制
                except Exception as e:
                    print(f"生成问题 {question_id} 的第 {attempt+1} 个额外回答时出错: {e}")
                    selected_responses.append(f"生成失败: {str(e)}")
        
        # 添加到最终数据集，确保格式统一
        for seq_id, response in enumerate(selected_responses[:5]):
            final_data.append([
                question_id,
                seq_id,  # 0-4的序号
                response
            ])
        
        print(f"问题 {question_id} 完成，共 {len(selected_responses[:5])} 条回答")
    
    # 保存标准化数据集
    try:
        result_df = pd.DataFrame(final_data, columns=['question_id', 'sequence_id', 'response_content'])
        result_df.to_csv(output_file, index=False, header=False)  # 不保存列名
        
        print(f"\n标准化数据集已保存到 {output_file}")
        print(f"总计 {len(result_df)} 行数据")
        print(f"涵盖 {len(questions)} 个问题，每个问题5条回答")
        
        # 验证数据质量
        question_counts = result_df['question_id'].value_counts()
        invalid_questions = question_counts[question_counts != 5]
        
        if len(invalid_questions) > 0:
            print(f"警告: 以下问题的回答数量不是5条: {invalid_questions.to_dict()}")
        else:
            print("✓ 所有问题都有正确的5条回答")
            
    except Exception as e:
        print(f"保存文件时出错: {e}")

def main():
    csv_file = "output0707.csv"
    correct_answers_file = "final_result_txt.txt"
    output_file = "filtered_correct_answers.csv"
    input_csv = "input.csv"
    
    print("开始创建标准化数据集...")
    
    try:
        create_standardized_dataset(csv_file, correct_answers_file, input_csv, output_file)
        print("\n处理完成!")
    except Exception as e:
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()