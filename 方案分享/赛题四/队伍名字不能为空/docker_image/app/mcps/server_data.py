"""
获取数据的MCP服务

1.0 @nambo 2025-07-20
"""
from mcp.server.fastmcp import FastMCP
from data_types import StockPrice, Doc, StockInfo
from spider import data_gjtjj
from spider import data_rmyh
from spider import index_hs

mcp = FastMCP("DataServer")

@mcp.tool()
def get_data_list() -> list[Doc]:
  """
  获取可用的数据列表，目前收录了：国家统计局、人民银行统计司、恒生指数
  """
  gjtjj_list = data_gjtjj.get_data_list()
  rmyh_list = data_rmyh.get_data_list()
  hszs_list = index_hs.get_data_list()
  res = gjtjj_list + rmyh_list + hszs_list

  simple_list = []
  for item in res:
    simple_list.append({
      "name": item['name'],
      "en_name": "",
      "url": "",
      "desc": "",
      "comp_name": "",
      "code": "",
      "key": item['key'],
      "file_type": item['file_type'],
      "category": item['category'],
      "en_category": "",
      "source": item['source'],
      "date": item['date']
    })

  return simple_list

@mcp.tool()
def get_data_file(key: str, source: str) -> str:
  """
  根据可用数据列表返回的key，下载数据明细，返回下载后的文件路径

  参数：
    key: 数据的key，可用数据列表方法返回的列表中的元素的key
    source: 数据来源：可用数据列表方法返回的列表中的元素的source，支持：中国国家统计局、香港恒生指数有限公司、中国人民银行调查统计司
  """
  if '中国国家统计局' in source:
    res = data_gjtjj.get_detail(key)
  elif '香港恒生指数有限公司' in source:
    res = index_hs.get_detail(key)
  elif '中国人民银行调查统计司' in source:
    res = data_rmyh.get_detail(key)
  else:
    raise ValueError('目前仅支持：中国国家统计局、香港恒生指数有限公司、中国人民银行调查统计司的数据，注意来源名称必须完全一致')
  
  return res
  
if __name__ == "__main__":
  mcp.run()