"""
获取股票价格数据的mcp服务

1.0 @nambo 2025-07-20
"""
import sys

from mcp.server.fastmcp import FastMCP
from data_types import StockPrice, Doc, StockInfo
from spider.stock_bd import getStockPrice, getIndustryKLine, search_stock, get_business_composition, get_company_basic_info
import spider.report_hk as hk
import spider.report_sh as sh
import spider.report_sz as sz

mcp = FastMCP("StockServer")

@mcp.tool()
def search_stock_info(comp_name: str) -> StockInfo:
  """
  根据企业名称，搜索股票的基本信息，如：股票代码、所在交易所等

  参数：
    comp_name: 搜索的企业名称
  """
  res = search_stock(comp_name)
  return res


@mcp.tool()
def stock_business_composition(stock_code: str, market='sh', date=None) -> str:
  """
  根据股票代码，获取对应上市公司的业务构成，返回csv字符串格式数据，包含按产品、按地区的业务构成、收入、占比

  参数：
    stock_code: 上市公司股票代码
    market: 所属证券交易所(sh-上海证券交易所、sz-深圳证券交易所、hk-香港证券交易所)
    date: 数据截止日期(格式yyyy-mm-dd，非必传，默认当前日期)
  """
  res = get_business_composition(stock_code, market, end=date)
  return res


@mcp.tool()
def stock_company_basic_info(stock_code: str, market='sh') -> str:
  """
  根据股票代码，获取对应上市公司在对应证券交易所留存的企业介绍，返回介绍字符串

  参数：
    stock_code: 上市公司股票代码
    market: 所属证券交易所(sh-上海证券交易所、sz-深圳证券交易所、hk-香港证券交易所)
  """
  res = get_company_basic_info(stock_code, market)
  return res

def get_stock_kline(stock_code: str, end_date: str) -> list[StockPrice]:
  """获取上市公司，指定时间前30天，每日的股票价格
  参数：
   stock_code: 上市公司股票代码
   end_date: 数据截止日期
  """
  res = getStockPrice(stock_code, end_date)
  return res

def get_industry_kline(name: str, end_date: str) -> list[StockPrice]:
  """获取指定时间前30天，股票板块/行业的每日价格
  参数：
   name: 板块/行业名称
   end_date: 数据截止日期
  """
  print('开始获取板块/行业数据', name, end_date)
  res = getIndustryKLine(name, end_date)
  print('数据获取成功，len=', str(len(res)))
  return res

def get_company_reports(stock_code: str, market: str, start_date: str, end_date: str) -> list[Doc]:
  """
  获取上市公司在对应证券交易所的近期公共列表

  参数：
    stock_code: 股票编号
    market: 所属证券交易所(sh-上海证券交易所、sz-深圳证券交易所、hk-香港证券交易所)
    start_date: 开始日期(格式yyyy-mm-dd)
    end_date: 结束日期(格式yyyy-mm-dd)
  """
  print('开始获取上市公司公告', stock_code, market, start_date, end_date)
  res = []
  if market == 'sh':
    res = sh.get_report(stock_code, start=start_date, end=end_date)
  elif market == 'sz':
    res = sz.get_report(stock_code, start=start_date, end=end_date)
  elif market == 'hk':
    res = hk.get_report(stock_code, start=start_date, end=end_date)
  else:
    raise ValueError('目前仅支持上海、深圳、香港证券交易所上市的股票，参数market=' + market)

  print('公告获取成功，len=', str(len(res)))
  return res
  
if __name__ == "__main__":
  mcp.run()