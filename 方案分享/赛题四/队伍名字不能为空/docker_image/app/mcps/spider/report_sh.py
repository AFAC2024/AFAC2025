"""
上海证券交易所：公开报告获取

1.0 @nambo 2025-07-20
"""
from datetime import date, timedelta, datetime
import requests
import json
import sys
import os
from bs4 import BeautifulSoup
import execjs
import time
import random

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache
from common.http_utils import get, get_header, download, download_pdf_with_selenium
from common.pdf_reader import parse_pdf

pdf_host = 'https://static.sse.com.cn'
url = 'https://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do?jsonCallBack=jsonpCallback4738832&isPagination=true&pageHelp.pageSize=50&pageHelp.cacheSize=1&START_DATE={start}&END_DATE={end}&SECURITY_CODE={code}&TITLE={title}&BULLETIN_TYPE={type}&stockType=&pageHelp.pageNo=1&pageHelp.beginPage=1&pageHelp.endPage=1&_=1751959476227'

TYPE_MAP = {
  '年报': '0101',
  '业绩预测': '11'
}

def get_sh(url):
  print('开始获取数据：', url)
  res_txt = get(url, headers={
    'Referer': 'https://www.sse.com.cn/'
  }, sleep=2)

  if '(' in res_txt and ')' in res_txt:
    res_txt = res_txt.split('(')[1]
    res_txt = res_txt.split(')')[0]
  else:
    print(res_txt)
    removeCache(url)
    raise ValueError('响应结果格式化失败')
  
  res = json.loads(res_txt)
    
  if 'success' in res and res['success'] == 'false':
    removeCache(url)
    raise ValueError('响应失败, ' + res['error'])

  print('数据获取成功')
  return res
  
def format(reports):
  res_arr = []
  for report_l in reports:
    for report in report_l:
      report_url = pdf_host + report['URL']
      if '.pdf' not in report_url and '.PDF' not in report_url:
        continue
      obj = {
        "name": report['TITLE'],
        "en_name": "",
        "url": report_url,
        "desc": '',
        'comp_name': report['SECURITY_NAME'],
        'code': report['SECURITY_CODE'],
        "file_type": "pdf",
        "category": '临时:公告-' + report['BULLETIN_TYPE_DESC'],
        "en_category": "",
        "source": "上海证券交易所",
        "date": report['SSEDATE'],
        "key": report_url,
        "handler": "report_sh"
      }
      obj['desc'] = "上市公司{0}(股票代码:{1})，于{2}发布的，{3}".format(obj['comp_name'], obj['code'], obj['date'], obj['name'])
    
      res_arr.append(obj)
  return res_arr

def get_report(code='', start='', end='', type='', title=''):
  "获取上交所企业报告，code：股票号码；start：开始日期（默认365天前）；end：结束日期（默认今天）；type：报告类型，年报/业绩预测；title：报告标题"
  if code == '' or code == None:
    raise ValueError('参数code不能为空')
  
  today = date.today()
  if start == '' or start == None:
    start = today - timedelta(days=365)
    start = start.strftime("%Y-%m-%d")
  
  if end == '' or end == None:
    end = today.strftime("%Y-%m-%d")

  if len(type) > 0:
    if type not in TYPE_MAP:
      raise ValueError('未知的type类型，仅支持: ', TYPE_MAP.keys())
    else:
      type = TYPE_MAP[type]
  
  req_url = url.format(code=code, start=start, end=end, type=type, title=title)
  res = get_sh(req_url)

  if 'result' in res:
    return format(res['result'])

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

def get_pdf_token(url):
  now = datetime.now()
  cache_key = 'get_sh_report_token_' + now.strftime('%Y%m%d%H')
  print(cache_key)
  res_txt = get(url, cache_key=cache_key)
  soup = BeautifulSoup(res_txt, 'html.parser')

  scripts = soup.find_all('script')
  js_code = [script.string for script in scripts if script.string]
  js_code = ";".join(js_code)
  js_code = js_code.replace('\\n', '')
  js_code = js_code.replace('document', 'doc')
  js_code = 'function res(){return doc["cookie"];};var doc = {location: {reload: function() {console.log(doc)}}};var location = {host: "static.sse.com.cn"}' + js_code
  
  ctx = execjs.compile(js_code)
  token = ctx.call("res")

  if token is None:
    removeCache(cache_key)
  if ';' in token:
    token = token.split(';')
    token = token[0]

  return token

def get_pdf(url=None, save_path=None, filename=None, stock=None):

  if url is None and stock is not None:
    url = stock['url']

  print('开始下载pdf: ' + url)

  if (filename is None or filename == '') and stock is not None:
    filename = stock['code'] + '_' + stock['comp_name'] + '_'  + stock['name'] + '_' + stock['date'] + '.pdf' 
  filename = filename.replace('/', '_').replace(' ', '')
  
  print('开始下载')
  token = get_pdf_token(url)
  print('获取到token', token)

  try:
    filepath = download(url + '?t=pdf', headers={
      'Cookie': token
    }, save_path=save_path, filename=filename)
  except Exception as e:
    removeCache(url)
    removeCache(url + '?t=pdf')
    raise e
  
  txt, tables = parse_pdf(filepath)
  print('下载成功')
  return txt

def get_detail(url: str):
  filename = f"{time.time()}{random.randint(0, 9999)}"
  return get_pdf(url, filename=filename)

if __name__ == "__main__":
  res = get_report("601128")
  print(res)

  res = get_detail(res[0]['key'])
  print(res)
  print(len(res))