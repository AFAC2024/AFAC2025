import asyncio
import json
import time
from typing import Any, Dict

from src.logger import logger
from src.tool.base import BaseTool, ToolResult
from src.tool.financial_deep_search.get_section_data import get_all_section
from src.tool.financial_deep_search.index_capital import get_index_capital_flow


class SentimentTool(BaseTool):
    """Tool for retrieving market sentiment data including hot sectors and index capital flow."""

    name: str = "sentiment_tool"
    description: str = "整合市场情绪与行业热点分析工具，提供全面的市场脉搏和资金流向监测。"
    parameters: dict = {
        "type": "object",
        "properties": {
            "index_code": {
                "type": "string",
                "description": "指数代码（必填），如'000001'（上证指数）、'399001'（深证成指）、'399006'（创业板指）、'000016'（上证50）、'000300'（沪深300）、'000905'（中证500）等",
            },
            "sector_types": {
                "type": "string",
                "description": "板块类型筛选，精确可选值：'all'（所有板块）、'hot'（热门活跃板块）、'concept'（概念题材板块）、'regional'（地域区域板块）、'industry'（行业分类板块）",
                "default": "all",
            },
            "max_retry": {
                "type": "integer",
                "description": "数据获取最大重试次数，范围1-5，用于处理网络波动情况",
                "default": 3,
            },
        },
        "required": ["index_code"],
    }

    async def execute(
        self,
        index_code: str,
        sector_types: str = "all",
        max_retry: int = 3,
        sleep_seconds: int = 1,
        **kwargs,
    ) -> ToolResult:
        """
        Get market data with retry mechanism.

        Args:
            index_code: Index code
            sector_types: Sector types, options: 'all', 'hot', 'concept', 'regional', 'industry'
            max_retry: Maximum retry attempts
            sleep_seconds: Seconds to wait between retries
            **kwargs: Additional parameters

        Returns:
            ToolResult: Result containing market data
        """
        try:
            # Execute synchronous operation in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(
                self._get_market_data,
                index_code=index_code,
                sector_types=sector_types,
                max_retry=max_retry,
                sleep_seconds=sleep_seconds,
            )

            # Check if result contains error
            if "error" in result:
                return ToolResult(error=result["error"])

            return ToolResult(output=result)

        except Exception as e:
            error_msg = f"Failed to get market data: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)

    def _get_market_data(
        self,
        index_code: str,
        sector_types: str = "all",
        max_retry: int = 3,
        sleep_seconds: int = 1,
    ) -> Dict[str, Any]:
        """
        Get market data including hot sectors and index capital flow.
        Supports maximum retry mechanism.
        """
        for attempt in range(1, max_retry + 1):
            try:
                # 1. Get hot sector data
                section_data = get_all_section(sector_types=sector_types)
                logger.info(f"[Attempt {attempt}] Retrieved hot sector data")

                # 2. Get index capital flow
                index_flow = get_index_capital_flow(index_code=index_code)
                logger.info(f"[Attempt {attempt}] Retrieved index capital flow data")

                # 3. Combine data and return
                return {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "index_code": index_code,
                    "sector_types": sector_types,
                    "hot_section_data": section_data,
                    "index_net_flow": index_flow,
                }

            except Exception as e:
                logger.warning(f"[Attempt {attempt}] Failed to get market data: {e}")
                if attempt < max_retry:
                    logger.info(f"Waiting {sleep_seconds} seconds before retry...")
                    time.sleep(sleep_seconds)
                else:
                    logger.error(f"Max retries ({max_retry}) reached, failed")
                    return {"error": f"Failed to get market data: {str(e)}"}


if __name__ == "__main__":
    import sys

    code = sys.argv[1] if len(sys.argv) > 1 else "000001"

    tool = SentimentTool()
    result = asyncio.run(tool.execute(index_code=code))

    if result.error:
        print(f"Failed: {result.error}")
    else:
        output = result.output
        print(f"Success! Timestamp: {output['timestamp']}")
        print(f"Index Code: {output['index_code']}")

        for key in ["hot_section_data", "index_net_flow"]:
            status = "Retrieved" if output.get(key) else "Not Retrieved"
            print(f"- {key}: {status}")

        filename = f"market_data_{code}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nComplete results saved to: {filename}")
