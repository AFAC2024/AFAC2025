import os
import json
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from datetime import datetime, timedelta
from chinese_calendar import is_holiday
import pickle
from openai import OpenAI
from tool_feature_client import MCPClient
from mcp_fetch_client import MCPFetch
import asyncio
import time
import logging  # 添加日志模块导入

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)  # 创建logger对象

import warnings
warnings.filterwarnings('ignore')
#######################################################


def call_qwen_api(prompt, model_name="qwen3-32b", temperature=0.7):
    # 初始化通义千问 API 客户端
    client = OpenAI(
        api_key="sk-b157d2837ecf4af484079352c80c7978", 
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    """调用通义千问 API 生成文本"""
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            extra_body={"enable_thinking": False}
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"API调用失败: {e}")
        return None

def generate_llm_features(df, cache_path="llm_features.pkl", max_retries=5):
    
    fund_codes = df['fund_code'].unique()
    # 尝试加载缓存的特征
    if os.path.exists(cache_path):
        print(f"加载缓存的大模型特征: {cache_path}")
        with open(cache_path, 'rb') as f:
            cache_data = pickle.load(f)

            # 验证缓存是否匹配当前数据
            if np.array_equal(cache_data['fund_codes'], fund_codes):
                print("缓存匹配，直接使用缓存的特征")
                # 将特征合并到DataFrame
                df = df.merge(cache_data['features'], on='fund_code', how='left')
                # 确保编码列为数值类型
                df['fund_type_encoded'] = pd.to_numeric(df['fund_type_encoded'], errors='coerce').fillna(2)
                df['fund_size_encoded'] = pd.to_numeric(df['fund_size_encoded'], errors='coerce').fillna(2)
                print(df)
                return df
    
    # 存储所有大模型交互记录
    llm_record = {"prompts": [], "responses": []}
    # 存储所有MCP交互记录
    mcp_records = []

    print("使用qwen3-32b生成基金的网址...")
    web_prompt = f"""
    你是一名专业的金融分析师，请提供基金集合{fund_codes}的天天基金基金概况网址.
    输出格式-JSON对象,示例：
    {{
      {{ "fund_code": "000086", "fund_url": "https://fundf10.eastmoney.com/jbgk_000086.html" }},
      {{"fund_code": "000192", "fund_url": "https://fundf10.eastmoney.com/jbgk_000192.html" }},
      ...
    }}
    """

    # 记录交互
    llm_record["prompts"].append(web_prompt)
    
    # 调用API获取基金类型
    fund_web = None
    for attempt in range(max_retries):
        fund_web = call_qwen_api(web_prompt)  # 替换为通义千问API调用
        if fund_web:
            break
        print(f"描述生成失败，重试 {attempt+1}/{max_retries}")
    
    # 记录响应
    llm_record["responses"].append(fund_web)
    # 解析fund_web JSON字符串为Python字典
    fund_web_dict = parse_fund_web_json(fund_web)
    print('fund_web:\n', fund_web)

    # 将交互记录保存为JSON文件
    with open('llm_records.json', 'w', encoding='utf-8') as f:
        json.dump(llm_record, f, ensure_ascii=False, indent=2)  # 修改为正确的变量名

    print("使用mcp爬虫工具fetch生成基金的结构化描述...")
    
    async def fetch_fund_desc():
        # 初始化魔塔mcp服务：fetch
        mcp_fetch = MCPFetch()
        fund_data = []

        try:
            # 加载服务器配置并连接
            server_urls = mcp_fetch.load_server_config()
            await mcp_fetch.connect_to_sse_server(server_urls)
        
            for fund_code in fund_codes:
                mcp_record = {"fund_code": fund_code, "prompts": [], "responses": []}
        
                try:
                    fund_url = fund_web_dict.get(fund_code, "")
                    if not fund_url:
                        logger.warning(f"未找到基金 {fund_code} 的URL，使用默认值")
                        fund_data.append({"fund_code": fund_code, "fund_type": 2, "fund_size": 2})
                        continue
                        
                    print('fund_code:', fund_code, 'fund_url:', fund_url)
                    
                    mcp_fetch_prompt = f"""
                    请从下面网址提取基金的结构化描述.
                    包括以下字段：
                    1. 基金类型（'债券型': 1,'混合型': 2, '股票型': 3, 'QDII': 4)
                    2. 基金规模（'小型基金(资产规模<10亿元)': 1, '中型基金(资产规模10-50亿元)': 2, '大型基金(资产规模50-100亿元)': 3, '超大型基金(资产规模100亿元以上)': 4)
                
                    输出格式-JSON对象,示例：
                    {{
                        "fund_code": "{fund_code}", "fund_type": 1, "fund_size": 2 
                    }}
                    网址：{fund_url}
                    """
        
                    mcp_record["prompts"].append(mcp_fetch_prompt)
                    # 使用异步方式调用
                    fund_desc = await mcp_fetch.process_user_query(mcp_fetch_prompt)
        
                    print('fund_desc:\n', fund_desc)
                    mcp_record["responses"].append(fund_desc)
                    
                    # 解析fund_desc并添加到fund_data列表
                    try:
                        # 尝试解析JSON响应
                        import re
                        # 查找JSON对象
                        json_match = re.search(r'\{[^\{\}]*"fund_code"[^\{\}]*\}', fund_desc)
                        if json_match:
                            fund_json = json.loads(json_match.group())
                            fund_data.append(fund_json)
                        else:
                            # 如果没有找到JSON，使用默认值
                            logger.warning(f"未能从响应中提取JSON数据，基金 {fund_code} 使用默认值")
                            fund_data.append({"fund_code": fund_code, "fund_type": 2, "fund_size": 2})
                    except Exception as parse_error:
                        logger.error(f"解析基金{fund_code}描述失败: {parse_error}")
                        # 使用默认值
                        fund_data.append({"fund_code": fund_code, "fund_type": 2, "fund_size": 2})
                        
                except Exception as e:
                    logger.error(f"处理基金{fund_code}失败: {e}")
                    # 使用默认值
                    fund_data.append({"fund_code": fund_code, "fund_type": 2, "fund_size": 2})
                    
                # 添加记录到mcp_records
                mcp_records.append(mcp_record)

        except Exception as e:
            logger.error(f"初始化或连接MCP服务失败: {e}")
            # 如果连接失败，为所有基金使用默认值
            for fund_code in fund_codes:
                fund_data.append({"fund_code": fund_code, "fund_type": 2, "fund_size": 2})
        finally:
            # 确保资源被正确清理
            try:
                await mcp_fetch.cleanup()
                logger.info("MCP资源已清理")
            except Exception as cleanup_error:
                logger.error(f"清理MCP资源时出错: {cleanup_error}")
            
        return fund_data
    
    # 调用异步函数并获取结果
    fund_data = asyncio.run(fetch_fund_desc())
    
    # 创建基金特征字典
    fund_type_dict = {}
    fund_size_dict = {}
    
    for item in fund_data:
        fund_code = item.get('fund_code')
        if fund_code:
            fund_type_dict[fund_code] = item.get('fund_type', 2)  # 默认为混合型
            fund_size_dict[fund_code] = item.get('fund_size', 2)  # 默认为中型基金
    
    for fund_code in fund_codes:
        # 默认值
        fund_type_dict[fund_code] = 2  # 默认为混合型
        fund_size_dict[fund_code] = 2  # 默认为中型基金
        
        # 尝试从解析结果中获取基金类型和规模
        if isinstance(fund_data, list):
            # 如果是列表形式
            for item in fund_data:
                if item.get('fund_code') == fund_code:
                    fund_type_dict[fund_code] = item.get('fund_type', 2)
                    fund_size_dict[fund_code] = item.get('fund_size', 2)
                    break
        elif isinstance(fund_data, dict):
            # 如果是字典形式
            if fund_code in fund_data:
                item = fund_data[fund_code]
                if isinstance(item, dict):
                    fund_type_dict[fund_code] = item.get('fund_type', 2)
                    fund_size_dict[fund_code] = item.get('fund_size', 2)
    
    # 创建特征DataFrame
    features_df = pd.DataFrame({
        'fund_code': list(fund_type_dict.keys()),
        'fund_type_encoded': list(fund_type_dict.values()),
        'fund_size_encoded': list(fund_size_dict.values())
    })
    
    # 保存特征和交互记录
    cache_data = {
        "fund_codes": fund_codes,
        "features": features_df,
        "llm_record": llm_record,  # 修改为正确的变量名
        "mcp_records": mcp_records,  # 添加MCP交互记录
        "timestamp": datetime.now().isoformat()
    }
    
    with open(cache_path, 'wb') as f:
        pickle.dump(cache_data, f)
    print(f"大模型特征已缓存至: {cache_path}")
    
    # 将交互记录保存为JSON文件
    with open('llm_records.json', 'w', encoding='utf-8') as f:
        json.dump(llm_record, f, ensure_ascii=False, indent=2)  # 修改为正确的变量名
    
    # 将MCP交互记录保存为JSON文件
    with open('mcp_records.json', 'w', encoding='utf-8') as f:
        json.dump(mcp_records, f, ensure_ascii=False, indent=2)  # 保存MCP交互记录
    
    # 将特征合并到DataFrame
    df = df.merge(features_df, on='fund_code', how='left')
    # 确保编码列为数值类型
    df['fund_type_encoded'] = pd.to_numeric(df['fund_type_encoded'], errors='coerce').fillna(2)
    df['fund_size_encoded'] = pd.to_numeric(df['fund_size_encoded'], errors='coerce').fillna(2)

    print('合并后特征\n',df)
    return df

def parse_fund_web_json(fund_web_str):
    
    # 移除可能的markdown标记和多余的反引号
    cleaned_str = fund_web_str.replace('```json', '').replace('```', '').replace('`', '').strip()
    # 解析为JSON
    fund_web_array = json.loads(cleaned_str)
    # 将数组转换为字典
    fund_web_dict = {item['fund_code']: item['fund_url'].strip() for item in fund_web_array}

    return fund_web_dict

def create_basic_features(data_path):
    mcp_integration = MCPClient()

    user_input = f"请帮我对{data_path}目录下的数据添加特征"
        
    result = mcp_integration.process_user_input(user_input)
    print(f"处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

    if result.get('status') == "success":
        feature_df = pd.read_csv(result.get('saved_file'), dtype={'fund_code': str})
        feature_df['transaction_date'] = pd.to_datetime(feature_df['transaction_date'], format='%Y%m%d')
        print("基础特征提取完成，数据已保存。")
    else:
        print(f"基础特征提取失败: {result.get('error')}")
        return None

    print("Feature engineering completed. Number of features:", feature_df.shape[1])
    print("\n=== 特征样本预览 ===")
    print(feature_df)
    
    return feature_df

def filter_anomalies(X_train, target_col, zscore_threshold=3):
    """
    根据z-score过滤异常样本
    """
    days_ahead = int(target_col.split('_')[-1])
    target_type = 'apply' if 'apply' in target_col else 'redeem'

    # 对赎回使用更严格的阈值
    if target_type == 'redeem':
        zscore_threshold = zscore_threshold - 0.5  # 降低赎回的异常值阈值
    
    # 创建基础掩码
    valid_mask = pd.Series(True, index=X_train.index)
    
    # 根据z-score过滤异常值
    zscore_col = f'{target_type}_amt_zscore'
    print(f"Using z-score column: {zscore_col}")
    
    # 获取异常日期的基金
    abnormal_samples = X_train[abs(X_train[zscore_col]) > zscore_threshold]
    print(f"Found {len(abnormal_samples)} abnormal samples")
    
    if not abnormal_samples.empty:
        for _, abnormal_row in abnormal_samples.iterrows():
            abnormal_date = abnormal_row['transaction_date']
            abnormal_fund = abnormal_row['fund_code']
            
            # 计算需要删除的日期（向前偏移days_ahead天）
            delete_date = (pd.to_datetime(abnormal_date) - pd.Timedelta(days=days_ahead)).strftime('%Y%m%d')
            
            # 在训练集中标记需要删除的样本
            delete_mask = ((X_train['transaction_date'] == abnormal_date) | 
                         (X_train['transaction_date'] == delete_date)) & \
                        (X_train['fund_code'] == abnormal_fund)
            valid_mask[delete_mask] = False
    
    return valid_mask

# 模型训练
def train_models(X_train, y_train_all):
    """
    训练LightGBM模型，每个模型预测一个目标
    """
    models = {}
    feature_importance_dict = {}

    # 准备模型训练特征
    features_col = [col for col in X_train.columns if not col.startswith(('apply_amt_future', 'redeem_amt_future', 'fund_code', 'transaction_date'))]
    
    # 基础参数配置
    params = {
        'objective': 'regression',
        'metric': ['rmse', 'mae'],
        'boosting_type': 'gbdt',
        'learning_rate': 0.01,
        'num_leaves': 63,
        'max_depth': 8,
        'min_child_samples': 30,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'reg_alpha': 0.1,
        'reg_lambda': 0.1,
        'verbose': -1,
        'random_state': 42
    }
    
    # 对每个目标训练一个模型
    for idx, target_col in enumerate(y_train_all.columns):
        print(f"\nTraining model for {target_col}...")

        # 过滤异常样本
        valid_mask = filter_anomalies(X_train, target_col)
        
        # 应用过滤
        X_train_filtered = X_train[valid_mask]
        y_train_filtered = y_train_all[target_col][valid_mask]
        
        print(f"Samples before filtering: {len(X_train)}")
        print(f"Samples after filtering: {len(X_train_filtered)}")
        print(f"Removed {len(X_train) - len(X_train_filtered)} samples")
        
        # 划分训练集和验证集
        X_train_split, X_val, y_train_split, y_val = train_test_split(
            X_train_filtered[features_col],
            y_train_filtered,
            test_size=0.2,
            random_state=42
        )
        
        # 创建数据集
        train_data = lgb.Dataset(X_train_split, label=y_train_split)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        # 训练模型
        model = lgb.train(
            params,
            train_data,
            valid_sets=[train_data, val_data],
            num_boost_round=2000,
            callbacks=[
                lgb.early_stopping(stopping_rounds=100),
                lgb.log_evaluation(period=100)
            ]
        )
        
        # 保存模型和特征重要性
        models[target_col] = model
        
        # 计算并保存特征重要性
        feature_importance = pd.DataFrame({
            'feature': features_col,
            'importance': model.feature_importance()
        })
        feature_importance_dict[target_col] = feature_importance.sort_values(
            'importance', ascending=False
        )
        
        # 打印每个模型的top5重要特征
        print(f"\nTop 5 important features for {target_col}:")
        print(feature_importance.nlargest(10, 'importance'))
    
    return models, features_col, feature_importance_dict

# 预测未来一周数据
def predict_future(models, feature_names, df):
    """
    使用模型进行预测
    """
    fund_codes = df['fund_code'].unique()

    start_date = df['transaction_date'].max() + timedelta(days=1)
    end_date = df['transaction_date'].max() + timedelta(days=7)
    print('start_date:', start_date)
    print('end_date:', end_date)
   
    # 计算first_data的日期
    first_date = df['transaction_date'].max()
    print('first_date:', first_date)
    date_range = pd.date_range(start=start_date, end=end_date)  
    results = []

    for fund_code in fund_codes:
        # 获取该基金的最新数据
        fund_data = df[df['fund_code'] == fund_code].copy()
        fund_data['transaction_date'] = pd.to_datetime(fund_data['transaction_date'], format='%Y%m%d')
        first_data = fund_data[fund_data['transaction_date'] == first_date].iloc[0].copy()

        # 为该基金维护历史数据，用于计算滚动统计
        fund_history = fund_data.sort_values('transaction_date').tail(30).copy()
        
        for date in date_range:
            new_row = first_data.copy()
  
            # 准备特征
            features = new_row[feature_names].values.reshape(1, -1)
            
            # 构建结果字典
            result_dict = {
                'fund_code': fund_code,
                'transaction_date': date.strftime('%Y%m%d'),
            }
            
            
            # 只使用对应天数的模型进行预测
            apply_pred = models["apply_amt_future_1"].predict(features)[0]
            redeem_pred = models["redeem_amt_future_1"].predict(features)[0]
            result_dict[f'apply_amt_pred'] = apply_pred
            result_dict[f'redeem_amt_pred'] = redeem_pred
            
            results.append(result_dict)

            # 更新最新数据
            new_row['transaction_date'] = date
            new_row['apply_amt'] = apply_pred
            new_row['redeem_amt'] = redeem_pred

            #-------------- 更新特征----------------
            new_row['year'] = new_row['transaction_date'].year
            new_row['month'] = new_row['transaction_date'].month
            new_row['day_of_week'] = new_row['transaction_date'].dayofweek + 1
            new_row['day_of_month'] = new_row['transaction_date'].day
            new_row['day_of_year'] = new_row['transaction_date'].dayofyear
            new_row['week_of_year'] = new_row['transaction_date'].isocalendar().week

            new_row["is_weekend"] = int(new_row["day_of_week"] >= 6)
            new_row["is_sunday"] = int(new_row["day_of_week"] == 7)
            new_row['is_month_end'] = int(new_row['transaction_date'].is_month_end)
            new_row['is_month_start'] = int(new_row['transaction_date'].is_month_start)
            new_row['is_quarter_end'] = int(new_row['transaction_date'].is_quarter_end)
            new_row['is_quarter_start'] = int(new_row['transaction_date'].is_quarter_start)

            # 添加节假日特征
            new_row['is_holiday'] = int(is_holiday(new_row['transaction_date']))

            # 是否为当月第1个，最后1个工作日
            month_start = new_row['transaction_date'].replace(day=1)
            if new_row['transaction_date'].month == 12:
                next_month = new_row['transaction_date'].replace(year=new_row['transaction_date'].year + 1, month=1, day=1)
            else:
                next_month = new_row['transaction_date'].replace(month=new_row['transaction_date'].month + 1, day=1)
            month_end = next_month - pd.Timedelta(days=1)
            month_dates = pd.date_range(month_start, month_end)
            workdays = [d for d in month_dates if d.weekday() < 5 and not is_holiday(d)]
            if workdays:
                new_row['is_first_workday_of_month'] = int(new_row['transaction_date'] == workdays[0])
                new_row['is_last_workday_of_month'] = int(new_row['transaction_date'] == workdays[-1])
            else:
                new_row['is_first_workday_of_month'] = 0
                new_row['is_last_workday_of_month'] = 0
            
            # 月初、月末标记
            new_row['near_month_start'] = int(new_row['day_of_month'] <= 3)
            new_row['near_month_end'] = int(new_row['day_of_month'] >= 28)

            # 傅里叶编码（周/月周期）
            new_row['sin_week'] = np.sin(2 * np.pi * new_row['day_of_week'] / 7)
            new_row['cos_week'] = np.cos(2 * np.pi * new_row['day_of_week'] / 7)
            new_row['month_sin'] = np.sin(2 * np.pi * new_row['day_of_month'] / 30)
            new_row['month_cos'] = np.cos(2 * np.pi * new_row['day_of_month'] / 30)

            new_row['day_sin'] = np.sin(2 * np.pi * new_row['day_of_year'] / 365)
            new_row['day_cos'] = np.cos(2 * np.pi * new_row['day_of_year'] / 365) 
            new_row['week_sin'] = np.sin(2 * np.pi * new_row['week_of_year'] / 52)
            new_row['week_cos'] = np.cos(2 * np.pi * new_row['week_of_year'] / 52)
            
            # 将新预测的数据添加到历史数据中
            new_history_row = pd.DataFrame({
                'fund_code': [fund_code],
                'transaction_date': [date],
                'apply_amt': [apply_pred],
                'redeem_amt': [redeem_pred]
            })
            fund_history = pd.concat([fund_history, new_history_row], ignore_index=True)
            
            # 保持历史数据窗口大小，只保留最近30天
            fund_history = fund_history.sort_values('transaction_date').tail(30)
            
            # 更新滚动平均特征
            # 3天滚动平均
            recent_3_days = fund_history.tail(3)
            if len(recent_3_days) >= 1:
                new_row['apply_amt_rolling_mean_3'] = recent_3_days['apply_amt'].mean()
                new_row['redeem_amt_rolling_mean_3'] = recent_3_days['redeem_amt'].mean()
                new_row['apply_amt_rolling_std_3'] = recent_3_days['apply_amt'].std() if len(recent_3_days) > 1 else 0
                new_row['redeem_amt_rolling_std_3'] = recent_3_days['redeem_amt'].std() if len(recent_3_days) > 1 else 0
                new_row['redeem_amt_volatility_3'] = (recent_3_days['redeem_amt'].std() / recent_3_days['redeem_amt'].mean()) if recent_3_days['redeem_amt'].mean() != 0 else 0
            
            # 7天滚动平均
            recent_7_days = fund_history.tail(7)
            if len(recent_7_days) >= 1:
                new_row['apply_amt_rolling_mean_7'] = recent_7_days['apply_amt'].mean()
                new_row['redeem_amt_rolling_mean_7'] = recent_7_days['redeem_amt'].mean()
                new_row['apply_amt_rolling_std_7'] = recent_7_days['apply_amt'].std() if len(recent_7_days) > 1 else 0
                new_row['redeem_amt_rolling_std_7'] = recent_7_days['redeem_amt'].std() if len(recent_7_days) > 1 else 0
                new_row['redeem_amt_volatility_7'] = (recent_7_days['redeem_amt'].std() / recent_7_days['redeem_amt'].mean()) if recent_7_days['redeem_amt'].mean() != 0 else 0
            
            first_data = new_row.copy()
    
    return pd.DataFrame(results)

# 主函数
def main(date):
    # 数据文件路径
    delta = 1
    data_path = f'./data/{date}_update/'
    print(f'预测 20250725-0731的申购/赎回')

    # ——————————————————————— 特征工程 ———————————————————————————
    print("--------特征工程-----------")
    print("添加基础特征...")
    feature_df = create_basic_features(data_path)

    print("添加大模型特征...")
    feature_df = generate_llm_features(feature_df)

    # 输出train_set 
    os.makedirs("results", exist_ok=True)
    feature_df['transaction_date'] = feature_df['transaction_date'].dt.strftime('%Y%m%d')
    feature_df.to_csv("results/train_set_roll.csv", index=False)
    # 转换日期格式
    feature_df['transaction_date'] = pd.to_datetime(feature_df['transaction_date'], format='%Y%m%d')
    
    # 添加未来delta天的申购和赎回标签
    grouped = feature_df.groupby('fund_code')
    for i in range(1, delta + 1):
        feature_df[f'apply_amt_future_{i}'] = grouped['apply_amt'].shift(-i)
        feature_df[f'redeem_amt_future_{i}'] = grouped['redeem_amt'].shift(-i)    
    
    # 准备训练数据、测试数据
    X_train = (feature_df.groupby('fund_code', group_keys=False)
                 .apply(lambda x: x.sort_values('transaction_date').iloc[30:-1])).reset_index(drop=True)
    X_train = X_train.sort_values(['transaction_date', 'fund_code'])
    print('X_train:\n', X_train)


    # 准备标签
    target_cols = []
    for i in range(1, delta + 1):
        target_cols.extend([f'apply_amt_future_{i}', f'redeem_amt_future_{i}'])
    y_train = X_train[target_cols]

    # ———————————————————————— 训练独立模型 —————————————————————————————————
    print("Training separate models...")
    models, feature_names, feature_importance_dict = train_models(X_train, y_train)
    print('feature_names:', feature_names)
    
    # ———————————————————————— 预测未来数据 ——————————————————————————————————
    print("\nPredicting future amounts...")
    predictions = predict_future(models, feature_names, feature_df)
    
    # ———————————————————————— 保存预测结果 ——————————————————————————————————
    predictions = predictions.sort_values(['transaction_date', 'fund_code'])
    predictions.to_csv('results/predict_result_roll.csv', index=False)
    print("\nPredictions saved to results/predict_result_roll.csv")
    
    return predictions

if __name__ == '__main__':
    predictions = main('20250724')
    print("\nPrediction results preview:")
    print(predictions.head())