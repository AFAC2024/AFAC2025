#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
风控数据获取工具
用于爬取并保存公司公告和财务相关数据
支持一次性爬取所有股票的公告和财务数据
"""

import os
import time
import traceback
from datetime import datetime

import pandas as pd


# 股票代码到公司名称的缓存字典
STOCK_NAME_CACHE = {}

# 导入 akshare 库用于获取财务数据
try:
    import akshare as ak

    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("警告：未安装akshare库，财务数据获取功能将不可用")

# 请求头设置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

import requests


def get_eastmoney_announcements(
    stock_code, page_size=50, page_index=1, max_retries=3, retry_delay=2
):
    """获取东方财富公告列表"""
    api_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    params = {
        "sr": -1,
        "page_size": page_size,
        "page_index": page_index,
        "ann_type": "A",
        "client_source": "web",
        "stock_list": stock_code,
        "f_node": 0,
        "s_node": 0,
        "_": int(time.time() * 1000),
    }

    # 请求数据
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # 检查数据
            if not data or "data" not in data or "list" not in data["data"]:
                print(f"未获取到公告数据 (第{attempt}次尝试): {data}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return []

            return data["data"]["list"]

        except Exception as e:
            print(f"获取公告列表失败: {e} (第{attempt}次尝试)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return []


def get_eastmoney_announcement_detail(art_code, max_retries=3, retry_delay=2):
    """获取东方财富公告详情"""
    detail_url = "https://np-cnotice-stock.eastmoney.com/api/content/ann"
    params = {"art_code": art_code, "client_source": "web", "page_index": 1}

    # 请求数据
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(detail_url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if "data" in data:
                content = data["data"].get("content")
                if content:
                    return content  # 优先返回正文
                else:
                    return data["data"]  # 没正文时返回结构体（含PDF等）
            else:
                print(f"未获取到公告详情 (第{attempt}次尝试)")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

        except Exception as e:
            print(f"公告详情解析失败 art_code={art_code}: {e} (第{attempt}次尝试)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None


def get_announcements_with_detail(stock_code, max_count=30):
    """获取指定股票公告的标题列表, 只保留标题, 并限制至最多50条"""
    # 强制限制 max_count 不超过 10
    max_count = min(max_count, 10)

    try:
        # 只抓取第一页公告，page_size 同步为 max_count 以减少无用数据
        anns = get_eastmoney_announcements(stock_code, page_size=max_count)
        result = []

        for i, ann in enumerate(anns[:max_count]):
            art_code = ann.get("art_code")
            title = ann.get("title")
            notice_date = ann.get("notice_date", "").split("T")[0]

            # 获取公告正文并截断至前 1000 字，避免超长文本导致上下文溢出
            content = ""
            if art_code:
                detail = get_eastmoney_announcement_detail(art_code)
                if isinstance(detail, str):
                    content = detail[:1000]
                elif isinstance(detail, dict):
                    raw_content = detail.get("content") or detail.get("notice_content") or ""
                    content = raw_content[:1000]

            # 打印简单调试信息
            print(f"[{i + 1}] {title} {notice_date}")

            # 汇总结果：标题 + 日期 + 截断后的正文(≤1000 字)
            result.append(
                {
                    "title": title,
                    "date": notice_date,
                    "content": content,
                }
            )

            # 适当休眠，避免过快请求被限速
            time.sleep(0.3)

        return result

    except Exception as e:
        print(f"获取公告标题失败: {e}")
        print(traceback.format_exc())
        return []


# 添加财务数据获取函数
def get_balance_sheet(stock_code, period="按年度"):
    """获取资产负债表"""
    if not HAS_AKSHARE:
        print("未安装akshare库，无法获取资产负债表数据")
        return pd.DataFrame()

    try:
        df = ak.stock_financial_debt_ths(symbol=stock_code, indicator=period)
        # 只取前5行数据，通常是最新的
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.head(5)
        return df
    except Exception as e:
        print(f"获取资产负债表失败: {e}")
        return pd.DataFrame()


def get_income_statement(stock_code, period="按年度"):
    """获取利润表"""
    if not HAS_AKSHARE:
        print("未安装akshare库，无法获取利润表数据")
        return pd.DataFrame()

    try:
        df = ak.stock_financial_benefit_ths(symbol=stock_code, indicator=period)
        # 只取前5行数据
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.head(5)
        return df
    except Exception as e:
        print(f"获取利润表失败: {e}")
        return pd.DataFrame()


def get_cash_flow(stock_code, period="按年度"):
    """获取现金流量表"""
    if not HAS_AKSHARE:
        print("未安装akshare库，无法获取现金流量表数据")
        return pd.DataFrame()

    try:
        df = ak.stock_financial_cash_ths(symbol=stock_code, indicator=period)
        # 只取前5行数据
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.head(5)
        return df
    except Exception as e:
        print(f"获取现金流量表失败: {e}")
        return pd.DataFrame()


def get_financial_reports(stock_code, period="按年度"):
    """获取财务报表数据（资产负债表、利润表、现金流量表）"""
    if not HAS_AKSHARE:
        return {"error": "未安装akshare库，无法获取财务报表数据"}

    try:
        # 获取各类财务报表
        print(f"获取 {stock_code} 的财务报表数据...")
        balance_sheet = get_balance_sheet(stock_code, period)
        income_statement = get_income_statement(stock_code, period)
        cash_flow = get_cash_flow(stock_code, period)

        # 如果所有报表都为空，则返回错误
        if (
            (isinstance(balance_sheet, pd.DataFrame) and balance_sheet.empty)
            and (isinstance(income_statement, pd.DataFrame) and income_statement.empty)
            and (isinstance(cash_flow, pd.DataFrame) and cash_flow.empty)
        ):
            return {"error": f"未能获取到 {stock_code} 的任何财务报表数据"}

        # 获取当前时间作为处理时间戳
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建财务报表数据字典
        financial_reports = {
            "元数据": {
                "股票代码": stock_code,
                "数据周期": period,
                "数据获取时间": current_time,
                "报表类型": ["资产负债表", "利润表", "现金流量表"],
                "报表条目数": {
                    "资产负债表": len(balance_sheet)
                    if isinstance(balance_sheet, pd.DataFrame)
                    else 0,
                    "利润表": len(income_statement)
                    if isinstance(income_statement, pd.DataFrame)
                    else 0,
                    "现金流量表": len(cash_flow)
                    if isinstance(cash_flow, pd.DataFrame)
                    else 0,
                },
            },
            "资产负债表": balance_sheet.to_dict(orient="records")
            if isinstance(balance_sheet, pd.DataFrame) and not balance_sheet.empty
            else [],
            "利润表": income_statement.to_dict(orient="records")
            if isinstance(income_statement, pd.DataFrame) and not income_statement.empty
            else [],
            "现金流量表": cash_flow.to_dict(orient="records")
            if isinstance(cash_flow, pd.DataFrame) and not cash_flow.empty
            else [],
        }

        print(f"成功获取 {stock_code} 的财务报表数据")
        return financial_reports

    except Exception as e:
        print(f"获取财务报表数据失败: {str(e)}")
        return {"error": f"获取财务报表数据失败: {str(e)}"}


def get_company_name_for_stock(stock_code, csv_path=None):
    """从CSV文件或缓存中获取股票对应的公司名称"""
    global STOCK_NAME_CACHE

    # 如果缓存中已有，直接返回
    if stock_code in STOCK_NAME_CACHE:
        return STOCK_NAME_CACHE[stock_code]

    # 从CSV文件中加载所有股票
    if csv_path is None:
        # 在工具目录下查找stocks.csv
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "stocks.csv"
        )
        if not os.path.exists(csv_path):
            # 备选路径
            csv_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "utils",
                "stocks.csv",
            )

    if not os.path.exists(csv_path):
        print(f"股票列表文件不存在: {csv_path}，将使用股票代码作为公司名称")
        STOCK_NAME_CACHE[stock_code] = stock_code
        return stock_code

    try:
        # 读取CSV文件
        df = pd.read_csv(csv_path, dtype=str)

        # 检查必要的列
        if "股票代码" not in df.columns or "股票名称" not in df.columns:
            print(f"CSV文件缺少必要的列: 股票代码, 股票名称，将使用股票代码作为公司名称")
            STOCK_NAME_CACHE[stock_code] = stock_code
            return stock_code

        # 查找股票代码对应的公司名称
        matched = df[df["股票代码"] == stock_code]
        if not matched.empty:
            company_name = matched.iloc[0]["股票名称"]
            STOCK_NAME_CACHE[stock_code] = company_name
            return company_name
        else:
            print(f"未找到股票代码 {stock_code} 对应的公司名称，将使用股票代码作为公司名称")
            STOCK_NAME_CACHE[stock_code] = stock_code
            return stock_code

    except Exception as e:
        print(f"读取股票列表文件出错: {e}，将使用股票代码作为公司名称")
        STOCK_NAME_CACHE[stock_code] = stock_code
        return stock_code


def get_all_stock_codes(csv_path=None):
    """从CSV文件获取所有股票代码和名称"""
    if csv_path is None:
        # 默认路径
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "stocks.csv"
        )
        if not os.path.exists(csv_path):
            # 备选路径
            csv_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "utils",
                "stocks.csv",
            )

    if not os.path.exists(csv_path):
        print(f"股票列表文件不存在: {csv_path}")
        return []

    try:
        # 读取CSV文件
        df = pd.read_csv(csv_path, dtype=str)

        # 检查必要的列
        if "股票代码" not in df.columns or "股票名称" not in df.columns:
            print(f"CSV文件缺少必要的列: 股票代码, 股票名称")
            return []

        # 提取股票代码和名称
        stocks = []
        for _, row in df.iterrows():
            stocks.append((row["股票代码"], row["股票名称"]))

        print(f"从CSV文件读取到 {len(stocks)} 只股票")
        return stocks

    except Exception as e:
        print(f"读取股票列表文件失败: {e}")
        return []


def get_risk_control_data(
    stock_code,
    max_count=100,
    period="按年度",
    include_announcements=True,
    include_financial=True,
    max_retry=3,
    sleep_seconds=1,
):
    """
    获取单只股票的风控数据（财务数据和法务公告），集成版，支持最大重试机制。

    Args:
        stock_code (str): 股票代码，如"600519"
        max_count (int, optional): 最多获取的公告数量. Defaults to 100.
        period (str, optional): 财务数据周期，可选值：按年度、按报告期、按单季度. Defaults to "按年度".
        include_announcements (bool, optional): 是否包含公告数据. Defaults to True.
        include_financial (bool, optional): 是否包含财务数据. Defaults to True.
        max_retry (int, optional): 最大重试次数. Defaults to 3.
        sleep_seconds (int, optional): 重试前等待的秒数. Defaults to 1.

    Returns:
        dict: 包含财务数据和公告数据的字典
    """
    last_exception = None
    for attempt in range(1, max_retry + 1):
        try:
            # 获取公告数据（法务）
            legal_data = None
            if include_announcements:
                legal_data = get_announcements_with_detail(stock_code, max_count)
            # 获取财务数据
            financial_data = None
            if include_financial:
                financial_data = get_financial_reports(stock_code, period)
            # 直接返回拼接的json结构
            # 仅保留 financial 元数据，减少返回体大小，且保证 legal 字段先出现，避免被截断
            financial_meta = (
                financial_data.get("元数据", {}) if isinstance(financial_data, dict) else {}
            )
            return {"legal": legal_data, "financial_meta": financial_meta}
        except Exception as e:
            last_exception = str(e)
            print(f"[第{attempt}次] 获取风控数据失败: {e}")
            if attempt < max_retry:
                time.sleep(sleep_seconds)
                print(f"正在尝试第{attempt + 1}次获取...")

    print(f"获取风控数据达到最大重试次数 {max_retry}，获取失败")
    return {"financial": None, "legal": None, "error": f"获取风控数据失败，原因: {last_exception}"}
