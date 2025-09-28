"""
数据加载和预处理模块

此模块提供了加载和预处理金融领域长思维链压缩赛题数据的功能。
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional

class DataLoader:
    """
    数据加载器类，用于加载和预处理金融领域长思维链压缩赛题数据。
    """
    
    def __init__(self, file_path: str, sep: str = '\t', header=None):
        """
        初始化数据加载器。
        
        参数:
            file_path: 数据文件路径
            sep: 分隔符，默认为制表符
            header: 表头行，默认为None（无表头）
        """
        self.file_path = file_path
        self.sep = sep
        self.header = header
        self.df = None
        self.questions = []
        
    def load_data(self) -> pd.DataFrame:
        """
        加载数据文件。
        
        返回:
            加载的DataFrame对象
        """
        try:
            self.df = pd.read_csv(self.file_path, sep=self.sep, header=self.header)
            print(f"成功加载数据，共{len(self.df)}条记录")
            return self.df
        except Exception as e:
            print(f"加载数据失败: {e}")
            raise
    
    def get_questions(self) -> List[str]:
        """
        获取所有问题文本。
        
        返回:
            问题文本列表
        """
        if self.df is None:
            self.load_data()
        
        self.questions = []
        for i in range(len(self.df)):
            this_row = self.df.iloc[i]
            self.questions.append(this_row[2])  # 问题文本在第3列
        
        return self.questions
    
    def get_question_by_id(self, question_id: int) -> str:
        """
        根据问题ID获取问题文本。
        
        参数:
            question_id: 问题ID
            
        返回:
            问题文本
        """
        if self.df is None:
            self.load_data()
        
        return self.df.iloc[question_id][2]
    
    def prepare_prompt(self, question: str, system_prompt: Optional[str] = None) -> Dict[str, str]:
        """
        准备模型输入的prompt。
        
        参数:
            question: 问题文本
            system_prompt: 系统提示词，如果为None则使用默认提示词
            
        返回:
            包含system和user字段的字典
        """
        if system_prompt is None or system_prompt == "":
            system_prompt = ""
        
        tips = "如果是选择题，在\\boxed{}中填写答案字母，字母之间不需要分隔；如果是数学题，直接在\\boxed{}中填写答案。"
        return {
            "system": system_prompt,
            "user": question + "\n" + tips
        }
    
    def prepare_batch_prompts(self, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        """
        准备所有问题的prompt。
        
        参数:
            system_prompt: 系统提示词，如果为None则使用默认提示词
            
        返回:
            包含system和user字段的字典列表
        """
        if not self.questions:
            self.get_questions()
        
        prompts = []
        for question in self.questions:
            prompts.append(self.prepare_prompt(question, system_prompt))
        
        return prompts
    
    def save_results(self, results: List[Tuple[int, int, str]], output_path: str) -> None:
        """
        保存模型推理结果到CSV文件。
        
        参数:
            results: 结果列表，每个元素为(id, sample_id, output)的元组
            output_path: 输出文件路径
        """
        output_df = pd.DataFrame(results, columns=['id', 'sample_id', 'output'])
        output_df.to_csv(output_path, sep='\t', index=False, header=False)
        print(f"结果已保存到 {output_path}")



