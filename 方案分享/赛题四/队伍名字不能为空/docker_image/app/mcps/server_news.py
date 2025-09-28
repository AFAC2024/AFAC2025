"""
获取新闻的mcp服务

1.0 @nambo 2025-07-20
"""
from mcp.server.fastmcp import FastMCP
from data_types import StockPrice, Doc, StockInfo
from spider import data_gjtjj
from spider import data_rmyh
from spider import index_hs
from spider import zhengce_gwy
from spider import news

mcp = FastMCP("NewsServer")

@mcp.tool()
def search_news(words: str, start_date='', end_date='') -> list[Doc]:
  """
  搜索中国新闻网，获取关键字对应的最新的新闻列表，如果为空则获取全部最新新闻

  参数：
    words: 搜索的关键字，可以是企业名称、行业、产业、产品名称、设备、材料名称
    start_date: 开始日期(格式yyyy-mm-dd, 非必须)
    end_date: 结束日期(格式yyyy-mm-dd, 非必须)
  """
  res = news.search_news(words, start_date, end_date)
  return res

@mcp.tool()
def get_news_content(url: str) -> str:
  """
  从中国新闻网，根据新闻的url地址，获取新闻的具体内容

  参数：
    url: 新闻搜索返回的数据中url字段
  """
  res = news.get_detail(url)
  return res
  
if __name__ == "__main__":
  mcp.run()