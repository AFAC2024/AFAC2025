import asyncio
import json
import sys
import time
from typing import Any, Dict

import efinance as ef

from src.logger import logger
from src.tool.base import BaseTool, ToolResult
from src.tool.financial_deep_search.stock_capital import get_stock_capital_flow


class TechnicalAnalysisTool(BaseTool):
    """Tool for retrieving technical data for stocks."""

    name: str = "technical_analysis_tool"
    description: str = "获取股票技术面数据，包括实时行情、日K线、分钟K线和资金流向。支持最大重试机制，适合大模型自动调用。返回结构化字典。"
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "股票代码（必填），如'600519'（贵州茅台）、'000001'（平安银行）、'300750'（宁德时代）、'601318'（中国平安）等",
            },
            "need_realtime": {
                "type": "boolean",
                "description": "是否获取实时行情数据，包括最新价、涨跌幅、成交量等核心指标",
                "default": True,
            },
            "need_daily_kline": {
                "type": "boolean",
                "description": "是否获取日K线历史数据，包括开盘价、最高价、最低价、收盘价等OHLC数据",
                "default": True,
            },
            "need_minute_kline": {
                "type": "boolean",
                "description": "是否获取分钟级K线数据，用于分析盘中短期价格走势与波动",
                "default": True,
            },
            "need_capital_flow": {
                "type": "boolean",
                "description": "是否获取资金流向数据，展示主力资金、散户资金净流入/流出情况",
                "default": True,
            },
            "kline_count": {
                "type": "integer",
                "description": "K线数据获取条数，范围10-200，控制历史数据回溯深度",
                "default": 30,
            },
            "max_retry": {
                "type": "integer",
                "description": "数据获取最大重试次数，范围1-5，用于处理网络波动情况",
                "default": 3,
            },
        },
        "required": ["stock_code"],
    }

    async def execute(
        self,
        stock_code: str,
        need_realtime: bool = True,
        need_daily_kline: bool = True,
        need_minute_kline: bool = True,
        need_capital_flow: bool = True,
        kline_count: int = 30,
        max_retry: int = 3,
        sleep_seconds: int = 1,
        **kwargs,
    ) -> ToolResult:
        """
        Get technical data for a stock with retry mechanism.

        Args:
            stock_code: Stock code
            need_realtime: Whether to get real-time quotes
            need_daily_kline: Whether to get daily K-line data
            need_minute_kline: Whether to get minute K-line data
            need_capital_flow: Whether to get capital flow data
            kline_count: Number of K-line data points to retrieve
            max_retry: Maximum retry attempts
            sleep_seconds: Seconds to wait between retries
            **kwargs: Additional parameters

        Returns:
            ToolResult: Result containing technical data
        """
        try:
            # Execute synchronous operation in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(
                self._get_tech_data,
                stock_code=stock_code,
                need_realtime=need_realtime,
                need_daily_kline=need_daily_kline,
                need_minute_kline=need_minute_kline,
                need_capital_flow=need_capital_flow,
                kline_count=kline_count,
                max_retry=max_retry,
                sleep_seconds=sleep_seconds,
            )

            # Check if result contains error
            if "error" in result:
                return ToolResult(error=result["error"])

            # Return success result
            return ToolResult(output=result)

        except Exception as e:
            error_msg = f"Failed to get technical data: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)

    def _get_tech_data(
        self,
        stock_code: str,
        need_realtime: bool = True,
        need_daily_kline: bool = True,
        need_minute_kline: bool = True,
        need_capital_flow: bool = True,
        kline_count: int = 30,
        max_retry: int = 3,
        sleep_seconds: int = 1,
    ):
        """
        Get technical data including real-time quotes, K-line data and capital flow.
        Supports maximum retry mechanism.
        """
        for attempt in range(1, max_retry + 1):
            try:
                # Build result dictionary
                result = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "stock_code": stock_code,
                }

                # 1. Get real-time quotes
                if need_realtime:
                    realtime_data = self._get_realtime_quotes(stock_code)
                    result["realtime_quotes"] = realtime_data
                    logger.info(
                        f"[Attempt {attempt}] Retrieved real-time quotes for {stock_code}"
                    )

                # 2. Get daily K-line data
                if need_daily_kline:
                    daily_kline = self._get_daily_kline(stock_code, count=kline_count)
                    result["daily_kline"] = daily_kline
                    logger.info(
                        f"[Attempt {attempt}] Retrieved daily K-line data for {stock_code}"
                    )

                # 3. Get minute K-line data
                if need_minute_kline:
                    minute_kline = self._get_minute_kline(stock_code, count=kline_count)
                    result["minute_kline"] = minute_kline
                    logger.info(
                        f"[Attempt {attempt}] Retrieved minute K-line data for {stock_code}"
                    )

                # 4. Get stock capital flow data
                if need_capital_flow:
                    capital_flow = self._get_capital_flow(stock_code)
                    result["capital_flow"] = capital_flow
                    logger.info(
                        f"[Attempt {attempt}] Retrieved capital flow data for {stock_code}"
                    )

                return result

            except Exception as e:
                logger.warning(
                    f"[Attempt {attempt}] Failed to get technical data for {stock_code}: {e}"
                )
                if attempt < max_retry:
                    logger.info(f"Waiting {sleep_seconds} seconds before retry...")
                    time.sleep(sleep_seconds)
                else:
                    logger.error(f"Max retries ({max_retry}) reached, failed")
                    return {"error": f"Failed to get technical data: {str(e)}"}

    @staticmethod
    def _get_realtime_quotes(stock_code: str) -> Dict[str, Any]:
        """Get real-time quotes data"""
        try:
            # Format stock code according to market
            if stock_code.startswith("6"):
                formatted_code = f"sh{stock_code}"
            elif stock_code.startswith(("0", "3")):
                formatted_code = f"sz{stock_code}"
            else:
                formatted_code = stock_code

            quotes_df = ef.stock.get_realtime_quotes(formatted_code)

            # Process returned DataFrame
            if quotes_df is not None and not quotes_df.empty:
                if hasattr(quotes_df, "to_dict"):
                    if hasattr(quotes_df, "shape") and len(quotes_df.shape) > 1:
                        # DataFrame
                        records = quotes_df.to_dict(orient="records")
                        if records:
                            return records[0]  # Return first record
                    else:
                        # Series
                        return quotes_df.to_dict()
            return {}
        except Exception as e:
            logger.error(f"Failed to get real-time quotes: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_daily_kline(stock_code: str, count: int = 30) -> list:
        """Get daily K-line data"""
        try:
            kline_df = ef.stock.get_quote_history(stock_code, klt=101)

            if kline_df is not None and not kline_df.empty:
                # Keep only the most recent count records
                if len(kline_df) > count:
                    kline_df = kline_df.tail(count)

                # Convert to list of dictionaries
                if hasattr(kline_df, "to_dict"):
                    return kline_df.to_dict(orient="records")
            return []
        except Exception as e:
            logger.error(f"Failed to get daily K-line data: {e}")
            return []

    @staticmethod
    def _get_minute_kline(stock_code: str, count: int = 30) -> list:
        """Get minute K-line data"""
        try:
            kline_df = ef.stock.get_quote_history(stock_code, klt=1)

            if kline_df is not None and not kline_df.empty:
                # Keep only the most recent count records
                if len(kline_df) > count:
                    kline_df = kline_df.tail(count)

                # Convert to list of dictionaries
                if hasattr(kline_df, "to_dict"):
                    return kline_df.to_dict(orient="records")
            return []
        except Exception as e:
            logger.error(f"Failed to get minute K-line data: {e}")
            return []

    @staticmethod
    def _get_capital_flow(stock_code: str) -> Dict[str, Any]:
        """Get stock capital flow data"""
        try:
            return get_stock_capital_flow(stock_code=stock_code)
        except Exception as e:
            logger.error(f"Failed to get capital flow data: {e}")
            return {}


if __name__ == "__main__":
    # Direct tool testing
    code = sys.argv[1] if len(sys.argv) > 1 else "600519"

    # Get technical data
    tool = TechnicalAnalysisTool()
    result = asyncio.run(tool.execute(stock_code=code))

    # Output results
    if result.error:
        print(f"Failed: {result.error}")
    else:
        output = result.output
        print(f"Success! Timestamp: {output['timestamp']}")
        print(f"Stock Code: {output['stock_code']}")

        # Check if each data item was successfully retrieved
        for key in ["realtime_quotes", "daily_kline", "minute_kline", "capital_flow"]:
            if key in output:
                item_count = 0
                if isinstance(output[key], list):
                    item_count = len(output[key])
                    status = f"Retrieved ({item_count} items)"
                else:
                    status = "Retrieved" if output[key] else "Not Retrieved"
                print(f"- {key}: {status}")

        # Save complete results to JSON file
        filename = f"tech_data_{code}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nComplete results saved to: {filename}")
