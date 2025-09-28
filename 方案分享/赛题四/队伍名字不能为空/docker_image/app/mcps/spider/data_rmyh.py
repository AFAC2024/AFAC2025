"""
人民银行统计调查司数据

1.0 @nambo 2025-07-20
"""
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import json
import sys
import os
import time
from urllib.parse import quote
import pandas as pd
import re

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import removeCache, getCache, setCache
from common.http_utils import get, post, download

host = 'http://www.pbc.gov.cn'
year_url = host + '/diaochatongjisi/116219/116319/index.html'

def split_chinese_english(text):
    # 遍历字符，找到第一个英文字母的位置
    if 'Shibor统计表Statistics of Shibor' == text:
      return 'Shibor统计表', 'Statistics of Shibor'
    
    parts = re.split(r'([a-zA-Z]+ .*)', text, maxsplit=1)
    chinese = parts[0]
    english = parts[1] if len(parts) > 1 else ""
    return chinese.strip(), english.strip()

def get_url_date(url):
  date_pattern = r'/(20\d{6})\d+\.'
  match = re.search(date_pattern, url)
  if match:
    d = match.group(1)
    return datetime.strptime(d, "%Y%m%d").strftime("%Y-%m-%d")
  
  return ''

def get_cats(years=['2025'], cats=None, sheets=None):
  cache_key_y = year_url + str(datetime.now().strftime("%Y%m")) 
  res_txt = get(year_url, cache_key=cache_key_y)
  html = BeautifulSoup(res_txt, 'html.parser')
  content_html = html.find("div", id="r_con")
  a_tags = content_html.select('td .wengao2 a')

  res = []
  for a_tag in a_tags:
    year = a_tag.get_text(strip=True)
    year = year[:4]
    if year not in years:
      print('{0}不在获取范围{1}内，跳过'.format(year, years))
      continue
    print('开始获取“{0}”:{1}'.format(year, a_tag['href']))
    cache_key_d = a_tag['href'] + str(datetime.now().strftime("%Y%m")) 
    res_txt_y = get(host + a_tag['href'], cache_key=cache_key_d, sleep=3)
    html_y = BeautifulSoup(res_txt_y, 'html.parser')

    if html_y is None:
      continue

    content_html_y = html_y.find("div", id="r_con")
    a_tags_y = content_html_y.select('td a')

    if a_tags_y == None or len(a_tags_y) <= 0:
      removeCache(cache_key_d)
      continue

    for a_tag_y in a_tags_y:
      cat_name = a_tag_y.get_text(strip=True)
      cat_chn, cat_eng  = split_chinese_english(cat_name)

      if cats is not None and cat_chn not in cats:
        continue

      href = a_tag_y['href']
      print('开始获取{0}“{1}”:{2}'.format(year, cat_name, href))
      cache_key_cat = href + str(datetime.now().strftime("%Y%m")) 

      if href == '' or href is None:
        continue

      if 'www.pbc.gov.cn' not in href:
        href = host + href

      if href[-4:] == '.htm':
          res.append({
            'name': str(year) + '年' + cat_chn,
            'en_name': str(year) + ' ' + cat_eng,
            'desc': '来自人民银行发布的，{0}，所属分类：{1}。'.format(str(year) + '年' + cat_chn, cat_chn),
            'file_type': 'htm',
            'url': href,
            'category': cat_chn,
            'en_category': cat_eng,
            'source': '中国人民银行调查统计司',
            'date': get_url_date(href),
            'key': str(year) + '|' + cat_chn,
            "handler": "data_rmyh"
          })
          continue

      res_txt_cat = get(href, cache_key=cache_key_cat, sleep=3)
      html_cat = BeautifulSoup(res_txt_cat, 'html.parser')
      content_html_cat = html_cat.find("div", id="con")

      if content_html_cat is None:
        continue

      trs_cat = content_html_cat.select('table.border_nr table tr')
      for tr in trs_cat:
        tds = tr.select('td')

        doc = {
          'name': '',
          'en_name': '',
          'url': '',
          'desc': '',
          'file_type': '',
          'category': cat_chn,
          'en_category': cat_eng,
          'source': '中国人民银行调查统计司',
          'date': ''
        }
        doc_urls = {
          'pdf_url': '',
          'xls_url': '',
          'html_url': ''
        }
        for td in tds:
          txt = str(td)

          if 'class="titp20"' in txt:
            doc_name = td.find('div').get_text(strip=True)
            doc_name_chn, doc_name_eng  = split_chinese_english(doc_name)
            doc['name'] = str(year) + '年' + doc_name_chn
            doc['en_name'] = str(year) + ' ' + doc_name_eng
          
          if 'href' in txt:
            doc_a = td.find('a')
            if '.pdf' in txt:
              doc_url = doc_a['href']
              if 'www.pbc.gov.cn' not in doc_url:
                doc_url = host + doc_url
              doc_urls['pdf_url'] = doc_url
            elif '.xls' in txt:
              doc_url = doc_a['href']
              if 'www.pbc.gov.cn' not in doc_url:
                doc_url = host + doc_url
              doc_urls['xls_url'] = doc_url
            elif '.htm' in txt:
              doc_url = doc_a['href']
              if 'www.pbc.gov.cn' not in doc_url:
                doc_url = host + doc_url
              doc_urls['html_url'] = doc_url
        
        doc['url'] = doc_urls['pdf_url'] if doc_urls['pdf_url'] != '' else (doc_urls['html_url'] if doc_urls['html_url'] != '' else doc_urls['xls_url'])
        doc['file_type'] = 'pdf' if doc_urls['pdf_url'] != '' else ('htm' if doc_urls['html_url'] != '' else 'xls')
        

        doc['desc'] = '来自人民银行发布的，{0}，所属分类：{1}。'.format(doc['name'], doc['category'])
        if doc['name'] == '':
          print('无信息文件，跳过。', str(tr))
          continue
        
        if sheets is not None and doc['name'] not in sheets:
          continue
        
        doc['key'] = doc['url']
        doc["handler"] = "data_rmyh"

        if doc['url'] != '':
          doc['date'] = get_url_date(doc['url'])

          res.append(doc)

  return res

def get_data_list():
  today = date.today().strftime("%Y-%m-%d")
  cache_key = 'data_rmyh_cat_list_' + today 
  cache = getCache(cache_key)

  if cache != None:
    print("从缓存中获取到结果")
    return json.loads(cache)
  
  res = get_cats(['2025', '2024'])

  setCache(cache_key, json.dumps(res, ensure_ascii=False))
  return res

def get_detail(key):

  if key is None or key == '':
    raise ValueError('获取详情的key不能为空')
  
  return download(key)

if __name__ == '__main__':
  res = get_data_list()
  print(res)

  p = get_detail(res[0]['key'])
  print(p)