"""
生成行业研报的脚本

使用示例: python run_industry_research_report.py --industry_name '中国智能服务机器人产业'

1.0 @nambo 2025-07-24
"""
import argparse
from agent import agent_industry
import asyncio

async def main():
  parser = argparse.ArgumentParser(description='行业研报生成助手')
  parser.add_argument('--industry_name', type=str, help='行业名称')
  args = parser.parse_args()
  
  print(f'开始编写《{args.industry_name}研报》')
  topic = f'我需要生成"{args.industry_name}"的研报'
  res_path = await agent_industry.ainvoke(topic)
  
  print(f'《{args.company_name}({args.company_code})研报》编写完成，结果在: {res_path}')

if __name__ == '__main__':
  asyncio.run(main())
