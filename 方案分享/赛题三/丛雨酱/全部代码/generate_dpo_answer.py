import pandas as pd
import json
import re
import time
from typing import List, Dict, Tuple
import openpyxl
from openpyxl import Workbook
import os
from datetime import datetime
import pandas as pd
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class DeepSeekAPIProcessor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    def call_deepseek_chat_for_analysis(self, question: str, answer: str) -> str:
        """调用DeepSeek-Chat补充解题过程"""
        prompt = f"""
{question}

该题目的正确答案：{answer}

根据已知的答案，对原问题以及问题对应的四个选项进行分析：

问题分析：
[分析题目的关键信息、涉及的知识点、解题思路等，不得超过150字]

选项分析：
[如果是选择题，分析各个选项的正确性；如果是计算题，分析计算步骤]
[每个选项的分析非必要不得超过100字]

注意：
- 保持推理过程尽量精简
- 只保留必要的推理和计算步骤
- 推理过程清晰完整，不得缺少中间步骤
"""
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",  # DeepSeek-Chat模型
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=900  # 设置超时时间为900秒
            )
            
            content = response.choices[0].message.content
            return content
            
        except Exception as e:
            print(f"调用DeepSeek-Chat API失败: {e}")
            return ""  # 失败时返回空字符串

class FinancialDataProcessor:
    def __init__(self, api_key: str, max_workers: int = 5):
        self.api_processor = DeepSeekAPIProcessor(api_key)
        self.processed_count = 0
        self.total_count = 0
        self.answers_list = []  # 添加答案列表属性
        self.max_workers = max_workers  # 并发线程数
        self.lock = threading.Lock()  # 线程锁，用于保护共享变量
        self.results = []  # 存储结果的线程安全列表
    
    def _parse_answer_file(self, answer_file: str) -> List[str]:
        """解析答案文件，将分组格式转换为按索引访问的答案列表"""
        answers = []
        
        with open(answer_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ':' in line:
                    # 分割范围和答案部分
                    range_part, answers_part = line.split(':', 1)
                    # 提取答案，去除空格
                    line_answers = [ans.strip() for ans in answers_part.split(',')]
                    answers.extend(line_answers)
        
        return answers
    
    def _process_single_question(self, i: int, question_row, answer: str) -> Dict:
        """处理单个问题的函数，用于并发执行"""
        try:
            question_id = question_row.iloc[0] if len(question_row) > 0 else i
            
            # 获取完整问题文本
            if len(question_row) > 2:
                question = str(question_row.iloc[2])  # 确保转换为字符串
            else:
                question = str(question_row.iloc[-1])  # 如果没有第三列，使用最后一列
            
            print(f"\n处理问题 {i+1}: ID={question_id}")
            print(f"答案: {answer}")
            
            # 调用DeepSeek-Chat补充解题过程
            print(f"线程 {threading.current_thread().name} 调用DeepSeek-Chat...")
            analysis_content = self.api_processor.call_deepseek_chat_for_analysis(question, answer)
            
            if not analysis_content:
                print(f"问题 {i+1} DeepSeek-Chat调用失败")
                return None
            
            # 解析分析内容
            problem_analysis, option_analysis, solution_process = self._parse_analysis_content(analysis_content)
            
            # 准备结果数据
            result = {
                'index': i,
                'question_id': question_id,
                'question': question,
                'answer': answer,
                'problem_analysis': problem_analysis,
                'option_analysis': option_analysis,
                'solution_process': solution_process,
                'analysis_content': analysis_content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 线程安全地更新计数器
            with self.lock:
                self.processed_count += 1
                print(f"✓ 问题 {i+1} 处理完成 (已完成: {self.processed_count})")
            
            # API调用间隔（避免过于频繁的请求）
            time.sleep(1)
            
            return result
            
        except Exception as e:
            print(f"处理问题 {i+1} 时出错: {e}")
            return None
    
    def process_csv_data_with_answers(self, csv_file: str, answer_file: str, output_excel: str, output_json: str, 
                    start_index: int = 0, end_index: int = None, batch_size: int = 10):
        """处理CSV数据的主函数，使用并发处理
        
        Args:
            csv_file: 问题CSV文件路径
            answer_file: 答案文件路径（支持txt格式）
            output_excel: Excel输出文件路径
            output_json: JSON输出文件路径
            start_index: 开始处理的问题索引（默认0）
            end_index: 结束处理的问题索引（默认None，处理到文件末尾）
            batch_size: 批处理大小（当end_index为None时使用）
        """
        print(f"开始并发处理CSV文件: {csv_file}")
        print(f"答案文件: {answer_file}")
        print(f"并发线程数: {self.max_workers}")
        
        # 读取问题CSV文件 - 修复：添加header=None参数
        df_questions = pd.read_csv(csv_file, sep='\t', header=None)
        
        # 解析答案文件
        self.answers_list = self._parse_answer_file(answer_file)
        print(f"成功解析 {len(self.answers_list)} 个答案")
        
        self.total_count = len(df_questions)
        
        # 确定实际的结束索引
        if end_index is None:
            actual_end_index = min(start_index + batch_size, self.total_count)
            print(f"总共{self.total_count}个问题，处理第{start_index+1}到第{actual_end_index}个问题")
        else:
            actual_end_index = min(end_index, self.total_count)
            print(f"总共{self.total_count}个问题，处理第{start_index+1}到第{actual_end_index}个问题")
        
        # 准备任务列表
        tasks = []
        for i in range(start_index, actual_end_index):
            if i < len(self.answers_list):
                question_row = df_questions.iloc[i]
                answer = self.answers_list[i]
                tasks.append((i, question_row, answer))
            else:
                print(f"警告：无法找到问题 {i+1} 对应的答案，跳过")
        
        print(f"准备并发处理 {len(tasks)} 个任务...")
        
        # 使用线程池并发处理
        self.results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self._process_single_question, i, question_row, answer): (i, question_row, answer)
                for i, question_row, answer in tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                result = future.result()
                if result is not None:
                    self.results.append(result)
        
        # 按索引排序结果
        self.results.sort(key=lambda x: x['index'])
        
        # 保存结果到Excel和JSON
        self._save_results_to_files(output_excel, output_json)
        
        print(f"\n并发处理完成！成功处理 {self.processed_count} 个问题")
        
        return [{
            "question": result['question'],
            "answer": result['answer'],
            "problem_analysis": result['problem_analysis'],
            "option_analysis": result['option_analysis'],
            "solution_process": result['solution_process'],
            "full_analysis": result['analysis_content']
        } for result in self.results]
    
    def _save_results_to_files(self, output_excel: str, output_json: str):
        """保存结果到Excel和JSON文件"""
        # 保存到Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "解题过程分析结果"
        ws.append(["问题ID", "原问题", "正确答案", "问题分析", "选项分析", "解题过程", "完整分析内容", "处理时间"])
        
        for result in self.results:
            # 清理完整分析内容中的 ### 符号
            cleaned_analysis = re.sub(r'###\s*', '', result['analysis_content'])
            
            ws.append([
                result['question_id'],
                result['question'],
                result['answer'],
                result['problem_analysis'],
                result['option_analysis'],
                result['solution_process'],
                cleaned_analysis,  # 使用清理后的内容
                result['timestamp']
            ])
        
        wb.save(output_excel)
        print(f"Excel结果已保存到: {output_excel}")
        
        # 保存到JSON
        json_data = [{
            "question": result['question'],
            "answer": result['answer'],
            "problem_analysis": result['problem_analysis'],
            "option_analysis": result['option_analysis'],
            "solution_process": result['solution_process'],
            "full_analysis": re.sub(r'###\s*', '', result['analysis_content'])  # 清理后的内容
        } for result in self.results]
        
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"JSON数据已保存到: {output_json}")
    
    def _parse_analysis_content(self, content: str) -> Tuple[str, str, str]:
        """解析分析内容，分离问题分析、选项分析和解题过程"""
        problem_analysis = ""
        option_analysis = ""
        solution_process = ""
        
        # 使用正则表达式分离不同部分
        problem_pattern = r'问题分析[：:]\s*([\s\S]*?)(?=选项分析|解题过程|$)'
        option_pattern = r'选项分析[：:]\s*([\s\S]*?)(?=解题过程|$)'
        solution_pattern = r'解题过程[：:]\s*([\s\S]*?)$'
        
        problem_match = re.search(problem_pattern, content)
        if problem_match:
            problem_analysis = problem_match.group(1).strip()
        
        option_match = re.search(option_pattern, content)
        if option_match:
            option_analysis = option_match.group(1).strip()
        
        solution_match = re.search(solution_pattern, content)
        if solution_match:
            solution_process = solution_match.group(1).strip()
        
        return problem_analysis, option_analysis, solution_process

# 使用示例
def main():
    # 配置API密钥
    API_KEY = "none"  # 🔧 请替换为您的API密钥
    
    # 文件路径
    CSV_FILE = "input.csv"
    ANSWER_FILE = "final_result_txt.txt"
    EXCEL_OUTPUT = "answer_results.xlsx"
    JSON_OUTPUT = "answer_data.json"
    
    # 创建处理器（设置并发线程数为5）
    processor = FinancialDataProcessor(API_KEY, max_workers=5)
    
    # 处理数据
    processor.process_csv_data_with_answers(
        csv_file=CSV_FILE,
        answer_file=ANSWER_FILE,
        output_excel=EXCEL_OUTPUT,
        output_json=JSON_OUTPUT,
        start_index=0,
        end_index= 100
    )

if __name__ == "__main__":
    main()