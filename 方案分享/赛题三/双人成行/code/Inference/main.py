"""
主程序

此程序整合了数据加载、模型推理和评估功能，实现了完整的金融领域长思维链压缩基线方法。
"""

import os
import argparse
import time
from data_loader import DataLoader
from model_inference import ModelInference
from evaluator import Evaluator

def parse_args():
    """
    解析命令行参数。
    
    返回:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description="金融领域长思维链压缩基线方法")
    
    parser.add_argument("--input_path", type=str, default="xxx", help="输入数据路径")
    parser.add_argument("--output_path", type=str, default="xxx", help="输出数据路径")
    parser.add_argument("--reference_path", type=str, default=None, help="参考答案路径")
    parser.add_argument("--model_name_or_path", type=str, default="xxx", help="模型名称或路径")
    parser.add_argument("--system_prompt", type=str, default="", help="系统提示词")
    parser.add_argument("--max_new_tokens", type=int, default=32768, help="最大生成token数")
    parser.add_argument("--temperature", type=float, default=1.0, help="温度参数")
    parser.add_argument("--top_p", type=float, default=1.0, help="top-p采样参数")
    parser.add_argument("--num_samples", type=int, default=5, help="每个问题生成的样本数量")
    parser.add_argument("--save_model_path", type=str, default=None, help="保存模型的路径")
    parser.add_argument("--result_dir", type=str, default="xxx", help="结果保存目录")
    
    return parser.parse_args()

def main():
    """
    主函数。
    """
    # 解析命令行参数
    args = parse_args()
    
    # 创建结果目录
    os.makedirs(args.result_dir, exist_ok=True)
    
    # 记录开始时间
    start_time = time.time()
    
    # 加载数据
    print("=== 加载数据 ===")
    loader = DataLoader(args.input_path)
    questions = loader.get_questions()
    print(f"共加载 {len(questions)} 个问题")
    
    # 准备prompts
    prompts = loader.prepare_batch_prompts(args.system_prompt)
    
    # 加载模型并进行推理
    print("\n=== 模型推理 ===")
    inference = ModelInference(args.model_name_or_path)
    inference.load_model()
    
    results = inference.batch_inference(
        prompts,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        num_samples=args.num_samples
    )
    
    # 保存结果
    loader.save_results(results, args.output_path)
    
    # 保存模型（如果需要）
    if args.save_model_path:
        inference.save_model(args.save_model_path)
    
    # 评估结果
    print("\n=== 评估结果 ===")
    if args.reference_path:
        evaluator = Evaluator(args.output_path, args.reference_path)
        report = evaluator.analyze_results(args.result_dir)
    else:
        print("未提供参考答案，跳过评估")
    
    # 记录结束时间
    end_time = time.time()
    print(f"\n总耗时: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    main()

