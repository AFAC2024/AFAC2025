"""
百度股市通获取采集

1. 关键字搜索股票/板块
2. 获取股票/板块K线数据
3. 获取股票三大会计报表
4. 获取企业十大股东
5. 获取企业主营业务结构
6. 获取企业高管信息

1.0 @nambo 2025-07-20
"""
import pandas as pd
import json
import sys
import os
import requests
import time 
from datetime import date, timedelta, datetime
import urllib.parse
import urllib.request
import ssl

# 爬取百度股市通内的股票数据

# 获取当前文件的绝对路径  
current_file_path = os.path.abspath(__file__)  
  
# 获取当前文件所在的目录  
current_dir = os.path.dirname(current_file_path)  
  
# 获取上级目录的路径  
parent_dir = os.path.dirname(current_dir)
parent_dir = os.path.dirname(parent_dir)
sys.path.append(parent_dir)

from mcps.common.cache import setCache, getCache, removeCache
from mcps.common.http_utils import get, get_header

from mcps.spider import report_hk, report_sh, report_sz
from config import conf

search_url = "http://finance.pae.baidu.com/selfselect/sug?wd={0}&skip_login=1&finClientType=pc"

headers = {
	"Cookie": conf['bd_stock_token'],
	# "User-Agent": "PostmanRuntime/7.26.8",
	"User-Agent": "curl/7.83.1",
	"Connection": "Keep-Alive",
	# "Cache-Control":"no-cache",
	"Host":"finance.pae.baidu.com",
}

def get_db(url, headers=headers, sleep=3, timeout=30,cache_key=''):
	"""
	调用百度股市通的通用方法
	"""
	if cache_key == None or cache_key == '':
		cache_key = url

	cache = getCache(cache_key)
	if cache != None:
		print("从缓存中获取到关键字结果")
		return json.loads(cache)
	
	# 创建上下文忽略SSL证书验证
	ssl_context = ssl.create_default_context()
	ssl_context.check_hostname = False
	ssl_context.verify_mode = ssl.CERT_NONE

	try:
			if sleep is not None and sleep > 0 :
				time.sleep(sleep)
			response = requests.get(
					url,
					headers=headers,
					timeout=timeout
			)
			# 检查状态码
			if response.status_code == 200:
					return response.text
			else:
					msg = f"请求失败，状态码: {response.status_code}"
					raise ValueError(msg)
	except requests.exceptions.RequestException as e:
			print(f"请求异常: {e}")
			raise e

def init_headers():
	"""
	初始化股市通的token
	"""
	res = get_header(search_url.format('股票'), headers=headers)
	print(res)
	if 'Set-Cookie' in res:
		cookie = res['Set-Cookie']
		if 'BAIDUID=' in cookie:
			cookie = cookie.split('BAIDUID=')[1].split(';')[0]
			headers['Cookie'] = 'BAIDUID=' + cookie
			print('更新Cookie:', cookie)

# init_headers()

# 数据格式化
def format(data, columns):
	"""
	股市通k线数据格式化
	"""
	data_list = []
	for item in data.split(';'):
		item_arr = item.split(',')
		data_list.append(item_arr)

	df = pd.DataFrame(data=data_list, columns=columns)

	float_col = [
		"open",
		"close",
		"high",
		"low",
		"range",
		"ratio",
		"turnoverratio",
		"preClose",
		"ma5avgprice",
		"ma10avgprice",
		"ma20avgprice"
	]
	for col in float_col:
		df[col] = df[col].replace('--', '0') 
		df[col] = df[col].astype(float).round(2)

	int_col = [
		"timestamp",
		"volume",
		"amount",
		"ma5volume",
		"ma10volume",
		"ma20volume"
	]
	for col in int_col:
		df[col] = df[col].replace('--', '0') 
		df[col] = df[col].astype(float).astype(int)

	return json.loads(df.to_json(orient='records'))

# 基于关键字搜索股票或板块代码
def search(key_words, type="stock"):
	url = search_url
	url = url.format(key_words)

	print("开始搜索关键字：", key_words)
	cache_key = url + type
	cache = getCache(cache_key)
	if cache != None:
		print("从缓存中获取到关键字结果")
		return json.loads(cache)

	# 发送 POST 请求
	print(url, headers)
	response = requests.get(url, headers=headers, timeout=60)

	# 检查请求是否成功
	if response.status_code == 200:
		res_json = response.json()
		print(res_json)
		res_arr = res_json["Result"]["stock"]
		res = None
		print(res_arr)
		for item in res_arr:
			item["exchange"] = item["exchange"].lower()
			exchange = item["exchange"]
			if type == "stock" and item["type"] == type and (exchange == "sz" or exchange == "sh" or exchange == 'hk'):
				res = item
				break
			elif type == "block" and item["type"] == type:
				res = item
				break
		
		if res != None:
			setCache(cache_key, json.dumps(res, ensure_ascii=False))
			print("搜索成功!")
		else:
			print("搜索结果为空!")
		return res
	else:
		print("搜索失败!")
		print(f"状态码: {response.status_code}")
		print(response.text)
		raise ValueError("搜索失败")

# 搜索股票信息
def search_stock(key_words):
	res = None
	count = 1
	e_data = None
	while count > 0 and count < 10:
		try:
			res = search(key_words)
			count = -1
		except Exception as e:
			print("搜索股票信息失败，将重试：", count, key_words)
			print(e)
			e_data = e
			time.sleep(2)
			count += 1

	if res == None:
		raise ValueError('未搜索到数据，请更换关键字然后重试')
	
	del res['logo']
	del res['sf_url']
	del res['follow_status']
	del res['src_loc']
	del res['subType']
	del res['holdingAmount']
	del res['stockStatus']
	del res['status']
	return res

# 搜索板块
def search_block(key_words):
	res = None
	count = 1
	e_data = None
	while count > 0 and count < 10:
		try:
			res = search(key_words, "block")
			count = -1
		except Exception as e:
			print("搜索板块信息失败，将重试：", count, key_words)
			print(e)
			e_data = e
			time.sleep(2)
			count += 1

	if res == None:
		raise e_data
	return res

# 获取股票价格
def get_price(stock_code, end_date, count=30, type="stock"):
	url = ""
	if type ==  "stock":
		code = stock_code.replace("sz", "")
		code = code.replace("sh", "")
		url = "http://finance.pae.baidu.com/vapi/v1/getquotation?srcid=5353&pointType=string&group=quotation_kline_ab&query={0}&code={0}&market_type=ab&newFormat=1&name=%E7%A7%91%E9%99%86%E7%94%B5%E5%AD%90&is_kc=0&ktype=day&finClientType=pc&finClientType=pc"
		url = url.format(code)
	elif type == "block":
		url = "http://finance.pae.baidu.com/vapi/v1/getquotation?pointType=string&group=quotation_block_kline&query={0}&code={0}&market_type=ab&newFormat=1&name=%E9%94%82%E7%94%B5%E6%B1%A0%E6%A6%82%E5%BF%B5&ktype=day&end_time={1}&count={2}&finClientType=pc"
		url = url.format(stock_code, end_date, count)

	print("开始获取股价：")
	cache_key = url + end_date + str(count)
	cache = getCache(cache_key)
	if cache != None:
		print("从缓存中获取到股价")
		return json.loads(cache)

	# 发送 POST 请求
	response = requests.get(url, headers=headers)

	# 检查请求是否成功
	if response.status_code == 200:
		res_json = response.json()
		res_json = format(res_json["Result"]["newMarketData"]["marketData"],
			res_json["Result"]["newMarketData"]["keys"])

		res_arr = []

		start_date = datetime.strptime(end_date, "%Y-%m-%d")
		start_date = start_date - timedelta(count)
		start_date = start_date.strftime('%Y-%m-%d')
		for item in res_json:
			date = item["time"]
			if date >= start_date and  date <= end_date:
				res_arr.append({
					"open": round(float(item["open"]), 2),
					"close": round(float(item["close"]), 2),
					"high": round(float(item["high"]), 2),
					"low": round(float(item["low"]), 2),
					"volume": item["volume"],
					"amount": round(float(item["amount"]), 2),
					"range": round(float(item["range"]), 2),
					"ratio": round(float(item["ratio"]), 2),
					"turnoverratio": round(float(item["turnoverratio"]), 2),
					"preClose": round(float(item["preClose"]), 2),
					"ma5avgprice": round(float(item["ma5avgprice"]), 2),
					"ma5volume": round(float(item["ma5volume"]), 2),
					"ma10avgprice": round(float(item["ma10avgprice"]), 2),
					"ma10volume": round(float(item["ma10volume"]), 2),
					"ma20avgprice": round(float(item["ma20avgprice"]), 2),
					"ma20volume": round(float(item["ma20volume"]), 2),
					"date": date,
				})
		setCache(cache_key, json.dumps(res_arr, ensure_ascii=False))
		print("股价获取成功!")
		return res_arr
	else:
		print("股价获取失败!")
		print(f"状态码: {response.status_code}")
		print(response.text)
		raise ValueError("股价获取失败")



def get_block_price(block_code, end_date):
	print("开始获取板块股价：" + block_code)
	json_data = None
	count = 1
	e_data = None
	while count > 0 and count < 10:
		try:
			json_data = get_price(block_code, end_date=end_date, count=30, type="block")
			count = -1
		except Exception as e:
			print("获取板块股价失败，将重试：", count, block_code)
			print(e)
			e_data = e
			time.sleep(2)
			count += 1

	if json_data == None:
		raise e_data

	print("板块股价获取成功：" + block_code)
	return json_data

# 获取股票近7日价格
def getStockPrice(stock_code, end_date):
	print("开始获取股价：" + stock_code)
	json_data = None
	count = 1
	e_data = None
	while count > 0 and count < 10:
		try:
			json_data = get_price(stock_code, end_date=end_date, count=40)	  #默认获取今天往前5天的日线实时行情
			count = -1
		except Exception as e:
			print("获取股价失败，将重试：", count, stock_code)
			print(e)
			time.sleep(2)
			e_data = e
			count += 1

	if json_data == None:
		raise e_data

	print("股价获取成功：" + stock_code)
	return json_data

def getStockPriceByName(name, end_date):
	res = search_stock(name)
	print("获取到股票信息：", res["code"], res["name"], res)
	prices = getStockPrice(res["code"], end_date)
	return prices

# 获取指定名称行业的K线数据
def getIndustryKLine(industry_name, end_date):
	res = search_block(industry_name)
	print("获取到板块信息：", res["code"], res["name"], res)
	prices = get_block_price(res["code"], end_date)
	return prices

def get_business_composition_type(stock_code: str, market='sh', start=None, end=None, data_type='按产品'):
	print('获取主营业务构成明细数据', stock_code, market, start, end, data_type)
	product_url = 'http://finance.pae.baidu.com/vapi/v1/mainop?market={market}&code={code}&type=product&text=%E4%BA%A7%E5%93%81&params=%7B%22classification%22:20,%22ff_segment_type%22:%22BUS%22,%22type%22:%22product%22%7D&finClientType=pc'
	area_url = 'http://finance.pae.baidu.com/vapi/v1/mainop?market={market}&code={code}&type=region&text=%E5%9C%B0%E5%9F%9F&params=%7B%22classification%22:30,%22ff_segment_type%22:%22REG%22,%22type%22:%22region%22%7D&finClientType=pc'

	today = date.today()
	if end is None or end == '':
		end = today
	else:
		end = datetime.strptime(end, '%Y-%m-%d')

	if start is None or start == '':
		start = end - timedelta(days=1110)
		start = start.strftime("%Y-%m-%d")
	end = end.strftime("%Y-%m-%d")

	url = ''
	if data_type == '按产品':
		url = product_url
	elif data_type == '按地区':
		url = area_url
	else:
		raise ValueError('data_type仅支持：按产品、按地区')
	
	url = url.format(market=market, code=stock_code)
	cache_key = 'get_business_composition1{0},{1}'.format(url, today.strftime("%Y-%m"))

	print(url)
	res_txt = get(url, headers=headers, sleep=3, cache_key=cache_key)
	data = json.loads(res_txt)

	if 'ResultCode' not in data or data['ResultCode'] != 0:
		raise ValueError('数据获取失败')

	res = []
	for item in data['Result']['list']:
		item_date = item['title']
		if '年报' not in item_date:
			continue

		item_date = item_date.replace('一季报', '-03-31').replace('年报', '-12-31').replace('中报', '-06-30').replace('三季报', '-09-30')
		for detail in item['body']:
			res_item = {}
			res_item['报告日期'] = item_date
			res_item['分类类型'] = data_type + '分类'
			res_item['主营构成'] = detail['name']
			res_item['主营收入'] = detail['income']
			res_item['收入比例'] = detail['ratio']
			res.append(res_item)
	
	df = pd.DataFrame(res)
	if len(df) <= 0:
		return df
	
	df = df[df['报告日期'] >= start]
	df = df[df['报告日期'] <= end]
	if len(df) > 0:
		df = df.sort_values(by='报告日期', ascending=False)

	res = df.to_csv(index=False)
	return df

def get_business_composition(stock_code: str, market='sh', end=None, start=None):
	product_res = get_business_composition_type(stock_code, market, start, end, '按产品')
	area_res = get_business_composition_type(stock_code, market, start, end, '按地区')
	
	df = pd.concat([product_res, area_res], axis=0)
	if len(df) > 0:
		df = df.sort_values(by='报告日期', ascending=False)
		return df.to_csv(index=False)
	else:
		return '暂无数据'

def get_bdstock_data(url, headers_p=None):
	if headers_p is None:
		headers_p = headers
	cache_key = '{0},{1}'.format(url, date.today().strftime("%Y-%m"))
	res_txt = get(url, headers=headers_p, sleep=2, cache_key=cache_key)

	data = json.loads(res_txt)
	
	if 'ResultCode' not in data or data['ResultCode'] != '0':
		removeCache(cache_key)
		raise ValueError('获取数据失败')
	
	return data

def get_company_basic_info_data(stock_code: str, market='sh'):
	url = 'http://finance.pae.baidu.com/api/stockwidget?finClientType=pc&code={code}&market={market}&type=stock&widgetType=company'
	
	market_bd = market

	if market_bd in ['sh', 'sz']:
		market_bd = 'ab'
	url = url.format(code=stock_code, market=market_bd)

	print('开始获取上市公司简介', url)
	return get_bdstock_data(url)

def get_company_basic_info(stock_code: str, market='sh'):
		data = get_company_basic_info_data(stock_code, market)
		market = {
			'sh': '上海',
			'sz': '深圳',
			'hk': '香港',
		}[market]
		result = data['Result']
		basic = result['content']['newCompany']['basicInfo']
		industrys = basic['industry']
		industry = []
		for ind in industrys:
			industry.append(ind['text'])
		industry = '、'.join(industry)
		if len(industrys) == 1:
			industry = '，属于' + industry + '行业'
		elif len(industrys) > 1:
			industry = '，属于' + industry + '等行业'
		else:
			industry = ''
		
		create_info = ''

		if 'chairman' in basic:
			create_info = '由' + basic['chairman'] + '创立'

		if 'region' in basic:
			create_info += '位于' + basic['region']

		shares = 0
		if 'issueNumber' in basic:
			shares = '总发行' + basic['issueNumber'] + '股'
		elif 'totalShares' in basic:
			shares = '总发行' + basic['totalShares']
		
		main_business = ''
		if 'companyInfo' in result['content'] and 'issuedBy' in result['content']['companyInfo']:
			issued_by = result['content']['companyInfo']['issuedBy']
			if market != '香港':
				main_business = result['content']['companyInfo']['name'] + issued_by['description'] + '主营业务包括：' + issued_by['mainBusiness']
			else:
				main_business = issued_by['description'] + issued_by['mainBusiness']
		else:
			main_business = basic['mainBusiness']
			if market != '香港':
				main_business = '主营业务包括：' + main_business

		website = ''
		if 'website' in basic:
			website = '其官方网站为：' + basic['website']
		info = '股票名称“{stock_name}(代码:{code})”，是{comp_name}于{release_date}在{market}证券交易所公开发行的股票，{total_shares}。{comp_name}{create_info}{industry}。{main_business}{website}'
		info = info.format(stock_name=result['stockName']
										 , code=result['code']
										 , release_date=basic['releaseDate']
										 , comp_name=basic['companyName']
										 , market=market
										 , create_info=create_info
										 , industry=industry
										 , total_shares=shares
										 , main_business=main_business
										 , website=website)
		
		print('上市公司简介获取成功')
		return info

def get_company_executive(stock_code: str, market='sh'):
		company = get_company_basic_info_data(stock_code, market)
		name = company['Result']['stockName']
		company_code = company['Result']['content']['newCompany']['basicInfo']['companyCode']
		inner_code = company['Result']['content']['newCompany']['basicInfo']['innerCode']
		
		res = []
		if market in ['sh', 'sz']:
			url = 'http://finance.pae.baidu.com/selfselect/openapi?srcid=5539&code={code}&company_code={company_code}&inner_code={inner_code}&group=leader_info&listedSector=1&finClientType=pc'
			url = url.format(company_code=company_code, code=stock_code, inner_code=inner_code)
			data = get_bdstock_data(url)
			executive_list = data['Result']['executiveInfo']['body']
			cols = data['Result']['executiveInfo']['header']
			for item in executive_list:
				res_item = {}
				for idx, col in enumerate(cols):
					res_item[col] = item[idx]
				res.append(res_item)
		elif market == 'hk':
			executive_list = company['Result']['content']['newCompany']['executiveInfo']['body']
			for item in executive_list:
				res.append({
					'高管': item['executive'],
					'职务': item['post']
				})

		df = pd.DataFrame(res)
		return df.to_csv(index=False)

def get_stock_holder(stock_code: str, market='sh'):
		company = get_company_basic_info_data(stock_code, market)
		name = company['Result']['stockName']
		company_code = company['Result']['content']['newCompany']['basicInfo']['companyCode']
		inner_code = company['Result']['content']['newCompany']['basicInfo']['innerCode']
		
		res = []
		if market in ['sh', 'sz']:
			url = 'http://finance.pae.baidu.com/selfselect/openapi?srcid=5539&code={code}&company_code={company_code}&inner_code={inner_code}&group=holder_equity&listedSector=6&finClientType=pc'
			url = url.format(company_code=company_code, code=stock_code, inner_code=inner_code)
		elif market == 'hk':
			url = 'http://finance.pae.baidu.com/selfselect/openapi?srcid=5539&code={code}&name={name}&market={market}&company_code={company_code}&inner_code={inner_code}&group=hk_holder_equity&finClientType=pc'
			url = url.format(company_code=company_code, code=stock_code, inner_code=inner_code, market=market, name=name)
		print(url)
		data = get_bdstock_data(url)
		holder_list = data['Result']['holdShareInfo']['content']['body']
		for item in holder_list:
			res_item = {
				'股东': item['holder'],
				'持股数量': item['holdNum'],
				'持股比例': item['holdPer'],
				'持股变化': item['holdChange']
			}
			res.append(res_item)

		df = pd.DataFrame(res)
		return df.to_csv(index=False)


data_list_tpl = '[{{"name":"{comp_name}企业基本信息","en_name":"","url":"{detail_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的企业基本信息。包含其在证券交易所留存的企业介绍、主营业务、基本信息。","file_type":"pdf","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_company_basic_info|{stock_code}|{market}","handler":"stock_bd"}},{{"name":"{comp_name}近期的股票K线数据(按日)","en_name":"","url":"{detail_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})近期，按日的股票K线数据。包含其每日的开盘价、收盘价、最高价、最低价、成交量、成交额、5日均价、10日均价、20日均价、涨跌幅、日期等字段。","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"getStockPrice|{stock_code}|{data_date}","handler":"stock_bd"}},{{"name":"{comp_name}的主营业务构成","en_name":"","url":"{invest_report_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的主营业务构成，返回csv字符串格式数据，包含按产品、按地区的业务构成、收入、占比","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_business_composition|{stock_code}|{market}|{data_date}","handler":"stock_bd"}},{{"name":"{comp_name}的管理层信息","en_name":"","url":"{invest_report_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的管理层信息，返回csv字符串格式数据，包含高管姓名、职务","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_company_executive|{stock_code}|{market}","handler":"stock_bd"}},{{"name":"{comp_name}的十大股东","en_name":"","url":"{invest_report_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的十大股东，返回csv字符串格式数据，包含股东名称、持股数量、持股比例、持股变化","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_stock_holder|{stock_code}|{market}","handler":"stock_bd"}},{{"name":"{comp_name}的财务指标摘要","en_name":"","url":"{invest_report_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的财务指标摘要，返回csv字符串格式数据","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_financial_abstract|{stock_code}|{market}|{data_date}","handler":"stock_akshare"}},{{"name":"{comp_name}的资产负债表","en_name":"","url":"{invest_report_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的资产负债表，返回csv字符串格式数据","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_financial_report|{stock_code}|资产负债表|{market}|{data_date}","handler":"stock_akshare"}},{{"name":"{comp_name}的利润表","en_name":"","url":"{invest_report_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的利润表，返回csv字符串格式数据","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_financial_report|{stock_code}|利润表|{market}|{data_date}","handler":"stock_akshare"}},{{"name":"{comp_name}的现金流量表","en_name":"","url":"{invest_report_url}","desc":"上市公司{comp_name}(股票代码{stock_code}.{market})的现金流量表，返回csv字符串格式数据","file_type":"csv","category":"临时:股票数据","en_category":"","source":"{market_name}","date":"{data_date}","key":"get_financial_report|{stock_code}|现金流量表|{market}|{data_date}","handler":"stock_akshare"}},{{"name": "基于{comp_name}财报进行的ROE分析","en_name": "ROE Analysis Report","url": "{invest_report_url}","desc": "上市公司{comp_name}(股票代码{stock_code}.{market})的基于资产负债表、利润表进行财务ROE分析得到的净资产收益率(ROE)分析报告。包含ROE趋势分析、行业对比、杜邦分析等核心财务指标。","file_type": "pdf","category": "临时:财务分析报告","en_category": "Financial Analysis Reports","source": "{market_name}","date": "{data_date}","key": "get_roe_analysis_report|{comp_name}|{stock_code}|{market}","handler": "financial_analysis"}},{{"name": "基于{comp_name}财报进行的DCF+FCF估值分析","en_name": "DCF & FCF Valuation Report","url": "{invest_report_url}","desc": "上市公司{comp_name}(股票代码{stock_code}.{market})基于现金流量表进行财务分析，得到的现金流折现(DCF)与自由现金流(FCF)分析报告。包含历史现金流分析、未来现金流预测、折现率计算、企业估值及敏感性分析等内容。","file_type": "pdf","category": "临时:估值分析报告","en_category": "Valuation Analysis Reports","source": "{market_name}","date": "{data_date}","key": "get_dcf_fcf_analysis|{comp_name}|{stock_code}|{market}","handler": "financial_analysis"}}]'
def get_data_list(comp_name, stock_code, market, data_date=None):
	market_name = {
		'sh': '上海证券交易所',
		'sz': '深圳证券交易所',
		'hk': '香港证券交易所'
	}[market]

	market_detail_url = {
		'sz': 'https://www.szse.cn/certificate/individual/index.html?code={code}',
		'sh': 'https://www.sse.com.cn/home/search/index.shtml?webswd={comp_name}',
		'hk': 'https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym={code_int}&sc_lang=zh-hk'
	}

	detail_url = market_detail_url[market].format(code=stock_code, comp_name=comp_name, code_int=str(int(stock_code)))
	invest_report_url = ''

	# 获取股票的公告数据目录
	reports = []
	try:
		if market == 'sh':
			reports = report_sh.get_report(stock_code, end=data_date)
			invest_report_url = report_sh.get_invest_report(stock_code, end=data_date)
		elif market == 'sz':
			reports = report_sz.get_report(stock_code, end=data_date)
			invest_report_url = report_sz.get_invest_report(stock_code, end=data_date)
		elif market == 'hk':
			reports = report_hk.get_report(stock_code, end=data_date)
			invest_report_url = report_hk.get_invest_report(stock_code, end=data_date)
		
		if invest_report_url is not None and 'url' in invest_report_url and invest_report_url['url'] != '':
			invest_report_url = invest_report_url['url']
		else:
			invest_report_url = detail_url
	except:
		reports = []

	if data_date is None or data_date == '':
		data_date = date.today().strftime('%Y-%m-%d')
	
	# 获取股票的k线、三大报表、主营业务等数据目录
	res = data_list_tpl.format(comp_name=comp_name, stock_code=stock_code, market=market, data_date=data_date, market_name=market_name, detail_url=detail_url, invest_report_url=invest_report_url)
	res = json.loads(res)

	if reports is not None and len(reports) > 0:
		res += reports

	return res

if __name__ == '__main__':
	# res = get_db('http://finance.pae.baidu.com/selfselect/sug?wd=%E8%82%A1%E7%A5%A8&skip_login=1&finClientType=pc')
	# print(res)
	# res = search_block('宁德时代')
	# print(res)

	# res = get_data_list('商汤科技', '00020', 'hk', '2025-07-01')
	# print(res)
	# res = get_business_composition('00020', 'hk', end='2025-07-01')
	# print(res)
	res = get_stock_holder('00020', 'hk')
	print(res)
	# res = get_stock_holder('601128', 'sh')
	# print(res)
	# res = get_stock_holder('300750', 'sz')
	# print(res)
