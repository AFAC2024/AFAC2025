"""
生成个股研报的脚本

使用示例: python run_company_research_report.py --company_name 4Paradigm --company_code '02220.HK'

1.0 @nambo 2025-07-24
"""
import argparse
from agent import agent_stock
import asyncio

async def main():
  parser = argparse.ArgumentParser(description='企业研报生成助手')
  parser.add_argument('--company_name', type=str, help='上市公司名称')
  parser.add_argument('--company_code', type=str, help='股票代码.交易所, 如: 00020.HK')
  args = parser.parse_args()
  
  print(f'开始编写《{args.company_name}({args.company_code})研报》')
  topic = f'我需要生成"{args.company_name}({args.company_code})"的研报'
  res_path = await agent_stock.ainvoke(topic)
  
  print(f'《{args.company_name}({args.company_code})研报》编写完成，结果在: {res_path}')

if __name__ == '__main__':
  asyncio.run(main())
