"""
搜索引擎封装模块
支持 DuckDuckGo 和 Sogou 两种搜索方式
"""

import time
from typing import List, Dict, Any
from duckduckgo_search import DDGS

# 尝试导入搜狗搜索，如果失败则只支持DDG
try:
    from sogou_search import sogou_search
    SOGOU_AVAILABLE = True
except ImportError:
    SOGOU_AVAILABLE = False

class SearchEngine:
    """搜索引擎封装类"""

    def __init__(self, engine: str = "ddg"):
        """
        初始化搜索引擎

        Args:
            engine: 搜索引擎类型，支持 "ddg" (DuckDuckGo) 和 "sogou" (搜狗)
        """
        self.engine = engine.lower()
        self.delay = 1.0  # 默认搜索延迟

        if self.engine not in ["ddg", "sogou"]:
            raise ValueError(f"不支持的搜索引擎: {engine}. 支持的类型: 'ddg', 'sogou'")

        if self.engine == "sogou" and not SOGOU_AVAILABLE:
            print("警告: 搜狗搜索 (k_sogou_search) 未安装, 将回退到 DuckDuckGo。")
            self.engine = "ddg"

    def search(self, keywords: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        统一搜索接口

        Args:
            keywords: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果列表，每个结果包含 title, url, description 字段
        """
        print(f"使用 {self.engine.upper()} 搜索引擎搜索: '{keywords}'")
        try:
            if self.engine == "ddg":
                results = self._search_ddg(keywords, max_results)
            elif self.engine == "sogou":
                results = self._search_sogou(keywords, max_results)
            else:
                results = []
            
            time.sleep(self.delay)
            return results
        except Exception as e:
            print(f"搜索失败 ({self.engine}): {e}")
            # 如果搜狗失败，可以考虑回退
            if self.engine == "sogou":
                print("搜狗搜索失败，尝试回退到 DuckDuckGo...")
                self.engine = "ddg"
                return self.search(keywords, max_results)
            return []

    def _search_ddg(self, keywords: str, max_results: int) -> List[Dict[str, Any]]:
        """DuckDuckGo 搜索"""
        results = DDGS().text(
            keywords=keywords,
            region="cn-zh",
            max_results=max_results
        )
        # 标准化结果格式
        return [
            {
                'title': r.get('title', '无标题'),
                'url': r.get('href', '无链接'),
                'description': r.get('body', '无摘要')
            }
            for r in results
        ]

    def _search_sogou(self, keywords: str, max_results: int) -> List[Dict[str, Any]]:
        """搜狗搜索"""
        if not SOGOU_AVAILABLE:
            return []
        return sogou_search(keywords, num_results=max_results)


if __name__ == "__main__":
    # 测试代码
    print("测试搜索引擎封装...")

    # 测试 DuckDuckGo
    print("\n=== 测试 DuckDuckGo ===")
    ddg_engine = SearchEngine(engine="ddg")
    ddg_results = ddg_engine.search("贵州茅台近五年资产负债率", max_results=2)
    for i, result in enumerate(ddg_results, 1):
        print(f"{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   描述: {result['description'][:100]}...")

    # 测试搜狗（如果可用）
    if SOGOU_AVAILABLE:
        print("\n=== 测试搜狗搜索 ===")
        sogou_engine = SearchEngine(engine="sogou")
        sogou_results = sogou_engine.search("智能风控&大数据征信服务的行业龙头股有哪些")
        for i, result in enumerate(sogou_results, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   描述: {result['description'][:100]}...")
    else:
        print("\n=== 搜狗搜索不可用 (k_sogou_search 未安装) ===")
