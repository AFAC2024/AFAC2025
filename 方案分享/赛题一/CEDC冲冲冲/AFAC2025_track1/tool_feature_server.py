"""
MCP时间特征工程服务 (Enhanced Version 2.0.0)

功能概述:
这是一个基于FastAPI的微服务, 专门用于为时间序列数据(特别是基金申购赎回数据)
添加丰富的时间特征和统计特征, 以支持机器学习模型的训练和预测。

主要功能模块:
1. 基础时间特征提取 - 年、月、日、星期等基本时间维度
2. 节假日特征识别 - 基于中国日历的节假日判断
3. 工作日特征工程 - 月初月末工作日标记和统计
4. 周期性特征编码 - 使用傅里叶变换进行周期性编码
5. 滚动统计特征 - 多时间窗口的均值、标准差、波动率
6. 滞后特征生成 - 历史数据的时间延迟特征
7. 标准化特征 - Z-score标准化处理
8. 曝光UV特征 - 用户访问量相关的滚动统计
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from chinese_calendar import is_holiday
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging
from typing import List, Optional, Dict, Any

import warnings
warnings.filterwarnings('ignore')

# 配置日志
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_feature_service.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path)
    ]
)
logger = logging.getLogger("MCP-Feature-Service")

app = FastAPI(
    title="时间特征工程MCP服务",
    description="为时间序列数据添加基础时间特征和增强特征",
    version="2.0.0",
    openapi_url="/openapi.json"
)

# ----------------------------
# 数据模型定义
# ----------------------------
class FeatureRequest(BaseModel):
    data_path: Optional[str] = './data'      # 接收数据所在的目录
    save_path: Optional[str] = './'
    
class FeatureResponse(BaseModel):
    status: str
    saved_file: Optional[str] = None

# ----------------------------
# 特征工程函数
# ----------------------------
def extract_features_tool(data_path):
    # 读取数据
    data_file = os.path.join(data_path, 'fund_apply_redeem_series.csv')
    df = pd.read_csv(data_file, dtype={'fund_code': str})
    df['transaction_date'] = pd.to_datetime(df['transaction_date'], format='%Y%m%d')

    feature_df = df.copy()

    # 时间特征
    feature_df['year'] = feature_df['transaction_date'].dt.year
    feature_df['month'] = feature_df['transaction_date'].dt.month

    feature_df['day_of_week'] = feature_df['transaction_date'].dt.dayofweek + 1
    feature_df['day_of_month'] = feature_df['transaction_date'].dt.day
    feature_df['day_of_year'] = feature_df['transaction_date'].dt.dayofyear
    feature_df['week_of_year'] = feature_df['transaction_date'].dt.isocalendar().week

    feature_df["is_weekend"] = (feature_df["day_of_week"] >= 6).astype(int)
    feature_df["is_sunday"] = (feature_df["day_of_week"] == 7).astype(int)
    feature_df['is_month_end'] = feature_df['transaction_date'].dt.is_month_end.astype(int)
    feature_df['is_month_start'] = feature_df['transaction_date'].dt.is_month_start.astype(int)
    feature_df['is_quarter_end'] = feature_df['transaction_date'].dt.is_quarter_end.astype(int)
    feature_df['is_quarter_start'] = feature_df['transaction_date'].dt.is_quarter_start.astype(int)

    # 添加节假日特征
    feature_df['is_holiday'] = feature_df['transaction_date'].apply(is_holiday).astype(int)

    # 月初第1个工作日、月末最后1个工作日
    feature_df['is_first_workday_of_month'] = 0
    feature_df['is_last_workday_of_month'] = 0

    workday_mask = (feature_df['is_weekend'] == 0) & (feature_df['is_holiday'] == 0)
    for (fund_code, year, month), group in feature_df[workday_mask].groupby(['fund_code', 'year', 'month']):
        if not group.empty:
            first_idx = group['transaction_date'].idxmin()
            last_idx = group['transaction_date'].idxmax()
            feature_df.loc[first_idx, 'is_first_workday_of_month'] = 1
            feature_df.loc[last_idx, 'is_last_workday_of_month'] = 1

    # 增加月初月末前后几天的标记
    feature_df['near_month_start'] = 0
    feature_df['near_month_end'] = 0
    for (fund_code, year, month), group in feature_df.groupby(['fund_code', 'year', 'month']):
        month_dates = group['transaction_date'].dt.day
        feature_df.loc[group.index[month_dates <= 3], 'near_month_start'] = 1
        feature_df.loc[group.index[month_dates >= 28], 'near_month_end'] = 1
    
    # 添加月初月末赎回统计特征
    grouped = feature_df.groupby('fund_code')
    for period in ['start', 'end']:
        mask = feature_df[f'near_month_{period}'] == 1
        feature_df[f'redeem_month_{period}_mean'] = grouped['redeem_amt'].transform(
            lambda x: x[mask].expanding().mean())
        feature_df[f'redeem_month_{period}_std'] = grouped['redeem_amt'].transform(
            lambda x: x[mask].expanding().std())
    
    # 计算每个基金的周末与工作日统计特征
    for col in ['apply_amt', 'redeem_amt']:
        # 工作日统计
        feature_df[f'{col}_weekday_mean'] = grouped.apply(
            lambda x: x[~x['is_weekend'].astype(bool)][col].expanding().mean()
        ).reset_index(0, drop=True)
        
        feature_df[f'{col}_weekday_std'] = grouped.apply(
            lambda x: x[~x['is_weekend'].astype(bool)][col].expanding().std()
        ).reset_index(0, drop=True)

        # 周末统计
        feature_df[f'{col}_weekend_mean'] = grouped.apply(
            lambda x: x[x['day_of_week'] >= 6][col].expanding().mean()
        ).reset_index(0, drop=True)
        
        feature_df[f'{col}_weekend_std'] = grouped.apply(
            lambda x: x[x['day_of_week'] >= 6][col].expanding().std()
        ).reset_index(0, drop=True)

        # 添加周末降低系数
        feature_df[f'{col}_weekend_factor'] = 1.0
        feature_df.loc[feature_df['day_of_week'] == 6, f'{col}_weekend_factor'] = 0.7  # 周六降低系数
        feature_df.loc[feature_df['day_of_week'] == 7, f'{col}_weekend_factor'] = 0.5  # 周日降低系数
    
    # 傅里叶编码（周/月周期）
    feature_df['sin_week'] = np.sin(2 * np.pi * feature_df['day_of_week'] / 7)
    feature_df['cos_week'] = np.cos(2 * np.pi * feature_df['day_of_week'] / 7)
    feature_df['month_sin'] = np.sin(2 * np.pi * feature_df['day_of_month'] / 30)
    feature_df['month_cos'] = np.cos(2 * np.pi * feature_df['day_of_month'] / 30)

    feature_df['day_sin'] = np.sin(2 * np.pi * feature_df['day_of_year'] / 365)
    feature_df['day_cos'] = np.cos(2 * np.pi * feature_df['day_of_year'] / 365)
    feature_df['week_sin'] = np.sin(2 * np.pi * feature_df['week_of_year'] / 52)
    feature_df['week_cos'] = np.cos(2 * np.pi * feature_df['week_of_year'] / 52)    

    # 添加当月平均值特征(4个)
    monthly_stats = feature_df.groupby(['fund_code', 'year', 'month']).agg({
        'apply_amt': ['mean', 'std'],
        'redeem_amt': ['mean', 'std']}).reset_index()
    
    # 重命名列
    monthly_stats.columns = ['fund_code', 'year', 'month', 
                           'monthly_apply_mean', 'monthly_apply_std',
                           'monthly_redeem_mean', 'monthly_redeem_std']
    feature_df = feature_df.merge(monthly_stats, on=['fund_code', 'year', 'month'], how='left')
    
    # 删除辅助列
    feature_df = feature_df.drop(['year', 'month'], axis=1)

    # 7天滚动统计量（12个）
    for window in [3, 7, 14, 30]:
        feature_df[f'apply_amt_rolling_mean_{window}'] = grouped['apply_amt'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean())
        feature_df[f'redeem_amt_rolling_mean_{window}'] = grouped['redeem_amt'].transform(
            lambda x: x.rolling(window=window, min_periods=1).mean())
        feature_df[f'apply_amt_rolling_std_{window}'] = grouped['apply_amt'].transform(
            lambda x: x.rolling(window=window, min_periods=1).std())
        feature_df[f'redeem_amt_rolling_std_{window}'] = grouped['redeem_amt'].transform(
            lambda x: x.rolling(window=window, min_periods=1).std())
        
        feature_df[f'redeem_amt_volatility_{window}'] = grouped['redeem_amt'].transform(
            lambda x: x.rolling(window=window, min_periods=1).std() / 
                     x.rolling(window=window, min_periods=1).mean())
    
    # 滞后特征（10个）
    for lag in [3, 7, 14, 30]:
        feature_df[f'apply_amt_lag_{lag}'] = grouped['apply_amt'].shift(lag)
        feature_df[f'redeem_amt_lag_{lag}'] = grouped['redeem_amt'].shift(lag)
    
    # 曝光UV相关特征（6个）
    for col in ['uv_key_page_1', 'uv_key_page_2', 'uv_key_page_3']:
        for window in [3, 7, 14, 30]:
            feature_df[f'{col}_rolling_mean_{window}'] = grouped[col].transform(
                lambda x: x.rolling(window=window, min_periods=1).mean())

    # 添加Z-score特征
    for col in ['apply_amt', 'redeem_amt']:
        # 计算每个基金的申购、赎回金额的Z-score
        feature_df[f'{col}_zscore'] = grouped[col].transform(
            lambda x: (x - x.mean()) / x.std())
    
    feature_df = feature_df.sort_values(['transaction_date', 'fund_code'])
    logger.info(f"特征工程完成。生成特征数量: {feature_df.shape[1]}")

    # 保存特征文件
    output_file = 'basic_features.csv'
    feature_df['transaction_date'] = feature_df['transaction_date'].dt.strftime('%Y%m%d')
    feature_df.to_csv(output_file, index=False)

    return {
        'status': 'success',
        'output_file': output_file,
        }

# ----------------------------
# API 端点
# ----------------------------
@app.post("/add_time_features", 
          response_model=FeatureResponse,
          summary="添加时间特征到数据集",
          description="为包含日期字段的数据集添加多种时间相关特征")

async def mcp_add_time_features(request: FeatureRequest):    
    logger.info(f"收到特征处理请求，输入参数: data_path={request.data_path}")

    df_dict = extract_features_tool(request.data_path)
    response = {
        "status": df_dict.get("status", "error"),
        "saved_file": df_dict.get("output_file", None),
    }
    return response

@app.get("/health", summary="服务健康检查")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "MCP Feature Engineering (Enhanced)"
    }

# ----------------------------
# MCP工具描述清单接口
# ----------------------------
@app.get("/mcp_manifest", summary="获取MCP工具描述清单")
async def get_mcp_manifest():
    manifest = {
        "name": "time_feature_engineering",
        "description": "为时间序列数据添加基础时间特征和增强特征",
        "version": "2.0.0",
        "api_endpoint": "/add_time_features",
        "parameters": {
            "data_path": {
                "type": "str",
                "description": "输入数据所在的目录路径，格式为字符串"
            },
            "save_path": {
                "type": "str",
                "description": "保存的文件目录"
            },
        },
        "output": {
            "saved_file": {"type": "string", "description": "保存的特征文件路径"}
        }
    }
    return manifest

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MCP 时间特征工程服务（增强版）")
    parser.add_argument("--host", type=str, default='127.0.0.1', help="服务主机地址")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")
    args = parser.parse_args()
    logger.info(f"启动MCP服务: {args.host}:{args.port} (workers={args.workers})")
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port, 
        workers=args.workers,
        log_config=None
    )