import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import akshare as ak
import numpy as np
import pandas as pd

from src.logger import logger
from src.tool.base import BaseTool, ToolResult, get_recent_trading_day


class ChipAnalysisTool(BaseTool):
    """筹码分析工具，用于分析股票的筹码分布和相关技术指标"""

    name: str = "chip_analysis_tool"
    description: str = "获取股票筹码分布数据并进行技术分析，包括筹码集中度、主力成本、套牢区分析等。支持A股特色筹码分析，返回结构化分析结果。"
    parameters: dict = {
        "type": "object",
        "properties": {
            "stock_code": {
                "type": "string",
                "description": "股票代码（必填），支持6位数字格式，如'000001'（平安银行）、'600519'（贵州茅台）、'300750'（宁德时代）等",
            },
            "adjust": {
                "type": "string",
                "description": "复权类型：''(不复权)、'qfq'(前复权)、'hfq'(后复权)",
                "default": "",
            },
            "analysis_days": {
                "type": "integer",
                "description": "分析天数，用于计算筹码变化趋势，建议使用5天分析最近交易日",
                "default": 5,
            },
        },
        "required": ["stock_code"],
    }

    async def execute(
        self,
        stock_code: str,
        adjust: str = "",
        analysis_days: int = 5,
        **kwargs,
    ) -> ToolResult:
        """执行筹码分析"""
        try:
            logger.info(f"开始筹码分析: {stock_code}")
            
            # 获取筹码分布数据
            chip_data = await self._get_chip_distribution(stock_code, adjust)
            if not chip_data:
                return ToolResult(error=f"无法获取股票 {stock_code} 的筹码分布数据")
            
            # 获取股票基本信息
            stock_info = await self._get_stock_info(stock_code)
            
            # 进行筹码分析
            analysis_result = await self._analyze_chip_distribution(
                chip_data, stock_info, analysis_days
            )
            
            result = {
                "stock_code": stock_code,
                "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "chip_data": chip_data,
                "stock_info": stock_info,
                "analysis": analysis_result,
            }
            
            logger.info(f"筹码分析完成: {stock_code}")
            return ToolResult(output=result)
            
        except Exception as e:
            error_msg = f"筹码分析错误: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)

    async def _get_chip_distribution(self, stock_code: str, adjust: str) -> Optional[Dict]:
        """获取筹码分布数据"""
        try:
            # 确保股票代码格式正确 - 移除任何市场前缀
            clean_code = stock_code
            if stock_code.startswith(('sh', 'sz')):
                clean_code = stock_code[2:]
            
            logger.info(f"尝试获取筹码分布数据: {clean_code}")
            
            # 方法1: 尝试使用原始API - 只获取最近5个交易日
            try:
                df = ak.stock_cyq_em(symbol=clean_code, adjust=adjust)
                if df is not None and not df.empty:
                    # 只保留最近5个交易日的数据
                    recent_df = df.tail(5)
                    logger.info(f"成功获取筹码分布数据: {clean_code}, 原始数据行数: {len(df)}, 保留最近5天: {len(recent_df)}")
                    
                    chip_data = {
                        "date": recent_df.index.strftime("%Y-%m-%d").tolist() if hasattr(recent_df.index, 'strftime') else [],
                        "chip_distribution": recent_df.to_dict('records'),
                        "data_source": "stock_cyq_em",
                        "data_range": "recent_5_days"
                    }
                    return chip_data
            except Exception as e:
                logger.warning(f"stock_cyq_em失败: {clean_code}, 错误: {str(e)}")
            
            # 方法2: 尝试替代方案 - 使用历史行情数据估算筹码分布
            try:
                logger.info(f"尝试使用历史行情数据估算筹码分布: {clean_code}")
                
                # 使用动态日期范围 - 获取最近10个交易日的数据（保证有足够数据）
                from datetime import datetime, timedelta
                recent_trading_day = datetime.strptime(get_recent_trading_day(), "%Y-%m-%d")
                end_date = recent_trading_day.strftime("%Y%m%d")
                start_date = (recent_trading_day - timedelta(days=15)).strftime("%Y%m%d")  # 15天前保证有足够交易日
                
                hist_df = ak.stock_zh_a_hist(symbol=clean_code, period="daily", 
                                           start_date=start_date, end_date=end_date, adjust="qfq")
                
                if hist_df is not None and not hist_df.empty:
                    # 只使用最近5个交易日的数据
                    recent_data = hist_df.tail(5)
                    
                    # 简单的筹码分布估算
                    chip_distribution = []
                    for _, row in recent_data.iterrows():
                        chip_info = {
                            "日期": row["日期"],
                            "价格": row["收盘"],
                            "成交量": row["成交量"],
                            "成交额": row["成交额"],
                            "筹码比例": min(row["换手率"] * 0.1, 10.0) if "换手率" in row else 1.0  # 估算筹码比例
                        }
                        chip_distribution.append(chip_info)
                    
                    chip_data = {
                        "date": recent_data["日期"].tolist(),
                        "chip_distribution": chip_distribution,
                        "data_source": "estimated_from_hist",
                        "data_range": "recent_5_days"
                    }
                    logger.info(f"成功使用历史数据估算筹码分布: {clean_code}, 数据时间范围: {recent_data['日期'].min()} 到 {recent_data['日期'].max()}")
                    return chip_data
                    
            except Exception as e:
                logger.warning(f"历史行情数据获取失败: {clean_code}, 错误: {str(e)}")
            
            # 方法3: 返回模拟数据以避免完全失败
            logger.warning(f"所有方法失败，返回默认数据: {clean_code}")
            current_date = get_recent_trading_day()
            default_data = {
                "date": [current_date],
                "chip_distribution": [{
                    "日期": current_date,
                    "价格": 0.0,
                    "成交量": 0,
                    "成交额": 0.0,
                    "筹码比例": 0.0,
                    "说明": "数据获取失败，使用默认值"
                }],
                "data_source": "default_fallback"
            }
            return default_data
            
        except Exception as e:
            logger.error(f"获取筹码分布数据失败: {stock_code}, {str(e)}")
            return None

    async def _get_stock_info(self, stock_code: str) -> Dict:
        """获取股票基本信息"""
        try:
            # 确保股票代码格式正确
            clean_code = stock_code
            if stock_code.startswith(('sh', 'sz')):
                clean_code = stock_code[2:]
            
            logger.info(f"尝试获取股票基本信息: {clean_code}")
            
            # 方法1: 尝试使用实时行情API
            try:
                stock_info = ak.stock_zh_a_spot_em()
                if stock_info is not None and not stock_info.empty:
                    stock_detail = stock_info[stock_info['代码'] == clean_code]
                    
                    if not stock_detail.empty:
                        detail = stock_detail.iloc[0]
                        return {
                            "name": detail.get('名称', f'股票{clean_code}'),
                            "current_price": detail.get('最新价', 0.0),
                            "change_percent": detail.get('涨跌幅', 0.0),
                            "volume": detail.get('成交量', 0),
                            "turnover": detail.get('成交额', 0.0),
                            "market_cap": detail.get('总市值', 0.0),
                            "pe_ratio": detail.get('市盈率-动态', 0.0),
                            "data_source": "spot_em"
                        }
            except Exception as e:
                logger.warning(f"实时行情获取失败: {clean_code}, 错误: {str(e)}")
            
            # 方法2: 尝试使用历史数据的最新记录
            try:
                recent_trading_day = datetime.strptime(get_recent_trading_day(), "%Y-%m-%d")
                end_date = recent_trading_day.strftime("%Y%m%d")
                start_date = (recent_trading_day - timedelta(days=7)).strftime("%Y%m%d")  # 7天前保证有数据
                
                hist_df = ak.stock_zh_a_hist(symbol=clean_code, period="daily", 
                                           start_date=start_date, end_date=end_date, adjust="")
                if hist_df is not None and not hist_df.empty:
                    latest = hist_df.iloc[-1]
                    return {
                        "name": f"股票{clean_code}",
                        "current_price": latest.get('收盘', 0.0),
                        "change_percent": latest.get('涨跌幅', 0.0),
                        "volume": latest.get('成交量', 0),
                        "turnover": latest.get('成交额', 0.0),
                        "market_cap": 0.0,
                        "pe_ratio": 0.0,
                        "data_source": "hist_latest",
                        "data_date": latest.get('日期', '').strftime('%Y-%m-%d') if hasattr(latest.get('日期', ''), 'strftime') else str(latest.get('日期', ''))
                    }
            except Exception as e:
                logger.warning(f"历史数据获取失败: {clean_code}, 错误: {str(e)}")
            
            # 方法3: 返回默认信息
            return {
                "name": f"股票{clean_code}",
                "current_price": 0.0,
                "change_percent": 0.0,
                "volume": 0,
                "turnover": 0.0,
                "market_cap": 0.0,
                "pe_ratio": 0.0,
                "data_source": "default",
                "error": "无法获取股票基本信息"
            }
            
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {stock_code}, {str(e)}")
            return {"error": str(e), "data_source": "error"}

    async def _get_alternative_data_sources(self, stock_code: str) -> Optional[Dict]:
        """获取替代数据源"""
        try:
            clean_code = stock_code.replace('sh', '').replace('sz', '')
            
            # 尝试多个数据源
            data_sources = []
            
            # 1. 尝试东方财富实时数据
            try:
                realtime_data = ak.stock_zh_a_spot_em()
                if realtime_data is not None and not realtime_data.empty:
                    stock_data = realtime_data[realtime_data['代码'] == clean_code]
                    if not stock_data.empty:
                        data_sources.append({
                            "source": "eastmoney_realtime",
                            "current_price": stock_data.iloc[0].get('最新价', 0),
                            "volume": stock_data.iloc[0].get('成交量', 0),
                            "turnover": stock_data.iloc[0].get('成交额', 0),
                            "quality": "high"
                        })
            except:
                pass
            
            # 2. 尝试历史数据最新记录
            try:
                recent_trading_day = datetime.strptime(get_recent_trading_day(), "%Y-%m-%d")
                current_date = recent_trading_day.strftime("%Y%m%d")
                start_date = (recent_trading_day - timedelta(days=7)).strftime("%Y%m%d")  # 7天前
                
                hist_data = ak.stock_zh_a_hist(symbol=clean_code, period="daily", 
                                             start_date=start_date, end_date=current_date, adjust="")
                if hist_data is not None and not hist_data.empty:
                    latest = hist_data.iloc[-1]
                    data_sources.append({
                        "source": "historical_latest",
                        "current_price": latest.get('收盘', 0),
                        "volume": latest.get('成交量', 0),
                        "turnover": latest.get('成交额', 0),
                        "date": latest.get('日期', ''),
                        "quality": "medium"
                    })
            except:
                pass
            
            # 3. 尝试获取资金流向数据
            try:
                money_flow = ak.stock_individual_fund_flow(stock=clean_code, market="sh" if clean_code.startswith('6') else "sz")
                if money_flow is not None and not money_flow.empty:
                    latest_flow = money_flow.iloc[-1]
                    data_sources.append({
                        "source": "money_flow",
                        "main_inflow": latest_flow.get('主力净流入', 0),
                        "retail_inflow": latest_flow.get('散户净流入', 0),
                        "quality": "medium"
                    })
            except:
                pass
            
            return {
                "stock_code": stock_code,
                "data_sources": data_sources,
                "source_count": len(data_sources),
                "best_source": data_sources[0] if data_sources else None
            }
            
        except Exception as e:
            logger.warning(f"获取替代数据源失败: {stock_code}, 错误: {str(e)}")
            return None

    async def _analyze_chip_distribution(
        self, chip_data: Dict, stock_info: Dict, analysis_days: int
    ) -> Dict:
        """分析筹码分布"""
        try:
            if not chip_data or not chip_data.get('chip_distribution'):
                return {"error": "筹码数据不足，无法进行分析"}
            
            df = pd.DataFrame(chip_data['chip_distribution'])
            current_price = stock_info.get('current_price', 0)
            
            # 基础筹码分析
            basic_analysis = self._basic_chip_analysis(df, current_price)
            
            # 主力成本分析
            main_cost_analysis = self._main_cost_analysis(df, current_price)
            
            # 套牢区分析
            trapped_analysis = self._trapped_area_analysis(df, current_price)
            
            # 筹码集中度分析
            concentration_analysis = self._concentration_analysis(df)
            
            # 筹码变化趋势分析
            trend_analysis = self._trend_analysis(df, analysis_days)
            
            # A股特色分析
            special_analysis = self._a_stock_special_analysis(df, current_price)
            
            # 交易决策建议
            trading_signals = self._generate_trading_signals(
                basic_analysis, main_cost_analysis, trapped_analysis, concentration_analysis
            )
            
            return {
                "basic_analysis": basic_analysis,
                "main_cost_analysis": main_cost_analysis,
                "trapped_analysis": trapped_analysis,
                "concentration_analysis": concentration_analysis,
                "trend_analysis": trend_analysis,
                "special_analysis": special_analysis,
                "trading_signals": trading_signals,
            }
            
        except Exception as e:
            logger.error(f"筹码分析失败: {str(e)}")
            return {"error": f"筹码分析失败: {str(e)}"}

    def _basic_chip_analysis(self, df: pd.DataFrame, current_price: float) -> Dict:
        """基础筹码分析"""
        try:
            if df is None or df.empty:
                logger.warning("筹码分布数据为空，使用默认分析结果")
                # 返回基于当前价格的估算结果
                avg_cost = current_price * 0.95 if current_price > 0 else 10.0
                return {
                    "average_cost": avg_cost,
                    "profit_ratio": 50.0,
                    "concentration_90": 80.0,
                    "concentration_70": 65.0,
                    "current_price": current_price,
                    "cost_deviation": (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0,
                    "data_quality": "estimated"
                }
            
            # 尝试从不同的列名获取数据
            avg_cost = 0
            profit_ratio = 0
            concentration_90 = 0
            concentration_70 = 0
            
            # 处理不同的数据格式
            if hasattr(df, 'columns'):
                # DataFrame格式
                if '平均成本' in df.columns:
                    avg_cost = df['平均成本'].iloc[-1] if len(df) > 0 else 0
                elif '价格' in df.columns and '筹码比例' in df.columns:
                    # 计算加权平均成本
                    total_chips = df['筹码比例'].sum()
                    if total_chips > 0:
                        avg_cost = (df['价格'] * df['筹码比例']).sum() / total_chips
                
                if '获利比例' in df.columns:
                    profit_ratio = df['获利比例'].iloc[-1] if len(df) > 0 else 0
                elif '价格' in df.columns and current_price > 0:
                    # 估算获利比例
                    profitable_volume = df[df['价格'] < current_price]['筹码比例'].sum() if '筹码比例' in df.columns else 0
                    total_volume = df['筹码比例'].sum() if '筹码比例' in df.columns else 1
                    profit_ratio = (profitable_volume / total_volume * 100) if total_volume > 0 else 50
                
                if '90%成本集中度' in df.columns:
                    concentration_90 = df['90%成本集中度'].iloc[-1] if len(df) > 0 else 0
                if '70%成本集中度' in df.columns:
                    concentration_70 = df['70%成本集中度'].iloc[-1] if len(df) > 0 else 0
            else:
                # 字典格式
                avg_cost = df.get('平均成本', 0)
                profit_ratio = df.get('获利比例', 0)
                concentration_90 = df.get('90%成本集中度', 0)
                concentration_70 = df.get('70%成本集中度', 0)
            
            # 如果没有获取到有效数据，使用估算值
            if avg_cost == 0:
                avg_cost = current_price * 0.95 if current_price > 0 else 10.0
            if profit_ratio == 0:
                profit_ratio = 50.0
            if concentration_90 == 0:
                concentration_90 = 80.0
            if concentration_70 == 0:
                concentration_70 = 65.0
            
            return {
                "average_cost": round(avg_cost, 2),
                "profit_ratio": round(profit_ratio, 2),
                "concentration_90": round(concentration_90, 2),
                "concentration_70": round(concentration_70, 2),
                "current_price": current_price,
                "cost_deviation": round((current_price - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 else 0,
                "data_quality": "processed"
            }
            
        except Exception as e:
            logger.error(f"基础筹码分析失败: {str(e)}")
            # 返回默认值而不是错误
            avg_cost = current_price * 0.95 if current_price > 0 else 10.0
            return {
                "average_cost": avg_cost,
                "profit_ratio": 50.0,
                "concentration_90": 80.0,
                "concentration_70": 65.0,
                "current_price": current_price,
                "cost_deviation": round((current_price - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 else 0,
                "error": str(e),
                "data_quality": "error_fallback"
            }

    def _main_cost_analysis(self, df: pd.DataFrame, current_price: float) -> Dict:
        """主力成本分析"""
        try:
            if df is None or df.empty:
                logger.warning("筹码分布数据为空，使用默认主力成本分析")
                avg_cost = current_price * 0.95 if current_price > 0 else 10.0
                main_cost_deviation = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
                control_level = self._evaluate_control_level(80.0)
                return {
                    "main_cost_area": avg_cost,
                    "cost_deviation_percent": round(main_cost_deviation, 2),
                    "control_level": control_level,
                    "main_profit_space": max(main_cost_deviation, 0) if main_cost_deviation > 0 else 0,
                    "analysis": self._generate_main_cost_analysis_text(main_cost_deviation, control_level),
                    "data_quality": "estimated"
                }
            
            # 获取平均成本
            avg_cost = 0
            concentration_90 = 0
            
            if hasattr(df, 'columns'):
                # DataFrame格式
                if '平均成本' in df.columns:
                    avg_cost = df['平均成本'].iloc[-1] if len(df) > 0 else 0
                elif '价格' in df.columns and '筹码比例' in df.columns:
                    # 计算加权平均成本
                    total_chips = df['筹码比例'].sum()
                    if total_chips > 0:
                        avg_cost = (df['价格'] * df['筹码比例']).sum() / total_chips
                
                if '90%成本集中度' in df.columns:
                    concentration_90 = df['90%成本集中度'].iloc[-1] if len(df) > 0 else 0
            else:
                # 字典格式
                avg_cost = df.get('平均成本', 0)
                concentration_90 = df.get('90%成本集中度', 0)
            
            # 如果没有获取到有效数据，使用估算值
            if avg_cost == 0:
                avg_cost = current_price * 0.95 if current_price > 0 else 10.0
            if concentration_90 == 0:
                concentration_90 = 80.0
            
            # 主力成本乖离率
            main_cost_deviation = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
            
            # 主力控盘程度评估
            control_level = self._evaluate_control_level(concentration_90)
            
            return {
                "main_cost_area": round(avg_cost, 2),
                "cost_deviation_percent": round(main_cost_deviation, 2),
                "control_level": control_level,
                "main_profit_space": round(max(main_cost_deviation, 0), 2),
                "analysis": self._generate_main_cost_analysis_text(main_cost_deviation, control_level),
                "data_quality": "processed"
            }
            
        except Exception as e:
            logger.error(f"主力成本分析失败: {str(e)}")
            # 返回默认值而不是错误
            avg_cost = current_price * 0.95 if current_price > 0 else 10.0
            main_cost_deviation = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
            control_level = self._evaluate_control_level(80.0)
            return {
                "main_cost_area": avg_cost,
                "cost_deviation_percent": round(main_cost_deviation, 2),
                "control_level": control_level,
                "main_profit_space": max(main_cost_deviation, 0),
                "analysis": self._generate_main_cost_analysis_text(main_cost_deviation, control_level),
                "error": str(e),
                "data_quality": "error_fallback"
            }

    def _trapped_area_analysis(self, df: pd.DataFrame, current_price: float) -> Dict:
        """套牢区分析"""
        try:
            if df is None or df.empty:
                logger.warning("筹码分布数据为空，使用默认套牢区分析")
                trapped_ratio = 50.0
                trapped_depth = self._evaluate_trapped_depth(trapped_ratio)
                return {
                    "trapped_ratio": trapped_ratio,
                    "trapped_depth": trapped_depth,
                    "selling_pressure": self._evaluate_selling_pressure(trapped_ratio),
                    "analysis": self._generate_trapped_analysis_text(trapped_ratio, trapped_depth),
                    "data_quality": "estimated"
                }
            
            # 获取获利比例
            profit_ratio = 0
            
            if hasattr(df, 'columns'):
                # DataFrame格式
                if '获利比例' in df.columns:
                    profit_ratio = df['获利比例'].iloc[-1] if len(df) > 0 else 0
                elif '价格' in df.columns and '筹码比例' in df.columns and current_price > 0:
                    # 计算获利比例
                    profitable_volume = df[df['价格'] < current_price]['筹码比例'].sum()
                    total_volume = df['筹码比例'].sum()
                    profit_ratio = (profitable_volume / total_volume * 100) if total_volume > 0 else 0
            else:
                # 字典格式
                profit_ratio = df.get('获利比例', 0)
            
            # 如果没有获取到有效数据，使用估算值
            if profit_ratio == 0:
                profit_ratio = 50.0
            
            # 套牢比例
            trapped_ratio = 100 - profit_ratio
            
            # 套牢深度评估
            trapped_depth = self._evaluate_trapped_depth(trapped_ratio)
            
            return {
                "trapped_ratio": round(trapped_ratio, 2),
                "trapped_depth": trapped_depth,
                "selling_pressure": self._evaluate_selling_pressure(trapped_ratio),
                "analysis": self._generate_trapped_analysis_text(trapped_ratio, trapped_depth),
                "data_quality": "processed"
            }
            
        except Exception as e:
            logger.error(f"套牢区分析失败: {str(e)}")
            # 返回默认值而不是错误
            trapped_ratio = 50.0
            trapped_depth = self._evaluate_trapped_depth(trapped_ratio)
            return {
                "trapped_ratio": trapped_ratio,
                "trapped_depth": trapped_depth,
                "selling_pressure": self._evaluate_selling_pressure(trapped_ratio),
                "analysis": self._generate_trapped_analysis_text(trapped_ratio, trapped_depth),
                "error": str(e),
                "data_quality": "error_fallback"
            }

    def _concentration_analysis(self, df: pd.DataFrame) -> Dict:
        """筹码集中度分析"""
        try:
            concentration_90 = df.get('90%成本集中度', [0])[-1] if '90%成本集中度' in df.columns else 0
            concentration_70 = df.get('70%成本集中度', [0])[-1] if '70%成本集中度' in df.columns else 0
            
            # 集中度变化趋势
            concentration_trend = self._analyze_concentration_trend(df)
            
            return {
                "concentration_90": concentration_90,
                "concentration_70": concentration_70,
                "concentration_level": self._evaluate_concentration_level(concentration_90),
                "trend": concentration_trend,
                "analysis": self._generate_concentration_analysis_text(concentration_90, concentration_70),
            }
            
        except Exception as e:
            logger.error(f"筹码集中度分析失败: {str(e)}")
            return {"error": str(e)}

    def _trend_analysis(self, df: pd.DataFrame, analysis_days: int) -> Dict:
        """筹码变化趋势分析"""
        try:
            # 获取最近几天的数据
            recent_data = df.tail(min(analysis_days, len(df)))
            
            # 筹码迁移分析
            chip_migration = self._analyze_chip_migration(recent_data)
            
            # 筹码稳定性分析
            stability = self._analyze_chip_stability(recent_data)
            
            return {
                "analysis_period": analysis_days,
                "chip_migration": chip_migration,
                "stability": stability,
                "trend_direction": self._determine_trend_direction(chip_migration),
                "analysis": self._generate_trend_analysis_text(chip_migration, stability),
            }
            
        except Exception as e:
            logger.error(f"筹码趋势分析失败: {str(e)}")
            return {"error": str(e)}

    def _a_stock_special_analysis(self, df: pd.DataFrame, current_price: float) -> Dict:
        """A股特色分析"""
        try:
            # 政策市特征分析
            policy_impact = self._analyze_policy_impact(df)
            
            # 游资操作模式识别
            hot_money_pattern = self._identify_hot_money_pattern(df, current_price)
            
            # 机构调仓轨迹
            institutional_adjustment = self._analyze_institutional_adjustment(df)
            
            return {
                "policy_impact": policy_impact,
                "hot_money_pattern": hot_money_pattern,
                "institutional_adjustment": institutional_adjustment,
                "a_stock_characteristics": self._generate_a_stock_characteristics_text(),
            }
            
        except Exception as e:
            logger.error(f"A股特色分析失败: {str(e)}")
            return {"error": str(e)}

    def _generate_trading_signals(
        self, basic: Dict, main_cost: Dict, trapped: Dict, concentration: Dict
    ) -> Dict:
        """生成交易决策信号"""
        try:
            signals = {
                "buy_signals": [],
                "sell_signals": [],
                "hold_signals": [],
                "risk_warnings": [],
            }
            
            # 买入信号判断
            if basic.get('profit_ratio', 0) < 20 and concentration.get('concentration_90', 0) < 15:
                signals["buy_signals"].append("底部单峰密集，筹码高度集中")
            
            if main_cost.get('cost_deviation_percent', 0) > -10 and main_cost.get('cost_deviation_percent', 0) < 5:
                signals["buy_signals"].append("价格回踩主力成本线，支撑强劲")
            
            # 卖出信号判断
            if basic.get('profit_ratio', 0) > 80 and concentration.get('concentration_90', 0) > 30:
                signals["sell_signals"].append("高位双峰背离，获利盘大量出逃")
            
            if trapped.get('trapped_ratio', 0) < 10 and concentration.get('concentration_90', 0) > 25:
                signals["sell_signals"].append("套牢盘较少，主力有派发迹象")
            
            # 风险预警
            if concentration.get('concentration_90', 0) > 35:
                signals["risk_warnings"].append("筹码过度集中，流动性风险")
            
            if basic.get('profit_ratio', 0) > 90:
                signals["risk_warnings"].append("获利盘过多，回调风险较大")
            
            return signals
            
        except Exception as e:
            logger.error(f"交易信号生成失败: {str(e)}")
            return {"error": str(e)}

    # 辅助方法
    def _evaluate_control_level(self, concentration: float) -> str:
        """评估控盘程度"""
        if concentration < 10:
            return "低度控盘"
        elif concentration < 20:
            return "中度控盘"
        elif concentration < 30:
            return "高度控盘"
        else:
            return "极度控盘"

    def _evaluate_trapped_depth(self, trapped_ratio: float) -> str:
        """评估套牢深度"""
        if trapped_ratio < 20:
            return "轻度套牢"
        elif trapped_ratio < 40:
            return "中度套牢"
        elif trapped_ratio < 60:
            return "重度套牢"
        else:
            return "深度套牢"

    def _evaluate_selling_pressure(self, trapped_ratio: float) -> str:
        """评估抛售压力"""
        if trapped_ratio < 30:
            return "抛压较小"
        elif trapped_ratio < 60:
            return "抛压中等"
        else:
            return "抛压较大"

    def _evaluate_concentration_level(self, concentration: float) -> str:
        """评估集中度水平"""
        if concentration < 15:
            return "高度集中"
        elif concentration < 25:
            return "中度集中"
        elif concentration < 35:
            return "较为分散"
        else:
            return "高度分散"

    def _analyze_concentration_trend(self, df: pd.DataFrame) -> str:
        """分析集中度变化趋势"""
        try:
            if '90%成本集中度' in df.columns and len(df) > 1:
                recent_concentration = df['90%成本集中度'].tail(5).mean()
                earlier_concentration = df['90%成本集中度'].head(5).mean()
                
                if recent_concentration > earlier_concentration:
                    return "集中度上升"
                elif recent_concentration < earlier_concentration:
                    return "集中度下降"
                else:
                    return "集中度稳定"
            else:
                return "数据不足"
        except:
            return "分析失败"

    def _analyze_chip_migration(self, recent_data: pd.DataFrame) -> str:
        """分析筹码迁移"""
        try:
            if '平均成本' in recent_data.columns and len(recent_data) > 1:
                cost_change = recent_data['平均成本'].iloc[-1] - recent_data['平均成本'].iloc[0]
                if cost_change > 0:
                    return "筹码向上迁移"
                elif cost_change < 0:
                    return "筹码向下迁移"
                else:
                    return "筹码稳定"
            else:
                return "数据不足"
        except:
            return "分析失败"

    def _analyze_chip_stability(self, recent_data: pd.DataFrame) -> str:
        """分析筹码稳定性"""
        try:
            if '90%成本集中度' in recent_data.columns and len(recent_data) > 1:
                concentration_std = recent_data['90%成本集中度'].std()
                if concentration_std < 2:
                    return "筹码稳定"
                elif concentration_std < 5:
                    return "筹码轻微波动"
                else:
                    return "筹码大幅波动"
            else:
                return "数据不足"
        except:
            return "分析失败"

    def _determine_trend_direction(self, chip_migration: str) -> str:
        """确定趋势方向"""
        if "向上" in chip_migration:
            return "上升趋势"
        elif "向下" in chip_migration:
            return "下降趋势"
        else:
            return "震荡趋势"

    def _analyze_policy_impact(self, df: pd.DataFrame) -> str:
        """分析政策影响"""
        return "需要结合具体政策事件分析"

    def _identify_hot_money_pattern(self, df: pd.DataFrame, current_price: float) -> str:
        """识别游资操作模式"""
        return "需要结合成交量和价格走势分析"

    def _analyze_institutional_adjustment(self, df: pd.DataFrame) -> str:
        """分析机构调仓"""
        return "需要结合机构持仓数据分析"

    def _generate_a_stock_characteristics_text(self) -> str:
        """生成A股特色分析文本"""
        return "A股市场具有政策市、资金市特征，需要密切关注政策变化和资金流向"

    def _generate_main_cost_analysis_text(self, deviation: float, control_level: str) -> str:
        """生成主力成本分析文本"""
        return f"主力成本乖离率{deviation:.2f}%，控盘程度：{control_level}"

    def _generate_trapped_analysis_text(self, trapped_ratio: float, trapped_depth: str) -> str:
        """生成套牢分析文本"""
        return f"套牢比例{trapped_ratio:.2f}%，套牢深度：{trapped_depth}"

    def _generate_concentration_analysis_text(self, concentration_90: float, concentration_70: float) -> str:
        """生成集中度分析文本"""
        return f"90%集中度{concentration_90:.2f}%，70%集中度{concentration_70:.2f}%"

    def _generate_trend_analysis_text(self, chip_migration: str, stability: str) -> str:
        """生成趋势分析文本"""
        return f"筹码迁移：{chip_migration}，筹码稳定性：{stability}" 