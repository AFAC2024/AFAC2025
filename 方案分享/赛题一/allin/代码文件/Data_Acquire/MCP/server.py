"""
定义MCP工具供大模型调用
金融数据来源自akshare金融数据接口
"""
import json
from fastmcp import FastMCP
import akshare as ak
import pandas as pd

mcp = FastMCP()
@mcp.tool()
def get_daily_news(start_date:str, end_date:str):
    """
    获取指定日期内的每日财经新闻
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 每日财经新闻的json数据
    """
    global_news=ak.stock_info_cjzc_em()
    global_news.columns = ['title','summary','date','url']
    global_news['date'] = pd.to_datetime(global_news['date'])
    global_news['date'] = global_news['date'].apply(lambda x: pd.to_datetime(x.strftime('%Y-%m-%d')))
    global_news = global_news[(global_news['date'] >= pd.to_datetime(start_date)) & (global_news['date'] <= pd.to_datetime(end_date))]
    global_news = global_news[global_news.columns[:-1]]
    global_news['date'] = global_news['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    return json.dumps(
                {
                    "success": True,
                    "msg": global_news.to_dict(orient="records"),
                },
            )
    
@mcp.tool()
#获取基金净值数据
def get_fund_nav(fund_code:str,start_date:str, end_date:str):
    """
    获取基金净值数据
    :param fund_code: 基金代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 基金净值的json数据
    """
    net_value = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
    net_value.columns = ['date', 'net_asset_value','growth_rate']
    net_value['date'] = pd.to_datetime(net_value['date'])
    net_value = net_value[(net_value['date'] >= pd.to_datetime(start_date)) & (net_value['date'] <= pd.to_datetime(end_date))]
    net_value['date'] = net_value['date'].dt.strftime('%Y-%m-%d')
    return json.dumps(
                {
                    "success": True,
                    "msg": net_value.to_dict(orient="records"),
                },
            )
@mcp.tool()
def get_stock_data(index_code:str,start_date:str, end_date:str):
    """
    获取股票市场指数的历史交易数据
    :param index_code: 指数代码
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return: 股票市场指数的历史交易数据的json数据
    """
    stock_market = ak.stock_zh_index_daily(symbol=index_code)
    stock_market['date'] = pd.to_datetime(stock_market['date'])
    stock_market = stock_market[(stock_market['date'] >= pd.to_datetime(start_date)) & (stock_market['date'] <= pd.to_datetime(end_date))]
    stock_market.reset_index(drop=True, inplace=True)
    stock_market['date'] = stock_market['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    return json.dumps(
                {
                    "success": True,
                    "msg": stock_market.to_dict(orient="records"),
                },
            )

@mcp.tool()
def rank(fund_code: str,start_date:str,end_date:str):
    """
    获取指定基金代码所代表的基金在同类排名百分比数据，并返回 JSON 格式结果。
    :param fund_code (str): 需要查询的基金代码。
    :param start_date (str): 开始时间，格式为 YYYY-MM-DD。
    :param end_date (str): 结束时间，格式为 YYYY-MM-DD。
    :return str: JSON 格式的字符串，包含 success 和 msg 两个字段。
             - success (bool): 表示请求是否成功。
             - msg (list of dict): 同类排名百分比数据的查询结果数据
    """
    data = ak.fund_open_fund_info_em(symbol=fund_code, indicator="同类排名百分比")
    data.columns = ['date', 'rank']
    data['date'] = pd.to_datetime(data['date'])
    data = data[(data['date'] >= pd.to_datetime(start_date)) & (data['date'] <= pd.to_datetime(end_date))]
    data['date'] = data['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    data_list = data.to_dict('records')
    return json.dumps(
                {
                    "success": True,
                    "msg": data_list,
                },
            )


if __name__ == '__main__':
    mcp.run()
    