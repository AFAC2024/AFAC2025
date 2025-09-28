"""
生成宏观研报的脚本

使用示例: python run_marco_research_report.py --marco_name '国家级“人工智能+”政策效果评估' --time 2023-2025

1.0 @nambo 2025-07-24
"""
import argparse
from agent import agent_macro
import asyncio

async def main():
  parser = argparse.ArgumentParser(description='宏观经济研报生成助手')
  parser.add_argument('--marco_name', type=str, help='宏观经济研报的主题')
  parser.add_argument('--time', type=str, help='时间范围')
  args = parser.parse_args()
  
  print(f'开始编写《{args.marco_name}研报》')
  topic = f'我需要生成"{args.marco_name}({args.time})"的研报'
  res_path = await agent_macro.ainvoke(topic)
  
  print(f'《{args.marco_name}({args.time})研报》编写完成，结果在: {res_path}')

if __name__ == '__main__':
  asyncio.run(main())
