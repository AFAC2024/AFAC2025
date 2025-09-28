"""
国务院政策文件搜索

1. 基于关键字搜索
2. 过去url的详情

1.0 @nambo 2025-07-20
"""
from datetime import date, timedelta, datetime
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
from common.http_utils import get, get_header, download_pdf_with_selenium

# search_url = 'https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q={key}&timetype={time}&mintime=&maxtime=&sort=pubtime&sortType=1&searchfield=&puborg=&pcodeYear=&pcodeNum=&filetype=&p=1&n=30&inpro=&dup=&orpro=&type=gwyzcwjk'
search_url = 'https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary_gw_bm_gb&q={key}&timetype=timezd&mintime={start}&maxtime={end}&sort=pubtime&sortType=1&searchfield=title&pcodeJiguan=&childtype=&subchildtype=&tsbq=&pubtimeyear=&puborg=&pcodeYear=&pcodeNum=&filetype=&p=1&n=5&inpro=&bmfl=&dup=&orpro=&bmpubyear='

TIME_MAP = {
  'year': 'timeyn',
  'month': 'timeyy',
  'week': 'timeyz'
}

def expand_data(data, cat_name=''):
  res_list = []
  if data is not None and 'listVO' in data:
    for item in data['listVO']:
      item['catName'] = cat_name
      
      item_res = {
        "name": item['title'],
        "en_name": "",
        "url": item['url'],
        "desc": item['summary'],
        "file_type": "htm",
        "category": '临时:政策-' + (item['catName'] + ':' + item['childtype']) if ('childtype' in item and item['childtype'] is not None and item['childtype'] != '') else item['catName'],
        "en_category": "",
        "source": item['puborg'] if ('puborg' in item and item['puborg'] is not None and item['puborg'] != '') else '国务院政策文件库',
        "date": item['pubtimeStr'].replace('.', '-'),
        "key": item['url'],
        "handler": "zhengce_gwy"
      }

      res_list.append(item_res)

  return res_list

def search(key='', start=None, end=None):
  print('开始获取国务院政策文件, key=' + key)
  key = quote(key)

  today = date.today()
  if end == '' or end == None:
    end = today
  else:
    end = datetime.strptime(end, "%Y-%m-%d")

  if start == '' or start == None:
    start = today - timedelta(days=90)
    start = start.strftime("%Y-%m-%d")
  
  end = today.strftime("%Y-%m-%d")
  
  
  req_url = search_url.format(key=key, start=start, end=end)
  cache_key = req_url + date.today().isoformat()
  res_txt = get(req_url, cache_key=cache_key, sleep=2)

  res = json.loads(res_txt)
  if res is None or 'code' not in res:
    removeCache(cache_key)
    raise ValueError('请求失败')
  
  if res['code'] != 200:
    print('请求失败: ' + res['msg'])
    if '没有找到相关结果' not in res['msg']:
      removeCache(cache_key)
    raise ValueError('请求失败: ' + res['msg'])
  
  if 'searchVO' not in res or 'catMap' not in res['searchVO']:
    print('未获取到数据')
    # removeCache(cache_key)
    raise ValueError('未获取到数据')
  
  gongwen = []
  bumenfile = []
  gongbao = []
  otherfile = []

  cat_map = res['searchVO']['catMap']
  
  if 'gongwen' in cat_map:
    gongwen = cat_map['gongwen']
  if 'bumenfile' in cat_map:
    bumenfile = cat_map['bumenfile']
  if 'gongbao' in cat_map:
    gongbao = cat_map['gongbao']
  if 'otherfile' in cat_map:
    otherfile = cat_map['otherfile']

  res_list = []
  res_list = res_list + expand_data(gongwen, '公文')
  res_list = res_list + expand_data(bumenfile, '部门文件')
  res_list = res_list + expand_data(gongbao, '公告')
  res_list = res_list + expand_data(otherfile, '其他文件')

  res_list = sorted(res_list, key=lambda x: x['date'], reverse=True)
  print('获取成功，共计' + str(len(res_list)) + '条')
  return res_list

def get_detail(url):
  print('开始获取国务院文件, url=' + url)
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
  list = search('镍')
  print(list)
  # txt = get_detail(list[0]['key'])
  # print(txt)