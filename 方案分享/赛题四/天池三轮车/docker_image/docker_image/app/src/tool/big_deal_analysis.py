from typing import Any, Dict
import time
import pandas as pd  # type: ignore

from src.logger import logger
from src.tool.base import BaseTool, ToolResult

try:
    import akshare as ak  # type: ignore
except ImportError:
    ak = None  # type: ignore


class BigDealAnalysisTool(BaseTool):
    """Tool for analysing big order fund flows using akshare interfaces."""

    name: str = "big_deal_analysis_tool"
    description: str = (
        "获取市场及个股资金大单流向数据，并返回综合分析结果。"
        "调用 akshare 的 stock_fund_flow_big_deal、stock_fund_flow_individual、"
        "stock_individual_fund_flow、stock_zh_a_hist 接口。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "股票代码，如 '600036'，若为空代表全市场分析",
                "default": "",
            },
            "top_n": {
                "type": "integer",
                "description": "排行前 N 名股票的数据",
                "default": 10,
            },
            "rank_symbol": {
                "type": "string",
                "description": "排行时间窗口，{\"即时\", \"3日排行\", \"5日排行\", \"10日排行\", \"20日排行\"}",
                "default": "即时",
            },
            "max_retry": {
                "type": "integer",
                "description": "最大重试次数",
                "default": 3,
            },
            "sleep_seconds": {
                "type": "integer",
                "description": "重试间隔秒数",
                "default": 1,
            },
        },
    }

    async def execute(
        self,
        stock_code: str = "",
        top_n: int = 10,
        rank_symbol: str = "即时",
        max_retry: int = 3,
        sleep_seconds: int = 1,
        **kwargs,
    ) -> ToolResult:
        """Fetch big deal fund flow data and return structured result."""
        if ak is None:
            return ToolResult(error="akshare library not installed")

        try:
            result: Dict[str, Any] = {}

            def _with_retry(func, *args, **kwargs):
                """Simple retry wrapper for unstable akshare endpoints."""
                for attempt in range(1, max_retry + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt >= max_retry:
                            raise
                        logger.warning(f"{func.__name__} attempt {attempt} failed: {e}. Retrying...")
                        time.sleep(sleep_seconds)

            def _safe_fetch(func, *args, **kwargs):
                """Fetch data with retries; return None on ultimate failure instead of raising."""
                try:
                    return _with_retry(func, *args, **kwargs)
                except Exception as e:
                    logger.warning(f"{func.__name__} failed after {max_retry} attempts: {e}")
                    return None

            # Market wide big deal flow (逐笔大单)
            df_bd = _safe_fetch(ak.stock_fund_flow_big_deal)
            if df_bd is not None and not df_bd.empty:
                # 清洗数字列
                def _to_float(series):
                    return (
                        series.astype(str)
                        .str.replace(",", "", regex=False)
                        .str.replace("亿", "e8")  # unlikely present here
                        .str.replace("万", "e4")
                        .str.extract(r"([\d\.-eE]+)")[0]
                        .astype(float)
                    )

                if df_bd["成交额"].dtype == "O":
                    df_bd["成交额"] = _to_float(df_bd["成交额"])

                # 计算买盘/卖盘汇总
                inflow = df_bd[df_bd["大单性质"] == "买盘"]["成交额"].sum()
                outflow = df_bd[df_bd["大单性质"] == "卖盘"]["成交额"].sum()
                result["market_summary"] = {
                    "total_inflow_wan": round(inflow, 2),
                    "total_outflow_wan": round(outflow, 2),
                    "net_inflow_wan": round(inflow - outflow, 2),
                }

                # 按净额排序股票
                grouped = (
                    df_bd.groupby(["股票代码", "股票简称", "大单性质"])["成交额"].sum().reset_index()
                )
                buy_df = grouped[grouped["大单性质"] == "买盘"].sort_values("成交额", ascending=False)
                sell_df = grouped[grouped["大单性质"] == "卖盘"].sort_values("成交额", ascending=False)

                result["top_inflow"] = buy_df.head(top_n).to_dict(orient="records")
                result["top_outflow"] = sell_df.head(top_n).to_dict(orient="records")

                # 保存部分原始逐笔记录以备调试（最多 top_n 条）
                result["market_big_deal_samples"] = df_bd.head(top_n).to_dict(orient="records")
            else:
                result["market_big_deal_samples"] = []

            # Individual fund flow rank 使用 stock_fund_flow_individual(symbol)
            individual_rank = _safe_fetch(ak.stock_fund_flow_individual, symbol=rank_symbol)

            # 默认返回排行榜前 top_n 条
            result["individual_rank_top"] = (
                individual_rank.head(top_n).to_dict(orient="records")
                if individual_rank is not None else []
            )

            # 若指定了 stock_code, 仅保留其对应行数据
            if stock_code and individual_rank is not None:
                rank_filtered = individual_rank[
                    individual_rank["股票代码"].astype(str) == stock_code
                ]
                result["individual_rank_stock"] = (
                    rank_filtered.to_dict(orient="records") if not rank_filtered.empty else []
                )

            if stock_code:
                # Stock specific fund flow trend 使用 stock_individual_fund_flow
                individual_flow = _safe_fetch(ak.stock_individual_fund_flow, stock=stock_code)
                result["stock_fund_flow"] = (
                    individual_flow.to_dict(orient="records") if individual_flow is not None else []
                )

                # Historical price data for correlation
                hist_price = _safe_fetch(ak.stock_zh_a_hist, symbol=stock_code, period="daily")
                if hist_price is not None:
                    result["stock_price_hist"] = hist_price.tail(120).to_dict(orient="records")
                else:
                    result["stock_price_hist"] = []

                # 1. 先整体抓取逐笔大单
                # 复用已获取的 df_bd，若为空再尝试一次
                if df_bd is None:
                    df_bd = _safe_fetch(ak.stock_fund_flow_big_deal)

                stk_df = pd.DataFrame()
                if df_bd is not None and not df_bd.empty:
                    stk_df = df_bd[df_bd["股票代码"] == stock_code]

                if not stk_df.empty:
                    inflow = stk_df[stk_df["大单性质"] == "买盘"]["成交额"].sum()
                    outflow = stk_df[stk_df["大单性质"] == "卖盘"]["成交额"].sum()

                    result["stock_big_deal_summary"] = {
                        "inflow_wan": round(inflow, 2),
                        "outflow_wan": round(outflow, 2),
                        "net_inflow_wan": round(inflow - outflow, 2),
                        "trade_count": len(stk_df),
                    }
                    result["stock_big_deal_samples"] = stk_df.head(top_n).to_dict(orient="records")
                else:
                    result["stock_big_deal_summary"] = {}
                    result["stock_big_deal_samples"] = []

            return ToolResult(output=result)
        except Exception as e:
            logger.error(f"BigDealAnalysisTool error: {e}")
            return ToolResult(error=str(e)) 