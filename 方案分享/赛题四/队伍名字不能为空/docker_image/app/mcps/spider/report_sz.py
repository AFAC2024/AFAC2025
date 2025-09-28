"""
深圳证券交易所：公开报告获取

1.0 @nambo 2025-07-20
"""
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import json
import sys
import os
import random
import time

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache
from common.http_utils import get, post, download
from common.pdf_reader import parse_pdf

pdf_host = 'https://disc.static.szse.cn'
url = 'https://www.szse.cn/api/disc/announcement/annList?random={random}'
search_url = 'https://www.szse.cn/api/report/shortname/gethangqing?dataType=ZA%7C%7CXA%7C%7CDM%7C%7CBG%7C%7CCY%7C%7CEB%7C%7C%5Bzzss%5D%7C%7C%5Bts%5D&input={key}&random={random}'

TYPE_MAP = {
  '年报': { 'bigCategoryId': ["010301"] }
}

def search(key):
  random_num = round(random.random(), 10)/10
  rand = random_num + 0.43497109579620397
  req_url = search_url.format(key=key, random=str(rand))
  res_txt = get(req_url, sleep=2)

  if 'data' not in res_txt:
    print(res_txt)
    removeCache(req_url)
    raise ValueError('响应结果格式化失败')
  
  res = json.loads(res_txt)
    
  if 'data' not in res or len(res['data']) <= 0:
    removeCache(url)
    return []
  
  return res['data']

def get_stock(code):
  stock_l = search(code)
  for stock in stock_l:
    if stock['code'] == code:
      return stock
  return None

def get_sz(body):
  random_num = round(random.random(), 10)/10
  rand = random_num + 0.43497109579620397
  req_url = url.format(random=str(rand))

  print('开始获取数据：', req_url, body)
  cache_key = url + json.dumps(body, ensure_ascii=False)
  res_txt = post(req_url, data=body, headers={
    'Content-Type': 'application/json'
  }, cache_key=cache_key, sleep=1)
  
  try:
    res = json.loads(res_txt)
  except Exception as e:
    removeCache(cache_key)
    raise e

  if 'data' in res:
    return res['data']
  else:
    removeCache(cache_key)
    raise ValueError('结果无数据')
  
def format(reports, type):
  res_arr = []
  for report in reports:
    date = report['publishTime']
    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    date = date.date().isoformat()
    report_url = pdf_host + report['attachPath']
    if '.pdf' not in report_url and '.PDF' not in report_url:
      continue
    obj = {
      "name": report['title'],
      "en_name": "",
      "url": report_url,
      "desc": '',
      'comp_name': report['secName'][0],
      'code': report['secCode'][0],
      "file_type": "pdf",
      "category": '临时:公告',
      "en_category": "",
      "source": "深圳证券交易所",
      "date": date,
      "key": report_url,
      "handler": "report_sz"
    }
    obj['desc'] = "上市公司{0}(股票代码:{1})，于{2}发布的，{3}".format(obj['comp_name'], obj['code'], obj['date'], obj['name'])
  
    res_arr.append(obj)
  return res_arr

def get_report(code='', start='', end='', type='', title=''):
  "获取上交所企业报告，code：股票号码；start：开始日期（默认365天前）；end：结束日期（默认今天）；type：报告类型，年报/业绩预测；title：报告标题"
  if code == '' or code == None:
    raise ValueError('参数code不能为空')
  
  stock = get_stock(code)

  if stock is None:
    raise ValueError('未找到对应股票')
  
  today = date.today()
  if start == '' or start == None:
    start = today - timedelta(days=365)
    start = start.strftime("%Y-%m-%d")
  
  if end == '' or end == None:
    end = today.strftime("%Y-%m-%d")
  
  body_data = {
    "seDate":[start, end],
    "stock":[str(code)],
    "channelCode":["listedNotice_disc"],
    "pageSize":50,
    "pageNum":1
  }

  if title != '' and title is not None:
    body_data['searchKey'] = [str(title)]

  if len(type) > 0:
    if type not in TYPE_MAP:
      raise ValueError('未知的type类型，仅支持: ', TYPE_MAP.keys())
    else:
      type = TYPE_MAP[type]
      body_data.update(type)

  res = get_sz(body_data)

  if res is not None and res != '':
    return format(res, type)

  return []

def get_invest_report(code, end=None):
  "获取上市公司最新的财务报告"
  if end is None or end == '':
    end = date.today()
  else:
    end = datetime.strptime(end, "%Y-%m-%d")

  start = end - timedelta(days=400)
  end = end.strftime("%Y-%m-%d")
  start = start.strftime("%Y-%m-%d")

  reports = get_report(code=code, type='年报', start=start, end=end)
  if len(reports) > 0:
    for report in reports:
      print(report['name'][-4:])
      if report['name'][-4:] == '年度报告' or report['name'][-2:] == '年报':
        return report

  return None

def get_pdf(url=None, save_path=None, filename=None, stock=None):
  if stock is None and filename is None:
    raise ValueError('参数filename、stock不能均为空')
  
  if url is None and stock is not None:
    url = stock['url']

  print('开始下载pdf: ' + url)
  url = url + ''

  if (filename is None or filename == '') and stock is not None:
    filename = stock['code'] + '_' + stock['comp_name'] + '_'  + stock['name'] + '_' + stock['date'] + '.pdf' 
  filename = filename.replace('/', '_').replace(' ', '')

  filepath = download(url, save_path=save_path, filename=filename)
  txt, tables = parse_pdf(filepath)
  print('下载成功')
  return txt

def get_detail(url: str):
  filename = f"{time.time()}{random.randint(0, 9999)}"
  return get_pdf(url, filename=filename)

if __name__ == "__main__":
  stock = get_report("002208")
  print(stock)
  pdf = get_detail(stock[0]['key'])
  print(pdf)
  print(len(pdf))