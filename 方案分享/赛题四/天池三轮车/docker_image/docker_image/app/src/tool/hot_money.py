import asyncio
import json
from datetime import datetime
from typing import Optional

import efinance as ef
import pandas as pd
from pydantic import Field

from src.logger import logger
from src.tool.base import BaseTool, ToolResult, get_recent_trading_day
from src.tool.financial_deep_search.get_section_data import get_all_section
from src.tool.financial_deep_search.index_capital import get_index_capital_flow
from src.tool.financial_deep_search.stock_capital import get_stock_capital_flow


_HOT_MONEY_DESCRIPTION = """
获取股票热点资金和市场数据工具，用于分析主力资金流向和市场热点变化。

该工具提供以下精确数据服务：
1. 股票实时数据：提供目标股票的最新价格、涨跌幅、成交量、换手率、市值等关键指标
2. 龙虎榜数据：获取特定日期的市场龙虎榜，展示主力机构资金买卖方向和具体金额
3. 热门板块分析：按类型（概念、行业、地域）提供当日热门板块涨跌情况和资金流向
4. 个股资金流向：展示目标股票近期主力、散户、超大单资金净流入/流出数据
5. 大盘资金流向：提供指数级别的资金面分析，包括北向资金、融资余额等宏观指标

结果以结构化JSON格式返回，包含完整的数据类别、时间戳和数值指标。
"""


class HotMoneyTool(BaseTool):
    """Tool for retrieving hot money and market data for stocks."""

    name: str = "hot_money_tool"
    description: str = _HOT_MONEY_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "股票代码（必填），如'600519'（贵州茅台）、'000001'（平安银行）、'300750'（宁德时代）等",
            },
            "index_code": {
                "type": "string",
                "description": "指数代码，如'000001'（上证指数）、'399001'（深证成指）。不提供则默认使用与股票代码相同的值",
            },
            "date": {
                "type": "string",
                "description": "查询日期，精确格式为YYYY-MM-DD（如'2023-05-15'），不提供则默认使用当天日期",
                "default": "",
            },
            "sector_types": {
                "type": "string",
                "description": "板块类型筛选，可选值：'all'（所有板块）、'hot'（热门板块）、'concept'（概念板块）、'regional'（地域板块）、'industry'（行业板块）",
                "default": "all",
            },
            "max_retry": {
                "type": "integer",
                "description": "数据获取最大重试次数，范围1-5，用于处理网络波动情况",
                "default": 3,
            },
            "sleep_seconds": {
                "type": "integer",
                "description": "重试间隔秒数，范围1-10，防止频繁请求被限制",
                "default": 1,
            },
        },
        "required": ["stock_code"],
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)

    async def execute(
        self,
        stock_code: str,
        index_code: Optional[str] = None,
        date: str = "",
        sector_types: str = "all",
        max_retry: int = 3,
        sleep_seconds: int = 1,
        **kwargs,
    ) -> ToolResult:
        """
        Execute the hot money data retrieval operation.

        Args:
            stock_code: Stock code, e.g. "600519"
            index_code: Index code, e.g. "000001", defaults to stock_code if not provided
            date: Query date in YYYY-MM-DD format, defaults to current date
            sector_types: Sector types, options: 'all', 'hot', 'concept', 'regional', 'industry'
            max_retry: Maximum retry attempts, default 3
            sleep_seconds: Seconds to wait between retries, default 1
            **kwargs: Additional parameters

        Returns:
            ToolResult: Unified JSON format containing all data sources results or error message
        """
        async with self.lock:
            try:
                date = date or get_recent_trading_day()
                actual_index_code = index_code or stock_code

                result = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stock_code": stock_code,
                    "date": date,
                }
                if index_code:
                    result["index_code"] = index_code

                # Get all data with retry mechanism
                data_sources = {
                    "stock_latest_info": lambda: ef.stock.get_realtime_quotes(
                        stock_code
                    ),
                    "daily_top_list": lambda: ef.stock.get_daily_billboard(
                        start_date=date, end_date=date
                    ),
                    "hot_section_data": lambda: get_all_section(
                        sector_types=sector_types
                    ),
                    "stock_net_flow": lambda: get_stock_capital_flow(
                        stock_code=stock_code
                    ),
                    "index_net_flow": lambda: get_index_capital_flow(
                        index_code=actual_index_code
                    ),
                }

                # Retrieve each data source
                for key, func in data_sources.items():
                    result[key] = await self._get_data_with_retry(
                        func, key, max_retry, sleep_seconds
                    )

                return ToolResult(output=result)

            except Exception as e:
                error_msg = f"Failed to get hot money data: {str(e)}"
                logger.error(error_msg)
                return ToolResult(error=error_msg)

    @staticmethod
    async def _get_data_with_retry(func, data_name, max_retry=3, sleep_seconds=1):
        """
        Get data with retry mechanism.

        Args:
            func: Function to call
            data_name: Data name (for logging)
            max_retry: Maximum retry attempts
            sleep_seconds: Seconds to wait between retries

        Returns:
            Function return data or None
        """
        last_error = None
        for attempt in range(1, max_retry + 1):
            try:
                # Use asyncio.to_thread for synchronous operations
                data = await asyncio.to_thread(func)

                # Convert data based on type
                if isinstance(data, pd.DataFrame):
                    return data.to_dict(orient="records")
                elif isinstance(data, pd.Series):
                    return data.to_dict()
                elif hasattr(data, "to_json"):
                    return json.loads(data.to_json())

                logger.info(f"[{data_name}] Data retrieved successfully")
                return data

            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{data_name}][Attempt {attempt}] Failed: {e}")

                if attempt < max_retry:
                    await asyncio.sleep(sleep_seconds)
                    logger.info(f"[{data_name}] Preparing attempt {attempt+1}...")

        logger.error(
            f"[{data_name}] Max retries ({max_retry}) reached, failed: {last_error}"
        )
        return None


if __name__ == "__main__":
    import sys

    code = sys.argv[1] if len(sys.argv) > 1 else "600519"
    index_code = "000001"  # Default to Shanghai Composite Index

    async def run_tool():
        tool = HotMoneyTool()
        result = await tool.execute(stock_code=code, index_code=index_code)

        if result.error:
            print(f"Failed: {result.error}")
        else:
            data = result.output
            print(f"Success! Timestamp: {data['timestamp']}")
            print(f"Stock Code: {data['stock_code']}")
            if "index_code" in data:
                print(f"Index Code: {data['index_code']}")

            for key in [
                "stock_latest_info",
                "daily_top_list",
                "hot_section_data",
                "stock_net_flow",
                "index_net_flow",
            ]:
                status = "Success" if data.get(key) is not None else "Failed"
                print(f"- {key}: {status}")

            filename = (
                f"hotmoney_data_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\nComplete results saved to: {filename}")

    asyncio.run(run_tool())
