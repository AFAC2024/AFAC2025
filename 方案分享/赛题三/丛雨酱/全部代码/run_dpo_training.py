#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

class DPOTrainingRunner:
    """DPO训练执行器"""
    
    def __init__(self):
        self.config = {
            'nproc_per_node': 2,
            'cuda_visible_devices': '0,1',
            'rlhf_type': 'dpo',
            'model': '/data/model/Qwen3-4B',
            'train_type': 'full',
            'dataset': '/data/dpo_dataset_combined.json',
            'model_type': 'qwen3',
            'template': 'qwen3',
            'torch_dtype': 'bfloat16',
            'seed': '3407',
            'num_train_epochs': 2,
            'per_device_train_batch_size': 1,
            'per_device_eval_batch_size': 1,
            'learning_rate': '1e-4',
            'gradient_accumulation_steps': 16,
            'eval_steps': 20,
            'save_steps': 20,
            'save_total_limit': 10,
            'logging_steps': 5,
            'max_length': 100000,
            'output_dir': 'output',
            'warmup_ratio': 0,
            'save_only_model': 'true',
            'deepspeed': 'zero3',
            'attn_impl': 'None',
            'rpo_alpha': '0.2'
        }
    
    def build_command(self):
        """构建swift命令"""
        # 设置环境变量
        env_vars = [
            f"NPROC_PER_NODE={self.config['nproc_per_node']}",
            f"CUDA_VISIBLE_DEVICES={self.config['cuda_visible_devices']}"
        ]
        
        # 构建swift命令参数
        swift_args = [
            'swift', 'rlhf',
            '--rlhf_type', self.config['rlhf_type'],
            '--model', self.config['model'],
            '--train_type', self.config['train_type'],
            '--dataset', self.config['dataset'],
            '--model_type', self.config['model_type'],
            '--template', self.config['template'],
            '--torch_dtype', self.config['torch_dtype'],
            '--seed', self.config['seed'],
            '--num_train_epochs', str(self.config['num_train_epochs']),
            '--per_device_train_batch_size', str(self.config['per_device_train_batch_size']),
            '--per_device_eval_batch_size', str(self.config['per_device_eval_batch_size']),
            '--learning_rate', self.config['learning_rate'],
            '--gradient_accumulation_steps', str(self.config['gradient_accumulation_steps']),
            '--eval_steps', str(self.config['eval_steps']),
            '--save_steps', str(self.config['save_steps']),
            '--save_total_limit', str(self.config['save_total_limit']),
            '--logging_steps', str(self.config['logging_steps']),
            '--max_length', str(self.config['max_length']),
            '--output_dir', self.config['output_dir'],
            '--warmup_ratio', str(self.config['warmup_ratio']),
            '--save_only_model', self.config['save_only_model'],
            '--deepspeed', self.config['deepspeed'],
            '--attn_impl', self.config['attn_impl'],
            '--rpo_alpha', self.config['rpo_alpha']
        ]
        
        return env_vars, swift_args
    
    def run_training(self):
        """执行DPO训练"""
        try:
            print("🚀 开始DPO训练...")
            
            # 构建命令
            env_vars, swift_args = self.build_command()
            
            # 设置环境变量
            env = os.environ.copy()
            for var in env_vars:
                key, value = var.split('=', 1)
                env[key] = value
                print(f"设置环境变量: {key}={value}")
            
            # 打印命令
            print(f"执行命令: {' '.join(swift_args)}")
            
            # 执行命令
            process = subprocess.Popen(
                swift_args,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 实时输出日志
            for line in process.stdout:
                print(line.rstrip())
            
            # 等待进程完成
            return_code = process.wait()
            
            if return_code == 0:
                print("✅ DPO训练完成！")
            else:
                print(f"❌ 训练失败，退出码: {return_code}")
                
            return return_code
            
        except Exception as e:
            print(f"❌ 执行过程中出现错误: {e}")
            return 1
    
    def update_config(self, **kwargs):
        """更新配置参数"""
        self.config.update(kwargs)
        print(f"配置已更新: {kwargs}")


def main():
    """主函数"""
    print("=" * 60)
    print("🎯 DPO训练启动器")
    print("=" * 60)
    
    # 创建训练器实例
    trainer = DPOTrainingRunner()
    
    # 可选：根据命令行参数更新配置
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("使用方法:")
            print("python run_dpo_training.py [--help]")
            print("\n可在脚本中修改config字典来调整训练参数")
            return
    
    # 执行训练
    exit_code = trainer.run_training()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()