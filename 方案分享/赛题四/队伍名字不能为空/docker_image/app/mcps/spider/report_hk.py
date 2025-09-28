"""
相关证券交易所：公开报告获取

1.0 @nambo 2025-07-20
"""
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import json
import sys
import os
import time
import random

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path) 
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache
from common.http_utils import get, post, download
from common.pdf_reader import parse_pdf

pdf_host = 'https://www1.hkexnews.hk'
url = 'https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh'
search_url = 'https://www1.hkexnews.hk/search/prefix.do?&callback=callback&lang=ZH&type=A&name={key}&market=SEHK&_=1752024209813'

TYPE_MAP = {
  '年报': { 't1code': '40000', 't2code': '40100' }
}

def search(key):
  req_url = search_url.format(key=key)
  res_txt = get(req_url, sleep=1)

  if '(' in res_txt and ')' in res_txt:
    res_txt = res_txt.split('(')[1]
    res_txt = res_txt.split(')')[0]
  else:
    print(res_txt)
    removeCache(req_url)
    raise ValueError('响应结果格式化失败')
  
  res = json.loads(res_txt)
    
  if 'stockInfo' not in res or len(res['stockInfo']) <= 0:
    removeCache(url)
    return []
  
  return res['stockInfo']

def get_stock(code):
  stock_l = search(code)
  for stock in stock_l:
    if stock['code'] == code:
      return stock
  return None

def get_hk(body, cache_key=None):
  print('开始获取数据：', url, body)
  if cache_key is None or cache_key == '':
    cache_key = url + json.dumps(body, ensure_ascii=False)
  res_txt = post(url, data=body, headers={
    'Content-Type': 'application/x-www-form-urlencoded'
  }, cache_key=cache_key, sleep=1)
  html = BeautifulSoup(res_txt, 'html.parser')
  
  err_html = html.find("div", class_="result_norecords")
  if err_html is not None:
    removeCache(cache_key)
    err_msg = err_html.get_text(strip=True)
    raise ValueError(err_msg)
  
  res_rows = html.select('#titleSearchResultPanel table tbody tr')
  if res_rows is not None and res_rows != '' and len(res_rows) > 0:
    print('数据获取成功')
    return html
  else:
    removeCache(cache_key)
    raise ValueError('结果无数据')
  
def format(html):
  res_arr = []
  res_rows = html.select('#titleSearchResultPanel table tbody tr')
  print(len(res_rows))
  for i, row in enumerate(res_rows, 1):
    # 提取行中的单元格数据
    cells = row.find_all(['td'])
    date = cells[0].get_text(strip=True).replace('發放時間:', '')
    date = datetime.strptime(date, "%d/%m/%Y %H:%M")
    date = date.date().isoformat()

    report_url = pdf_host + cells[3].find(class_='doc-link').find('a')['href']
    if '.pdf' not in report_url and '.PDF' not in report_url:
      continue
    obj = {
      "name": cells[3].find(class_='doc-link').find('a').get_text(strip=True),
      "en_name": "",
      "url": report_url,
      "desc": '',
      'code': cells[1].get_text(strip=True).replace('股份代號:', ''),
      'comp_name': cells[2].get_text(strip=True).replace('股份簡稱:', ''),
      "file_type": "pdf",
      "category": '临时:公告-' + cells[3].find(class_='headline').get_text(strip=True),
      "en_category": "",
      "source": "香港证券交易所",
      "date": date,
      "key": report_url,
      "handler": "report_hk"
    }

    obj['desc'] = "上市公司{0}(股票代码:{1})，于{2}发布的，{3}".format(obj['comp_name'], obj['code'], obj['date'], obj['name'])
    obj['name'] = obj['comp_name'] + '股份（HK' + obj['code'] + '）' + obj['name']
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
    start = start.strftime("%Y%m%d")
  
  if end == '' or end == None:
    end = today.strftime("%Y%m%d")
  
  body_data = {
    'lang': 'ZH',
    'category': '0',
    'market': 'SEHK',
    'searchType': '1',
    'documentType': '-1',
    't1code': '-2',
    't2Gcode': '-2',
    't2code': '-2',
    'stockId': str(stock['stockId']),
    'from': start.replace('-', ''),
    'to': end.replace('-', ''),
    'MB-Daterange': '0',
    'title': title
  }

  if len(type) > 0:
    if type not in TYPE_MAP:
      raise ValueError('未知的type类型，仅支持: ', TYPE_MAP.keys())
    else:
      type = TYPE_MAP[type]
      body_data.update(type)

  cache_key = url + json.dumps(body_data, ensure_ascii=False)
  res = get_hk(body_data, cache_key=cache_key)

  if res is not None and res != '':
    return format(res)

  removeCache(cache_key)
  return []

def get_invest_report(code, end=None):
  "获取上市公司最新的财务报告"
  if end is None or end == '':
    end = date.today()
  else:
    end = datetime.strptime(end, "%Y-%m-%d")

  start = end - timedelta(days=400)
  end = end.strftime("%Y%m%d")
  start = start.strftime("%Y%m%d")

  reports = get_report(code=code, type='年报', start=start, end=end)
  if len(reports) > 0:
    for report in reports:
      if report['name'][-2:] == '年報' or report['name'][-4:] == '年度報告':
        return report

  return None

def get_pdf(url=None, save_path=None, filename=None, stock=None):

  if url is None and stock is not None:
    url = stock['url']
  
  print('开始下载pdf: ' + url)

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

  stock = get_stock('00780')

  # stock = get_report("09961")
  print(stock)
  # pdf = get_detail(stock[0]['key'])
  # print(pdf)
  # print(len(pdf))
  # stock = get_invest_report("09961", "2025-07-15")
  # print(stock)
  # pdf = get_pdf(stock=stock)
  # print(pdf)