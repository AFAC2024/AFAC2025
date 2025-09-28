"""
模型加载和推理模块

此模块提供了加载Qwen3-4b模型和进行推理的功能。
"""

import torch
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from typing import List, Dict, Tuple, Optional, Union
import re
import time
import os

class ModelInference:
    """
    模型推理类，用于加载模型和进行推理。
    """
    
    def __init__(self, model_name_or_path: str = "Qwen/Qwen3-4B-Chat"):
        """
        初始化模型推理类。
        
        参数:
            model_name_or_path: 模型名称或路径，默认为"Qwen/Qwen3-4B-Chat"
        """
        self.model_name_or_path = model_name_or_path
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
    def load_model(self) -> None:
        """
        加载模型和分词器。
        """
        print(f"正在加载模型 {self.model_name_or_path}...")
        start_time = time.time()
        
        # 加载分词器
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path, trust_remote_code=True)
        
        # 使用vLLM加载模型
        self.model = LLM(
            model=self.model_name_or_path,
            trust_remote_code=True,
            dtype="bfloat16",
            gpu_memory_utilization=0.9,
            max_model_len=16384,
            tensor_parallel_size=8,
        )
        
        end_time = time.time()
        print(f"模型加载完成，耗时 {end_time - start_time:.2f} 秒")
        print(f"模型运行设备: {self.device}")
        
    def generate(self, 
                prompt: Dict[str, str], 
                max_new_tokens: int = 16384, 
                temperature: float = 1.0,
                top_p: float = 0.9,
                repetition_penalty: float = 1.05,
                num_return_sequences: int = 1) -> List[str]:
        """
        生成回答。
        
        参数:
            prompt: 包含system和user字段的字典
            max_new_tokens: 最大生成token数
            temperature: 温度参数
            top_p: top-p采样参数
            num_return_sequences: 返回序列数量
            
        返回:
            生成的回答列表
        """
        if self.model is None or self.tokenizer is None:
            self.load_model()
        
        # 构建消息
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]}
        ]
        
        # 将消息转换为模型输入
        input_text = self.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        # 设置采样参数
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_new_tokens,
            repetition_penalty=repetition_penalty,
            n=num_return_sequences
        )
        
        # 使用vLLM生成回答
        outputs = self.model.generate([input_text], sampling_params)
        
        # 提取生成的文本
        responses = []
        for output in outputs:
            for completion in output.outputs:
                responses.append(completion.text)
        
        return responses
    
    def extract_answer(self, response: str) -> str:
        """
        从回答中提取最终答案。
        
        参数:
            response: 模型生成的回答
            
        返回:
            提取的答案
        """
        # 尝试使用####分隔符提取答案
        if "####" in response:
            answer = response.split("####")[-1].strip()
            return answer
        
        # 尝试使用$\\boxed{答案}$格式提取答案
        boxed_pattern = r'\$\\boxed\{(.*?)\}\$'
        boxed_match = re.search(boxed_pattern, response)
        if boxed_match:
            return boxed_match.group(1).strip()
        
        # 尝试使用最后一行作为答案
        lines = response.strip().split('\n')
        if lines:
            return lines[-1].strip()
        
        return response.strip()
    
    def batch_inference(self, 
                       prompts: List[Dict[str, str]], 
                       max_new_tokens: int = 16384,
                       temperature: float = 0.7,
                       top_p: float = 0.9,
                       repetition_penalty: float = 1.05,
                       num_samples: int = 5) -> List[Tuple[int, int, str]]:
        """
        批量推理。
        
        参数:
            prompts: prompt列表
            max_new_tokens: 最大生成token数
            temperature: 温度参数
            top_p: top-p采样参数
            num_samples: 每个问题生成的样本数量
            
        返回:
            结果列表，每个元素为(id, sample_id, output)的元组
        """
        if self.model is None or self.tokenizer is None:
            self.load_model()
        
        # 准备所有输入文本
        all_inputs = []
        input_mapping = []
        
        for i, prompt in enumerate(prompts):
            # 构建消息
            messages = [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ]
            # 将消息转换为模型输入
            input_text = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            # 为每个问题生成多个样本
            for j in range(num_samples):
                all_inputs.append(input_text)
                input_mapping.append((i, j))
        
        # 设置采样参数
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_new_tokens,
            repetition_penalty=repetition_penalty,
            n=1
        )
        
        print(f"正在批量处理 {len(prompts)} 个问题，每个问题 {num_samples} 个样本...")
        
        # 使用vLLM批量生成
        outputs = self.model.generate(all_inputs, sampling_params)
        
        # 整理结果
        results = []
        for output, (prompt_id, sample_id) in zip(outputs, input_mapping):
            response = output.outputs[0].text
            results.append((prompt_id, sample_id, response))
            
            print(f"问题 {prompt_id+1}, 样本 {sample_id+1} 完成，长度: {len(response)}")
        
        # 输出平均长度
        total_length = sum(len(resp[2]) for resp in results)
        average_length = total_length / len(results) if results else 0
        print(f"平均生成长度: {average_length:.2f} 个字符")
        return results
    
    def save_model(self, save_path: str) -> None:
        """
        保存模型。
        
        参数:
            save_path: 保存路径
        """
        print("vLLM模型不支持直接保存，请使用原始模型路径")
        
        # 如果需要保存分词器
        if self.tokenizer is not None:
            os.makedirs(save_path, exist_ok=True)
            self.tokenizer.save_pretrained(save_path)
            print(f"分词器已保存到 {save_path}")

