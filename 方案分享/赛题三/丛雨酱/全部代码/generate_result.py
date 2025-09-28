#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import csv
import threading
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dataclasses import dataclass


@dataclass
class APIConfiguration:
    """API配置数据类，用于存储API相关的配置信息"""
    endpoint_url: str = 'http://127.0.0.1:11230/v1/chat/completions'
    authorization_token: str = ""  # 修复：空字符串而不是"None"
    model_name: str = "Qwen3-4b"
    system_prompt: str = "你是一位金融领域专家，尤其擅长分析金融问题和生成简明扼要的回答。你惜字如金，回复问题会尽量精简但不缺少重要分析，严格遵守提问人的需要格式。"
    temperature: float = 0.6
    timeout_seconds: int = 500
    max_retry_attempts: int = 5
    max_concurrent_workers: int = 100


class FinancialQuestionProcessor:
    """
    金融问题处理器类
    负责处理金融领域的问答任务，包括API调用、答案生成、
    并发处理和结果管理等功能。
    """
    
    def __init__(self, config: APIConfiguration):
        """
        初始化金融问题处理器
        
        Args:
            config (APIConfiguration): API配置对象
        """
        self.config = config
        self._thread_lock = threading.Lock()
        self._session = requests.Session()  # 使用会话复用连接
        
    def _construct_request_payload(self, question_text: str) -> Dict:
        """
        构建API请求的负载数据
        
        Args:
            question_text (str): 问题文本内容
            
        Returns:
            Dict: 格式化的请求数据字典
        """
        return {
            "model": self.config.model_name,
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": question_text}
            ],
            "temperature": self.config.temperature,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": True}}
        }
    
    def _prepare_request_headers(self) -> Dict[str, str]:
        """
        准备HTTP请求头
        
        Returns:
            Dict[str, str]: 包含认证信息的请求头字典
        """
        return {
            "Authorization": f"Bearer {self.config.authorization_token}",
            "Content-Type": "application/json",
        }
    
    def invoke_ai_model(self, question_content: str) -> Optional[str]:
        """
        调用AI模型生成答案
        
        Args:
            question_content (str): 输入的问题内容
            
        Returns:
            Optional[str]: 生成的答案文本，失败时返回None
        """
        headers = self._prepare_request_headers()
        payload = self._construct_request_payload(question_content)
        
        try:
            response = self._session.post(
                self.config.endpoint_url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # 增强错误处理
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    if "message" in response_data["choices"][0] and "content" in response_data["choices"][0]["message"]:
                        return response_data["choices"][0]["message"]['content']
                    else:
                        print(f"响应格式错误：缺少message.content字段")
                        print(f"实际响应：{response_data}")
                        return None
                else:
                    print(f"响应格式错误：缺少choices字段")
                    print(f"实际响应：{response_data}")
                    return None
            else:
                print(f"API请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"网络请求异常: {e}")
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"响应数据解析错误: {e}")
            return None
        except Exception as e:
            print(f"未知错误: {e}")
            return None
    
    def execute_multiple_attempts(self, question_id: str, question_text: str) -> List[Dict]:
        """
        对单个问题执行多次尝试生成答案
        
        Args:
            question_id (str): 问题的唯一标识符
            question_text (str): 问题的文本内容
            
        Returns:
            List[Dict]: 包含所有尝试结果的列表
        """
        attempt_results = []
        
        for attempt_index in range(self.config.max_retry_attempts):
            generated_answer = self.invoke_ai_model(question_text)
            
            # 构建结果记录
            result_record = {
                'id': question_id,
                'attempt': attempt_index,
                'response': generated_answer if generated_answer else "$\\boxed{模型响应异常}$"
            }
            
            attempt_results.append(result_record)
            
            # 输出当前尝试的结果（用于调试）
            print(f"问题ID: {question_id}, 尝试: {attempt_index + 1}, 答案: {generated_answer}")
            
        return attempt_results


class FileFormatConverter:
    """
    文件格式转换器类
    
    提供CSV文件格式转换功能，支持将逗号分隔的CSV文件
    转换为制表符分隔的格式。
    """
    
    @staticmethod
    def transform_csv_delimiter(source_file_path: str, target_file_path: str) -> bool:
        """
        将CSV文件的分隔符从逗号转换为制表符
        
        Args:
            source_file_path (str): 源文件路径
            target_file_path (str): 目标文件路径
            
        Returns:
            bool: 转换是否成功
        """
        try:
            with open(source_file_path, 'r', encoding='utf-8') as input_stream, \
                 open(target_file_path, 'w', newline='', encoding='utf-8') as output_stream:
                
                csv_reader = csv.reader(input_stream)
                tab_writer = csv.writer(output_stream, delimiter='\t')
                
                # 逐行读取并写入，转换分隔符
                for row_data in csv_reader:
                    tab_writer.writerow(row_data)
                    
            print(f"✅ 文件格式转换成功: {source_file_path} → {target_file_path}")
            return True
            
        except FileNotFoundError:
            print(f" 源文件不存在: {source_file_path}")
            return False
        except PermissionError:
            print(f"文件权限不足，无法写入: {target_file_path}")
            return False
        except Exception as e:
            print(f" 文件转换过程中发生错误: {e}")
            return False


class BatchQuestionHandler:
    """
    批量问题处理器类
    
    负责批量处理问题文件，协调问题处理器和文件转换器，
    实现完整的批处理工作流程。
    """
    
    def __init__(self, processor: FinancialQuestionProcessor, converter: FileFormatConverter):
        """
        初始化批量问题处理器
        
        Args:
            processor (FinancialQuestionProcessor): 问题处理器实例
            converter (FileFormatConverter): 文件转换器实例
        """
        self.question_processor = processor
        self.format_converter = converter
        
    def _parse_input_row(self, csv_row: List[str]) -> Tuple[str, str]:
        """
        解析输入CSV行数据，提取问题ID和问题内容
        
        Args:
            csv_row (List[str]): CSV行数据列表
            
        Returns:
            Tuple[str, str]: (问题ID, 问题内容)
        """
        # 从第一列提取问题ID（制表符分隔的第一部分）
        question_id = csv_row[0].split('\t')[0]
        
        # 从第一列提取问题内容（制表符分隔的最后部分）
        question_content = csv_row[0].split('\t')[-1]
        
        # 如果有多列，将后续列内容追加到问题中
        for column_index in range(1, len(csv_row)):
            question_content += csv_row[column_index]
            
        return question_id, question_content
    
    def execute_batch_processing(self, input_file_path: str = 'input.csv') -> bool:
        """
        执行批量问题处理流程
        
        Args:
            input_file_path (str): 输入文件路径
            
        Returns:
            bool: 处理是否成功完成
        """
        # 定义输出文件路径
        intermediate_output = 'raw_result.csv'
        final_output = 'result.csv'
        
        # 检查输入文件是否存在
        if not os.path.exists(input_file_path):
            print(f"❌ 输入文件不存在: {input_file_path}")
            return False
        
        try:
            # 打开输入和输出文件
            with open(input_file_path, 'r', encoding='utf-8') as input_file, \
                 open(intermediate_output, 'w', newline='', encoding='utf-8') as output_file:
                
                # 初始化CSV读写器
                csv_reader = csv.reader(input_file)
                result_writer = csv.DictWriter(
                    output_file, 
                    fieldnames=['id', 'attempt', 'response']
                )
                
                # 写入CSV头部
                result_writer.writeheader()
                
                # 使用线程池进行并发处理
                with ThreadPoolExecutor(max_workers=self.question_processor.config.max_concurrent_workers) as executor:
                    # 提交所有任务到线程池
                    future_to_question = {}
                    
                    for row in csv_reader:
                        question_id, question_text = self._parse_input_row(row)
                        
                        future = executor.submit(
                            self.question_processor.execute_multiple_attempts,
                            question_id,
                            question_text
                        )
                        future_to_question[future] = (question_id, question_text)
                    
                    # 收集并写入结果
                    for future in as_completed(future_to_question):
                        try:
                            results = future.result()
                            
                            # 使用线程锁确保写入安全
                            with self.question_processor._thread_lock:
                                for result in results:
                                    result_writer.writerow(result)
                                    
                        except Exception as e:
                            question_id, question_text = future_to_question[future]
                            print(f"❌ 处理问题 {question_id} 时发生错误: {e}")
            
            # 执行文件格式转换
            conversion_success = self.format_converter.transform_csv_delimiter(
                intermediate_output, 
                final_output
            )
            
            if conversion_success:
                print(f"🎉 批量处理完成！结果已保存到 {intermediate_output} 和 {final_output}")
                return True
            else:
                print(f"⚠️ 批量处理完成，但格式转换失败")
                return False
                
        except FileNotFoundError:
            print(f"❌ 输入文件不存在: {input_file_path}")
            return False
        except Exception as e:
            print(f"❌ 批量处理过程中发生错误: {e}")
            return False


def main():
    """
    主函数：程序入口点
    初始化所有组件并执行批量处理流程
    """
    
    # 创建API配置
    api_config = APIConfiguration()
    
    # 初始化各个组件
    question_processor = FinancialQuestionProcessor(api_config)
    format_converter = FileFormatConverter()
    batch_handler = BatchQuestionHandler(question_processor, format_converter)
    
    # 执行批量处理
    success = batch_handler.execute_batch_processing()
    
    if success:
        print("程序执行完成！")
    else:
        print(" 程序执行过程中遇到错误！")


if __name__ == "__main__":
    main()
    print("处理完成！输出结果已保存到raw_result.csv和result.csv")