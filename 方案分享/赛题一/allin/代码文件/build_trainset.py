import pandas as pd
import numpy as np
import os

#需要增加的特征
#特征1 - 上证指数
fea1 = pd.read_csv(r"Data/unprocessed_data/上证指数.csv")
# 将日期列转换为datetime格式
fea1['date'] = pd.to_datetime(fea1['date'])
# 填充上证指数周末缺失值（非交易日数据）
fea1 = fea1.set_index('date').asfreq('D').ffill().reset_index()
# 重命名列名，将'date'改为'transaction_date'
fea1.columns = ['transaction_date'] + list(fea1.columns[1:].copy())

# 特征2 - 基金排名数据
csv_files = os.listdir(r'Data/unprocessed_data/rank')
fea2_df = None
# 遍历所有基金排名文件，合并为一个DataFrame
for i,file in enumerate(csv_files):
    path = os.path.join(r'Data/unprocessed_data/rank',file)
    fund_code = int(file.split('.')[0])# 从文件名提取基金代码
    csv = pd.read_csv(path)
    csv['fund_code'] = fund_code
    if i == 0:
        fea2_df = csv
    else:
        fea2_df = pd.concat([fea2_df,csv],axis=0)
# 确保fund_code为整数类型
fea2_df['fund_code'] = fea2_df['fund_code'].astype(int)
# 转换日期格式
fea2_df['date'] = pd.to_datetime(fea2_df['date'])
# 按基金代码和日期排序
fea2_df.sort_values(by=['fund_code','date'],inplace=True)
fea2_df.reset_index(drop=True,inplace=True)
# 重命名列名
fea2_df.columns = ['transaction_date','rank','fund_code']


#合并特征
# 读取原始基金申购赎回数据
origrin_data = pd.read_csv(r'Data/unprocessed_data/fund_apply_redeem_series.csv')
# 获取所有基金代码列表
fund_code_list = origrin_data.drop_duplicates('fund_code')['fund_code'].values.tolist()
# 每只基金的历史数据
fund_data_list = []
# 最终得到的数据
final_data = None
# 遍历每只基金，合并特征数据
for i,fund_code in enumerate(fund_code_list):
    # 原始基金数据集
    fund_data = origrin_data.loc[origrin_data['fund_code']==fund_code].copy()
    # 转换交易日期格式
    fund_data['transaction_date'] = pd.to_datetime(fund_data['transaction_date'], format='%Y%m%d')
    fund_data.reset_index(drop=True, inplace=True)
    fund_data = fund_data.sort_values(by='transaction_date')
    # 获取该基金的排名特征数据
    fea2_fund_data = fea2_df.loc[fea2_df['fund_code']==fund_code].copy()
    # 合并排名特征
    fund_data = pd.merge(
        left=fund_data,
        right=fea2_fund_data[fea2_fund_data.columns[:-1]],
        how='left',
        on='transaction_date'
    )
    # 填充rank列的缺失值，使用前一个有效值
    fund_data['rank'] = fund_data.groupby('fund_code')['rank'].fillna(method='ffill')
    # 合并上证指数特征
    fund_data = pd.merge(
        left=fund_data,
        right=fea1,
        how='left',
        on='transaction_date'
    )
    # 将处理后的基金数据添加到最终数据集中
    if i==0:
        final_data = fund_data
    else:
        final_data = pd.concat([final_data,fund_data],axis=0)
# 重置索引并排序
final_data.reset_index(drop=True,inplace=True)
# 按交易日期和基金代码排序
final_data.sort_values(by=['transaction_date','fund_code'],inplace=True)
# 处理日期格式，转换为YYYYMMDD格式的整数
final_data['transaction_date'] = final_data['transaction_date'].dt.strftime('%Y%m%d')
final_data['transaction_date'] = final_data['transaction_date'].astype('Int64')
final_data.reset_index(drop=True,inplace=True)
# 保存合并后的特征数据
final_data.to_csv(r"Data/fund_apply_redeem_series_addfea.csv",index=False)

def fix_date_format(input_file, output_file=None):
    """
    修改日期格式为xxxxxxxx格式（YYYYMMDD）
    
    参数:
        input_file (str): 输入文件路径
        output_file (str, optional): 输出文件路径，默认为None（覆盖原文件）
    
    返回:
        str: 保存路径
    """
    df = pd.read_csv(input_file)
    # 确保transaction_date是字符串类型
    df['transaction_date'] = df['transaction_date'].astype(str)
    # 将日期中的'-'替换为空字符串
    df['transaction_date'] = df['transaction_date'].str.replace('-', '')
    # 确定保存路径
    save_path = output_file if output_file else input_file
    # 保存修改后的数据
    df.to_csv(save_path, index=False)
    return save_path

def clean_line_features():
    """
    清洗折线图特征数据
    
    返回:
        DataFrame: 清洗后的折线图特征数据
    """
    df = pd.read_csv('Data/VLM.csv')
    # 使用正则表达式从文件路径中提取基金代码和交易日期
    pattern = r'images/(\d+)/\d+_(\d{4}-\d{2}-\d{2})'
    extracted = df['file'].str.extract(pattern)
    # 提取基金代码
    df['fund_code'] = extracted[0]
    # 提取并格式化交易日期
    df['transaction_date'] = extracted[1].str.replace('-', '')
    # 选择需要的列并保存
    result = df[['fund_code', 'transaction_date', 'apply', 'redeem']]
    result.to_csv('Data/cleaned_line_features.csv', index=False)
    return result

def merge_features():
    """
    合并折线图特征到主数据集
    
    返回:
        DataFrame: 合并后的数据
    """
    # 读取折线图特征数据
    line_features = pd.read_csv('Data/cleaned_line_features.csv')
    # 读取主数据集
    target_data = pd.read_csv(r'Data/fund_apply_redeem_series_addfea.csv')
    # 合并数据
    merged = pd.merge(
        target_data,
        line_features[['fund_code', 'transaction_date', 'apply', 'redeem']],
        on=['fund_code', 'transaction_date'],
        how='left'
    )
    # 重命名列名，避免与原始列名冲突
    merged = merged.rename(columns={
        'apply': 'line_apply',
        'redeem': 'line_redeem'
    })
    # 保存合并后的数据
    merged.to_csv('Data/fund_apply_redeem_series_addfea_with_line.csv', index=False)
    return merged

def fill_line_values(input_file):
    """
    填充折线图特征的缺失值
    
    参数:
        input_file (str): 输入文件路径
    
    返回:
        DataFrame: 填充缺失值后的数据
    """
    df = pd.read_csv(input_file)
    df['line_apply'] = df['line_apply'].fillna(method='bfill').fillna(method='ffill')
    df['line_redeem'] = df['line_redeem'].fillna(method='bfill').fillna(method='ffill')
    df.to_csv(input_file, index=False)
    return df

def merge_sentiment():
    """
    合并情感分析数据
    
    返回:
        DataFrame: 合并情感分析数据后的最终数据集
    """
    main_df = pd.read_csv(r'Data/fund_apply_redeem_series_addfea_with_line.csv')
    sentiment_data = []
    sentiment_dir = r'Data/sentiment_results'
    # 遍历所有情感分析结果文件
    for filename in os.listdir(sentiment_dir):
        if filename.endswith('.csv'):
            fund_code = int(filename.split('.')[0])
            df = pd.read_csv(os.path.join(sentiment_dir, filename))
            df['date'] = df['date'].str.replace('-', '').astype(int)
            df['fund_code'] = fund_code
            sentiment_data.append(df)
    sentiment_df = pd.concat(sentiment_data)
    merged_df = pd.merge(
        main_df,
        sentiment_df,
        left_on=['fund_code', 'transaction_date'],
        right_on=['fund_code', 'date'],
        how='left'
    )
    merged_df.drop(['date', 'Unnamed: 0'], axis=1, errors='ignore', inplace=True)
    merged_df['sentiment'] = merged_df['sentiment'].fillna(0)
    merged_df.to_csv('Data/train_set.csv', index=False)
    return merged_df

if __name__ == "__main__":
    # 1. 执行原始build_traindata功能
    print("正在合并上证指数和基金排名特征...")
    
    # 2. 格式化日期
    print("\n正在格式化日期...")
    addfea_path = r"Data/fund_apply_redeem_series_addfea.csv"
    fix_date_format(addfea_path)
    
    # 3. 清洗折线图特征
    print("\n正在清洗折线图特征...")
    clean_line_features()
    
    # 4. 合并折线图特征
    print("\n正在合并折线图特征...")
    merge_features()
    
    # 5. 填充折线图缺失值
    print("\n正在填充折线图缺失值...")
    line_path = 'Data/fund_apply_redeem_series_addfea_with_line.csv'
    fill_line_values(line_path)
    
    # 6. 合并情感特征
    print("\n正在合并情感特征...")
    final_df = merge_sentiment()
    
    print("\n训练数据构建完成！最终结果保存在: Data/train_set.csv")
