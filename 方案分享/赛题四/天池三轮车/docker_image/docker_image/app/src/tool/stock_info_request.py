import asyncio
import datetime
from typing import Any, Dict

import efinance as ef
import pandas as pd
from pydantic import Field

from src.tool.base import BaseTool, ToolResult, get_recent_trading_day


class StockInfoResponse(ToolResult):
    """Response model for stock information, extending ToolResult."""

    output: Dict[str, Any] = Field(default_factory=dict)

    @property
    def current_trading_day(self) -> str:
        """Get the current trading day from the output."""
        return self.output.get("current_trading_day", "")

    @property
    def basic_info(self) -> Dict[str, Any]:
        """Get the basic stock information from the output."""
        return self.output.get("basic_info", {})


class StockInfoRequest(BaseTool):
    """Tool to fetch basic information about a stock with the current trading date."""

    name: str = "stock_info_request"
    description: str = "获取股票基础信息和当前交易日，返回JSON格式的结果。"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {"stock_code": {"type": "string", "description": "股票代码"}},
        "required": ["stock_code"],
    }

    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1  # seconds

    async def execute(self, stock_code: str, **kwargs) -> StockInfoResponse | None:
        """
        Execute the tool to fetch stock information.

        Args:
            stock_code: The stock code to query

        Returns:
            StockInfoResponse containing stock information and current trading date
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Get current trading day
                trading_day = get_recent_trading_day()

                # Fetch stock information
                data = ef.stock.get_base_info(stock_code)

                # Convert data to dict format based on its type
                basic_info = self._format_data(data)

                # Create and return the response
                return StockInfoResponse(
                    output={
                        "current_trading_day": trading_day,
                        "basic_info": basic_info,
                    }
                )

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(float(self.RETRY_DELAY))
                return StockInfoResponse(
                    error=f"获取股票信息失败 ({self.MAX_RETRIES}次尝试): {str(e)}"
                )

    @staticmethod
    def _format_data(data: Any) -> Dict[str, Any]:
        """
        Format data to a JSON-serializable dictionary.

        Args:
            data: The data to format, typically from efinance

        Returns:
            A dictionary representation of the data
        """
        if isinstance(data, pd.DataFrame):
            return data.to_dict(orient="records")[0] if len(data) > 0 else {}
        elif isinstance(data, pd.Series):
            return data.to_dict()
        elif isinstance(data, dict):
            return data
        elif isinstance(data, (int, float, str, bool)):
            return {"value": data}
        else:
            return {"value": str(data)}


if __name__ == "__main__":
    import json
    import sys

    # Use default stock code "600519" (Maotai) if not provided
    code = sys.argv[1] if len(sys.argv) > 1 else "600519"

    # Create and run the tool
    tool = StockInfoRequest()
    result = asyncio.run(tool.execute(code))

    # Print the result
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(json.dumps(result.output, ensure_ascii=False, indent=2))
