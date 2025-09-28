# 获取恒生指数
# 1. 获取目录，seriesName指数名称，seriesCode指数编号
# https://www.hsi.com.hk/data/schi/index-series/directory.json
# 2. 获取指数ID，indexSeriesList[0].indexList[0].indexCode
# https://www.hsi.com.hk/data/schi/rt/index-series/hsi/performance.do?7602
# 3. 获取指数数据，
# https://www.hsi.com.hk/data/schi/indexes/{指数ID}/chart.json
from datetime import date, timedelta, datetime
import json
import sys
import os
import pandas as pd

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache, getCache, setCache, get_md5
from common.http_utils import get, get_header, download_pdf_with_selenium

file_dir = os.path.join(current_dir, 'hszs_files')
# 检查目录是否存在，如果不存在则创建
if not os.path.exists(file_dir):
    os.makedirs(file_dir)

list_url = 'https://www.hsi.com.hk/data/schi/index-series/directory.json'
detail_url = 'https://www.hsi.com.hk/data/schi/rt/index-series/{code}/performance.do?7602'
data_url = 'https://www.hsi.com.hk/data/schi/indexes/{code}/chart.json'

def expand_index_data(index, seriesCode=None):
  """
  解析恒生目录至列表
  """
  if 'seriesCode' in index and index['seriesCode'] != '':
    seriesCode = index['seriesCode']

  if seriesCode is None:
    seriesCode = ''

  res = [{
    'name': index['indexName'],
    'en_name': index['indexShortName'],
    'desc': '{0}，是由恒生发布的，针对{1}的，{2}'.format(index['indexName'], index['regionName'], index['categoryName']),
    'file_type': 'json',
    'url': 'https://www.hsi.com.hk/schi/indexes/all-indexes/' + seriesCode,
    'code': index['indexCode'],
    'category': index['categoryName'],
    'en_category': index['categoryFragment'],
    'source': '香港恒生指数有限公司',
    'date': str(datetime.now().strftime("%Y-%m-%d")),
    "key": index['indexCode'],
    "handler": "index_hs"
  }]
  sub_indexs = index['subIndexList']
  if sub_indexs is not None and len(sub_indexs) > 0 and sub_indexs != '':
    for sub_index in sub_indexs:
      res = res + expand_index_data(sub_index, seriesCode)
  return res


def get_data_list():
  """
  获取恒生指数列表
  """
  
  today = date.today().strftime("%Y-%m-%d")
  cache_key_list = 'data_hszs_cat_list_' + today 
  cache = getCache(cache_key_list)

  if cache != None:
    print("从缓存中获取到结果")
    return json.loads(cache)
  
  print('开始获取恒生指数目录')
  cache_key = list_url + date.today().isoformat()
  res_txt = get(list_url, cache_key=cache_key)

  res = json.loads(res_txt)
  if res is None or 'indexSeriesList' not in res:
    raise ValueError('未获取到数据')
  
  res_list = []
  for series in res['indexSeriesList']:
    indexs = series['indexList']
    for index in indexs:
      res_list = res_list + expand_index_data(index, series['seriesCode'])

  print('获取成功')
  setCache(cache_key_list, json.dumps(res_list, ensure_ascii=False))
  return res_list

def idx_search(key, full_match=True):
  """
  根据指数名称搜索指数信息

  参数：
    key: 搜索的关键字
    full_match: 是否完全匹配，默认：True
  """
  list = get_data_list()
  res = []
  for index in list:
    need = False
    name = index['name']
    shortName = index['shortName']
    if full_match:
      need = name == key or shortName == key
    else:
      need = key in name or key in shortName
    
    if need:
      res.append(index)
  
  return res

def get_data(code=None, name=None):
  print('开始获取恒生指数，code: {0}, name: {1}'.format(code, name))
  if code is None and name is None:
    raise ValueError('code和name不能都为空')
  
  if code is None:
    idx_list = idx_search(name)
    if len(idx_list) <= 0:
      raise ValueError('未找到对应指数，name=' + name)
    code = idx_list[0]['code']

  req_url = data_url.format(code=code)
  cache_key = req_url + date.today().isoformat()
  res_txt = get(req_url, cache_key=cache_key)
  res = json.loads(res_txt)

  print('获取成功')
  return res

def get_detail(key):
  if key is None or key == '':
    raise ValueError('获取详情的key不能为空')
  
  res = get_data(key)

  data_1y = res['indexLevels-3m']
  idx_name = res['indexName']

  res = []
  for item in data_1y:
    res_item = {
      '日期': datetime.fromtimestamp(item[0]/1000).strftime("%Y-%m-%d")
    }
    res_item[idx_name] = item[1]
    res.append(res_item)
  
  df = pd.DataFrame(res)
  if len(df) > 0:
    df = df.sort_values(by='日期', ascending=False)
  return df.to_csv(index=False)
  
if __name__ == '__main__':
  list = get_data_list()
  # list = get_data(name='HSCGSI')
  print(list)

  # res = get_detail(list[1]['key'])
  # print(res)