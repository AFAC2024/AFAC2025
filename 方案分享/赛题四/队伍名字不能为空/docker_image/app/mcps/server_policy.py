"""
获取政策的MCP服务

1.0 @nambo 2025-07-20
"""
from mcp.server.fastmcp import FastMCP
from data_types import StockPrice, Doc, StockInfo
from spider import data_gjtjj
from spider import data_rmyh
from spider import index_hs
from spider import zhengce_gwy
from spider import news

mcp = FastMCP("PolicyServer")

@mcp.tool()
def search_policy(words: str) -> list[Doc]:
  """
  搜索国务院政策公开网站，获取关键字对应的最新的政策文件与国务院公告列表，如果为空则获取全部最新政策

  参数：
    words: 搜索的关键字，可以是企业名称、行业、产业、产品名称、设备、材料名称
  """
  res = zhengce_gwy.search_zc(words)
  return res

@mcp.tool()
def get_policy_content(url: str) -> str:
  """
  从国务院政策公开网站，根据政策文件的地址，获取政策文件的具体内容

  参数：
    url: 国务院政策搜索返回的数据中url字段
  """
  res = zhengce_gwy.get_detail(url)
  return res
  
if __name__ == "__main__":
  mcp.run()