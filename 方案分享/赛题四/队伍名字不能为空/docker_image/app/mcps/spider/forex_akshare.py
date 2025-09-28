"""
Akshare外汇数据采集

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

def get_forex_cat_list():
  today = date.today()
  print('开始获取外汇分类列表')

  cache_key = 'get_forex_cat_list{0}'.format(today.strftime("%Y-%m"))
  cache = getCache(cache_key)

  if cache != None:
    print("从缓存中获取到结果")
    cache = json.loads(cache)
    return cache
  
  df = ak.forex_spot_em() 

  # 选择需要的列并重命名
  result = df[['名称', '代码']].rename(columns={
    '名称': 'name',
    '代码': 'en_name'
  })
  if '中间价' in result['name']:
    result['url'] = 'https://quote.eastmoney.com/cnyrate/' + result['en_name'] + '.html'
  else:
    result['url'] = 'https://quote.eastmoney.com/forex/' + result['en_name'] + '.html'
    
  result['desc'] = '来自东方财富网-行情中心-外汇市场-所有汇率-历史行情数据，' + result['name']
  result['file_type'] = 'csv'
  result['category'] = '外汇数据'
  result['en_category'] = ''
  result['source'] = '东方财富网'
  result['date'] = ''
  result['key'] = result['en_name']
  result['handler'] = 'forex_akshare'

  # 转换为JSON数组格式
  res = result.to_json(orient='records', force_ascii=False)
  # res = df.to_csv(index=False)
  setCache(cache_key, res)
  res = json.loads(res)
  return res

def get_forex_detail(forex_code: str, start=None, end=None):
  today = date.today()
  print('开始获外汇历史行情数据')

  if end is None or end == '':
    end = today
  else:
    end = datetime.strptime(end, "%Y-%m-%d")

  if start is None or start == '':
    start = end - timedelta(days=90)
    start = start.strftime("%Y-%m-%d")
  end = end.strftime("%Y-%m-%d")

  cache_key = 'get_forex_detail{0},{1}'.format(forex_code, today.strftime("%Y-%m-%d"))
  cache = getCache(cache_key)

  if cache != None:
    print("从缓存中获取到结果")
    cache = StringIO(cache)
    df = pd.read_csv(cache)
  else:
    df = ak.forex_hist_em(symbol=forex_code)
    res = df.to_csv(index=False)
    setCache(cache_key, res)

  df['日期'] = df['日期'].astype(str)
  df = df[df['日期'] >= start]
  df = df[df['日期'] <= end]
  if len(df) > 0:
    df = df.sort_values(by='日期', ascending=False)
  res = df.to_csv(index=False)
  return res

if __name__ == '__main__':
  res = get_forex_cat_list()
  print(res)

  res = get_forex_detail(res[0]['key'])
  print(res)