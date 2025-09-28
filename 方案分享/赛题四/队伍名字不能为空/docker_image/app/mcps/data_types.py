"""
数据类型定义

1.0 @nambo 2025-07-20
"""
from pydantic import BaseModel, Field
from typing import TypedDict, Optional

# 数据目录
class Doc(BaseModel):
  name: str = Field(description="公告名称")
  en_name: str = Field(description="英文名称")
  url: str = Field(description="公告原始文件链接")
  desc: str = Field(description="公告的简要描述")
  comp_name: Optional[str] = Field(default='', description="公司简称(非必须)")
  code: Optional[str] = Field(default='', description="股票代码(非必须)")
  key: Optional[str] = Field(default='', description="获取具体内容的关键字")
  file_type: str = Field(description="文件类型")
  category: str = Field(description="公告类别")
  en_category: str = Field(description="英文类别")
  source: str = Field(description="来源")
  date: str = Field(description="发布日期")

# 股票数据
class StockInfo(BaseModel):
  code: str = Field(description="股票代码")
  type: str = Field(description="证券类型(stock: 股票, block: 板块)")
  market: str = Field(description="交易市场(sh-上海证券交易所、sz-深圳证券交易所、hk-香港证券交易所)")
  amount: str = Field(description="最后交易日成交金额（上交所、深交所为人民币元，港交所为港元）")
  exchange: str = Field(description="交易所代码，与market相同")
  name: str = Field(description="股票名称")
  price: str = Field(description="当前价格（上交所、深交所为人民币元，港交所为港元）")
  increase: str = Field(description="价格涨跌额")
  ratio: str = Field(description="涨跌幅百分比(%)。")
  amplitudeRatio: str = Field(description="振幅，当日最高最低价波动幅度(%)")
  turnoverRatio: str = Field(description="换手率(%)")
  volume: str = Field(description="成交量")
  capitalization: str = Field(description="总市值（上交所、深交所为人民币元，港交所为港元）")
  peRate: str = Field(description="市盈率(倍)")
  pbRate: str = Field(description="市净率(倍)")
  stockStatusInfo: str = Field(description="状态信息")
  pv: str = Field(description="浏览量")
  CNYPrice: str = Field(description="人民币计价价格")

# 股票价格定义
class StockPrice(BaseModel):
  open: float = Field(description="当日开盘价(单位：元)")
  close: float = Field(description="当日收盘价(单位：元)")
  high: float = Field(description="当日最高价(单位：元)")
  low: float = Field(description="当日最低价(单位：元)")
  volume: float = Field(description="当日成交量(单位：股)")
  amount: float = Field(description="当日成交金额(单位：元)")
  range: float = Field(description="价格变动绝对值(收盘价-前收盘价)")
  ratio: float = Field(description="涨跌幅百分比(%)")
  turnoverratio: float = Field(description="换手率(%)")
  preClose: float = Field(description="前一日收盘价(单位：元)")
  ma5avgprice: float = Field(description="5日均价(过去5个交易日的平均收盘价)")
  ma5volume: float = Field(description="5日均成交量(过去5个交易日的平均成交量)")
  ma10avgprice: float = Field(description="10日均价")
  ma10volume: float = Field(description="10日均成交量")
  ma20avgprice: float = Field(description="20日均价")
  ma20volume: float = Field(description="20日均成交量")
  date: str = Field(description="交易日期(格式yyyy-mm-dd)")