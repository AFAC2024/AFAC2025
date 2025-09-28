"""
内容生成agent

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

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import config
from mcps.tools import store
from prompts import data_prompts, stock_prompts
from mcps.common.cache import removeCache, getCache, setCache, get_md5
from mcps.common import parallelism
from agent.common import llm_utils

# 配置日志
logging.basicConfig(
    level=logging.DEBUG
)

# 使用语言模型 通义千问
print('开始加载个股生成模块')
llm = ChatTongyi(model=config.conf['APP_MODEL_VERSION'], model_kwargs={
  'enable_thinking': False
})

# 配置 MCP 服务器参数
print('模型初始化完成')
client = MultiServerMCPClient({
  "stock": {
    "command": config.conf['python_path'],
    "args": ["./mcps/server_stock.py"],
    "transport": "stdio",
  }
})
print('mcp初始化完成')

invoke_util = llm_utils.InvokeUtil(llm, client)

agent = None
async def llm_invoke(msgs, call_type='llm', res_type='str'):
  return await invoke_util.ainvoke(msgs, call_type, res_type)

async def get_section_keywords(topic, target="个股"):
   
  msgs = data_prompts['tpl_section_search_words'].invoke({
    "roles": "资深财经编辑、专业数据分析师",
    "target": target,
    "topic": topic
    }).to_messages()

  cache_key = 'get_section_keywords,{0}'.format(str(msgs))
  cache = getCache(cache_key)
  if cache is not None:
      keywords = json.loads(cache)
  else:
    keywords = await llm_invoke(msgs, res_type='json')
    setCache(cache_key, json.dumps(keywords, ensure_ascii=False))

  return keywords

async def check_relative(information, topic, target):
  try:
    msgs = data_prompts['tpl_relative_check'].invoke({
      "roles": "资深财经编辑、专业数据分析师",
      "target": target,
      "topic": topic,
      "file_info": information
      }).to_messages()
    cache_key = 'check_relative,{0}'.format( get_md5(str(msgs)))
    cache = getCache(cache_key)
    if cache is not None:
      res = cache
    else:
      res = await llm_invoke(msgs)
      setCache(cache_key, res)
    return res
  except:
    return '否'

async def check_doc_relative_worker(doc, topic, target):
  res = []
  relative = await check_relative(json.dumps(doc, ensure_ascii=False), topic, target)
  doc['relative'] = relative
  res = [doc]
  return res

async def get_relative_docs(docs, topic, target="个股"):
  relative_docs = []
  unknow_docs = []
  widgets = [
    '检测文本相关度',  # 替代prefix的固定标题
    progressbar.Bar(),  # 进度条本身
    ' ', progressbar.SimpleProgress(),  # 百分比
    ' ', progressbar.ETA()  # 预计剩余时间
  ]
  # bar = progressbar.ProgressBar(widgets=widgets, max_value=len(docs), term_width=100)
  tasks = []
  for idx, doc in enumerate(docs):
    tasks.append((check_doc_relative_worker, (doc, topic, target), {}))
  #   bar.update(idx + 1)
  # bar.finish()

  executor = parallelism.AsyncConcurrentExecutor(max_concurrent=config.conf['parallelism_count'])
  docs_res = await executor.execute(tasks)

  for idx,doc in enumerate(docs_res):
    if doc['relative'] == '是':
      relative_docs.append(doc)
    elif doc['relative'] == '未知':
      unknow_docs.append(doc)
  
  for doc in unknow_docs:
    content = await store.get_content(doc)
    res = await check_relative(content, topic, target)

    if res == '是':
      relative_docs.append(doc)

  print('总计获取到{0}篇，相关的有{1}'.format(len(docs), len(relative_docs)))
  return relative_docs

async def get_doc_summary(topic, doc, total_docs, target='个股'):
  cache_key = topic + str(doc)
  cache = getCache(cache_key)
  if cache is not None:
    return json.loads(cache)
  
  content = await store.get_content(doc)

  max_summary_len = 45000 / total_docs
  # 如果是生成的研报，则引用原文，否则使用摘要
  if doc['handler'] == 'financial_analysis' or len(content) < max_summary_len:
    summary = content
  else:
    msgs = data_prompts['tpl_relative_summary'].invoke({
      "roles": "资深财经编辑、专业数据分析师",
      "target": target,
      "topic": topic,
      "file_info": content,
      "summary_len": max_summary_len
      }).to_messages()
    summary = await llm_invoke(msgs)
  
  res = {
    'title': doc['name'],
    'url': doc['url'],
    'source': doc['source'],
    'file_type': doc['file_type'],
    'key': doc['key'],
    'handler': doc['handler'],
    'date': doc['date'],
    'summary': summary
  }
  setCache(cache_key, json.dumps(res, ensure_ascii=False))
  return res

async def get_doc_summary_worker(topic, doc, docs, target, start_idx):
    summary = await get_doc_summary(topic, doc, len(docs), target)
    summary['idx'] = start_idx 
    return [summary]

async def get_section_docs(topic, target="个股", start_idx=1):

  cache_key = 'get_section_docs1,{0},{1}'.format(topic, target)
  cache = getCache(cache_key)
  if cache is not None:
    return json.loads(cache)

  keywords = await get_section_keywords(topic, target)
  search_words = []
  for word in keywords:
    search_words.append(word.strip())
  docs = store.search(search_words)

  docs = await get_relative_docs(docs, topic, target)

  summary_list = []
  widgets = [
    '获取材料摘要',  # 替代prefix的固定标题
    progressbar.Bar(),  # 进度条本身
    ' ', progressbar.SimpleProgress(),  # 进度如1/4
    ' ', progressbar.ETA()  # 预计剩余时间
  ]
  # bar = progressbar.ProgressBar(widgets=widgets, max_value=len(docs), term_width=100)
  idx = 0
  tasks = []
  for doc in docs:
    start_idx += 1
    tasks.append((get_doc_summary_worker, (topic, doc, docs, target, start_idx), {}))
    idx += 1
  #   bar.update(idx)
  # bar.finish()

  executor = parallelism.AsyncConcurrentExecutor(max_concurrent=config.conf['parallelism_count'])
  summary_list = await executor.execute(tasks)

  setCache(cache_key, json.dumps(summary_list, ensure_ascii=False))

  return summary_list


async def search_docs(keywords, topic, data_date=None, target='个股'):
  docs = store.search_data(keywords, data_date)

  print('\n\n\n', docs, '\n\n\n')
  docs = await get_relative_docs(docs, topic, target)

  store.save_data_list(docs, '装载数据')
  print('总计获取到{0}篇'.format(len(docs)))
  return len(docs)


if __name__ == '__main__':
  import asyncio
  msg = stock_prompts['tpl_topic_info'].format(target='宁德时代', title='公司概况与主营业务', desc='介绍宁德时代的基本信息，包括企业名称、股票代码、上市地点，并概述其主营业务构成及主要产品应用领域。')
  res = asyncio.run(get_section_docs(msg))
  print(res)