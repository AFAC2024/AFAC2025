import asyncio

from src.logger import logger
from src.tool.base import BaseTool, ToolResult
from src.tool.financial_deep_search.risk_control_data import get_risk_control_data


class RiskControlTool(BaseTool):
    """Tool for retrieving risk control data for stocks."""

    name: str = "risk_control_tool"
    description: str = (
        "获取股票的风控数据，包括财务数据（现金流量表，资产负债表，利润表）(financial)和法务公告数据(legal)。"
        "支持最大重试机制，适合大模型自动调用。返回结构化字典。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "股票代码（必填），如'600519'（贵州茅台）、'000001'（平安银行）、'300750'（宁德时代）等",
            },
            "max_count": {
                "type": "integer",
                "description": "公告数据获取数量上限，建议不超过10，用于限制返回的法律公告数量",
                "default": 10,
            },
            "period": {
                "type": "string",
                "description": "财务数据周期类型，精确可选值：'按年度'（年报数据）、'按报告期'（含季报）、'按单季度'（环比数据）",
                "default": "按年度",
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

    async def execute(
        self,
        stock_code: str,
        max_count: int = 10,
        period: str = "按年度",
        max_retry: int = 3,
        sleep_seconds: int = 1,
        **kwargs,
    ) -> ToolResult:
        """
        Get risk control data for a single stock with retry mechanism.

        Args:
            stock_code: Stock code
            max_count: Maximum number of announcements to retrieve
            period: Financial data period (按年度/按报告期/按单季度)
            max_retry: Maximum retry attempts
            sleep_seconds: Seconds to wait between retries
            **kwargs: Additional parameters

        Returns:
            ToolResult: Result containing risk control data
        """
        try:
            # Execute synchronous operation in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(
                get_risk_control_data,
                stock_code=stock_code,
                max_count=max_count,
                period=period,
                include_announcements=True,
                include_financial=True,
                max_retry=max_retry,
                sleep_seconds=sleep_seconds,
            )

            if "error" in result:
                return ToolResult(error=result["error"])

            return ToolResult(output=result)

        except Exception as e:
            error_msg = f"Failed to get risk control data: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)


if __name__ == "__main__":
    # Direct tool testing
    import sys

    code = sys.argv[1] if len(sys.argv) > 1 else "600519"

    # Get risk control data
    tool = RiskControlTool()
    result = asyncio.run(tool.execute(stock_code=code))

    # Output results
    if result.error:
        print(f"Failed: {result.error}")
    else:
        output = result.output
        print(f"Success!")
        print(
            f"- Financial Data: {'Retrieved' if output['financial'] else 'Not Retrieved'}"
        )
        # print(
        #     "- Legal Data: {'Retrieved' + {} items if output['legal'] else 'Not Retrieved'}".format(len(output['legal']))
        # )
