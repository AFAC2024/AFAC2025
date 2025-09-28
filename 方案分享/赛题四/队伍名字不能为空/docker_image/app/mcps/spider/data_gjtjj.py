# 【中国国家统计局数据】
# 1. 获取分类
# https://data.stats.gov.cn/easyquery.htm
#
# 2. 获取数据
# https://data.stats.gov.cn/easyquery.htm?m=QueryData&dbcode=hgyd&rowcode=zb&colcode=sj&wds=%5B%5D&dfwds=%5B%7B%22wdcode%22%3A%22zb%22%2C%22valuecode%22%3A%22A0801%22%7D%5D&k1=1752137782720&h=1

from datetime import datetime, date, timedelta
import json
import sys
import os
import time
from urllib.parse import quote
import pandas as pd

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache, getCache, setCache, get_md5
from common.http_utils import get, post, download

file_dir = os.path.join(current_dir, 'data_files')
# 检查目录是否存在，如果不存在则创建
if not os.path.exists(file_dir):
    os.makedirs(file_dir)

# 月度数据分类
BASE_CATS = [
  {'id': 'A01', 'name': '价格指数', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A02', 'name': '工业', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A03', 'name': '能用', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A04', 'name': '固定资产投资（不含农户）', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A05', 'name': '服务业生产指数', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A0E', 'name': '城镇调查失业率', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A06', 'name': '房地产', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A07', 'name': '国内贸易', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A08', 'name': '对外经济', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A09', 'name': '交通运输', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A0A', 'name': '邮电通信', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A0B', 'name': '采购经理指数', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A0C', 'name': '财政', 'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True},
  {'id': 'A0D', 'name': '金融',  'dbcode': 'hgyd','wdcode': 'zb','m': 'getTree', 'isParent': True}
]

# 季度数据分类
BASE_CATS_JD = [
  { 'id':'A01', 'name': '国民经济核算', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True },
  { 'id':'A02', 'name': '农业', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True },
  { 'id':'A03', 'name': '工业', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True },
  { 'id':'A04', 'name': '建筑业', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True },
  { 'id':'A05', 'name': '人民生活', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True },
  { 'id':'A06', 'name': '价格指数', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True },
  { 'id':'A07', 'name': '国内贸易', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True },
  { 'id':'A08', 'name': '文化', 'dbcode':'hgjd', 'wdcode':'zb', 'm':'getTree', 'isParent': True }
]

cat_url = 'https://data.stats.gov.cn/easyquery.htm'
detail_url = 'https://data.stats.gov.cn/easyquery.htm?m=QueryData&dbcode={time}&rowcode=zb&colcode=sj&wds=%5B%5D&dfwds={key}&k1={timestamp}'

def get_all_cats(base_cats=BASE_CATS):
  """
  获取中国国家统计局，所有统计分类
  """
  print('开始获取数据统计局所有分类数据')
  t_cache_key = cat_url + json.dumps(base_cats, ensure_ascii=False)
  print(t_cache_key)
  cache = getCache(t_cache_key)
  if cache != None:
    print("从缓存中获取到结果")
    cache = json.loads(cache)
    return cache
  
  res_list = [] + base_cats
  for cat in base_cats:
    if 'isParent' in cat and cat['isParent']:
      print('获取子分类数据,', cat)
      cache_key = cat_url + json.dumps(cat, ensure_ascii=False)
      cat['m'] = 'getTree'
      res_txt = post(cat_url, data=cat, headers={
        'Content-Type': 'application/x-www-form-urlencoded'
      }, cache_key=cache_key, sleep=5)

      try:
        res = json.loads(res_txt)
      except Exception as e:
        removeCache(cache_key)
        raise e
      sub_list = get_all_cats(res)

      res_list += sub_list

  setCache(t_cache_key, json.dumps(res_list, ensure_ascii=False))
  return res_list

def get_child_cats():
  """
  获取所有最终子分类
  """
  month_cats = get_all_cats()
  quarter_cats = get_all_cats(BASE_CATS_JD)

  res = {
    'yd': [],
    'jd': []
  }

  for cat in month_cats:
    if not cat['isParent']:
      for p in month_cats:
        if p['id'] == cat['pid']:
          cat['pName'] = p['name']
      res['yd'].append(cat)

  for cat in quarter_cats:
    if not cat['isParent']:
      for p in quarter_cats:
        if p['id'] == cat['pid']:
          cat['pName'] = p['name']
      res['jd'].append(cat)

  return res

def format(data):
  datanodes = data['returndata']['datanodes']
  wdnodes = data['returndata']['wdnodes']

  code_map = {}
  for nodes in wdnodes:
    for node in nodes['nodes']:
      code_map[node['code']] = node['name']

  res = []
  res_map = {}
  for node in datanodes:
    if not node['data']['hasdata']:
      continue

    sj = None
    zb = None
    data = node['data']['data']
    for wd in node['wds']:
      if wd['wdcode'] == 'sj':
        sj = wd['valuecode']
        sj = code_map[sj]
      elif wd['wdcode'] == 'zb':
        zb = wd['valuecode']
        zb = code_map[zb]
    
    if sj in res_map:
      res_map[sj][zb] = data
    else:
      res_map[sj] = { zb: data }
  
  for sj in res_map.keys():
    d = {
      '时间': sj
    }
    for zb in res_map[sj]:
      d[zb] = res_map[sj][zb]
    res.append(d)
  df = pd.DataFrame(res)
  if len(df) > 0:
    df = df.sort_values(by='时间', ascending=False)
  return df

TYPE_MAP = {
  '季度': 'hgjd',
  '月度': 'hgyd'
}
def get_data(id=None, date_type='月度', wdcode='zb', cat=None):
  """
  获取中国国家统计局的明细数据

  参数：
    id: 统计项ID
    data_type: 月度/季度
    wdcode: 固定值，zb
    cat: 分类数据
  """
  if (id is None or date_type is None) and cat is None:
    raise ValueError('id, date_type, cat不能均为None')
  
  print('开始获取数据', id, date_type, cat)
  
  if date_type in TYPE_MAP:
    date_type = TYPE_MAP[date_type]
  
  if cat is not None:
    date_type = cat['dbcode']
    id = cat['id']
    wdcode = cat['wdcode']

  sj_last = 'LAST13'
  if date_type == 'hgjd':
    sj_last = 'LAST6'
  key = [{"wdcode":wdcode, "valuecode": id},{"wdcode": "sj", "valuecode": sj_last}]
  key = quote(json.dumps(key, ensure_ascii=False))
  timestamp = int(time.time() * 1000)

  cache_key = detail_url + str(datetime.now().strftime("%Y%m")) + key + date_type
  req_url = detail_url.format(time=date_type, key=key, timestamp=timestamp)
  
  res_txt = get(req_url, sleep=1, cache_key=cache_key, retry=3)
  try:
    res = json.loads(res_txt)
  except Exception as e:
    removeCache(req_url)
    raise e
  
  if 'returncode' not in res or res['returncode'] != 200:
    print(res)
    removeCache(req_url)
    raise ValueError('获取数据失败')

  print('数据获取成功')
  return format(res)

def get_stand_detail(cat, data, data_type='月度'):
  date_cn = str(datetime.now().strftime("%Y年%m月"))
  max_date = data['时间'].max()
  date = str(datetime.now().strftime("%Y-%m-01"))
  if data_type == '月度':
    type = '近13个月'
  elif data_type == '季度':
    type = '近6季度'
  else:
    raise ValueError('type只能是月度/季度')
  
  name = type + cat['name']
  desc = "来自中国国家统计局，{1}{2}，所属分类：{3}，包含字段：{4}".format('', type, cat['name'], cat['pName'], "、".join(data.columns))
  path =  os.path.join(file_dir, get_md5(desc) + '.csv')
  
  data.to_csv(path, index=False)
  return {
    "name": name,
    "en_name": cat['id'],
    "url": "https://data.stats.gov.cn/easyquery.htm?zb=" + cat['id'],
    "desc": desc,
    "file_type": "csv",
    "category": cat['pName'],
    "en_category": "",
    "source": "中国国家统计局",
    "date": date,
    "key": data_type + '|' + cat['id'],
    "handler": "data_gjtjj"
  }

def get_data_list():
  """
  获取标准化数据列表
  """

  today = date.today().strftime("%Y-%m-%d")
  cache_key = 'data_gjtjj_cat_list_' + today 
  cache = getCache(cache_key)

  if cache != None:
    print("从缓存中获取到结果")
    return json.loads(cache)
  
  res_list = []
  cats = get_child_cats()
  cat_map = {}
  i = 0
  for cat in cats['jd']:
    i += 1
    print('开始获取{0}_季度, 进度{1}/{2}'.format(cat['name'], i, len(cats['jd'])))
    res = get_data(cat=cat)
    if res.columns is None or len(res.columns) <= 0:
      continue
    res_list.append(get_stand_detail(cat, res, '季度'))
  
  i = 0
  for cat in cats['yd']:
    i += 1
    print('开始获取{0}_月度, 进度{1}/{2}'.format(cat['name'], i, len(cats['yd'])))
    res = get_data(cat=cat)
    if res.columns is None or len(res.columns) <= 0:
      continue
    res_list.append(get_stand_detail(cat, res))

  setCache(cache_key, json.dumps(res_list, ensure_ascii=False))
  return res_list

def get_detail(key):
  if key is None or key == '':
    raise ValueError('key不能为空')
  keys = key.split('|')
  data = get_data(id=keys[1], date_type=keys[0])
  path =  os.path.join(file_dir, get_md5(key) + '.csv')
  
  data.to_csv(path, index=False)
  return data.to_csv(index=False)

if __name__ == '__main__':
  res = get_data_list()
  print(res)

  res = get_detail(res[0]['key'])
  print(res)