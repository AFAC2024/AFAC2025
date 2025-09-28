"""
雪球股票相关数据（暂未使用）

1.0 @nambo 2025-07-20
"""
import pysnowball as ball
import requests
import os

if 'xq_token' not in os.environ:
  r = requests.get("https://xueqiu.com/hq", headers={"user-agent": "Mozilla"})
  token = r.cookies["xq_a_token"]
else:
  token = os.environ["xq_token"]
ball.set_token(token)

if __name__ == "__main__":
  # 获取股票信息
  stock = ball.quote_detail("HK:00020")
  print(stock)