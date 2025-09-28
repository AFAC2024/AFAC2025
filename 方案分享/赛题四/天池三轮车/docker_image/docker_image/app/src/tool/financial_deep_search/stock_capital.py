#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
获取东方财富个股资金流向数据
API: https://push2.eastmoney.com/api/qt/clist/get
"""

import json
import re
import time
import traceback
from datetime import datetime

import requests


# API URL - 个股资金流向
STOCK_CAPITAL_FLOW_URL = "https://push2.eastmoney.com/api/qt/clist/get?fid=f62&po=1&pz=50&pn=1&np=1&fltt=2&invt=2&ut=8dec03ba335b81bf4ebdf7b29ec27d15&fs=m%3A0%2Bt%3A6%2Bf%3A!2%2Cm%3A0%2Bt%3A13%2Bf%3A!2%2Cm%3A0%2Bt%3A80%2Bf%3A!2%2Cm%3A1%2Bt%3A2%2Bf%3A!2%2Cm%3A1%2Bt%3A23%2Bf%3A!2%2Cm%3A0%2Bt%3A7%2Bf%3A!2%2Cm%3A1%2Bt%3A3%2Bf%3A!2&fields=f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184%2Cf66%2Cf69%2Cf72%2Cf75%2Cf78%2Cf81%2Cf84%2Cf87%2Cf204%2Cf205%2Cf124%2Cf1%2Cf13"

# 请求头设置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def parse_jsonp(jsonp_str):
    """解析JSONP响应为JSON数据"""
    try:
        # 使用正则表达式提取JSON数据
        match = re.search(r"jQuery[0-9_]+\((.*)\)", jsonp_str)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            # 如果不是JSONP格式，尝试直接解析JSON
            return json.loads(jsonp_str)
    except Exception as e:
        print(f"解析JSONP失败: {e}")
        print(f"原始数据: {jsonp_str[:100]}...")  # 打印前100个字符用于调试
        return None


def fetch_stock_list_capital_flow(
    page_size=50, page_num=1, max_retries=3, retry_delay=2
):
    """
    获取股票列表的资金流向数据（按主力净流入排序）

    参数:
        page_size: 每页显示数量，默认50
        page_num: 页码，默认第1页
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间(秒)

    返回:
        dict: 包含股票列表资金流向数据的字典
    """
    # 构建API URL，包含分页参数
    url = STOCK_CAPITAL_FLOW_URL.replace("pz=50", f"pz={page_size}").replace(
        "pn=1", f"pn={page_num}"
    )

    # 添加时间戳防止缓存
    timestamp = int(time.time() * 1000)
    if "?" in url:
        url += f"&_={timestamp}"
    else:
        url += f"?_={timestamp}"

    # 请求数据
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            # 解析响应数据
            data = parse_jsonp(resp.text)
            if not data:
                print(f"解析个股资金流向数据失败 (第{attempt}次尝试)")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

            # 提取资金流向数据
            stock_list = data.get("data", {}).get("diff", [])
            if not stock_list:
                print(f"未获取到个股资金流向数据 (第{attempt}次尝试)")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

            # 处理股票数据
            return process_stock_list_data(
                stock_list, data.get("data", {}).get("total", 0)
            )

        except Exception as e:
            print(f"获取个股资金流向数据失败: {e} (第{attempt}次尝试)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None


def fetch_single_stock_capital_flow(stock_code, max_retries=3, retry_delay=2):
    """
    获取单个股票的资金流向数据

    参数:
        stock_code: 股票代码，如"000001"
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间(秒)

    返回:
        dict: 包含单个股票资金流向数据的字典，如果未找到则返回None
    """
    # 获取股票列表数据（多页搜索需要实现分页循环）
    for page in range(1, 10):  # 最多查找10页
        stock_list = fetch_stock_list_capital_flow(50, page)
        if not stock_list:
            break

        # 在列表中查找指定股票
        for stock in stock_list.get("股票列表", []):
            if stock.get("股票代码") == stock_code:
                return {
                    "success": True,
                    "message": f"成功获取股票{stock.get('股票名称')}({stock_code})资金流向数据",
                    "last_updated": datetime.now().isoformat(),
                    "data": stock,
                }

    # 如果未找到目标股票，使用精确查询
    # 这里可以实现具体股票的接口查询，暂不实现

    return {"success": False, "message": f"未找到股票{stock_code}的资金流向数据", "data": {}}


def process_stock_list_data(stock_list, total_count):
    """
    处理股票列表资金流向数据

    参数:
        stock_list: API返回的原始股票列表数据
        total_count: 总记录数

    返回:
        dict: 处理后的资金流向数据
    """
    # 字段映射表
    field_mapping = {
        "f12": "股票代码",
        "f14": "股票名称",
        "f2": "最新价",
        "f3": "涨跌幅",
        "f62": "主力净流入",
        "f184": "主力净占比",
        "f66": "超大单净流入",
        "f69": "超大单净占比",
        "f72": "大单净流入",
        "f75": "大单净占比",
        "f78": "中单净流入",
        "f81": "中单净占比",
        "f84": "小单净流入",
        "f87": "小单净占比",
        "f124": "更新时间",
        "f1": "市场代码",
        "f13": "市场类型",
    }

    # 交易市场映射
    market_map = {
        0: "SZ",  # 深圳
        1: "SH",  # 上海
        105: "NQ",  # 纳斯达克
        106: "NYSE",  # 纽交所
        107: "AMEX",  # 美交所
        116: "HK",  # 港股
        156: "LN",  # 伦敦
    }

    # 初始化结果
    result = {
        "股票列表": [],
        "总数": total_count,
        "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 处理每支股票数据
    for stock_item in stock_list:
        stock_data = {}

        # 转换每个字段
        for api_field, result_field in field_mapping.items():
            if api_field in stock_item:
                value = stock_item.get(api_field)

                # 特殊处理的字段
                if api_field == "f124":  # 更新时间
                    try:
                        timestamp = int(value) / 1000
                        stock_data[result_field] = datetime.fromtimestamp(
                            timestamp
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        stock_data[result_field] = "-"
                elif api_field in ["f62", "f66", "f72", "f78", "f84"]:  # 资金流入流出金额
                    stock_data[result_field] = (
                        round(float(value) / 10000, 2) if value else 0
                    )  # 转换为万元
                elif api_field in ["f3", "f184", "f69", "f75", "f81", "f87"]:  # 百分比
                    stock_data[result_field] = (
                        round(float(value), 2) if value else 0
                    )  # 保留两位小数
                elif api_field == "f13":  # 市场类型
                    market_code = value
                    stock_data[result_field] = market_map.get(
                        market_code, str(market_code)
                    )
                else:
                    stock_data[result_field] = value

        # 添加完整的股票代码
        if "股票代码" in stock_data and "市场类型" in stock_data:
            market_prefix = stock_data["市场类型"]
            stock_data["完整代码"] = f"{market_prefix}.{stock_data['股票代码']}"

        # 添加到结果列表
        result["股票列表"].append(stock_data)

    return result


def get_stock_capital_flow(page_size=50, page_num=1, stock_code=None):
    """
    获取股票资金流向数据，支持获取列表或单只股票数据

    参数:
        page_size: 每页显示数量，默认50
        page_num: 页码，默认第1页
        stock_code: 股票代码，如果指定，则返回单只股票数据，否则返回列表

    返回:
        dict: 包含资金流向数据的字典
    """
    try:
        # 获取数据（单只股票或列表）
        if stock_code:
            result = fetch_single_stock_capital_flow(stock_code)
        else:
            flow_data = fetch_stock_list_capital_flow(page_size, page_num)
            if not flow_data:
                return {"success": False, "message": f"获取股票资金流向数据失败", "data": {}}

            # 准备返回结果
            result = {
                "success": True,
                "message": f"成功获取股票资金流向数据，共{flow_data.get('总数', 0)}条",
                "last_updated": datetime.now().isoformat(),
                "data": flow_data,
            }

        return result
    except Exception as e:
        error_msg = f"获取股票资金流向数据时出错: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "success": False,
            "message": error_msg,
            "error": traceback.format_exc(),
            "data": {},
        }


def main():
    """命令行调用入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description="获取股票资金流向数据")
    parser.add_argument("--code", type=str, help="股票代码，不指定则获取列表")
    parser.add_argument("--page", type=int, default=1, help="页码，默认1")
    parser.add_argument("--size", type=int, default=50, help="每页数量，默认50")
    args = parser.parse_args()

    if args.code:
        result = get_stock_capital_flow(stock_code=args.code)
    else:
        result = get_stock_capital_flow(page_size=args.size, page_num=args.page)

    # 打印结果
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
