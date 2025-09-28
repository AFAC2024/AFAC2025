"""
Akshare宏观经济数据采集

1.0 @nambo 2025-07-20
"""
import akshare as ak
import pandas as pd
from datetime import date, timedelta, datetime
import sys
import os
from io import StringIO
import json

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache, getCache, setCache, get_md5

file_dir = os.path.join(current_dir, 'data_files')
# 检查目录是否存在，如果不存在则创建
if not os.path.exists(file_dir):
    os.makedirs(file_dir)

def get_macro_cat_list():
  print('开始获取宏观经济数据列表')
  with open(file_dir + '/macro_data_list.json', 'r', encoding='utf-8') as file:
    data = json.load(file)
    return data

def get_macro_detail(key: str, start=None, end=None):
  today = date.today()
  print('开始获宏观经济明细数据', key, start, end)

  if end is None or end == '':
    end = today
  else:
    end = datetime.strptime(end, "%Y-%m-%d")

  if start is None or start == '':
    start = end - timedelta(days=1110)
    start = start.strftime("%Y-%m-%d")
  end = end.strftime("%Y-%m-%d")

  if '|' in key:
    macro = key.split('|')
    date_col = macro[1]
    ak_method = macro[0]

  cache_key = 'get_macro_detail1{0},{1}'.format(key, today.strftime("%Y-%m-%d"))
  cache = getCache(cache_key)

  if cache != None:
    print("从缓存中获取到结果")
    cache = StringIO(cache)
    df = pd.read_csv(cache)
  elif hasattr(ak, ak_method):
    df = getattr(ak, ak_method)()
    res = df.to_csv(index=False)
    setCache(cache_key, res)
  else:
    raise ValueError('暂不支持的key，请检测是否有误。传入key=' + key)

  if date_col != None and date_col != '':
    if date_col == '年份':
      start = start[:7]
      end = end[:7]
    elif date_col == '月份':
      df[date_col] = df[date_col].str.replace("年", "-").str.replace("月份", "-01")

    df[date_col] = df[date_col].astype(str)
    df = df[df[date_col] >= start]
    df = df[df[date_col] <= end]
    if len(df) > 0:
      df = df.sort_values(by=date_col, ascending=False)
  res = df.to_csv(index=False)
  return res

if __name__ == '__main__':
  res = get_macro_cat_list()
  print(res)

  res = get_macro_detail(res[1]['key'])
  print(res)