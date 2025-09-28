"""
使用大模型进行ROE、DCF、FCF分析

1.0 @nambo 2025-07-20
"""
import os
import progressbar

from langchain_community.chat_models import ChatTongyi
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from typing_extensions import Annotated, TypedDict, List
from langchain_core.documents import Document
from langchain_mcp_adapters.client import MultiServerMCPClient
import sys
import logging
import json
import asyncio

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
parent_dir = os.path.dirname(parent_dir)
sys.path.append(parent_dir)

import config
from agent.common import llm_utils
from mcps.tools import store
from prompts import data_prompts, stock_prompts, financial_prompts
from mcps.common.cache import removeCache, getCache, setCache, get_md5
from mcps.spider import stock_akshare

# 配置日志
logging.basicConfig(
    level=logging.DEBUG
)

# 使用语言模型 通义千问
print('开始加载个股生成模块')
llm = ChatTongyi(model=config.conf['APP_MODEL_VERSION'], model_kwargs={
  'enable_thinking': False
})

invoke_util = llm_utils.InvokeUtil(llm)

async def get_roe_analysis_report(comp_name, stock_code, market):
  """
  生成企业的ROE分析报告
  """
  datas_zc = stock_akshare.get_financial_report(stock_code, '资产负债表', market)
  datas_lr = stock_akshare.get_financial_report(stock_code, '利润表', market)
  msgs = financial_prompts['tpl_roe_analysis'].invoke({
    "roles": "资深财经编辑、专业财务数据分析师",
    "comp_name": comp_name,
    "datas_zc": datas_zc,
    "datas_lr": datas_lr,
    }).to_messages()

  cache_key = 'get_roe_analysis_report,{0},{1},{2}'.format(comp_name, stock_code, market)
  cache = getCache(cache_key)
  if cache is not None:
      content = cache
  else:
    content = await invoke_util.ainvoke(msgs)
    setCache(cache_key, json.dumps(content, ensure_ascii=False))

  return content

async def get_dcf_fcf_analysis(comp_name, stock_code, market):
  """
  生成企业的DCF、FCF分析报告
  """
  datas = stock_akshare.get_financial_report(stock_code, '现金流量表', market)
  msgs = financial_prompts['tpl_dcf_fcf_analysis'].invoke({
    "roles": "资深财经编辑、专业财务数据分析师",
    "comp_name": comp_name,
    "datas": datas
    }).to_messages()

  cache_key = 'get_dcf_fcf_analysis,{0},{1},{2}'.format(comp_name, stock_code, market)
  cache = getCache(cache_key)
  if cache is not None:
      content = cache
  else:
    content = await invoke_util.ainvoke(msgs)
    setCache(cache_key, json.dumps(content, ensure_ascii=False))

  return content

if __name__ == '__main__':
   roe = asyncio.run(get_roe_analysis_report('商汤科技', '00020', 'hk'))
   print(roe)

   dcf = asyncio.run(get_dcf_fcf_analysis('商汤科技', '00020', 'hk'))
   print(dcf)