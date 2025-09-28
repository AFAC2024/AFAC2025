"""
生成个股研报的agent

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
from prompts import stock_prompts
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

class State(TypedDict):
    message: str
    context: List[Document]

invoke_util = llm_utils.InvokeUtil(llm, client)

agent = None
async def llm_invoke(msgs, call_type='llm', res_type='str'):
  return await invoke_util.ainvoke(msgs, call_type, res_type)
      
async def get_data_date(question: str):
    cache_key = 'get_data_date,,{0}'.format(question)
    cache = getCache(cache_key)
    if cache is not None:
      res = cache
    else:
      msgs = stock_prompts['tpl_get_data_date'].invoke({"roles": "股票分析师", "target": "个股", "msg": question}).to_messages()
      res = await llm_invoke(msgs)
      setCache(cache_key, res)

    if res == '无' or '-' not in res:
      return None

    return res

async def get_sotck_info(question: str):
    cache_key = 'get_sotck_info,{0}'.format(question)
    cache = getCache(cache_key)
    if cache is not None:
      return cache
    msgs = stock_prompts['tpl_get_comp_info'].invoke({"roles": "股票分析师", "target": "个股", "msg": question}).to_messages()
    res = await llm_invoke(msgs, call_type='agent')
    setCache(cache_key, res)
    return res

async def get_outline(comp_desc: str):
    cache_key = 'get_outline,{0}'.format(comp_desc)
    cache = getCache(cache_key)
    if cache is not None:
      cache = json.loads(cache)
      return cache
    msgs = stock_prompts['tpl_get_outline'].invoke({"roles": "资深财经主编", "target": "个股", "comp_desc": comp_desc}).to_messages()
    outline = await llm_invoke(msgs, res_type='json')
    setCache(cache_key, json.dumps(outline, ensure_ascii=False))
    return outline

async def get_comp_info_data(comp_desc):
    
    msgs = stock_prompts['tpl_get_comp_info_data'].invoke({"roles": "资深财经编辑、专业数据分析师", "target": "个股", "comp_desc": comp_desc}).to_messages()

    cache_key = 'get_comp_info_data,{0}'.format(str(msgs))
    cache = getCache(cache_key)
    if cache is not None:
       cache = json.loads(cache)
       return cache
    
    comp_data = await llm_invoke(msgs, res_type='json')
    setCache(cache_key, json.dumps(comp_data, ensure_ascii=False))
    return comp_data

async def get_section_content(section, compinfo, data_date, doc_idx=1):
  content = ''
  msg = stock_prompts['tpl_topic_info'].format(target=compinfo['name']
                                               , title=section['title']
                                               , desc=section['desc']
                                               , requirements=str(section['requirements']))
  summary_list = await agent_data.get_section_docs(msg, target='个股', start_idx=doc_idx)

  summary_content = ''
  idx = 1

  for summary in summary_list:
     summary_content += '{0}. {1}:{2}\n'.format(summary['idx'], summary['source'], summary['title'])
     summary_content += '{0}\n\n'.format(summary['summary'])
     idx += 1

  msgs = stock_prompts['tpl_general_section_content'].invoke({
      "roles": "资深财经编辑、专业数据分析师",
      "target": "个股",
      "title": section['title'],
      "summary": summary_content,
      "topic": msg,
      "object": compinfo['name']
    }).to_messages()

  content = await llm_invoke(msgs)

  return content, summary_list

async def get_key_words(outlines):
  outlines_txt = []
  for idx, outline in enumerate(outlines):
    outlines_txt.append('{0}.{1}\n主要内容：{2}\n要求：'.format(idx
                                                        , outline['title']
                                                        , outline['desc']
                                                        , str(outline['requirements'])))
  outlines_txt = '\n\n'.join(outlines_txt)
  print(outlines_txt)
  msgs = stock_prompts['tpl_get_key_words'].invoke({"roles": "资深财经编辑、专业数据分析师"
                                                    , "target": "个股"
                                                    , "outlines": outlines_txt}).to_messages()

  cache_key = 'get_key_words,{0}'.format(str(msgs))
  cache = getCache(cache_key)
  if cache is not None:
    return json.loads(cache)

  key_words = await llm_invoke(msgs, res_type='json')
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

  

  msgs = stock_prompts['tpl_beauty_section_content'].invoke({
      "roles": "资深财经编辑、专业编辑、研报编辑社资深主编",
      "target": '个股',
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

  print('开始执行个股研报生成任务，问题：', question)
  data_date = await get_data_date(question)
  print('data_date: ', data_date)

  comp_desc = await get_sotck_info(question)
  print(comp_desc)

  comp_data = await get_comp_info_data(comp_desc)
  print('企业信息', comp_data)

  if '请提供' in comp_desc and '生成研报' in comp_desc and '企业' in comp_desc and '名称' in comp_desc:
    logging.error(comp_desc)
    raise ValueError("抱歉，未能识别到您提供的企业信息，请试试提供完整的企业名称。")
  
  outlines = await get_outline(comp_desc)
  print('章节', outlines)

  key_words = await get_key_words(outlines)
  key_words['company'].append(comp_data['name'])
  print('数据关键字', key_words)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  
  content_info = []
  for idx, section in enumerate(outlines):
     content_info.append(f"段落{idx}. {section['title']}: {section['desc']}")
  content_info = "\n".join(content_info)

  # store.load_default_data()
  data_len = await agent_data.search_docs(key_words, comp_data['name'] + '研报\n\n' + content_info, data_date)
  print(data_len)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  res_list = []
  doc_idx = 0
  for section in outlines:
    content, summary_list = await get_section_content(section, comp_data, data_date, doc_idx=doc_idx)
    section['content'] = content
    section['sources'] = summary_list
    doc_idx += len(summary_list)
    res_list.append(section)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


  setCache('get_report_content,{0}'.format(json.dumps(res_list, ensure_ascii=False)), json.dumps(res_list, ensure_ascii=False), 'report_stock_' + current_time + '_')

  # 暂时不做了，做了缩减章节会降低分数
  # res_list = await beautyfy_content(comp_data, res_list)
  # setCache('get_report_content_beautfy,{0}'.format(json.dumps(res_list, ensure_ascii=False)), json.dumps(res_list, ensure_ascii=False), 'report_stock_beautfy_' + current_time + '_')

  # 加载本地缓存的debug代码
  # file_path = '/Users/nambo/Documents/project/tianchi/20250714AFAC2025/mcps/common/_cache/report_stock_2025072310:30:14__8720d59d40386ab91c0566260c87285d'
  # with open(file_path, 'r', encoding='utf-8') as f:
  #       file_content = f.read()
  # res_list = json.loads(file_content)

  print('内容生成完成:', len(res_list))
  all_sources = []
  for section in res_list:
     all_sources += section['sources']

  print('开始生成图表:', len(res_list))
  tasks = []
  for section in res_list:
    topic = stock_prompts['tpl_topic_info'].format(target=comp_data['name']
                                                   , title=section['title']
                                                   , desc=section['desc']
                                                   , requirements=str(section['requirements']))
    tasks.append((agent_chart.get_paragraph_chart_worker, (topic, section, all_sources, '个股'), {}))
  
  executor = parallelism.AsyncConcurrentExecutor(max_concurrent=config.conf['parallelism_count'])
  res_list = await executor.execute(tasks)
  last_success_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  setCache('get_report_content_with_img,{0}'.format(json.dumps(res_list, ensure_ascii=False)), json.dumps(res_list, ensure_ascii=False), 'report_stock_img_' + current_time + '_')

  report_name = '{0}（{1}.{2}）\n证券研究报告​​'.format(comp_data['name'], comp_data['code'], str.upper(comp_data['market']))
  file_name = SAVE_DIR + '/Company_Research_Report.docx'
  create_document.generate_report(res_list, file_name, report_name, data_date, '个股', comp_data['name'])
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
  res = await agent_executor("我需要生成4Paradigm（02220.HK）的研报")
  # print(res)

if __name__ == '__main__':
  import asyncio
  asyncio.run(main())

  # asyncio.run(beautyfy_content())
  
