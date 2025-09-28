"""
人民政府网信息搜索

1. 基于关键字搜索
2. 过去url的详情

1.0 @nambo 2025-07-20
"""
from datetime import date, timedelta, datetime
import time
import json
import sys
import os
from urllib.parse import quote
from bs4 import BeautifulSoup

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache
from common.http_utils import get, post, get_header, download_pdf_with_selenium
from config import conf

search_url = 'https://sousuoht.www.gov.cn/athena/forward/2B22E8E39E850E17F95A016A74FCB6B673336FA8B6FEC0E2955907EF9AEE06BE'
headers = conf['rmzfw_token']
headers['Content-Type'] = 'application/json'
search_body = """
{{
    "code": "17da70961a7",
    "historySearchWords": [],
    "dataTypeId": "107",
    "orderBy": "time",
    "searchBy": "all",
    "appendixType": "",
    "granularity": "ALL",
    "trackTotalHits": true,
    "beginDateTime": {start},
    "endDateTime": {end},
    "isSearchForced": 0,
    "filters": [],
    "pageNo": 1,
    "pageSize": 20,
    "customFilter": {{
        "operator": "and",
        "properties": []
    }},
    "searchWord": "{key}"
}}
"""

TIME_MAP = {
  'year': 'timeyn',
  'month': 'timeyy',
  'week': 'timeyz'
}

def expand_data(data_list):
  res_list = []
  if data_list is not None:
    for item in data_list:
      item_res = {
        "name": item['title'],
        "en_name": "",
        "url": item['url'],
        "desc": item['content'].replace('<em>', '').replace('</em>', ''),
        "file_type": "htm",
        "category": '临时:政府文件-' + item['label'],
        "en_category": "",
        "source": '中国人民政府网',
        "date": item['time'],
        "key": item['url'],
        "handler": "zhengce_rmzf"
      }

      res_list.append(item_res)

  return res_list

def search(key='', start=None, end=None):
  print('开始获取人民政府网文件, key=' + key)
  # key = quote(key)

  today = date.today()
  if end == '' or end == None:
    end = today
  else:
    end = datetime.strptime(end, "%Y-%m-%d")

  if start == '' or start == None:
    start = today - timedelta(days=90)
    start = int(time.mktime(start.timetuple())) * 1000
  
  end = int(time.mktime(end.timetuple())) * 1000
  
  body = search_body.format(key=key, start=start, end=end)
  cache_key = search_url + body + date.today().isoformat()
  body = json.loads(body)

  res_txt = post(search_url, data=body, headers=headers,cache_key=cache_key, sleep=2)

  res = json.loads(res_txt)
  if res is None or 'resultCode' not in res or 'code' not in res['resultCode']:
    removeCache(cache_key)
    raise ValueError('请求失败')

  if res['resultCode']['code'] != 200:
    msg = '请求失败: ' + str(res['resultCode']['cnMsg'])
    print(msg)
    removeCache(cache_key)
    raise ValueError(msg)
  
  if 'result' not in res or 'data' not in res['result'] or 'middle' not in res['result']['data'] or 'list' not in res['result']['data']['middle']:
    print('未获取到数据')
    removeCache(cache_key)
    raise ValueError('未获取到数据')
  
  data_list = res['result']['data']['middle']['list']

  res_list = expand_data(data_list)

  res_list = sorted(res_list, key=lambda x: x['date'], reverse=True)
  print('获取成功，共计' + str(len(res_list)) + '条')
  return res_list

def get_detail(url):
  print('开始获取人民政府网文件详情, url=' + url)
  res_txt = get(url, headers={
    "Content-Type": "text/html; charset=utf-8",
    "Accept-Encoding": "gzip, deflate"
  })
  html = BeautifulSoup(res_txt, 'html.parser')

  content_html = html.find("div", class_="trs_editor_view")

  if content_html is None:
    removeCache(url)
    raise ValueError('未解析到内容')
  
  txt = content_html.get_text(strip=True)

  print('文件获取成功，长度：' + str(len(txt)))
  return txt

if __name__ == '__main__':
  list = search('新能源')
  print(list)
  txt = get_detail(list[0]['key'])
  print(txt)