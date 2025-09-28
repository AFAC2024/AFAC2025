"""
使用AkShare获取数据

1. 财务摘要
2. 三大财务报告

* 期货、外汇、宏观经济等其他金融及衍生品指标通过data menu直接加载到向量库中

1.0 @nambo 2025-07-20
"""
import akshare as ak
import pandas as pd
from datetime import date, timedelta, datetime
import sys
import os

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from spider import stock_bd
from common.cache import removeCache, getCache, setCache, get_md5

def get_financial_abstract(stock_code: str, market='sh', end=None, start=None):
    """
    根据股票代码获取上市公司的财务指标摘要

    参数:
        stock_code: 上市公司代码(仅代码不需要所在交易所部分)
        market: 所在交易所(仅支持上交所-sh、深交所-sz、港交所-hk，非必传，默认：sh)
        start: 数据开始日期(格式yyyy-mm-dd，默认：2年前)
    """

    today = date.today()
    if end is None or end == '':
        end = today
    else:
        end = datetime.strptime(end, "%Y-%m-%d")

    if start is None or start == '':
        start = end - timedelta(days=1110)
        start = start.strftime("%Y-%m-%d")
    
    end = end.strftime("%Y-%m-%d")
    
    print('开始获取财务概况：{0},{1},{2}'.format(stock_code, market, start, end))

    cache_key = 'get_financial_abstract1{0},{1},{2},{3}'.format(stock_code, market, start, end)
    cache = getCache(cache_key)
    if cache != None:
        print("从缓存中获取到结果")
        return cache

    date_col = ''
    if market == 'hk':
        df = ak.stock_financial_hk_analysis_indicator_em(symbol=stock_code, indicator="报告期")
        date_col = 'REPORT_DATE'
    elif market == 'sh' or market == 'sz':
        df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
        date_col = '报告期'
    else:
        raise ValueError('market仅支持上交所-sh、深交所-sz、港交所-hk')
    
    df = df[df[date_col] >= start]
    df = df[df[date_col] <= end]
    if len(df) > 0:
        df = df.sort_values(by=date_col, ascending=False)
    
    res = df.to_csv(index=False)
    setCache(cache_key, res)

    print('财务概况获取成功')
    return res

def get_financial_report(stock_code, report_type='资产负债表', market='sh', end=None, start=None):
    """
    根据股票代码获取上市公司的三大会计报表

    参数:
        stock_code: 上市公司代码(仅代码不需要所在交易所部分)
        report_type: 报表类型(支持资产负债表、利润表、现金流量表)
        market: 所在交易所(仅支持上交所-sh、深交所-sz、港交所-hk，非必传，默认：sh)
        start: 数据开始日期(格式yyyy-mm-dd，默认：2年前)
    """
    today = date.today()
    if end is None or end == '':
        end = today
    else:
        end = datetime.strptime(end, "%Y-%m-%d")

    if start is None or start == '':
        start = end - timedelta(days=1110)
        start = start.strftime("%Y-%m-%d")
    
    end = end.strftime("%Y-%m-%d")

    if report_type not in ['资产负债表', '利润表', '现金流量表']:
        raise ValueError('report_type仅支持: 资产负债表、利润表、现金流量表，传入了:' + report_type)

    print('开始获取上市公司三大报表：{0},{1},{2},{3},{4}'.format(stock_code, report_type, market, start, end))

    cache_key = 'get_financial_report10{0},{1},{2},{3},{4}'.format(stock_code, report_type, market, start, end)
    cache = getCache(cache_key)
    if cache != None:
        print("从缓存中获取到结果")
        return cache

    date_col = ''
    use_cols = []
    if market == 'hk':
        df = ak.stock_financial_hk_report_em(stock=stock_code, symbol=report_type, indicator='报告期')
        date_col = 'REPORT_DATE'
        start = start + ' 00:00:00'
        end = end + ' 00:00:00'
        use_cols = ['REPORT_DATE', 'STD_ITEM_CODE', 'STD_ITEM_NAME', 'AMOUNT']
    elif market == 'sh' or market == 'sz':
        df = ak.stock_financial_report_sina(stock=market + stock_code, symbol=report_type)
        date_col = '报告日'
        start = start.replace('-', '')
        end = end.replace('-', '')
    else:
        raise ValueError('market仅支持上交所-sh、深交所-sz、港交所-hk')
    
    if date_col != '':
        df[date_col] = df[date_col].astype(str)
        df = df[df[date_col] <= end]
        df = df[df[date_col] >= start]
        if len(df) > 0:
            df = df.sort_values(by=date_col, ascending=False)
        
        df[date_col] = df[date_col].str.replace(' 00:00:00', '', regex=False)
    
    if use_cols is not None and len(use_cols) > 0:
        df = df[use_cols]
    
    res = df.to_csv(index=False)
    setCache(cache_key, res)

    print('三大报表获取成功')
    return res

def get_business_composition(stock_code: str, market='sh', end=None, start=None):
    """
    根据股票代码获取上市公司的经营业务构成

    参数:
        stock_code: 上市公司代码(仅代码不需要所在交易所部分)
        market: 所在交易所(仅支持上交所-sh、深交所-sz、港交所-hk，非必传，默认：sh)
        start: 数据开始日期(格式yyyy-mm-dd，默认：2年前)
    """
    today = date.today()
    if end is None or end == '':
        end = today
    else:
        end = datetime.strptime(end, "%Y-%m-%d")

    if start is None or start == '':
        start = end - timedelta(days=1110)
        start = start.strftime("%Y-%m-%d")
    
    end = end.strftime("%Y-%m-%d")
    
    print('开始获取业务构成1：{0},{1},{2}'.format(stock_code, market, start, end))

    if market == 'hk':
        return stock_bd.get_business_composition(stock_code, market, start=start, end=end)

    cache_key = 'get_main_business1{0},{1},{2},{3}'.format(stock_code, market, start, end)
    cache = getCache(cache_key)
    if cache != None:
        print("从缓存中获取到结果")
        return cache
    date_col = ''

    df = ak.stock_zygc_em(symbol=market + stock_code)
    date_col = '报告日期'

    if date_col != '':
        str_date_col = 'str' + date_col
        df[str_date_col] = df[date_col].astype(str)
        df = df[df[str_date_col] >= start]
        df = df[df[str_date_col] <= end]
        if len(df) > 0:
            df = df.sort_values(by=str_date_col, ascending=False)
        df.drop(columns=[str_date_col], inplace=True)
    
    res = df.to_csv(index=False)
    setCache(cache_key, res)

    print('业务构成获取成功')
    return res


if __name__ == '__main__':
    # res = get_business_composition('09961', 'hk')
    # print(res)

    # res = get_business_composition('601128', 'sh')
    # print(res)

    # res = get_business_composition('002208', 'sz')
    # print(res)

    res = get_financial_report('00020', '现金流量表', 'hk', '2025-07-21')
    print(res)