import pandas as pd
import json
import re
from typing import Dict, List, Any

def parse_correct_answers(file_path: str) -> Dict[int, str]:
    """解析正确答案文件"""
    answers = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                # 解析格式：0-4: A, BCD, C, ABC, B
                parts = line.split(': ')
                if len(parts) == 2:
                    range_part = parts[0]
                    answers_part = parts[1]
                    
                    # 解析范围
                    start, end = map(int, range_part.split('-'))
                    answer_list = [ans.strip() for ans in answers_part.split(', ')]
                    
                    # 分配答案
                    for i, answer in enumerate(answer_list):
                        question_id = start + i
                        answers[question_id] = answer
    return answers

def load_questions(file_path: str) -> Dict[int, str]:
    """从input.csv加载问题"""
    df = pd.read_csv(file_path, sep='\t', header=None)
    questions = {}
    for _, row in df.iterrows():
        question_id = int(row[0])
        question_content = row[2]  # 第三列是问题内容
        questions[question_id] = question_content
    return questions

def load_rejected_responses(file_path: str) -> Dict[int, List[str]]:
    """从filtered_correct_answers.csv加载rejected responses"""
    df = pd.read_csv(file_path)
    rejected_responses = {}
    
    for _, row in df.iterrows():
        question_id = int(row[0])  # 改为 int 类型，与其他函数保持一致
        response_content = str(row[2])  # 第三列是回答内容
        
        # 过滤掉nan值
        if response_content == 'nan' or pd.isna(response_content):
            continue
            
        if question_id not in rejected_responses:
            rejected_responses[question_id] = []
        rejected_responses[question_id].append(response_content)
    
    return rejected_responses

def load_analysis_content(file_path: str) -> Dict[int, str]:
    """从answer_results.xlsx加载完整分析内容"""
    df = pd.read_excel(file_path)
    analysis_content = {}
    
    for _, row in df.iterrows():
        question_id = int(row[0])  # 问题ID
        content = str(row[6])      # 完整分析内容（第7列，索引为6）
        analysis_content[question_id] = content
    
    return analysis_content

def create_dpo_dataset(questions: Dict[int, str], 
                      correct_answers: Dict[int, str], 
                      rejected_responses: Dict[int, List[str]],
                      analysis_content: Dict[int, str]) -> List[Dict[str, Any]]:
    """创建DPO格式的数据集"""
    dataset = []
    
    # 定义系统提示词
    system_prompt = ""
    user_prompt_prefix = "请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，你要给出解决问题的思考过程和最终答案。你要首先在头脑中思考推理过程，然后向用户提供答案。最后，答案要用 $\\boxed{答案}$的形式输出。\\n问题：\\n"
    
    for question_id in questions:
        if question_id in correct_answers and question_id in rejected_responses and question_id in analysis_content:
            question = questions[question_id]
            correct_answer = correct_answers[question_id]
            full_analysis = analysis_content[question_id]
            
            # 只取前5个有效的rejected responses
            valid_rejected_responses = [resp for resp in rejected_responses[question_id] 
                                      if resp != 'nan' and not pd.isna(resp)]
            
            # 限制为最多5个
            selected_rejected_responses = valid_rejected_responses[:5]
            
            # 为每个选中的rejected response创建一个数据条目
            for rejected_response in selected_rejected_responses:
                data_entry = {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": question
                        },
                        {
                            "role": "assistant", 
                            "content": f"<think>\n{full_analysis}\n</think>\n$\\boxed{{{correct_answer}}}$"
                        }
                    ],
                    "rejected_response": rejected_response
                }
                dataset.append(data_entry)
    
    return dataset

def main():
    # 文件路径
    input_csv_path = "input.csv"
    correct_answers_path = "final_result_txt.txt"
    rejected_responses_path = "filtered_correct_answers.csv"  
    analysis_excel_path = "answer_results.xlsx"
    output_path = "dpo_dataset_combined.json"
    
    print("正在加载数据...")
    
    # 加载数据
    questions = load_questions(input_csv_path)
    correct_answers = parse_correct_answers(correct_answers_path)
    rejected_responses = load_rejected_responses(rejected_responses_path)
    analysis_content = load_analysis_content(analysis_excel_path)  # 新增：加载分析内容
    
    print(f"加载了 {len(questions)} 个问题")
    print(f"加载了 {len(correct_answers)} 个正确答案")
    print(f"加载了 {len(rejected_responses)} 个问题的rejected responses")
    print(f"加载了 {len(analysis_content)} 个问题的分析内容")  # 新增
    
    # 检查每个问题的有效rejected responses数量
    min_rejected_count = float('inf')
    max_rejected_count = 0
    total_rejected = 0
    questions_with_insufficient_responses = []
    
    for question_id, responses in rejected_responses.items():
        # 过滤掉nan值
        valid_responses = [resp for resp in responses if resp != 'nan' and not pd.isna(resp)]
        count = len(valid_responses)
        
        if count > 0:
            min_rejected_count = min(min_rejected_count, count)
            max_rejected_count = max(max_rejected_count, count)
            total_rejected += min(count, 5)  # 每个问题最多取5个
            
            if count < 5:
                questions_with_insufficient_responses.append(question_id)
    
    print(f"每个问题的有效rejected responses数量: 最少 {min_rejected_count}, 最多 {max_rejected_count}")
    print(f"总共将使用 {total_rejected} 个rejected responses（每个问题最多5个）")
    
    if questions_with_insufficient_responses:
        print(f"警告: {len(questions_with_insufficient_responses)} 个问题的有效rejected数量少于5个")
    
    # 创建数据集
    print("正在创建DPO数据集...")
    dataset = create_dpo_dataset(questions, correct_answers, rejected_responses, analysis_content)  # 新增参数
    
    print(f"创建了 {len(dataset)} 个数据条目")
    
    # 保存数据集
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"数据集已保存到 {output_path}")
    
    # 统计信息
    question_counts = {}
    for question_id in rejected_responses.keys():  # 直接从rejected_responses的键获取question_id
        if question_id in questions and question_id in correct_answers:
            # 计算这个问题有多少个有效的rejected responses（最多5个）
            valid_responses = [resp for resp in rejected_responses[question_id] 
                             if resp != 'nan' and not pd.isna(resp)]
            count = min(len(valid_responses), 5)
            if count > 0:
                question_counts[question_id] = count
    
    print(f"\n统计信息:")
    print(f"涉及问题数量: {len(question_counts)}")
    if question_counts:
        avg_rejected = sum(question_counts.values()) / len(question_counts)
        print(f"平均每个问题的rejected数量: {avg_rejected:.2f}")
        
        # 统计每个问题实际使用的rejected数量分布
        count_distribution = {}
        for count in question_counts.values():
            count_distribution[count] = count_distribution.get(count, 0) + 1
        
        print(f"rejected数量分布:")
        for count, num_questions in sorted(count_distribution.items()):
            print(f"  {count}个rejected: {num_questions}个问题")

if __name__ == "__main__":
    main()