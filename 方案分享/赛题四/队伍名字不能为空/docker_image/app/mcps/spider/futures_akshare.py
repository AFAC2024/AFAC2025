"""
Akshare期货数据数据采集

1.0 @nambo 2025-07-20
"""
import akshare as ak
import pandas as pd
from datetime import date, timedelta, datetime
import sys
import os
import json

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache, getCache, setCache, get_md5

def get_futures_cat_list():
  today = date.today()
  print('开始获取期货分类列表')

  cache_key = 'get_futures_cat_list{0}'.format(today.strftime("%Y-%m-%d"))
  cache = getCache(cache_key)

  if cache != None:
    print("从缓存中获取到结果")
    cache = json.loads(cache)
    return cache
  
  df = ak.futures_hist_table_em() 

  # 选择需要的列并重命名
  result = df[['合约中文代码', '合约代码', '市场简称']].rename(columns={
    '合约中文代码': 'name',
    '合约代码': 'en_name',
    '市场简称': 'category'
  })

  result['url'] = 'https://qhweb.eastmoney.com/quote'
    
  result['desc'] = '来自东方财富网-期货行情-行情数据，在' + result['category'] + '的合约中文代码为' + result['name'] + '的行情数据'
  result['file_type'] = 'csv'
  result['category'] = '期货数据-' + result['category']
  result['en_category'] = ''
  result['source'] = '东方财富网'
  result['date'] = ''
  result['key'] = result['name']
  result['handler'] = 'futures_akshare'

  # 转换为JSON数组格式
  res = result.to_json(orient='records', force_ascii=False)
  # res = df.to_csv(index=False)
  setCache(cache_key, res)
  res = json.loads(res)
  return res

def get_futures_detail(future_name: str, start=None, end=None):
  today = date.today()
  print('开始获取明细数据', future_name, start, end)

  if end is None or end == '':
    end = today
  else:
    end = datetime.strptime(end, "%Y-%m-%d")

  if start is None or start == '':
    start = end - timedelta(days=90)
    start = start.strftime("%Y-%m-%d")
  end = end.strftime("%Y-%m-%d")

  cache_key = 'get_futures_detail{0},{1},{2}'.format(future_name, start, end)
  cache = getCache(cache_key)

  if cache != None:
    print("从缓存中获取到结果")
    return cache
  
  df = ak.futures_hist_em(symbol=future_name, period='daily', start_date=start, end_date=end)
  if len(df) > 0:
    df = df.sort_values(by='时间', ascending=False)
  res = df.to_csv(index=False)
  setCache(cache_key, res)
  return res

if __name__ == '__main__':
  res = get_futures_cat_list()
  # print(res)

  res = get_futures_detail(res[0]['key'])
  print(res)