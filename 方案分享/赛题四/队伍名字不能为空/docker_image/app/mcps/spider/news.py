"""
新闻采集

1.0 @nambo 2025-07-20
"""
import requests
from datetime import datetime
import json
import sys
import os
from dateutil.relativedelta import relativedelta
import re
from bs4 import BeautifulSoup


current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from common.cache import setCache, getCache
from common.http_utils import get, post, download

# 获取关键字近24小时的新闻
def getNews(key_words, end_date, start_date=None):
	url = "https://finnews.cubenlp.com/search_news"
	headers = {
		"Content-Type": "application/json; charset=utf-8"
	}
	end_time = datetime.strptime(end_date, '%Y-%m-%d')  
	
	if start_date is None:
		start_date = end_time - datetime.timedelta(hours=48)

	data = {	
		"query": key_words,	
		"start_timestamp": int(start_date.timestamp() * 1000),  
		"end_timestamp": int(end_time.timestamp() * 1000),  
		"top_k": 10
	}
	body = json.dumps(data, ensure_ascii=False).encode('utf-8')
	print("开始获取资讯：" + body.decode('utf-8'))

	cache_key = body.decode('utf-8')
	cache = getCache(cache_key)
	if cache != None:
		print("从缓存中获取到咨询")
		return json.loads(cache)

	# 发送 POST 请求
	response = None
	count = 1
	while count > 0:
		try:
			response = requests.post(url, data=body, headers=headers)
			count = -1
		except Exception as e:
			print("获取咨询失败，将重试：", count, key_words, e)
			count += 1

	# 检查请求是否成功
	if response.status_code == 200:
		res_json = response.json()
		res_arr = []
		for news in res_json["data"]:
			news['key_words'] = key_words
			news['snippet'] = news['snippet'].replace("【" + news['title'] + "】", "")
			news['content'] = news['snippet']
			res_arr.append(news)
		setCache(cache_key, json.dumps(res_arr, ensure_ascii=False))
		print("资讯获取成功!", len(res_arr))
		return res_arr
	else:
		print("资讯获取失败!")
		print(f"状态码: {response.status_code}")
		print(response.text)

CAT_MAPS = {
	'gj': '国际',
	'gn': '时政',
	'dxw': '东西问',
	'comment': '评论',
	'ty': '体育',
	'hr': '华人',
	'sh': '社会',
	'tp': '图片',
	'cul': '文娱',
	'cj': '财经',
	'life': '健康·生活',
	'auto': '汽车',
	'sp': '视频',
	'zhibo': '直播',
	'mil': '军事',
	'chuangyi': '创意',
	'gsztc': '国是直通车',
	'dwq': '大湾区',
	'edu': '教育',
	'fazhi': '法治',
	'fz': '法治'
}
def get_news_page(key='', page=1, start=None, end=None):
	if end is None or end == '':
		end = datetime.now().strftime("%Y-%m-%d")

	if start is None or start == '':
		three_months_ago = datetime.strptime(end, "%Y-%m-%d") - relativedelta(months=3)
		start = three_months_ago.strftime("%Y-%m-%d")

	cache_key = 'search_news{0},{1},{2}'.format(key, start, end, page)
	cache = getCache(cache_key)
	if cache is not None:
		print("从缓存中获取到新闻")
		return json.loads(cache)
	url = 'https://sou.chinanews.com/search/news'
	body = {
		'q': key,
		'searchField': 'all',
		'sortType': 'time',
		'dateType': '',
		'startDate': start,
		'endDate': end,
		'channel': 'all',
		'editor': '',
		'shouQiFlag': 'show',
		'pageNum': str(page)
	}

	print('开始获取新闻', url, body)
	res_txt = post(url, body, sleep=3)

	date_pattern = r'docArr = (\[.*\]);'
	match = re.search(date_pattern, res_txt)
	if match:
		list = match.group(1)

		if list == '' or list == '[]':
			return []
		
		list = json.loads(list)
		res = []
		for item in list:
			cat = item['primary_channel']
			if cat in CAT_MAPS:
				cat = CAT_MAPS[cat]
			title = item['title']
			if type(title) is not str:
				title = '。'.join(title)
			title = title.replace('<em>', '').replace('</em>', '')
			obj = {
				"name": title,
				"en_name": "",
				"url": item['url'],
				"desc": item['content_without_tag'].replace('<em>', '').replace('</em>', ''),
				"file_type": "htm",
				"category": '临时:新闻-' + cat,
				"en_category": item['primary_channel'],
				"source": "中国新闻网",
				"date": item['pubtime'][:10],
				"key": item['url'],
				"handler": 'news'
			}
			res.append(obj)
		print('新闻获取成功, 共计：' + str(len(res)))

		setCache(cache_key, json.dumps(res, ensure_ascii=False))
		return res

	raise ValueError('未获取到新闻')

def search_news(key='', start_date='', end_date=''):
	"""
	搜索新闻

	参数：
		key: 关键字
		end_date: 截止时间
	"""
	print('开始搜索新闻')
	page = 1
	res_list = []
	while page <= 2:
		print('逐页获取，' + str(page))
		res = get_news_page(key, start=start_date, end=end_date, page=page)
		if len(res) <= 0:
			break
		res_list = res_list + res
		page += 1

	print('新闻搜索成功，总计：{0}'.format(len(res_list)))
	return res_list

def get_detail(url):
	res_txt = get(url, sleep=3)
	html = BeautifulSoup(res_txt, 'html.parser')
	if html is None and html == '':
		return ''
	
	content_html = html.find("div", class_="left_zw")

	if content_html is None:
		content_html = html.find("div", class_="content_desc")

	if content_html is None or content_html == '':
		return ''

	return content_html.get_text(strip=True)


if __name__ == '__main__':
	news = search_news('中国黄金')
	print(news)
	content = get_detail(news[0]['key'])
	print(content)