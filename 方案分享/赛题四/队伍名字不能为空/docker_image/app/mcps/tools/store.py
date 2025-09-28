"""
基础数据工具

1. 向量库的数据保存、检索、过期数据清理等方法
2. 基于关键字进行外部信息采集的方法
3. 基于向量库中检索到的数据目录，获取详细数据的方法

1.0 @nambo 2025-07-20
"""
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
import progressbar
from langchain_milvus import BM25BuiltInFunction, Milvus
from pymilvus import MilvusClient
import json
import sys
import os
import logging
from datetime import date, timedelta, datetime
import time
import threading
from queue import Queue

# 创建线程安全的队列用于存储结果
result_queue = Queue()
# 创建锁对象用于保护共享资源
lock = threading.Lock()

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 获取当前脚本路径 (server_chart.py)
current_file = os.path.abspath(__file__)
# 获取项目根目录 (mcps的上级目录)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
# 将项目根目录添加到Python路径
sys.path.append(project_root)

from mcps.spider import data_gjtjj, zhengce_rmzf, forex_akshare, futures_akshare, index_hs, macro_akshare, news, report_hk, report_sh, report_sz, stock_akshare, stock_bd, stock_xq, zhengce_gwy, financial_analysis
import config
from mcps.common import parallelism

# 设置环境变量指向国内镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 本地HF的embedding
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

# 百炼的embedding
embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    # other params...
)

# vector_store = InMemoryVectorStore(embeddings)


# 连接到Milvus服务器
milvus_client = MilvusClient(
    uri=config.conf['zilliz_milvus_url'],
    token=config.conf['zilliz_milvus_token'],
    db_name=config.conf['zilliz_milvus_db_name']
)
milvus_collections_name = "LangChainCollection"

# 定义向量数据库
vector_store = Milvus(
    embedding_function=embeddings,
    connection_args={
        "uri": config.conf['zilliz_milvus_url'],
        "token": config.conf['zilliz_milvus_token'],
        "db_name": config.conf['zilliz_milvus_db_name']
      },
    index_params={"index_type": "FLAT", "metric_type": "L2"},
    consistency_level="Strong",
    drop_old=False,  # set to True if seeking to drop the collection with that name if it exists
)

# 批量保存的数量
BATCH_SAVE_SIZE = 20

def milvus_filter(filter_expr, limit=20, output_fields=["*"]):
  """
    基于检索表达式，在向量库中查找数据
    主要用于过期数据清理
  """
  try:
    results = milvus_client.query(
      collection_name=milvus_collections_name,
      filter=filter_expr,
      output_fields=output_fields,  # 返回所有字段，也可以指定特定字段
      limit=limit  # 限制返回结果数量
    )
    return results
  except Exception as e:
    return []

def save_to_milvus(data_list: list[Document]):
  """
    将数据保存到向量库中，会自动排除重复数据
  """
  pids = []
  # logging.debug("开始批量保存，总计：{0}".format(len(data_list)))
  for item in data_list:
    pids.append('"{0}"'.format(item.metadata['pid']))
  filter_exp = "pid in [{0}]".format(",".join(pids))
  exist_list = milvus_filter(filter_exp, limit=BATCH_SAVE_SIZE*10)
  exist_pids = []
  for item in exist_list:
    exist_pids.append(item['pid'])
  add_list = []
  add_pids = []
  for item in data_list:
    if item.metadata['pid'] not in exist_pids:
      add_list.append(item)
      add_pids.append(item.metadata['pid'])
    
  saved_len = len(add_list)
  if saved_len > 0:
    add(add_list)
    logging.debug("批量保存成功，总计：{0}, pids:{1}".format(saved_len, add_pids))
  return saved_len

def save_data_list(res_list, prefix="加载数据："):
  """
    基于原始数据, 构建DOC对象, 保存到向量库中
  """
  arr = []
  i = 0
  count = 0
  if prefix is not None and prefix != '':
    widgets = [
      prefix,  # 替代prefix的固定标题
      progressbar.Bar(),  # 进度条本身
      ' ', progressbar.SimpleProgress(),  # 百分比
      ' ', progressbar.ETA()  # 预计剩余时间
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=len(res_list), term_width=100)
  for item in res_list:
    i += 1
    doc = Document(
      page_content=json.dumps(item, ensure_ascii=False),  # 核心文本内容
      metadata={
        "source": item["source"],
        "url": item['url'],
        "category": item['category'],
        "pid": item['key'] + '|' + item['handler']
      }
    )
    bar.update(i)
    arr.append(doc)
    if len(arr) > BATCH_SAVE_SIZE:
      count += save_to_milvus(arr)
      arr = []
  if prefix is not None and prefix != '':
    bar.finish()
  if len(arr) > 0:
    count += save_to_milvus(arr)
    arr = []
  return len(arr)

def load_default_data() -> int:
  """
  加载默认数据列表
  """
  count = 0
  res_list = data_gjtjj.get_data_list()
  count += save_data_list(res_list, '加载国家统计局数据：')
  res_list = forex_akshare.get_forex_cat_list()
  count += save_data_list(res_list, '加载外汇数据：')
  res_list = futures_akshare.get_futures_cat_list()
  count += save_data_list(res_list, '加载期货数据：')
  res_list = index_hs.get_data_list()
  count += save_data_list(res_list, '加载恒生指数：')
  res_list = macro_akshare.get_macro_cat_list()
  count += save_data_list(res_list, '加载宏观经济数据：')
  return count

def add(docs: list[Document]) -> bool:
  """
  将文档列表保存到向量库中

  参数：
    docs: 文档列表
  """
  try:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200)
    all_splits = text_splitter.split_documents(docs)
    _ = vector_store.add_documents(documents=all_splits)
  except Exception as e:
    raise ValueError('保存失败' + str(e))

  return True

def similarity_search(msg: str) -> list[Document]:
  """
  在向量库中检索相关的文档

  参数:
    msg: 期望用于检索的信息
  """
  docs = vector_store.similarity_search(msg, k=10)
  return docs

def search(keywords):
  """
    基于关键字列表, 在项目库中搜索相关的内容
  """
  if keywords is None:
    keywords = []

  search_words = []
  for word in keywords:
    if ' ' in word:
      word = word.split(' ')
      search_words += word
    else:
      search_words.append(word)

  docs = []
  for word in search_words:
    doc_res = similarity_search(word)
    docs += doc_res
  res = []
  keymap = {}
  for doc in docs:
    if doc.metadata['pid'] not in keymap:
      d = doc.page_content
      try:
        d = json.loads(d)
        res.append(d)
        keymap[doc.metadata['pid']] = True
      except Exception as e:
        logging.warning('数据转换失败, pid:{0}, exception:{1}'.format(doc.metadata['pid'], str(e)))
        continue
  return res

def search_data_word(word, data_date):
  """
    基于关键字列表, 在外部采集相关信息
  """
  cat_list = []
  # 搜索新闻
  try:
    docs = news.search_news(word, end_date=data_date)
  except:
    docs = []
  cat_list += docs
  # 搜索国务院政策
  try:
    docs = zhengce_gwy.search(word, end=data_date)
  except:
    docs = []
  cat_list += docs
  # 搜索人民政府网政策
  try:
    docs = zhengce_rmzf.search(word, end=data_date)
  except:
    docs = []
  cat_list += docs

  return cat_list

def search_data(keywords, data_date:None):
  """
    基于行业、企业等信息，采集关键字对应的信息
  """
  res_list = []

  if data_date is None or data_date == '':
    data_date = date.today().strftime('%Y-%m-%d')
  else:
    data_date = datetime.strptime(data_date, '%Y-%m-%d')
    data_date = data_date.strftime("%Y-%m-%d")

  # 根据关键字搜索
  words = [keywords['industry']] + keywords['company'] + keywords['elements'] + keywords['technology'] + keywords['macro'] + keywords['tools'] 
  
  cat_list = []
  widgets = [
    '搜索相关咨询',  # 替代prefix的固定标题
    progressbar.Bar(),  # 进度条本身
    ' ', progressbar.SimpleProgress(),  # 百分比
    ' ', progressbar.ETA()  # 预计剩余时间
  ]
  # bar = progressbar.ProgressBar(widgets=widgets, max_value=len(words), term_width=100)
  
  task_list = []
  for idx, word in enumerate(words):
    task_list.append((search_data_word, (word, data_date), {}))
  #   bar.update(idx + 1)
  # bar.finish()
  
  executor = parallelism.ConcurrentExecutor(max_concurrent=config.conf['parallelism_count'])
  cat_list = executor.execute(task_list)
    
  print(f"关键字搜索，总共获取 {len(cat_list)} 条记录:")
  for i, result in enumerate(cat_list):
      print(f"{i+1}. {result}")

  # save_data_list(cat_list, '加载相关国家政策与资讯')
  res_list += cat_list
  cat_list = []

  # 当前公司及竞争对手的股票数据目录
  comp_names = keywords['company']
  widgets[0] = '搜索相关股票数据'
  bar = progressbar.ProgressBar(widgets=widgets, max_value=len(comp_names), term_width=100)
  for idx, compname in enumerate(comp_names):
    print('开始搜索上市公司', compname)
    comp = None
    try:
      comp = stock_bd.search(compname)
    except Exception as e:
      print('获取上市股票信息失败, ', compname, e)

    if comp is None:
      print('未获取到上市公司信息, ', compname)
      continue
    cat_list += stock_bd.get_data_list(comp['name'], comp['code'], comp['exchange'])
    bar.update(idx + 1)
  bar.finish()
  print(f"上市公司信息搜索，总共获取 {len(cat_list)} 条记录:")
  
  # save_data_list(cat_list, '加载股票公告与财务信息')
  res_list += cat_list
  cat_list = []

  # 根据行业，获取股票板块信息
  industry_list = keywords['industry']
  widgets[0] = '搜索行业指数'
  bar = progressbar.ProgressBar(widgets=widgets, max_value=len(industry_list), term_width=100)
  for idx, industry in enumerate(industry_list):
    print('开始搜索股市板块', industry)
    info = None
    try:
      info = stock_bd.search_block(industry)
    except Exception as e:
      print('获取股票板块信息失败, ', industry, e)
    if info is None:
      print('未获取到股票板块信息, ', industry)
      continue
    
    item = '{{"name":"{industry}板块股票近期的指数K线数据(按日)","en_name":"","url":"https://gushitong.baidu.com/stock/{market}-{code}","desc":"截止{data_date}{industry}板块股票近期的指数K线数据(按日)。包含其每日的开盘价、收盘价、最高价、最低价、成交量、成交额、5日均价、10日均价、20日均价、涨跌幅、日期等字段。","file_type":"csv","category":"临时:股票数据","en_category":"","source":"百度股市通","date":"{data_date}","key":"getIndustryKLine|{industry}|{data_date}","handler":"sotck_db"}}'.format(data_date=data_date, industry=info['name'], code=info['code'], market=info['market'])
    cat_list.append(json.loads(item))
    bar.update(idx + 1)
  bar.finish()
  print(f"行业信息搜索，总共获取 {len(cat_list)} 条记录:")
  
  # save_data_list(cat_list, '加载行业指数')
  res_list += cat_list

  unique_list = []
  unique_map = {}
  for doc in res_list:
    did = doc['key'] + doc['handler']
    if did not in unique_map:
      unique_list.append(doc)
      unique_map[did] = True

  return unique_list

def clean():
  print('数据清理完成')
  res = milvus_client.delete(
      collection_name=milvus_collections_name,
      # highlight-next-line
      filter="category LIKE '临时:%'"
    )
  return res

async def call_key_func(obj, key, type=None):
    """
      基于数据目录的key与handler配置,获取明细数据
    """
    keys = key.split('|')
    func = getattr(obj, keys[0])
    
    try:
      if len(keys) == 1:
        if type == 'await':
          return await func()
        else:
          return func()
      elif len(keys) == 2:
        if type == 'await':
          return await func(keys[1])
        else:
          return func(keys[1])
      elif len(keys) == 3:
        if type == 'await':
          return await func(keys[1], keys[2])
        else:
          return func(keys[1], keys[2])
      elif len(keys) == 4:
        if type == 'await':
          return await func(keys[1], keys[2], keys[3])
        else:
          return func(keys[1], keys[2], keys[3])
      elif len(keys) == 5:
        if type == 'await':
          return await func(keys[1], keys[2], keys[3], keys[4])
        else:
          return func(keys[1], keys[2], keys[3], keys[4])
      elif len(keys) == 6:
        if type == 'await':
          return await func(keys[1], keys[2], keys[3], keys[4], keys[5])
        else:
          return func(keys[1], keys[2], keys[3], keys[4], keys[5])
      elif len(keys) == 7:
        if type == 'await':
          return await func(keys[1], keys[2], keys[3], keys[4], keys[5], keys[6])
        else:
          return func(keys[1], keys[2], keys[3], keys[4], keys[5], keys[6])
      elif len(keys) == 8:
        if type == 'await':
          return await func(keys[1], keys[2], keys[3], keys[4], keys[5], keys[6], keys[7])
        else:
          return func(keys[1], keys[2], keys[3], keys[4], keys[5], keys[6], keys[7])
    except Exception as e:
      logging.warning('数据调用失败,key:{0}, exception:{1}'.format(key, str(e)))
      return None
    
    if len(keys) > 8:
      raise ValueError('暂不支持的函数调用')

MAX_CONTENT_LEN = 30000
async def do_get_content(doc=None, key=None, handler=None):
  """
    基于数据目录的key与handler配置,获取明细数据
  """
  if doc is not None:
    key = doc['key']
    handler = doc['handler']
  
  content = ''
  if handler == 'news':
    content = news.get_detail(key)
  elif handler == 'report_sh':
    content = report_sh.get_detail(key)
  elif handler == 'report_sz':
    content = report_sz.get_detail(key)
  elif handler == 'report_hk':
    content = report_hk.get_detail(key)
  elif handler == 'zhengce_gwy':
    content = zhengce_gwy.get_detail(key)
  elif handler == 'zhengce_rmzf':
    content = zhengce_rmzf.get_detail(key)
  elif handler == 'data_gjtjj':
    content = data_gjtjj.get_detail(key)
  elif handler == 'forex_akshare':
    content = forex_akshare.get_forex_detail(key)
  elif handler == 'futures_akshare':
    content = futures_akshare.get_futures_detail(key)
  elif handler == 'index_hs':
    content = index_hs.get_detail(key)
  elif handler == 'macro_akshare':
    content =macro_akshare.get_macro_detail(key)
  elif handler == 'sotck_db' or handler == 'stock_bd':
    content = await call_key_func(stock_bd, key)
  elif handler == 'sotck_akshare' or handler == 'stock_akshare':
    content = await call_key_func(stock_akshare, key)
  elif handler == 'financial_analysis':
    content = await call_key_func(financial_analysis, key, type='await')
  else:
    raise ValueError('未知的hanlder类型' + handler)
  
  if content is None:
    print(doc)
    # return content

  if len(content) > MAX_CONTENT_LEN:
    content = content[:MAX_CONTENT_LEN]

  return content

MAX_TRY_COUNT = 5
async def get_content(doc=None, key=None, handler=None):
  try_count = 1
  err = None
  while try_count <= MAX_TRY_COUNT:
    try:
      content = await do_get_content(doc, key, handler)
      return content
    except Exception as e:
      logging.error('获取内容失败, doc:{0}, key:{1}, handler:{2}, try_count:{3}, exception:{4}'.format(doc, key, handler, try_count, str(e)))
      logging.info('获取内容失败，将重试{0}/{1}'.format(try_count, MAX_TRY_COUNT))
      time.sleep(2)
      try_count += 1
      err = e
  
  if err is not None:
    logging.error('获取内容失败, doc:{0}, key:{1}, handler:{2}, exception:{3}'.format(doc, key, handler, str(err)))
    # raise err
    return ''

if __name__ == '__main__':
  import asyncio
  # res = search(['商汤科技'])
  # print('搜索结果：', res)

  # c = get_content({
  #   'name': '商汤科技的主营业务构成',
  #   'en_name': '',
  #   'url': 'https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=20&sc_lang=zh-hk',
  #   'desc': '上市公司商汤科技(股票代码00020.hk)的主营业务构成，返回csv字符串格式数据，包含按产品、按地区的业务构成、收入、占比',
  #   'file_type': 'csv',
  #   'category': '临时:股票数据',
  #   'en_category': '',
  #   'source': '香港证券交易',
  #   'date': '2025-07-20',
  #   'key': 'get_business_composition|00020|hk|2025-07-20',
  #   'handler': 'stock_bd'})

  # c = get_content({"name": "商汤-W的现金流量表", 
  #                  "en_name": "", 
  #                  "url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=20&sc_lang=zh-hk", 
  #                  "desc": "上市公司商汤-W(股票代码00020.hk)的现金流量表，返回csv字符串格式数据", 
  #                  "file_type": "csv", 
  #                  "category": "临时:股票数据", 
  #                  "en_category": "", 
  #                  "source": "香港证券交易所", 
  #                  "date": "2025-07-21", 
  #                  "key": "get_financial_report|00020|现金流量表|hk|2025-07-21", 
  #                  "handler": "stock_akshare"})
  # print(c)

  # c = get_content({"name": "商汤-W的资产负债表",
  #                  "en_name": "",
  #                  "url": "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=20&sc_lang=zh-hk",
  #                  "desc": "上市公司商汤-W(股票代码00020.hk)的资产负债表，返回csv字符串格式数据",
  #                  "file_type": "csv",
  #                  "category": "临时:股票数据",
  #                  "en_category": "",
  #                  "source": "香港证券交易所",
  #                  "date": "2025-07-21",
  #                  "key": "get_financial_report|00020|资产负债表|hk|2025-07-21",
  #                  "handler": "stock_akshare"})
  # print(c)

  c = asyncio.run(get_content({
      "name": "基于商汤科技财报进行的ROE分析",
      "en_name": "ROE Analysis Report",
      "url": "https://www1.hkexnews.hk/listedco/listconews/sehk/2025/0424/2025042400918_c.pdf",
      "desc": "上市公司商汤科技(股票代码00020.hk)的基于资产负债表、利润表进行财务ROE分析得到的净资产收益率(ROE)分析报告。包含ROE趋势分析、行业对比、杜邦分析等核心财务指标。",
      "file_type": "pdf",
      "category": "临时:财务分析报告",
      "en_category": "Financial Analysis Reports",
      "source": "香港证券交易所",
      "date": "2025-07-01",
      "key": "get_roe_analysis_report|商汤科技|00020|hk",
      "handler": "financial_analysis"
  }))
  # '601128', 'sh'
  print(c)
