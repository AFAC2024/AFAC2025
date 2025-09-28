"""
评估模块

此模块提供了评估模型推理结果的功能。
"""

import pandas as pd
import re
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

class Evaluator:
    """
    评估器类，用于评估模型推理结果。
    """
    
    def __init__(self, output_path: str, reference_path: Optional[str] = None):
        """
        初始化评估器。
        
        参数:
            output_path: 输出文件路径
            reference_path: 参考答案文件路径，如果为None则无法计算准确率
        """
        self.output_path = output_path
        self.reference_path = reference_path
        self.output_df = None
        self.reference_df = None
        
    def load_data(self) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """
        加载输出和参考数据。
        
        返回:
            输出DataFrame和参考DataFrame的元组
        """
        # 加载输出数据
        try:
            self.output_df = pd.read_csv(self.output_path, sep='\t', header=None, names=['id', 'sample_id', 'output'])
            print(f"成功加载输出数据，共{len(self.output_df)}条记录")
        except Exception as e:
            print(f"加载输出数据失败: {e}")
            raise
        
        # 加载参考数据（如果有）
        if self.reference_path:
            try:
                self.reference_df = pd.read_csv(self.reference_path, sep='\t', header=None, names=['id', 'answer'])
                print(f"成功加载参考数据，共{len(self.reference_df)}条记录")
            except Exception as e:
                print(f"加载参考数据失败: {e}")
                self.reference_df = None
        
        return self.output_df, self.reference_df
    
    def extract_answer(self, output: str) -> str:
        """
        从输出中提取答案。
        
        参数:
            output: 模型输出
            
        返回:
            提取的答案
        """
        # 尝试使用####分隔符提取答案
        if "####" in output:
            answer = output.split("####")[-1].strip()
            return answer
        
        # 尝试使用$\\boxed{答案}$格式提取答案
        boxed_pattern = r'\$\\boxed\{(.*?)\}\$'
        boxed_match = re.search(boxed_pattern, output)
        if boxed_match:
            return boxed_match.group(1).strip()
        
        # 尝试使用最后一行作为答案
        lines = output.strip().split('\n')
        if lines:
            return lines[-1].strip()
        
        return output.strip()
    
    def calculate_accuracy(self) -> float:
        """
        计算准确率。
        
        返回:
            准确率
        """
        if self.output_df is None or self.reference_df is None:
            self.load_data()
            
        if self.reference_df is None:
            print("无参考数据，无法计算准确率")
            return 0.0
        
        # 提取答案
        self.output_df['extracted_answer'] = self.output_df['output'].apply(self.extract_answer)
        
        # 计算每个问题的准确率
        correct_questions = 0
        total_questions = len(self.reference_df)
        
        for i in range(total_questions):
            question_samples = self.output_df[self.output_df['id'] == i]
            reference_answer = self.reference_df[self.reference_df['id'] == i]['answer'].values[0]
            
            # 检查是否有任何一个样本的答案正确
            correct = False
            for _, row in question_samples.iterrows():
                if self._is_answer_correct(row['extracted_answer'], reference_answer):
                    correct = True
                    break
            
            if correct:
                correct_questions += 1
        
        accuracy = correct_questions / total_questions
        print(f"准确率: {accuracy:.4f} ({correct_questions}/{total_questions})")
        
        return accuracy
    
    def _is_answer_correct(self, predicted: str, reference: str) -> bool:
        """
        判断预测答案是否正确。
        
        参数:
            predicted: 预测答案
            reference: 参考答案
            
        返回:
            是否正确
        """
        # 清理和标准化答案
        predicted = self._clean_answer(predicted)
        reference = self._clean_answer(reference)
        
        # 直接匹配
        if predicted == reference:
            return True
        
        # 选择题匹配（A/B/C/D）
        if len(predicted) == 1 and predicted.upper() in "ABCD" and reference.upper() in "ABCD":
            return predicted.upper() == reference.upper()
        
        # 多选题匹配（如"A,C"或"AC"）
        if all(c.upper() in "ABCD" for c in predicted.replace(",", "")) and all(c.upper() in "ABCD" for c in reference.replace(",", "")):
            pred_choices = set(c.upper() for c in predicted if c.upper() in "ABCD")
            ref_choices = set(c.upper() for c in reference if c.upper() in "ABCD")
            return pred_choices == ref_choices
        
        # 数值匹配（允许一定的误差）
        try:
            pred_num = float(predicted)
            ref_num = float(reference)
            # 允许0.1%的相对误差
            return abs(pred_num - ref_num) / max(abs(ref_num), 1e-10) < 0.001
        except ValueError:
            pass
        
        return False
    
    def _clean_answer(self, answer: str) -> str:
        """
        清理和标准化答案。
        
        参数:
            answer: 原始答案
            
        返回:
            清理后的答案
        """
        # 移除空白字符
        answer = answer.strip()
        
        # 移除常见的前缀
        prefixes = ["答案是", "答案:", "答案：", "the answer is", "answer:"]
        for prefix in prefixes:
            if answer.lower().startswith(prefix.lower()):
                answer = answer[len(prefix):].strip()
        
        # 移除引号
        answer = answer.strip('"\'')
        
        return answer
    
    def calculate_cot_length(self) -> Dict[int, int]:
        """
        计算每个问题的最短COT长度。
        
        返回:
            问题ID到最短COT长度的字典
        """
        if self.output_df is None or self.reference_df is None:
            self.load_data()
        
        # 计算每个输出的长度
        self.output_df['length'] = self.output_df['output'].apply(len)
        
        # 提取答案
        if 'extracted_answer' not in self.output_df.columns:
            self.output_df['extracted_answer'] = self.output_df['output'].apply(self.extract_answer)
        
        # 计算每个问题的最短COT长度
        cot_lengths = {}
        max_length = self.output_df['length'].max()  # 最大长度作为未回答正确问题的默认值
        
        for i in range(len(self.reference_df)):
            question_samples = self.output_df[self.output_df['id'] == i]
            reference_answer = self.reference_df[self.reference_df['id'] == i]['answer'].values[0]
            
            # 找出正确回答的样本
            correct_samples = []
            for _, row in question_samples.iterrows():
                if self._is_answer_correct(row['extracted_answer'], reference_answer):
                    correct_samples.append(row)
            
            # 如果有正确回答，取最短的长度；否则使用最大长度
            if correct_samples:
                min_length = min(sample['length'] for sample in correct_samples)
                cot_lengths[i] = min_length
            else:
                cot_lengths[i] = max_length
        
        return cot_lengths
    
    def calculate_score(self) -> float:
        """
        计算最终得分。
        
        返回:
            最终得分（所有问题COT长度总和的相反数）
        """
        cot_lengths = self.calculate_cot_length()
        total_length = sum(cot_lengths.values())
        score = -total_length
        
        print(f"总COT长度: {total_length}")
        print(f"最终得分: {score}")
        
        return score
    
    def analyze_results(self, save_path: Optional[str] = None) -> Dict:
        """
        分析结果并生成报告。
        
        参数:
            save_path: 保存报告的路径，如果为None则不保存
            
        返回:
            包含分析结果的字典
        """
        if self.output_df is None or self.reference_df is None:
            self.load_data()
        
        # 计算准确率
        accuracy = self.calculate_accuracy()
        
        # 计算COT长度
        cot_lengths = self.calculate_cot_length()
        avg_cot_length = np.mean(list(cot_lengths.values()))
        min_cot_length = np.min(list(cot_lengths.values()))
        max_cot_length = np.max(list(cot_lengths.values()))
        
        # 计算最终得分
        score = self.calculate_score()
        
        # 统计不同长度区间的问题数量
        length_bins = [0, 1000, 2000, 3000, 4000, 5000, 10000, float('inf')]
        length_counts = defaultdict(int)
        
        for length in cot_lengths.values():
            for i in range(len(length_bins) - 1):
                if length_bins[i] <= length < length_bins[i+1]:
                    bin_name = f"{length_bins[i]}-{length_bins[i+1]}"
                    length_counts[bin_name] += 1
                    break
        
        # 生成报告
        report = {
            "accuracy": accuracy,
            "avg_cot_length": avg_cot_length,
            "min_cot_length": min_cot_length,
            "max_cot_length": max_cot_length,
            "score": score,
            "length_distribution": dict(length_counts)
        }
        
        # 打印报告
        print("\n===== 结果分析报告 =====")
        print(f"准确率: {accuracy:.4f}")
        print(f"平均COT长度: {avg_cot_length:.2f}")
        print(f"最短COT长度: {min_cot_length}")
        print(f"最长COT长度: {max_cot_length}")
        print(f"最终得分: {score}")
        print("\nCOT长度分布:")
        for bin_name, count in length_counts.items():
            print(f"  {bin_name}: {count}")
        
        # 绘制COT长度分布图
        plt.figure(figsize=(10, 6))
        sns.histplot(list(cot_lengths.values()), bins=20)
        plt.title("COT长度分布")
        plt.xlabel("长度")
        plt.ylabel("问题数量")
        
        # 保存报告
        if save_path:
            plt.savefig(f"{save_path}/cot_length_distribution.png")
            
            # 保存报告文本
            with open(f"{save_path}/analysis_report.txt", "w") as f:
                f.write("===== 结果分析报告 =====\n")
                f.write(f"准确率: {accuracy:.4f}\n")
                f.write(f"平均COT长度: {avg_cot_length:.2f}\n")
                f.write(f"最短COT长度: {min_cot_length}\n")
                f.write(f"最长COT长度: {max_cot_length}\n")
                f.write(f"最终得分: {score}\n")
                f.write("\nCOT长度分布:\n")
                for bin_name, count in length_counts.items():
                    f.write(f"  {bin_name}: {count}\n")
        
        return report


# 使用示例
if __name__ == "__main__":
    # 初始化评估器
    evaluator = Evaluator("./output.csv", "./ref.csv")
    
    # 加载数据
    output_df, reference_df = evaluator.load_data()
    
    # 计算准确率
    accuracy = evaluator.calculate_accuracy()
    
    # 计算COT长度
    cot_lengths = evaluator.calculate_cot_length()
    print(f"问题0的COT长度: {cot_lengths.get(0, 'N/A')}")
    
    # 计算最终得分
    score = evaluator.calculate_score()
    
    # 分析结果
    report = evaluator.analyze_results("./results")

