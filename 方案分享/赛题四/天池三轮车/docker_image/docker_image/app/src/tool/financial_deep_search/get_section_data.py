import json
import time
import traceback
from datetime import datetime

import requests


### 每日热门板块爬取

API_URLS = {
    "hot": "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb=jQuery37109604366978044481_1744621126576&fs=m%3A90&fields=f12%2Cf13%2Cf14%2Cf3%2Cf152%2Cf4%2Cf128%2Cf140%2Cf141%2Cf136&fid=f3&pn=1&pz=10&po=1&ut=fa5fd1943c7b386f172d6893dbfba10b&dect=1&wbp2u=%7C0%7C0%7C0%7Cweb&_=1744621126577",
    "concept": "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb=jQuery37109604366978044481_1744621126580&fs=m%3A90%2Bt%3A3&fields=f12%2Cf13%2Cf14%2Cf3%2Cf152%2Cf4%2Cf8%2Cf104%2Cf105%2Cf128%2Cf140%2Cf141%2Cf136&fid=f3&pn=1&pz=10&po=1&ut=fa5fd1943c7b386f172d6893dbfba10b&dect=1&wbp2u=%7C0%7C0%7C0%7Cweb&_=1744621126708",
    "regional": "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb=jQuery37109604366978044481_1744621126574&fs=m%3A90%2Bt%3A1&fields=f12%2Cf13%2Cf14%2Cf3%2Cf152%2Cf4%2Cf8%2Cf104%2Cf105%2Cf128%2Cf140%2Cf141%2Cf136&fid=f3&pn=1&pz=10&po=1&ut=fa5fd1943c7b386f172d6893dbfba10b&dect=1&wbp2u=%7C0%7C0%7C0%7Cweb&_=1744621126762",
    "industry": "https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb=jQuery37109604366978044481_1744621126574&fs=m%3A90%2Bt%3A2&fields=f12%2Cf13%2Cf14%2Cf3%2Cf152%2Cf4%2Cf8%2Cf104%2Cf105%2Cf128%2Cf140%2Cf141%2Cf136&fid=f3&pn=1&pz=10&po=1&ut=fa5fd1943c7b386f172d6893dbfba10b&dect=1&wbp2u=%7C0%7C0%7C0%7Cweb&_=1744621126617",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}


def parse_jsonp(jsonp_str):
    import re

    match = re.search(r"\((.*)\)", jsonp_str)
    if match:
        return json.loads(match.group(1))
    return None


def fetch_data(sector_type, url, max_retries=3, retry_delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = parse_jsonp(resp.text)
            if not data:
                print(f"解析{sector_type}数据失败")
                return []
            return data.get("data", {}).get("diff", [])
        except Exception as e:
            print(f"获取{sector_type}数据失败: {e} (第{attempt}次尝试)")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return []


def simplify_sector_item(item):
    def to_float(val):
        try:
            if val is None:
                return None
            # 东方财富返回的涨跌幅通常是放大100倍的整数
            return round(float(val) / 100, 2)
        except Exception:
            return None

    return {
        "板块名称": item.get("f14"),
        "板块涨跌幅": to_float(item.get("f3")),
        "领涨股名称": item.get("f140"),
        "领涨股代码": item.get("f128"),
        "领涨股涨跌幅": to_float(item.get("f136")),
    }


def get_all_section(sector_types=None):
    """
    获取所有类型板块数据，包括热门板块、概念板块、行业板块和地域板块

    Args:
        sector_types (str, optional): 板块类型，可选值: 'all', 'hot', 'concept', 'regional', 'industry'，默认为None（等同于'all'）

    Returns:
        dict: 包含各类板块数据的字典
    """
    try:
        # 处理板块类型参数
        if sector_types is None or sector_types == "all":
            types_to_fetch = list(API_URLS.keys())
        elif isinstance(sector_types, str):
            if "," in sector_types:
                types_to_fetch = [t.strip() for t in sector_types.split(",")]
            else:
                types_to_fetch = [sector_types]
        elif isinstance(sector_types, list):
            types_to_fetch = sector_types
        else:
            return {
                "success": False,
                "message": f"不支持的板块类型格式: {type(sector_types)}",
                "data": {},
            }

        # 验证板块类型是否有效
        valid_types = []
        for sector_type in types_to_fetch:
            if sector_type in API_URLS:
                valid_types.append(sector_type)
            else:
                print(f"警告: 无效的板块类型 '{sector_type}'")

        if not valid_types:
            return {"success": False, "message": "没有提供有效的板块类型", "data": {}}

        # 获取数据
        all_data = {}
        for sector_type in valid_types:
            url = API_URLS[sector_type]
            raw_list = fetch_data(sector_type, url)
            all_data[sector_type] = [
                simplify_sector_item(item) for item in raw_list if item
            ]

        # 准备返回结果
        result = {
            "success": True,
            "message": f"成功获取板块数据: {', '.join(valid_types)}",
            "last_updated": datetime.now().isoformat(),
            "data": all_data,
        }

        return result
    except Exception as e:
        error_msg = f"获取板块数据时出错: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "error": traceback.format_exc(),
            "data": {},
        }


def main():
    """命令行调用入口函数"""
    import sys

    # 如果提供了参数，尝试按照参数获取特定板块
    if len(sys.argv) > 1:
        sector_types = sys.argv[1]
        result = get_all_section(sector_types=sector_types)
    else:
        # 否则获取所有板块
        result = get_all_section()

    # 打印结果
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
