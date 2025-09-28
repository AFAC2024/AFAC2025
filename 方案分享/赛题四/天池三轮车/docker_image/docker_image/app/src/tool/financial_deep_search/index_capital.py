#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
获取东方财富上证指数资金流向数据
API: https://push2.eastmoney.com/api/qt/stock/get
"""

import json
import os
import re
import time
import traceback
from datetime import datetime

import requests


# API URL - 上证指数(000001)资金流向
INDEX_CAPITAL_FLOW_URL = "https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=1&fields=f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149&secid=1.000001&ut=fa5fd1943c7b386f172d6893dbfba10b&wbp2u=|0|0|0|web&dect=1"

# 请求头设置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


# 加载指数代码和名称映射
def load_index_map():
    try:
        map_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "index_name_map.json"
        )
        if os.path.exists(map_file):
            with open(map_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # 如果映射文件不存在，返回默认映射
            return {
                "000001": "上证指数",
                "399001": "深证成指",
                "399006": "创业板指",
                "000300": "沪深300",
                "000905": "中证500",
                "000016": "上证50",
                "000852": "中证1000",
                "000688": "科创50",
                "399673": "创业板50",
            }
    except Exception as e:
        print(f"加载指数映射文件失败: {e}")
        # 返回默认映射
        return {
            "000001": "上证指数",
            "399001": "深证成指",
            "399006": "创业板指",
            "000300": "沪深300",
            "000905": "中证500",
        }


# 加载指数名称映射
INDEX_CODE_NAME_MAP = load_index_map()


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


def fetch_index_capital_flow(index_code="000001", max_retries=3, retry_delay=2):
    """
    获取指数资金流向数据

    参数:
        index_code: 指数代码，默认为上证指数(000001)
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间(秒)

    返回:
        dict: 包含资金流向数据的字典
    """
    # 根据指数代码构建API URL
    market = "1"  # 1:上海 0:深圳
    if index_code.startswith("39") or index_code.startswith("1"):
        market = "0"  # 深证指数

    url = INDEX_CAPITAL_FLOW_URL.replace(
        "secid=1.000001", f"secid={market}.{index_code}"
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
                print(f"解析指数资金流向数据失败 (第{attempt}次尝试)")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

            # 提取资金流向数据
            flow_data = data.get("data", {})
            if not flow_data:
                print(f"未获取到指数资金流向数据 (第{attempt}次尝试)")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                return None

            # 返回数据
            return process_flow_data(flow_data, index_code)

        except Exception as e:
            print(f"获取指数资金流向数据失败: {e} (第{attempt}次尝试)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return None


def process_flow_data(data, index_code):
    """
    处理资金流向数据

    参数:
        data: API返回的原始数据
        index_code: 指数代码

    返回:
        dict: 处理后的资金流向数据
    """
    # 根据API返回的字段定义
    field_mapping = {
        "f135": "今日主力净流入",
        "f136": "今日主力流入",
        "f137": "今日主力流出",
        "f138": "今日超大单净流入",
        "f139": "今日超大单流入",
        "f140": "今日超大单流出",
        "f141": "今日大单净流入",
        "f142": "今日大单流入",
        "f143": "今日大单流出",
        "f144": "今日中单净流入",
        "f145": "今日中单流入",
        "f146": "今日中单流出",
        "f147": "今日小单净流入",
        "f148": "今日小单流入",
        "f149": "今日小单流出",
    }

    # 获取指数名称
    index_name = INDEX_CODE_NAME_MAP.get(index_code, f"指数{index_code}")

    # 提取数据并转换为更友好的格式
    result = {
        "指数代码": index_code,
        "指数名称": index_name,
        "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 添加资金流向数据
    for field, label in field_mapping.items():
        # 将原始金额除以1亿，并保留2位小数
        if field in data:
            value = data.get(field, 0)
            if value:
                result[label] = round(float(value) / 100000000, 2)  # 转换为亿元
            else:
                result[label] = 0

    return result


def get_index_capital_flow(index_code="000001"):
    """
    获取指数资金流向数据

    Args:
        index_code (str, optional): 指数代码，默认为上证指数 000001

    Returns:
        dict: 资金流向数据
    """
    try:
        # 获取数据
        flow_data = fetch_index_capital_flow(index_code)

        if not flow_data:
            return {
                "success": False,
                "message": f"获取指数{index_code}资金流向数据失败",
                "data": {},
            }

        # 获取指数名称
        index_name = flow_data.get(
            "指数名称", INDEX_CODE_NAME_MAP.get(index_code, f"指数{index_code}")
        )

        # 准备返回结果
        result = {
            "success": True,
            "message": f"成功获取{index_name}({index_code})资金流向数据",
            "last_updated": datetime.now().isoformat(),
            "data": flow_data,
        }

        return result
    except Exception as e:
        error_msg = f"获取指数资金流向数据时出错: {str(e)}"
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
    import sys

    # 如果提供了参数，尝试按照参数获取特定指数的资金流向
    if len(sys.argv) > 1:
        index_code = sys.argv[1]
        result = get_index_capital_flow(index_code=index_code)
    else:
        # 否则获取上证指数资金流向
        result = get_index_capital_flow()

    # 打印结果
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
