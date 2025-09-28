"""
图表绘制agent

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
import re

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import config
from mcps.tools import store
from prompts import chart_prompts, stock_prompts
from mcps.common.cache import removeCache, getCache, setCache, get_md5
from agent.common import llm_utils

# 配置日志
logging.basicConfig(
    level=logging.DEBUG
)

client = MultiServerMCPClient({
  "stock": {
    "command": config.conf['python_path'],
    "args": ["./mcps/server_chart.py"],
    "transport": "stdio",
  }
})
invoke_util = llm_utils.InvokeUtil(client=client)

async def llm_invoke(msgs, call_type='llm', res_type='str'):
  return await invoke_util.ainvoke(msgs, call_type, res_type)

def split_conetent(content):
  print('split_conetent开始切割章节内容')
  res_list = []
  tmp_list = []
  if '\n\n' in content:
    content = re.sub(r'\n+', '\n', content)
  if '\n' in content:
    tmp_list = content.split('\n')
  else:
    tmp_list = [content]
  
  i = 0
  while i < len(tmp_list):
    txt_now = tmp_list[i]
    if len(txt_now) > 100:
      res_list.append(txt_now)
    else:
      if i + 1 < len(tmp_list):
        tmp_list[i+1] = txt_now + '\n' + tmp_list[i+1]
    i += 1

  return res_list

async def draw_chart(topic, content, chart, target="个股"):
  """
  绘制图表
  参数：
    topic: 章节标题
    content: 段落内容
    chart_info: 图表信息
    target: 目标类型（个股/行业）
  """

  cache_key = 'draw_chart1,{0},{1}'.format(topic, content)
  cache = getCache(cache_key)
  if cache is not None:
    cache = json.loads(cache)
    return cache
  
  content_source_msgs = []
  for s_i, source in enumerate(chart['sources']):
    try:
      data = await store.get_content(key=source['key'], handler=source['handler'])
      source['data'] = data
    except Exception as e:
      logging.error(f"获取数据源失败: {source['title']} - {e}")
      continue
    if data is None or len(data) == 0:
      logging.error(f"数据源内容为空: {source['title']}")
      continue

    content_source_msgs.append('数据{0}: {1}\n{2})'.format(s_i, source['title'], data))
  
  if len(content_source_msgs) <= 0:
    logging.error(f"没有有效的数据源可用于绘图")
    return {
      "success": 0,
      "title": "",
      "desc": "",
      "path": ""
    }
  
  content_source_msgs = '\n'.join(content_source_msgs)
  
  msgs = chart_prompts['tpl_draw_chart_data'].invoke({
    "roles": "资深财经数据分析师、专业数据可视化专家",
    "target": target,
    "topic": topic,
    "content": content,
    "img_title": chart['title'],
    "img_desc": chart['img_desc'],
    "datas": content_source_msgs,
    }).to_messages()
  
  data_msg = await llm_invoke(msgs)

  print('绘图数据生成成功：', data_msg)

  msgs = chart_prompts['tpl_draw_chart'].invoke({
    "roles": "资深财经数据分析师、专业数据可视化专家",
    "target": target,
    "topic": topic,
    "content": content,
    "img_title": chart['title'],
    "img_desc": chart['img_desc'],
    "datas": data_msg,
    }).to_messages()
  
  try:
    chart_item = await llm_invoke(msgs, call_type='agent', res_type='json')
    chart_item['sources'] = chart['sources']

    setCache(cache_key, json.dumps(chart_item, ensure_ascii=False))
    return chart_item
  except Exception as e:
    logging.warning('配图生成失败 ' + str(msgs))
    logging.error(e)
    raise e
    return {
      "success": 0,
      "title": "",
      "desc": "",
      "path": ""
    }
  
async def get_chart_list(topic, content_list, data_sources, target):

  content_msg = []
  for idx, content in enumerate(content_list):
    content = content.strip()
    content_msg.append('段落{0}: '.format(idx + 1) + content)
  content_msg = '\n'.join(content_msg)

  source_msg = []
  source_map = {}
  use_source = []
  for idx, source in enumerate(data_sources):
    unique_key = get_md5(source['key'] + source['handler'])
    if unique_key not in source_map and (source['file_type'] == 'csv' or source['file_type'] == 'json'):
      item = {
        "title": source['title'],
        "source": source['source'],
        "key": source['key'],
        "handler": source['handler'],
        "idx": source['idx']
      }
      source_msg.append('数据源序号：{0}. '.format(len(use_source)) + json.dumps(item, ensure_ascii=False))
      source_map[unique_key] = True
      use_source.append(item)
  source_msg = '\n'.join(source_msg)

  print('get_content_chart开始生产配图方案')
  content_len = str(len(content_list))

  charts = []
  try_count = 0
  while len(charts) != len(content_list):
    other_info = ''
    if try_count > 0:
      other_info = f'\n\n一定要注意返回数组长度，这是第{try_count}次重试'
    msgs = chart_prompts['tpl_paragraph_chart_list'].invoke({
      "roles": "资深财经数据分析师、专业数据可视化专家",
      "target": target,
      "topic": topic,
      "paragraph": content_msg,
      "content_len": content_len,
      "sources": source_msg,
      "other_info": other_info
      }).to_messages()
    charts = await llm_invoke(msgs, call_type='agent', res_type='json')
    if len(charts) != len(content_list):
      try_count += 1
      print(f'生成的配图方案长度{len(charts)}与contentlist长度{len(content_list)}不一致，重新生成次数{try_count}')

  return charts, use_source

async def get_content_chart(topic, content_list, data_sources, target="个股"):
  print('get_content_chart开始', topic)

  charts, use_source = await get_chart_list(topic, content_list, data_sources, target)

  for chart in charts:
    if 'imgs' in chart:
      imgs=  chart['imgs']
      for img in imgs:
        if 'sources' in img:
          source_ids = img['sources']
          source_list = []
          for sid in source_ids: 
            if int(sid) < len(use_source):
              source = use_source[int(sid)]
              source_list.append(source)
          img['sources'] = source_list

  chart_res = []
  print('get_content_chart开始配图')
  for i, chart in enumerate(charts):
    print("开始绘制段落配图, 进度：{0}/{1}".format(i, len(charts)))
    content_imgs = []
    if i < len(content_list):
      content = content_list[i]
      if chart['need'] == 0 or len(chart['imgs']) <= 0:
        chart_res.append(content_imgs)
        continue
      for img_idx, img in enumerate(chart['imgs']):
        print("开始图标, 进度：{0}/{1}->{2}/{3}".format(i, len(charts), img_idx, len(chart['imgs'])))
        draw_count = 0
        while draw_count < 5:
          try:
            chart_item = await draw_chart(topic, content, img, target)
            content_imgs.append(chart_item)
            break
          except Exception as e:
            print(e)
            logging.warning('生图失败，将重试: ', draw_count)
            draw_count += 1
            if draw_count >= 5:
              logging.warning("生图持续失败，跳过当前图片: " + str(img))
      chart['charts'] = content_imgs
      chart['content'] = content
  
  setCache('get_paragraph_chart,{0},{1}'.format(topic, json.dumps(content_list), json.dumps(data_sources))
           , json.dumps(charts, ensure_ascii=False)
           , prefix='report_chart_')
  
  print('开始合并配图结果')
  res_list = []
  for idx, chart in enumerate(charts):
    res_item = {
      "content": content_list[idx],
    }
    if chart['need'] == 1 and len(chart['charts']) > 0:
      res_imgs = []
      for img_item in chart['charts']:
        if img_item is not None and 'success' in img_item and img_item['success'] == 1:
          res_imgs.append({
            "title": img_item['title'],
            "desc": img_item['desc'],
            "path": img_item['path'],
          })
      res_item['imgs'] = res_imgs
    res_list.append(res_item)
  return res_list

async def get_paragraph_chart_worker(topic, section, all_sources, target):
  content_with_imgs = await get_paragraph_chart(topic, section, all_sources, target='个股')
  section['content_list'] = content_with_imgs
  return [section]

async def get_paragraph_chart(topic, paragraph, sources, target="个股"):
  print('开始生成图表', topic, paragraph)
  cache_key = 'get_paragraph_chart,{0},{1}'.format(topic, paragraph, target)
  cache = getCache(cache_key)
  if cache is not None:
    return json.loads(cache)

  content_list = split_conetent(paragraph['content'])
  res = await get_content_chart(topic, content_list, sources, target)

  return res

if __name__ == '__main__':
  import asyncio
  topic = stock_prompts['tpl_topic_info'].format(target='宁德时代', title='现金流匹配度与资本支出分析', desc='分析宁德时代经营性、投资性和筹资性现金流的匹配情况，评估其资本支出策略及资金链稳定性。', requirements='大方美观')
  paragraph = {
    "title": "现金流匹配度与资本支出分析",
    "desc": "分析宁德时代经营性、投资性和筹资性现金流的匹配情况，评估其资本支出策略及资金链稳定性。",
    "content": "宁德时代在2025年一季度的现金流表现整体稳健，经营性、投资性和筹资性现金流之间形成了较为合理的匹配关系。从经营活动来看，公司销售商品及提供劳务收到的现金为111,139.84万元，占经营性现金流入的绝大部分，反映出其较强的市场销售能力和资金回笼能力。同期经营性现金流出为86,238.81万元，主要用于采购和职工薪酬等日常运营支出，最终实现经营性现金流净额32,868.26万元，显示出良好的盈利质量与运营效率[:1]。\n\n在投资活动方面，公司持续加大资本开支力度，购建固定资产及其他长期资产的支出达108,144.00万元，导致投资性现金流净流出177,705.54万元。这一趋势也体现在财务指标摘要中，显示公司正处于产能扩张的关键阶段，投资性现金流受资本支出影响较大，表明其正积极布局未来增长点[:4]。截至2025年3月31日，公司货币资金达321.32亿元，在建工程合计为289.79亿元，进一步佐证了其当前较高的资本支出水平[:7]。\n\n为了应对资本支出带来的资金压力，公司在筹资活动中通过借款等方式获取资金支持。2025年一季度筹资性现金流净流入为16,141.10万元，主要来源于取得借款的现金流入。此外，公司此前已使用募集资金3,847,859.51万元，并计划将不超过45亿元的闲置募集资金用于短期现金管理，以提高资金使用效率并增强股东回报[:2][:3]。这些举措有助于缓解因资本支出而产生的资金缺口，同时优化资金结构。\n\n总体而言，宁德时代的现金流匹配度良好，流动比率与速动比率表现稳健，资产负债率处于合理区间，显示出较强的资金链稳定性。尽管资本支出规模较大，但公司通过多渠道融资和高效的资金管理手段，有效支撑了其战略扩张需求，未对正常经营造成明显负面影响。",
    "sources": [
        {
            "title": "截止2025-07-20宁德时代的现金流量表",
            "url": "https://www.szse.cn/certificate/individual/index.html?code=300750",
            "source": "深圳证券交易所",
            "file_type": "csv",
            "key": "get_financial_report|300750|现金流量表|sz|2025-07-20",
            "handler": "stock_akshare",
            "summary": "宁德时代2025年3月31日数据显示，经营活动现金流入小计为119,107.07万元，其中销售商品、提供劳务收到的现金为111,139.84万元，占比较大；经营性现金流出小计为86,238.81万元，主要用于支付采购及职工薪酬等。经营活动产生的现金流量净额为32,868.26万元，资金回笼能力良好。投资活动方面，购建固定资产等支出达108,144.00万元，显示公司持续扩大资本开支，而投资活动现金流入较少，净流出177,705.54万元。筹资活动现金流入主要来自取得借款，总流入为286,300.84万元，偿还债务支付现金为270,159.73万元，筹资活动净流入16,141.10万元。整体来看，公司现金流匹配度尚可，但需关注资本支出对资金链的长期影响。",
            "idx": 41
        },
        {
            "title": "宁德时代：关于使用部分闲置募集资金进行现金管理的公告",
            "url": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/215a951f-2b54-4c9d-a6cc-0d6dcc0d88b8.PDF",
            "source": "深圳证券交易所",
            "file_type": "pdf",
            "key": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/215a951f-2b54-4c9d-a6cc-0d6dcc0d88b8.PDF",
            "handler": "report_sz",
            "summary": "截至2025年5月31日，宁德时代2022年向特定对象发行股票募集资金已使用3,847,859.51万元，尚未使用的余额为728,164.49万元（含利息收入净额89,012.67万元）。公司拟在不影响募投项目建设的前提下，使用不超过45亿元的闲置募集资金进行现金管理，投资于安全性高、流动性好的保本型存款产品，期限不超过12个月。本次现金管理事项已通过董事会和监事会审议，并获保荐人无异议意见，旨在提高资金使用效率并增强股东回报。",
            "idx": 42
        },
        {
            "title": "宁德时代：中信建投证券股份有限公司关于宁德时代新能源科技股份有限公司使用部分闲置募集资金进行现金管理的核查意见",
            "url": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d41c7aa5-3c7b-4912-a2f7-8150b202159a.PDF",
            "source": "深圳证券交易所",
            "file_type": "pdf",
            "key": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d41c7aa5-3c7b-4912-a2f7-8150b202159a.PDF",
            "handler": "report_sz",
            "summary": "截至2025年5月31日，宁德时代2022年向特定对象发行股票募集资金总额为4,499,999.98万元，实际净额4,487,011.32万元，已投入使用3,847,859.51万元，尚余728,164.49万元（含利息收入89,012.67万元）未使用。公司拟使用不超过45亿元的闲置募集资金进行现金管理，投资期限不超过12个月的保本型存款产品，以提高资金使用效率。此前，公司曾于2024年3月审议通过65亿元额度的类似方案，并实现100%兑付本金。本次事项经董事会及监事会审议批准，保荐人认为其符合监管规定，不影响募投项目正常推进。",
            "idx": 43
        },
        {
            "title": "截止2025-07-20宁德时代的财务指标摘要",
            "url": "https://www.szse.cn/certificate/individual/index.html?code=300750",
            "source": "深圳证券交易所",
            "file_type": "csv",
            "key": "get_financial_abstract|300750|sz|2025-07-20",
            "handler": "stock_akshare",
            "summary": "宁德时代在报告期实现净利润及扣非净利润双增长，经营性现金流表现稳健，每股经营现金流为正值，反映出较强的盈利质量。投资性现金流受资本支出影响较大，公司持续加大投入以支持产能扩张。筹资性现金流则主要用于补充投资资金缺口。资产负债率处于合理区间，流动比率与速动比率表现良好，体现出较强的资金链稳定性。",
            "idx": 44
        },
        {
            "title": "宁德时代：关于全资子公司参与投资产业投资基金的公告",
            "url": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF",
            "source": "深圳证券交易所",
            "file_type": "pdf",
            "key": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF",
            "handler": "report_sz",
            "summary": "宁德时代全资子公司香港时代拟以不超过2.25亿美元认缴出资参与投资Lochpine Green Fund I, LP产业投资基金，基金目标规模为15亿美元，主要围绕碳中和领域上下游进行投资。该基金由Lochpine Capital Limited管理，组织形式为开曼豁免有限合伙企业，存续期基本为10年，收益按协议分配。公司表示本次投资资金来源为境外自有资金，不影响正常经营，有助于拓展碳中和业务布局并获取合理回报。同时提示基金投资周期长、流动性低及潜在收益不达预期等风险。",
            "idx": 45
        },
        {
            "title": "宁德时代：关于参与投资产业投资基金的进展公告",
            "url": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/59d421a4-1d72-4cf2-bf6d-4609f6b43e98.PDF",
            "source": "深圳证券交易所",
            "file_type": "pdf",
            "key": "https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/59d421a4-1d72-4cf2-bf6d-4609f6b43e98.PDF",
            "handler": "report_sz",
            "summary": "宁德时代作为有限合伙人参与设立的福建时代泽远股权投资基金合伙企业（有限合伙）已正式完成工商注册及私募投资基金备案，基金总规模为1,012,800万元，公司认缴出资70,000万元，出资比例由13.76%降至6.91%。该基金主要投资于新能源及高端制造领域，旨在通过市场化机制拓展碳中和生态布局，获取合理投资回报。",
            "idx": 46
        },
        {
            "title": "截止2025-07-20宁德时代的资产负债表",
            "url": "https://www.szse.cn/certificate/individual/index.html?code=300750",
            "source": "深圳证券交易所",
            "file_type": "csv",
            "key": "get_financial_report|300750|资产负债表|sz|2025-07-20",
            "handler": "stock_akshare",
            "summary": "宁德时代截至2025年3月31日，经营性现金流净额为89,988.9万元，投资性现金流净额为-208,506.66万元，筹资性现金流净额为79,844.17万元。公司货币资金达321.32亿元，在建工程合计为289.79亿元，固定资产净额为251.37亿元。流动资产合计为820.097亿元，其中存货为65.64亿元；流动负债合计为328.21亿元，非流动负债合计为230.13亿元。整体来看，公司现金流匹配度良好，资本支出规模较大，资金链稳定性较强。",
            "idx": 47
        }
    ]
  }
  sources = [{"title":"宁德时代企业基本信息","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"pdf","key":"get_company_basic_info|300750|sz","handler":"stock_bd","summary":"宁德时代（股票代码：300750）全称为宁德时代新能源科技股份有限公司，于2018年6月11日在深圳证券交易所上市，总发行股份数为2.17亿股。公司位于福建省，属于电池行业，是全球领先的新能源创新科技公司，专注于动力电池及储能电池的研发、生产与销售。主要产品包括锂离子电池、动力电池、储能电池及相关电池管理系统，应用领域涵盖新能源汽车和储能系统等。主营业务还包括锂电池及相关产品的技术服务、测试服务以及咨询服务，并涉及对新能源行业的投资。","idx":2},{"title":"宁德时代：《宁德时代新能源科技股份有限公司章程》（2025年6月修订）","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d40a5acb-3634-4099-bb41-a680e851dd67.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d40a5acb-3634-4099-bb41-a680e851dd67.PDF","handler":"report_sz","summary":"宁德时代新能源科技股份有限公司（股票代码：300750.SZ、300750.HK）于2018年6月11日在深圳证券交易所创业板上市，并于2025年5月20日在香港联交所上市。公司注册资本为455,931.0311万元，主营业务聚焦新能源领域，主要产品涵盖动力电池系统、储能系统及锂电池材料等，广泛应用于新能源汽车、电动交通工具及储能等领域。","idx":3},{"title":"宁德时代：关于境外上市外资股（H股）挂牌并上市交易的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-20/9f1efe7a-2f6a-4930-b108-5b96e2de83f7.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-20/9f1efe7a-2f6a-4930-b108-5b96e2de83f7.PDF","handler":"report_sz","summary":"宁德时代新能源科技股份有限公司（证券代码：300750，简称“宁德时代”）主要从事新能源创新科技业务，主要产品涵盖动力电池系统、储能系统及锂电池材料等，广泛应用于新能源汽车、电动交通工具及能源存储等领域。公司于2025年5月20日在香港联交所主板挂牌上市，H股股票中文简称为“寧德時代”，英文简称为“CATL”，股份代号为“3750”。本次全球发售H股总数为135,578,600股（行使超额配售权前），发售价为每股263港元，预计募集资金净额约为353.31亿港元。","idx":4},{"title":"宁德时代：关于境外上市外资股（H股）公开发行价格的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/233d73f8-4b9c-4821-82df-7c2aa8d78114.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/233d73f8-4b9c-4821-82df-7c2aa8d78114.PDF","handler":"report_sz","summary":"宁德时代新能源科技股份有限公司（证券代码：300750）拟发行境外上市外资股（H股），并在香港联合交易所有限公司主板挂牌上市。本次H股发行最终定价为每股263港元（不含相关费用），预计于2025年5月20日开始在香港联交所上市交易。","idx":5},{"title":"截止2025-07-20宁德时代的主营业务构成","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_business_composition|300750|sz|2025-07-20","handler":"stock_bd","summary":"宁德时代（股票代码：300750.SZ），主营业务涵盖动力电池系统、储能电池系统、电池材料及回收及其他补充业务。2024年，公司动力电池系统收入为2530亿元，占比69.90%；储能电池系统收入572.90亿元，占比15.83%；电池材料及回收收入287.00亿元，占比7.93%；其他业务收入229.81亿元，占比6.35%。按地区划分，境内收入2517亿元，占比69.52%；境外收入1103亿元，占比30.48%。","idx":6},{"title":"精准服务，用好“赋能之手”(评论员观察)","url":"http://www.chinanews.com.cn/ll/2025/06-06/10427712.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/ll/2025/06-06/10427712.shtml","handler":"news","summary":"宁德时代（股票代码：300750.SZ）于深圳证券交易所上市，主营业务涵盖动力电池、储能系统及新能源创新技术的研发与生产。其产品广泛应用于新能源汽车领域，并在全球市场占据领先地位，2024年以绝对优势位居全球储能出货排行榜首位。2025年，宁德时代在欧洲智慧能源展上发布全球首款可量产的9兆瓦时超大容量储能系统解决方案，进一步巩固其行业影响力。","idx":7},{"title":"广东建成首个全链条新型储能产业基地","url":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","handler":"news","summary":"宁德时代新能源科技股份有限公司(股票代码：300750.SZ)是全球领先的新能源创新科技公司，其动力电池使用量连续八年全球第一，储能电池出货量连续四年全球第一。瑞庆时代为宁德时代全资子公司，主要负责锂离子电池及相关系统的研发与制造，产品涵盖电芯、电池模组、电箱/电柜及储能集装箱系统。目前，瑞庆时代已在广东肇庆建成全链条新型储能产业基地，助力广东打造全球竞争力的新型储能产业高地。","idx":8},{"title":"以产业向新助力经济向好——进一步巩固经济持续回升向好基础③","url":"https://www.gov.cn/zhengce/202504/content_7020925.htm","source":"中国人民政府网","file_type":"htm","key":"https://www.gov.cn/zhengce/202504/content_7020925.htm","handler":"zhengce_rmzf","summary":"宁德时代（股票代码：300750.SZ）是一家在中国深圳证券交易所上市的新能源行业龙头企业，主营业务聚焦于锂离子电池的研发、生产和销售，产品广泛应用于新能源汽车、储能系统及电动工具等领域。作为锂电新能源产业的重要龙头，宁德时代带动福建宁德市形成较为完整的锂电产业链生态，目前当地已集聚80多家上下游企业，80%的采购实现就近配套，显著提升了区域产业集群的发展水平和全球竞争力。","idx":9},{"title":"“创”出新活力 “闯”出新优势——从三个关键词看民营企业科技创新","url":"http://www.chinanews.com.cn/gn/2025/05-22/10419994.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/gn/2025/05-22/10419994.shtml","handler":"news","summary":"宁德时代（股票代码：300750.SZ）是一家在中国深圳证券交易所上市的新能源科技企业，主营业务涵盖锂离子电池的研发、生产和销售，产品广泛应用于新能源汽车、储能系统及消费电子等领域。公司近年来持续加强核心技术攻关，如针对北方低温环境研发钠离子电池技术，实现零下40摄氏度环境下90%的可用电量，并积极拓展多元应用场景，巩固其在新能源产业链中的领先地位。","idx":10},{"title":"精准服务，用好“赋能之手”(评论员观察)","url":"http://www.chinanews.com.cn/ll/2025/06-06/10427712.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/ll/2025/06-06/10427712.shtml","handler":"news","summary":"宁德时代在全球动力电池市场中占据领先地位，2024年储能出货量全球第一，并推出全球首款可量产的9兆瓦时超大容量储能系统解决方案。目前，全球每销售3辆新能源车就有1辆搭载其电池，展现出强大的技术创新能力和市场占有率。同时，福建宁德通过优化营商环境、强化产业配套及政策支持，助力企业专注实业与创新，为其行业地位的巩固提供了有力支撑。","idx":11},{"title":"以产业向新助力经济向好——进一步巩固经济持续回升向好基础③","url":"https://www.gov.cn/zhengce/202504/content_7020925.htm","source":"中国人民政府网","file_type":"htm","key":"https://www.gov.cn/zhengce/202504/content_7020925.htm","handler":"zhengce_rmzf","summary":"宁德时代作为锂电新能源行业龙头，带动福建宁德市积极布局产业链，目前当地已集聚80多家锂电上下游企业，形成较为完整的产业链生态，80%的采购实现就近配套。这一产业集群不仅提升了企业的协同发展能力，也增强了中国制造在全球供应链中的竞争力。","idx":12},{"title":"“创”出新活力 “闯”出新优势——从三个关键词看民营企业科技创新","url":"http://www.chinanews.com.cn/gn/2025/05-22/10419994.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/gn/2025/05-22/10419994.shtml","handler":"news","summary":"宁德时代在低温电池技术方面取得突破，其发布的钠新电池在零下40摄氏度环境下仍可保持90%的可用电量，并通过多元快离子脱嵌、复合抗冻电解液等技术创新提升产品性能。当前，全球新能源汽车产业链优势持续扩大，中国新能源汽车出口前4月同比增长52.6%，达到64.2万辆，宁德时代作为核心供应商之一，在行业竞争中占据重要地位。","idx":13},{"title":"广东建成首个全链条新型储能产业基地","url":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","handler":"news","summary":"宁德时代动力电池使用量连续八年全球第一，储能电池出货量连续四年全球第一。其全资子公司瑞庆时代在广东肇庆建成涵盖电芯至储能集装箱系统集成的全链条研发制造基地，填补华南地区储能全产业链制造技术空白。二阶段工程投产后，将进一步助力广东打造万亿元规模的新型储能产业集群和全球竞争力产业高地。","idx":14},{"title":"宁德时代企业基本信息","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"pdf","key":"get_company_basic_info|300750|sz","handler":"stock_bd","summary":"宁德时代（300750）是全球领先的新能源创新科技公司，专注于动力电池及储能电池的研发、生产与销售。公司主要产品包括锂离子电池、动力电池、储能电池及相关系统解决方案，业务覆盖电池制造、技术服务及新能源投资等领域。作为中国电池行业的领军企业，宁德时代凭借强大的技术创新能力、广泛的合作伙伴关系以及在全球市场的高占有率，持续巩固其在动力电池行业的领先地位。","idx":15},{"title":"共建创新之路 第二届“一带一路”科技交流大会启动多项计划","url":"http://www.chinanews.com.cn/shipin/cns/2025/06-12/news1022718.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/shipin/cns/2025/06-12/news1022718.shtml","handler":"news","summary":"宁德时代董事长兼CEO曾毓群在第二届“一带一路”科技交流大会上提出，深化新能源领域合作需以开放共享为核心。当前，中国新能源车企加速出海，在“一带一路”共建国家用户基础持续扩大，宁德时代作为核心配套企业，凭借技术创新与全球布局，进一步巩固其在全球动力电池行业的领先地位。","idx":16},{"title":"香江观澜：香港乘势而上打造内地车企出海“桥头堡”","url":"http://www.chinanews.com.cn/dwq/2025/06-15/10432681.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/dwq/2025/06-15/10432681.shtml","handler":"news","summary":"宁德时代作为全球动力电池行业的重要参与者，展现出强大的核心竞争力和行业地位。2024年“全球汽车供应链百强”中，宁德时代位列前二十，彰显其在全球供应链中的关键角色。2025年，宁德时代在港上市，募资超千亿港元，其中90%资金用于推进匈牙利项目第一期及第二期建设，体现其全球化布局的加速。凭借技术创新能力和市场拓展能力，宁德时代正持续巩固其在全球动力电池行业的领先地位。","idx":17},{"title":"中国技术成全球车企采购的“必选项”","url":"http://www.chinanews.com.cn/cj/2025/06-30/10440534.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/cj/2025/06-30/10440534.shtml","handler":"news","summary":"宁德时代在全球动力电池行业中占据重要地位，凭借电池能量密度和续航优势，与比亚迪共同占据全球市场半壁江山，并成为丰田、特斯拉等国际车企的供应商。中国新能源汽车市场的超大规模及制造能力为技术创新提供了广阔空间，推动宁德时代在动力电池领域建立起核心技术优势。与此同时，中国汽车技术正从“输入国”向“输出国”转变，宁德时代作为行业领军企业，深度参与全球供应链体系，助力跨国车企电动化转型，巩固其在全球动力电池行业的领先地位。","idx":18},{"title":"百年前美国福特的一封拒信 如今变成“邀请函”","url":"http://www.chinanews.com.cn/gn/shipin/cns-d/2025/06-18/news1023217.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/gn/shipin/cns-d/2025/06-18/news1023217.shtml","handler":"news","summary":"宁德时代与福特在电动汽车领域展开合作，彰显其在全球动力电池行业的竞争力。6月17日，宁德时代首席制造官倪军在接待马英九及宋涛参观时介绍，百年间中国从技术引进方转变为技术输出方，福特为发展电动车选择与宁德时代签约，标志着中国企业在国际产业链中的地位提升。","idx":19},{"title":"宁德时代：H股公告（翌日披露报表）","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/d1bff047-a926-4808-970d-bbea1892e338.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/d1bff047-a926-4808-970d-bbea1892e338.PDF","handler":"report_sz","summary":"宁德时代于2025年5月20日完成H股在香港联交所主板的新上市，证券代码为03750。截至2025年5月20日，已发行H股股份为135,578,600股。2025年5月23日，公司根据超额配股权发行及配发H股股份20,336,700股，每股发行价为HKD 263，占变动前已发行股份的15%。变动后，宁德时代已发行股份总数增至155,915,300股。","idx":20},{"title":"截止2025-07-20宁德时代的资产负债表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|资产负债表|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代2025年3月31日财务数据显示，流动资产合计为820.1亿元，其中货币资金达321.32亿元，应收账款439.11亿元。非流动资产合计为530.96亿元，固定资产净额为251.37亿元，在建工程合计为56.48亿元。负债方面，流动负债合计为482.42亿元，其中应付账款及应付票据合计为208.51亿元；非流动负债合计为219.48亿元，主要由长期借款和应付债券构成。所有者权益合计为289.14亿元，归属于母公司股东权益为261.56亿元。","idx":21},{"title":"宁德时代：中信建投证券股份有限公司关于宁德时代新能源科技股份有限公司使用部分闲置募集资金进行现金管理的核查意见","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d41c7aa5-3c7b-4912-a2f7-8150b202159a.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d41c7aa5-3c7b-4912-a2f7-8150b202159a.PDF","handler":"report_sz","summary":"宁德时代2022年向特定对象发行股票募集资金总额为4,499,999.98万元，扣除发行费用后实际净额为4,487,011.32万元。截至2025年5月31日，已使用募集资金3,847,859.51万元，尚未使用的余额为728,164.49万元（含利息收入89,012.67万元）。公司拟使用不超过45亿元闲置募集资金进行现金管理，投资于安全性高、流动性好的保本型存款产品，期限不超过12个月，并已通过董事会及监事会审议。","idx":22},{"title":"截止2025-07-20宁德时代的利润表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|利润表|sz|2025-07-20","handler":"stock_akshare","summary":"2025年3月31日，宁德时代营业总收入达847.05亿元，营业成本为640.30亿元，研发费用为48.14亿元，销售费用为85.23亿元，管理费用为26.24亿元，财务费用为-22.88亿元。投资收益为7.83亿元，公允价值变动收益为13.39亿元。最终实现归属于母公司所有者的净利润148.62亿元，基本每股收益为3.18元。数据来源于合并期末的定期报告，尚未审计，公告日期为2025年4月15日。","idx":23},{"title":"截止2025-07-20宁德时代的现金流量表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|现金流量表|sz|2025-07-20","handler":"stock_akshare","summary":"2025年3月31日，宁德时代经营活动现金流入小计为119,107.07万元，其中销售商品、提供劳务收到的现金为111,139.84万元，收到其他与经营活动有关的现金为6,572.12万元。经营活动现金流出小计为86,238.81万元，主要支出包括支付给职工及为职工支付的现金7,189.75万元、支付的各项税费7,120.78万元及购买商品、接受劳务支付的现金69,577.37万元。经营活动产生的现金流量净额为32,868.26万元。投资活动现金流入小计为103,426.06万元，现金流出小计为195,822.58万元，净流出92,396.52万元。筹资活动现金流入小计为286,300.84万元，现金流出小计为270,159.73万元，净流入16,141.11万元。期末现金及现金等价物余额为117,878.97万元。","idx":24},{"title":"截止2025-07-20宁德时代的财务指标摘要","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_abstract|300750|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代报告期数据显示，其净利润及扣非净利润均实现同比增长，营业总收入亦保持增长态势，基本每股收益、每股净资产等指标反映公司盈利能力和股东权益状况良好。销售净利率与毛利率表现稳定，净资产收益率（摊薄）显示资本回报能力。现金流方面，每股经营现金流为正值，体现良好的经营回款能力。资产结构上，流动比率、速动比率及资产负债率等指标反映公司流动性较优，资产结构稳健。","idx":25},{"title":"宁德时代：H股公告（翌日披露报表）","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/d1bff047-a926-4808-970d-bbea1892e338.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/d1bff047-a926-4808-970d-bbea1892e338.PDF","handler":"report_sz","summary":"宁德时代于2025年5月23日根据超额配股权发行及配发H股股份，共增发20,336,700股，每股发行价为263港元，占发行前已发行股份的15%。此次变动后，公司已发行股份总数由135,578,600股增至155,915,300股。公司H股已于2025年5月20日在香港联交所主板新上市。","idx":26},{"title":"宁德时代：关于持股5%以上股东持股比例被动稀释触及1%整数倍的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-20/04817d2b-feaf-446a-84b2-945953004a5a.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-20/04817d2b-feaf-446a-84b2-945953004a5a.PDF","handler":"report_sz","summary":"宁德时代控股股东厦门瑞庭投资有限公司持股数量保持不变，为1,024,704,949股。因公司实施股权激励及H股上市，总股本由4,399,041,236股增至4,538,973,511股，厦门瑞庭持股比例由23.29%被动稀释至22.58%，降幅0.71个百分点。其中，股权激励使总股本增至4,403,394,911股，持股比例降至23.27%；H股发行135,578,600股后，进一步稀释至22.58%。","idx":27},{"title":"宁德时代：《宁德时代新能源科技股份有限公司章程》（2025年6月修订）","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d40a5acb-3634-4099-bb41-a680e851dd67.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d40a5acb-3634-4099-bb41-a680e851dd67.PDF","handler":"report_sz","summary":"截至2025年6月，宁德时代注册资本为人民币455,931.0311万元。公司股权结构显示，其前十大股东合计持股比例未直接披露，但通过章程内容可知，公司已实现A+H股上市，其中A股于2018年6月11日在深交所创业板上市，H股于2025年5月20日在香港联交所上市，体现了公司股权的多元化与国际化布局。股权结构的稳定性及主要股东的治理参与程度对公司战略决策和经营方向具有重要影响。","idx":28},{"title":"宁德时代的十大股东","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_stock_holder|300750|sz","handler":"stock_bd","summary":"宁德时代前十大股东中，厦门瑞庭投资有限公司以22.47%的持股比例位列第一，持股数量为10.25亿股，持股未变。黄世霖、宁波联合创新新能源投资管理合伙企业(有限合伙)及李平分别持股10.22%、6.23%和4.42%，持股亦保持稳定。机构方面，香港中央结算有限公司减持324.51万股至5.52亿股，持股比例12.10%。易方达及华泰柏瑞旗下基金分别增持110.14万股和28.55万股。此外，中国建设银行-易方达沪深300 ETF新进十大股东名单，持股0.66%。","idx":29},{"title":"宁德时代：关于股东无偿捐赠部分公司股份的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-12/1a108370-1d0b-4c6d-8697-62ff86ac1a70.pdf","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-12/1a108370-1d0b-4c6d-8697-62ff86ac1a70.pdf","handler":"report_sz","summary":"宁德时代副董事长李平先生拟无偿捐赠405万股公司股份（占总股本0.1%）予上海复旦大学教育发展基金会，用于设立“复旦大学学敏自然科学研究基金”。捐赠完成后，李平持股由201,510,277股（4.58%）降至197,460,277股（4.48%）。本次捐赠通过协议转让方式完成，非交易过户，符合相关法律法规要求。","idx":30},{"title":"宁德时代：关于股东无偿捐赠部分公司股份的进展公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-07-10/12c04174-566b-4a1a-bf18-841150673d5e.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-07-10/12c04174-566b-4a1a-bf18-841150673d5e.PDF","handler":"report_sz","summary":"宁德时代副董事长李平向上海复旦大学教育发展基金会捐赠405万股公司股份，占总股本的0.09%。捐赠完成后，李平持股由201,510,277股（4.42%）降至197,460,277股（4.33%），基金会由此成为新股东，持股4,050,000股（0.09%）。公司总股本为4,559,310,311股，若剔除回购股份22,632,510股，李平持股比例由4.44%降至4.35%，基金会持股不变。此次捐赠不影响公司治理结构及持续经营。","idx":31},{"title":"宁德时代：关于变更公司注册资本及修订公司章程的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/c470eb2f-2e77-40dc-b619-5a3c1fdcc19e.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/c470eb2f-2e77-40dc-b619-5a3c1fdcc19e.PDF","handler":"report_sz","summary":"截至2025年6月19日，宁德时代总股本为4,559,310,311股，其中A股占96.58%（440,339.5011万股），H股占3.42%（15,591.53万股）。公司注册资本由440,339.4911万元增至455,931.0311万元。此次股权结构变动主要由于H股发行及激励对象行权所致。","idx":32},{"title":"宁德时代：关于境外上市外资股（H股）挂牌并上市交易的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-20/9f1efe7a-2f6a-4930-b108-5b96e2de83f7.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-20/9f1efe7a-2f6a-4930-b108-5b96e2de83f7.PDF","handler":"report_sz","summary":"宁德时代本次发行H股135,578,600股（超额配售权未行使），其中A股股东持股比例由100%降至97.01%，H股占比2.99%。若超额配售权悉数行使，H股增至155,915,300股，占比提升至3.42%。前五大股东厦门瑞庭、黄世霖及宁波联合创新新能源持股比例分别为22.58%、10.35%和6.26%（超额配售权未行使情况下），合计持股39.18%，对公司治理具有重要影响。","idx":33},{"title":"截止2025-07-20宁德时代的财务指标摘要","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_abstract|300750|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代报告期显示，其净利润、扣非净利润及营业总收入均实现同比增长，基本每股收益与每股净资产稳步提升。销售净利率、毛利率及净资产收益率（ROE）等核心财务比率表现稳健，且高于行业平均水平。在运营效率方面，存货周转率良好，资产负债率处于合理区间，流动比率与速动比率反映公司具备较强短期偿债能力。通过横向对比，宁德时代在盈利能力与资产运用效率方面展现出较强的竞争力。","idx":34},{"title":"截止2025-07-20宁德时代的利润表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|利润表|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代2025年一季度营业总收入为847.05亿元，营业总成本为705.92亿元，其中营业成本为640.30亿元。研发费用为48.14亿元，销售费用为8.52亿元，管理费用为26.24亿元，财务费用为-22.88亿元。投资收益为7.83亿元，营业利润为30.83亿元，利润总额为30.83亿元，所得税费用为2.14亿元，归属于母公司所有者的净利润为28.69亿元，基本每股收益为3.18元。","idx":35},{"title":"截止2025-07-20宁德时代的资产负债表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|资产负债表|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代2025年3月31日财务数据显示，流动资产合计为820.097亿元，其中货币资金达321.324亿元，存货为656.397亿元。非流动资产合计为261.473亿元，固定资产净值为251.368亿元，在建工程合计为352.217亿元。负债方面，流动负债合计为521.585亿元，短期借款为208.507亿元；非流动负债合计为202.749亿元，长期借款为95.612亿元。所有者权益合计为298.752亿元，其中归属于母公司股东权益为286.669亿元。","idx":36},{"title":"截止2025-07-20宁德时代的主营业务构成","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_business_composition|300750|sz|2025-07-20","handler":"stock_bd","summary":"2024年宁德时代动力电池系统收入为2530亿，占比69.90%，较2023年的2853亿略有下降；储能电池系统收入572.90亿，占比15.83%，同比下降4.37%。境内业务收入2517亿，占总收入的69.52%，境外收入1103亿，占比30.48%。相较2023年，境外收入占比下降1.80个百分点，境内收入占比上升5.40个百分点。","idx":37},{"title":"截止2025-07-20宁德时代的现金流量表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|现金流量表|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代2025年一季度经营活动现金流入小计为1191.07亿元，其中销售商品、提供劳务收到的现金为1111.398亿元，占比较大。经营活动现金流出小计为862.388亿元，主要由支付给职工及税费等构成。经营活动产生的现金流量净额为328.683亿元。投资活动现金流入小计为10.343亿元，现金流出小计为195.823亿元，净额为-177.706亿元。筹资活动现金流入小计为117.879亿元，现金流出小计为270.160亿元，净额为-152.281亿元。期末现金及现金等价物余额为1192.640亿元。","idx":38},{"title":"截止2025-07-20比亚迪的财务指标摘要","url":"https://www.szse.cn/certificate/individual/index.html?code=002594","source":"深圳证券交易所","file_type":"csv","key":"get_financial_abstract|002594|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代报告期数据显示，其净利润、扣非净利润及营业总收入均实现同比增长，基本每股收益、销售净利率、销售毛利率、净资产收益率等关键财务指标表现稳健。与行业主要竞争对手相比，宁德时代在盈利能力（如ROE、毛利率、净利率）和运营效率（如存货周转率、应收账款周转天数）方面具有一定优势，同时资产负债率处于合理区间，流动比率与速动比率显示公司具备较强的短期偿债能力。","idx":39},{"title":"截止2025-07-20国轩高科的财务指标摘要","url":"https://www.szse.cn/certificate/individual/index.html?code=002074","source":"深圳证券交易所","file_type":"csv","key":"get_financial_abstract|002074|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代报告期数据显示，其净利润、扣非净利润及营业总收入均实现同比增长，基本每股收益、每股净资产等指标表现稳健。销售净利率、销售毛利率及净资产收益率（ROE）等关键财务比率显示公司盈利能力较强，且ROE（摊薄）进一步反映盈利质量。在运营效率方面，存货周转率与应收账款周转天数表明其资产运营能力良好，流动比率与速动比率体现短期偿债能力较优，资产负债率则处于合理区间，整体财务结构稳健。","idx":40},{"title":"截止2025-07-20宁德时代的现金流量表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|现金流量表|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代2025年3月31日数据显示，经营活动现金流入小计为119,107.07万元，其中销售商品、提供劳务收到的现金为111,139.84万元，占比较大；经营性现金流出小计为86,238.81万元，主要用于支付采购及职工薪酬等。经营活动产生的现金流量净额为32,868.26万元，资金回笼能力良好。投资活动方面，购建固定资产等支出达108,144.00万元，显示公司持续扩大资本开支，而投资活动现金流入较少，净流出177,705.54万元。筹资活动现金流入主要来自取得借款，总流入为286,300.84万元，偿还债务支付现金为270,159.73万元，筹资活动净流入16,141.10万元。整体来看，公司现金流匹配度尚可，但需关注资本支出对资金链的长期影响。","idx":41},{"title":"宁德时代：关于使用部分闲置募集资金进行现金管理的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/215a951f-2b54-4c9d-a6cc-0d6dcc0d88b8.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/215a951f-2b54-4c9d-a6cc-0d6dcc0d88b8.PDF","handler":"report_sz","summary":"截至2025年5月31日，宁德时代2022年向特定对象发行股票募集资金已使用3,847,859.51万元，尚未使用的余额为728,164.49万元（含利息收入净额89,012.67万元）。公司拟在不影响募投项目建设的前提下，使用不超过45亿元的闲置募集资金进行现金管理，投资于安全性高、流动性好的保本型存款产品，期限不超过12个月。本次现金管理事项已通过董事会和监事会审议，并获保荐人无异议意见，旨在提高资金使用效率并增强股东回报。","idx":42},{"title":"宁德时代：中信建投证券股份有限公司关于宁德时代新能源科技股份有限公司使用部分闲置募集资金进行现金管理的核查意见","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d41c7aa5-3c7b-4912-a2f7-8150b202159a.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d41c7aa5-3c7b-4912-a2f7-8150b202159a.PDF","handler":"report_sz","summary":"截至2025年5月31日，宁德时代2022年向特定对象发行股票募集资金总额为4,499,999.98万元，实际净额4,487,011.32万元，已投入使用3,847,859.51万元，尚余728,164.49万元（含利息收入89,012.67万元）未使用。公司拟使用不超过45亿元的闲置募集资金进行现金管理，投资期限不超过12个月的保本型存款产品，以提高资金使用效率。此前，公司曾于2024年3月审议通过65亿元额度的类似方案，并实现100%兑付本金。本次事项经董事会及监事会审议批准，保荐人认为其符合监管规定，不影响募投项目正常推进。","idx":43},{"title":"截止2025-07-20宁德时代的财务指标摘要","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_abstract|300750|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代在报告期实现净利润及扣非净利润双增长，经营性现金流表现稳健，每股经营现金流为正值，反映出较强的盈利质量。投资性现金流受资本支出影响较大，公司持续加大投入以支持产能扩张。筹资性现金流则主要用于补充投资资金缺口。资产负债率处于合理区间，流动比率与速动比率表现良好，体现出较强的资金链稳定性。","idx":44},{"title":"宁德时代：关于全资子公司参与投资产业投资基金的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF","handler":"report_sz","summary":"宁德时代全资子公司香港时代拟以不超过2.25亿美元认缴出资参与投资Lochpine Green Fund I, LP产业投资基金，基金目标规模为15亿美元，主要围绕碳中和领域上下游进行投资。该基金由Lochpine Capital Limited管理，组织形式为开曼豁免有限合伙企业，存续期基本为10年，收益按协议分配。公司表示本次投资资金来源为境外自有资金，不影响正常经营，有助于拓展碳中和业务布局并获取合理回报。同时提示基金投资周期长、流动性低及潜在收益不达预期等风险。","idx":45},{"title":"宁德时代：关于参与投资产业投资基金的进展公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/59d421a4-1d72-4cf2-bf6d-4609f6b43e98.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/59d421a4-1d72-4cf2-bf6d-4609f6b43e98.PDF","handler":"report_sz","summary":"宁德时代作为有限合伙人参与设立的福建时代泽远股权投资基金合伙企业（有限合伙）已正式完成工商注册及私募投资基金备案，基金总规模为1,012,800万元，公司认缴出资70,000万元，出资比例由13.76%降至6.91%。该基金主要投资于新能源及高端制造领域，旨在通过市场化机制拓展碳中和生态布局，获取合理投资回报。","idx":46},{"title":"截止2025-07-20宁德时代的资产负债表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|资产负债表|sz|2025-07-20","handler":"stock_akshare","summary":"宁德时代截至2025年3月31日，经营性现金流净额为89,988.9万元，投资性现金流净额为-208,506.66万元，筹资性现金流净额为79,844.17万元。公司货币资金达321.32亿元，在建工程合计为289.79亿元，固定资产净额为251.37亿元。流动资产合计为820.097亿元，其中存货为65.64亿元；流动负债合计为328.21亿元，非流动负债合计为230.13亿元。整体来看，公司现金流匹配度良好，资本支出规模较大，资金链稳定性较强。","idx":47},{"title":"截止2025-07-20宁德时代的财务指标摘要","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_abstract|300750|sz|2025-07-20","handler":"stock_akshare","summary":"本章节基于宁德时代历史财务数据，包括净利润、扣非净利润、营业总收入、基本每股收益、每股净资产等关键指标，结合未来增长假设，构建DCF或相对估值模型。同时考虑原材料成本与汇率变动对财务结果的影响，模拟测算各项财务比率如销售净利率、销售毛利率、净资产收益率及资产负债率等，以得出合理的估值区间。","idx":48},{"title":"截止2025-07-20宁德时代的现金流量表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|现金流量表|sz|2025-07-20","handler":"stock_akshare","summary":"根据2025年3月31日数据，宁德时代经营活动现金流入小计为119,107.07万元，其中销售商品、提供劳务收到的现金为111,139.84万元，占比较大。经营活动现金流出小计为86,238.81万元，主要由购买商品、接受劳务支付的现金（69,577.37万元）及支付给职工以及为职工支付的现金（7,189.75万元）构成。经营活动产生的现金流量净额为32,868.26万元。投资活动现金流入小计为10,342.61万元，现金流出小计为19,582.26万元，净流出9,239.65万元。筹资活动现金流入小计为117,878.97万元，现金流出小计为110,864.86万元，净流入7,014.11万元。","idx":49},{"title":"截止2025-07-20宁德时代近期的股票K线数据(按日)","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"getStockPrice|300750|2025-07-20","handler":"stock_bd","summary":"基于提供的历史股价数据，宁德时代在2025年6月10日至7月18日期间股价波动显著，最高达274.99元，最低为239.1元。日均成交量在976万至3380万之间，换手率介于0.24%至0.87%。技术指标显示，短期均线（MA5）和中期均线（MA10、MA20）呈现动态变化，反映市场对公司的估值预期存在分歧。该阶段股价受原材料成本及汇率变动影响明显，波动性增强，为DCF或相对估值模型提供了关键输入参数基础。","idx":50},{"title":"宁德时代：关于境外上市外资股（H股）公开发行价格的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/233d73f8-4b9c-4821-82df-7c2aa8d78114.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/233d73f8-4b9c-4821-82df-7c2aa8d78114.PDF","handler":"report_sz","summary":"宁德时代（证券代码：300750）公告确定H股发行最终价格为每股263港元（不含相关税费）。本次发行H股预计于2025年5月20日在香港联交所主板上市交易。","idx":51},{"title":"截止2025-07-20宁德时代的利润表","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_financial_report|300750|利润表|sz|2025-07-20","handler":"stock_akshare","summary":"基于2025年3月31日的财务数据，宁德时代实现营业总收入847.05亿元，营业成本为640.30亿元，研发费用达48.14亿元。净利润为148.62亿元，归属于母公司所有者的净利润为139.63亿元，基本每股收益为3.18元。该季度综合收益总额为154.76亿元，其中归属于母公司所有者的综合收益为145.08亿元。相关财务数据可作为构建DCF或相对估值模型的基础，并用于模拟原材料成本、研发支出等因素对估值的影响。","idx":52},{"title":"宁德时代：H股公告（翌日披露报表）","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/d1bff047-a926-4808-970d-bbea1892e338.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/d1bff047-a926-4808-970d-bbea1892e338.PDF","handler":"report_sz","summary":"2025年5月23日，宁德时代因超额配股权悉数行使，发行及配发20,336,700股H股股份，每股发行价为263港元。此次变动使公司已发行股份由135,578,600股增至155,915,300股，增幅达15%。该H股已于2025年5月20日于香港联交所主板新上市。","idx":53},{"title":"宁德时代：《宁德时代新能源科技股份有限公司章程》（2025年6月修订）","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d40a5acb-3634-4099-bb41-a680e851dd67.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/d40a5acb-3634-4099-bb41-a680e851dd67.PDF","handler":"report_sz","summary":"宁德时代公司章程显示，公司注册资本为455,931.0311万元，注册地为福建省宁德市。公司于2018年6月在深交所创业板上市，发行A股217,243,733股；并于2025年5月在香港联交所上市，发行H股135,578,600股（含超额配股权）。公司治理结构包括股东会、董事会、监事会及高级管理人员体系，明确划分职责与权力，并设立激励约束机制。章程规定总经理担任法定代表人，公司具有永久存续性质，治理体系符合《公司法》《证券法》及相关监管规则要求。","idx":54},{"title":"宁德时代的管理层信息","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_company_executive|300750|sz","handler":"stock_bd","summary":"宁德时代高管团队薪酬与股权结构显示管理层激励机制较为完善。董事长曾毓群年薪574.30万元，未披露持股情况；副董事长李平年薪53.80万元，但持有2.02亿股，股权激励力度较大。其他核心高管如蒋理（董事会秘书）年薪222.80万元、谭立斌（副总经理）272.40万元等，部分高管亦有少量持股。独立董事薪酬相对较低，多为20万元左右，体现其独立性。整体来看，公司通过合理的薪酬与股权分配，强化了管理层的稳定性与战略执行力，有助于支持公司长期可持续发展。","idx":55},{"title":"宁德时代：关于变更公司注册资本及修订公司章程的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/c470eb2f-2e77-40dc-b619-5a3c1fdcc19e.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-06-19/c470eb2f-2e77-40dc-b619-5a3c1fdcc19e.PDF","handler":"report_sz","summary":"宁德时代（300750）于2025年6月19日公告，因H股发行及激励对象行权，公司总股本由4,403,394,911股增至4,559,310,311股，注册资本相应由440,339.4911万元增加至455,931.0311万元。其中，H股共计发行155,915,300股，占总股本的3.42%；A股占比96.58%。公司已修订《公司章程》相关条款，并拟提交股东会审议。此次变更反映公司在资本结构和治理机制上的调整，为后续战略发展提供制度保障。","idx":56},{"title":"宁德时代：关于参与投资产业投资基金的进展公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/59d421a4-1d72-4cf2-bf6d-4609f6b43e98.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-23/59d421a4-1d72-4cf2-bf6d-4609f6b43e98.PDF","handler":"report_sz","summary":"宁德时代作为有限合伙人参与设立“福建时代泽远股权投资基金合伙企业（有限合伙）”，认缴出资7亿元，出资比例6.91%。该基金总规模达101.28亿元，较此前公告的50.86亿元增长显著，新增资金主要由鄂尔多斯市创新投资集团有限公司、国家绿色发展基金股份有限公司等机构认购。基金已完成工商注册及私募投资基金备案，备案编码SAPX68。公司通过此次投资进一步拓展碳中和生态布局，借助专业投资机构提升市场化投资能力，符合长期发展战略与股东利益。","idx":57},{"title":"宁德时代：关于全资子公司参与投资产业投资基金的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF","handler":"report_sz","summary":"宁德时代全资子公司香港时代拟以不超过2.25亿美元认缴出资参与投资15亿美元规模的Lochpine Green Fund I, LP产业投资基金，该基金聚焦碳中和领域上下游投资。公司通过此次投资借助专业机构优势，拓展业务合作渠道并获取合理回报，符合其长期发展战略。基金管理人为Lochpine Capital Limited，具备香港第4类及第9类受规管活动牌照，香港时代间接持有其32%股权。基金由普通合伙人GP公司管理，投资决策由基金管理人委派的三人委员会作出，收益按协议分配，存续期基本为10年。公司表示该投资不影响主营业务，资金来源为境外自有资金，不构成关联交易或同业竞争。","idx":58},{"title":"以产业向新助力经济向好——进一步巩固经济持续回升向好基础③","url":"https://www.gov.cn/zhengce/202504/content_7020925.htm","source":"中国人民政府网","file_type":"htm","key":"https://www.gov.cn/zhengce/202504/content_7020925.htm","handler":"zhengce_rmzf","summary":"宁德时代作为锂电新能源行业龙头，带动福建宁德市形成完整的产业链生态，目前当地已集聚80多家上下游企业，80%的采购实现就近配套，有效提升链上企业发展空间和区域产业竞争力。通过科技创新与产业创新深度融合，宁德时代不仅推动自身供给升级，也为新兴产业崛起提供牵引力，助力中国制造在全球供应链中塑造新优势。","idx":59},{"title":"宁德时代的十大股东","url":"https://www.szse.cn/certificate/individual/index.html?code=300750","source":"深圳证券交易所","file_type":"csv","key":"get_stock_holder|300750|sz","handler":"stock_bd","summary":"截至当前，宁德时代主要股东持股情况显示，厦门瑞庭投资有限公司以22.47%的持股比例为最大股东，持股数量10.25亿股，未发生变化。黄世霖、宁波联合创新新能源投资管理合伙企业等核心股东持股亦保持稳定。机构投资者中，易方达和华泰柏瑞旗下基金分别增持110.14万股和28.55万股，而香港中央结算有限公司减持324.51万股。此外，中国建设银行-易方达沪深300ETF新进持股3015万股，占比0.66%。整体来看，公司股权结构相对集中且稳定，部分机构小幅调整持仓，反映市场对企业发展战略的关注与信心。","idx":60},{"title":"宁德时代：关于股东无偿捐赠部分公司股份的进展公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-07-10/12c04174-566b-4a1a-bf18-841150673d5e.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-07-10/12c04174-566b-4a1a-bf18-841150673d5e.PDF","handler":"report_sz","summary":"宁德时代副董事长李平向上海复旦大学教育发展基金会捐赠405万股公司股份，占总股本0.09%。捐赠完成后，李平持股由4.42%降至4.33%，基金会首次持股0.09%。公司表示该事项不会对公司治理结构及持续经营产生重大影响。","idx":61},{"title":"出口200国，“中国绿”刷新世界能源版图","url":"http://www.chinanews.com.cn/gsztc/2025/06-19/10434702.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/gsztc/2025/06-19/10434702.shtml","handler":"news","summary":"宁德时代在全球新能源产业快速发展的背景下，依托中国绿色产能的全球扩张加速全球化布局。2024年，中国新增可再生能源发电量占全球总增量的60%，绿色贸易领跑全球，其中光伏产品连续4年出口超2000亿元，锂电池出口达39.1亿个创历史新高。宁德时代在匈牙利建厂，推动全球绿色产业链优化与国际合作，为能源转型注入新动力。政策支持、技术创新及产业链优势共同驱动中国新能源企业提升国际竞争力，助力公司长期战略目标实现可持续增长。","idx":62},{"title":"广东建成首个全链条新型储能产业基地","url":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","handler":"news","summary":"宁德时代全资子公司瑞庆时代在广东肇庆建成首个涵盖电芯至储能集装箱系统集成的全链条研发制造基地，二阶段工程已正式投产。该基地包括8万平方米前工序车间及1.5万平方米储能集装箱车间，助力填补华南地区储能全产业链制造技术空白。目前，宁德时代动力电池使用量连续八年全球第一，储能电池出货量连续四年全球领先。此次扩产将推动肇庆建设粤港澳大湾区绿色能源基地，并支持广东打造万亿级新型储能产业集群。","idx":63},{"title":"共建创新之路 第二届“一带一路”科技交流大会启动多项计划","url":"http://www.chinanews.com.cn/shipin/cns/2025/06-12/news1022718.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/shipin/cns/2025/06-12/news1022718.shtml","handler":"news","summary":"宁德时代董事长兼CEO曾毓群在第二届“一带一路”科技交流大会上提出，深化新能源领域合作的关键在于开放共享。此次大会发布了包括国际子午圈大科学计划、中医药科技创新专项合作计划等多项成果与新计划，推动构建多层次科技交流合作机制。中国新能源车企加速出海，在“一带一路”共建国家用户持续增长，宁德时代作为“中国制造”的代表，积极融入国际合作框架，助力新能源产业全球化布局。","idx":64},{"title":"宁德时代：关于全资子公司参与投资产业投资基金的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-16/9e1ceeb4-e759-48e1-88f0-71cd9b2a4f11.PDF","handler":"report_sz","summary":"宁德时代拟通过境外全资子公司香港时代以有限合伙人身份参与投资Lochpine Green Fund I, LP产业投资基金，认缴出资额不高于2.25亿美元。基金目标规模为15亿美元，主要围绕碳中和领域上下游进行投资。本次投资无需提交董事会及股东会批准，不影响公司正常经营。基金管理人为Lochpine Capital Limited，公司间接持有其32%股权。基金存续期基本为10年，退出方式包括份额转让或清算。公司强调该投资有助于拓展碳中和布局并获取合理回报，但提示存在投资周期长、流动性低及收益未达预期等风险。","idx":65},{"title":"以产业向新助力经济向好——进一步巩固经济持续回升向好基础③","url":"https://www.gov.cn/zhengce/202504/content_7020925.htm","source":"中国人民政府网","file_type":"htm","key":"https://www.gov.cn/zhengce/202504/content_7020925.htm","handler":"zhengce_rmzf","summary":"宁德时代作为锂电新能源产业龙头，带动福建宁德市形成80多家上下游企业集聚，产业链环节齐全，80%采购实现本地化，推动新兴产业快速发展并增强中国制造全球竞争力。然而，投资者需关注政策变化、市场竞争加剧及技术迭代等潜在风险因素，这些可能对企业发展和行业格局产生影响。","idx":66},{"title":"广东建成首个全链条新型储能产业基地","url":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/cj/2025/06-26/10438593.shtml","handler":"news","summary":"宁德时代全资子公司瑞庆时代在广东肇庆建成首个涵盖电芯至储能集装箱系统集成的全链条研发制造基地，二阶段工程正式投产。该基地建设进展迅速，新增前工序车间约8万平方米及储能集装箱车间约1.5万平方米，助力广东打造新型储能产业高地。据政策规划，广东力争2027年新型储能产业营收达1万亿元、装机规模400万千瓦。此次投产将推动肇庆建设粤港澳大湾区绿色能源基地，并支持宁德时代在全球储能市场的领先地位。","idx":67},{"title":"“创”出新活力 “闯”出新优势——从三个关键词看民营企业科技创新","url":"http://www.chinanews.com.cn/gn/2025/05-22/10419994.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/gn/2025/05-22/10419994.shtml","handler":"news","summary":"宁德时代在低温电池技术方面取得突破，推出钠新电池，零下40摄氏度环境下仍可保持90%的可用电量。随着新能源汽车智能化、网联化发展，我国新能源汽车出口持续增长，1至4月累计出口64.2万辆，同比增长52.6%。然而，投资需关注政策变化、市场竞争加剧及技术迭代等风险因素。","idx":68},{"title":"宁德时代：关于刊发境外上市外资股（H股）发行聆讯后资料集的公告","url":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-06/60759321-3d0e-4e51-a109-ddca5117f6e7.pdf","source":"深圳证券交易所","file_type":"pdf","key":"https://disc.static.szse.cn/disc/disk03/finalpage/2025-05-06/60759321-3d0e-4e51-a109-ddca5117f6e7.pdf","handler":"report_sz","summary":"宁德时代（300750）正推进境外H股发行并上市，已于2025年2月11日向香港联交所递交申请，并于4月10日通过聆讯。公司已获中国证监会备案通知书（国合函〔2025〕502号），目前正按要求在香港联交所网站刊发聆讯后资料集。本次发行尚需取得香港相关监管机构的最终批准，存在不确定性。公司提示投资者注意政策变化、审批风险及其他潜在投资风险。","idx":69},{"title":"从汽车产销、外贸大盘看中国经济前景","url":"https://www.gov.cn/yaowen/liebiao/202505/content_7023675.htm","source":"中国人民政府网","file_type":"htm","key":"https://www.gov.cn/yaowen/liebiao/202505/content_7023675.htm","handler":"zhengce_rmzf","summary":"投资建议方面，随着中国汽车以旧换新政策推动消费增长及新能源汽车占比超53%，叠加“两新”政策带动设备投资和消费回升，宁德时代作为核心供应链企业有望持续受益。当前全球新能源转型加速，中国新能源汽车出口强劲增长，为公司海外业务拓展提供广阔空间。风险提示方面，需关注美国关税政策不确定性、市场竞争加剧以及技术迭代带来的替代性风险。此外，全球宏观经济复苏不及预期或影响终端需求，进而对产业链造成压力。","idx":70},{"title":"东西问丨苏文菁：闽商千年商道，从海洋基因到全球文明的东方叙事","url":"http://www.chinanews.com.cn/dxw/2025/06-19/10434991.shtml","source":"中国新闻网","file_type":"htm","key":"http://www.chinanews.com.cn/dxw/2025/06-19/10434991.shtml","handler":"news","summary":"基于资料内容，宁德时代在改革开放以来通过技术输出与全球布局实现了从工艺改良到全球电池标准制定者的跃升，成为新能源产业的重要参与者。闽商文化中的开放包容、宗族协作与实用信仰体系为其发展提供了独特支持。然而，投资者需关注政策变化、市场竞争加剧及技术迭代等潜在风险因素，以全面评估投资价值。","idx":71}]
  res = asyncio.run(get_paragraph_chart(topic, paragraph, sources))
  print(res)