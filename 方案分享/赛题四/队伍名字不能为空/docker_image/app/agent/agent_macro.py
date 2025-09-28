"""
生成宏观研报的agent

1.0 @nambo 2025-07-20
"""
import os

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
from datetime import datetime

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import config
from mcps.tools import store
from mcps.tools import create_document
from prompts import stock_prompts, macro_prompts
from mcps.common.cache import removeCache, getCache, setCache, get_md5, clear_cache_with_time
from mcps.common import parallelism
from agent.common import llm_utils
from agent import agent_data
from agent import agent_chart

SAVE_DIR = os.path.join(parent_dir, 'results')

# 配置日志
logging.basicConfig(
    level=logging.DEBUG
)

# 使用语言模型 通义千问
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

class State(TypedDict):
    message: str
    context: List[Document]

invoke_util = llm_utils.InvokeUtil(llm, client)

agent = None
async def llm_invoke(msgs, call_type='llm', res_type='str'):
  return await invoke_util.ainvoke(msgs, call_type, res_type)
      
async def get_data_date(question: str):
    cache_key = 'macro_get_data_date,,{0}'.format(question)
    cache = getCache(cache_key)
    if cache is not None:
      res = cache
    else:
      msgs = stock_prompts['tpl_get_data_date'].invoke({"roles": "股票分析师", "target": "宏观", "msg": question}).to_messages()
      res = await llm_invoke(msgs)
      setCache(cache_key, res)

    if res == '无' or '-' not in res:
      return None
    return None
    return res

async def get_target_info(question: str):
    cache_key = 'macro_get_target_info,{0}'.format(question)
    cache = getCache(cache_key)
    if cache is not None:
      return cache
    msgs = macro_prompts['tpl_get_industry_info'].invoke({"roles": "股票分析师", "target": "宏观", "msg": question}).to_messages()
    res = await llm_invoke(msgs, call_type='agent')
    setCache(cache_key, res)
    return res

async def get_outline(desc: str):
    cache_key = 'macro_get_outline_industry,{0}'.format(desc)
    cache = getCache(cache_key)
    if cache is not None:
      cache = json.loads(cache)
      return cache
    msgs = macro_prompts['tpl_get_outline'].invoke({
       "roles": "资深财经主编",
       "target": "宏观",
       "desc": desc}).to_messages()
    outline = await llm_invoke(msgs, res_type='json')
    setCache(cache_key, json.dumps(outline, ensure_ascii=False))
    return outline

async def get_info_data(desc, outlines):
    
    msgs = macro_prompts['tpl_get_info_data'].invoke({"roles": "资深财经编辑、专业数据分析师", "target": "宏观", "desc": desc}).to_messages()

    cache_key = 'macro_get_info_data,{0}'.format(str(msgs))
    cache = getCache(cache_key)
    if cache is not None:
       cache = json.loads(cache)
       return cache
    
    comp_data = await llm_invoke(msgs, res_type='json')
    setCache(cache_key, json.dumps(comp_data, ensure_ascii=False))
    return comp_data

async def get_section_content(section, standinfo, data_date, doc_idx=1):
  content = ''
  msg = macro_prompts['tpl_topic_info'].format(target=standinfo['name']
                                               , title=section['title']
                                               , desc=section['desc']
                                               , requirements=str(section['requirements']))
  summary_list = await agent_data.get_section_docs(msg, target='宏观', start_idx=doc_idx)

  summary_content = ''
  idx = 1

  for summary in summary_list:
     summary_content += '{0}. {1}:{2}\n'.format(summary['idx'], summary['source'], summary['title'])
     summary_content += '{0}\n\n'.format(summary['summary'])
     idx += 1

  msgs = macro_prompts['tpl_general_section_content'].invoke({
      "roles": "经济学专家、资深财经主编、专业数据分析师",
      "target": "宏观",
      "title": section['title'],
      "summary": summary_content,
      "topic": msg,
      "object": standinfo['name']
    }).to_messages()

  content = await llm_invoke(msgs)

  return content, summary_list

async def get_key_words(outlines, stand_data):
  outlines_txt = []
  for idx, outline in enumerate(outlines):
    outlines_txt.append('{0}.{1}\n主要内容：{2}\n要求：'.format(idx
                                                        , outline['title']
                                                        , outline['desc']
                                                        , str(outline['requirements'])))
  outlines_txt = '\n\n'.join(outlines_txt)
  msgs = macro_prompts['tpl_get_key_words'].invoke({"roles": "资深财经编辑、专业数据分析师"
                                                    , "target": "宏观"
                                                    , "outlines": outlines_txt
                                                    , "name": stand_data['name']}).to_messages()

  cache_key = 'macro_get_key_words_industry,{0}'.format(str(msgs))
  cache = getCache(cache_key)
  if cache is not None:
    return json.loads(cache)

  key_words = await llm_invoke(msgs, res_type='json')
  key_words['macro'] += key_words['policy']
  setCache(cache_key, json.dumps(key_words, ensure_ascii=False))
  return key_words  

async def get_report_docx(summary_list, compinfo, data_date):
   res = ''
   return res

async def beautyfy_content(comp_info, content_list):

  simple_content_list = []
  for section in content_list:
     simple_content_list.append({
        'title': section['title'],
        'content': section['content']
      })

  

  msgs = macro_prompts['tpl_beauty_section_content'].invoke({
      "roles": "资深财经编辑、专业编辑、研报编辑社资深主编",
      "target": '行业',
      "title": comp_info['name'] ,
      "content": json.dumps(simple_content_list, ensure_ascii=False)
    }).to_messages()
  
  res = await llm_invoke(msgs, res_type='json')

  for idx, section in enumerate(res):
    content_list[idx]['content'] = section['content']
  return content_list

last_success_time = None
async def agent_executor(question: str):
  global last_success_time
  current_time = datetime.now()
  current_time = current_time.strftime("%Y%m%d%H:%M:%S")
  res_list = []

  # 清理过期数据
  store.clean()

  print('开始执行行业研报生成任务，问题：', question)
  data_date = await get_data_date(question)
  print('data_date: ', data_date)

  desc = await get_target_info(question)
  print(desc)

  if '请提供' in desc and '生成研报' in desc and '宏观经济' in desc and '名称' in desc:
    logging.error(desc)
    raise ValueError("抱歉，未能识别到您提供的主题信息，请试试提供完整的宏观经济主题名称。")
  
  outlines = await get_outline(desc)
  print(outlines)

  stand_data = await get_info_data(desc, outlines)
  print(stand_data)

  key_words = await get_key_words(outlines, stand_data)
  print(key_words)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  content_info = []
  for idx, section in enumerate(outlines):
     content_info.append(f"段落{idx}. {section['title']}: {section['desc']}")
  content_info = "\n".join(content_info)

  # store.load_default_data()
  data_len = await agent_data.search_docs(key_words, stand_data['name'] + '主题的研报\n\n' + content_info, data_date)
  print(data_len)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  res_list = []
  doc_idx = 0
  for section in outlines:
    content, summary_list = await get_section_content(section, stand_data, data_date, doc_idx=doc_idx)
    section['content'] = content
    section['sources'] = summary_list
    doc_idx += len(summary_list)
    res_list.append(section)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


  setCache('get_report_content,{0}'.format(json.dumps(res_list, ensure_ascii=False)), json.dumps(res_list, ensure_ascii=False), 'report_industry_' + current_time + '_')
  
  # 关闭润色
  # res_list = await beautyfy_content(stand_data, res_list)
  # setCache('get_report_content,{0}'.format(json.dumps(res_list, ensure_ascii=False)), json.dumps(res_list, ensure_ascii=False), 'report_industry_beautfy_' + current_time +'_')


  all_sources = []
  for section in res_list:
     all_sources += section['sources']

  print('开始生成图表:', len(res_list))
  tasks = []
  for section in res_list:
    topic = macro_prompts['tpl_topic_info'].format(target=stand_data['name']
                                                   , title=section['title']
                                                   , desc=section['desc']
                                                   , requirements=str(section['requirements']))
    tasks.append((agent_chart.get_paragraph_chart_worker, (topic, section, all_sources, '宏观'), {}))
  
  executor = parallelism.AsyncConcurrentExecutor(max_concurrent=config.conf['parallelism_count'])
  res_list = await executor.execute(tasks)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  
  setCache('get_report_content_with_img,{0}'.format(json.dumps(res_list, ensure_ascii=False)), json.dumps(res_list, ensure_ascii=False), 'report_industry_img_' + current_time +'_')

  topic_name = stand_data['name']

  report_name = '{0}\n证券研究报告'.format(topic_name)
  file_name = SAVE_DIR + '/Macro_Research_Report.docx'
  
  return create_document.generate_report(res_list, file_name, report_name, data_date, target='宏观', target_name=topic_name )
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  return res_list

async def ainvoke(msg: str):
  import time
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  while True:
    try:
      res = await agent_executor(msg)
      break
    except Exception as e:
      print(e)
      logging.warning(f'执行出现异常,清除缓存后重试, 最后成功时间：{last_success_time}')
      clear_cache_with_time(last_success_time)
      time.sleep(2)
  return res

async def main():
  res = await agent_executor("我需要生成《“国家级“人工智能+”政策效果评估 (2023-2025)”》的研报")
  print(res)

if __name__ == '__main__':
  import asyncio
  asyncio.run(main())

  # asyncio.run(beautyfy_content())
  
