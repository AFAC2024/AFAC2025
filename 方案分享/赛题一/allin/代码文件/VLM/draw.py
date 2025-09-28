import torch.nn as nn
import torch
from torch.utils.data import Dataset,DataLoader
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
#读取数据

def draw(data_path,save_path):
    """
    绘制基金申购和赎回金额的时间序列图，并保存为图像文件
    
    参数:
        data_path (str): 基金数据CSV文件路径
        save_path (str): 图像保存路径
    """
    # 读取基金数据
    data = pd.read_csv(data_path)
    # 获取不重复的基金代码列表
    fund_code_list = data.drop_duplicates('fund_code')['fund_code'].values.tolist()
    # 每只基金的历史数据列表
    fund_data_list = []
    # 顺序索引和基金代码的映射字典
    fund_code_map = {}
    # 遍历每只基金代码，处理对应的基金数据
    for i,fund_code in enumerate(fund_code_list):
        # 筛选出当前基金的数据
        fund_data = data.loc[data['fund_code']==fund_code].copy()
        # 将交易日期列转换为datetime格式
        fund_data['transaction_date'] = pd.to_datetime(fund_data['transaction_date'], format='%Y%m%d')
        date = fund_data['transaction_date']
        # 重置索引
        fund_data.reset_index(drop=True, inplace=True)
        # 按交易日期排序
        fund_data = fund_data.sort_values(by='transaction_date')
        # 设置时间窗口大小为14天
        window_size = 14
        # 按照窗口大小滑动，生成多个时间序列图
        for j in range(0, len(fund_data) - window_size + 1, window_size):
            # 截取当前窗口的数据
            fund_data_sampled = fund_data.iloc[j:j + window_size]
            # 获取窗口结束日期作为文件名的一部分
            date = fund_data.iloc[j + window_size - 1]['transaction_date']
            # 创建图像，设置图像大小
            plt.figure(figsize=(16, 9))
            # 绘制申购金额曲线
            plt.plot(fund_data_sampled['transaction_date'], fund_data_sampled['apply_amt'], label='Apply Amount', linewidth=3.5)
            # 绘制赎回金额曲线
            plt.plot(fund_data_sampled['transaction_date'], fund_data_sampled['redeem_amt'], label='Redeem Amount', linewidth=3.5)
            # 设置x轴和y轴标签
            plt.xlabel('Date')
            plt.ylabel('Amount')
            plt.legend()
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            os.makedirs(save_path + f"{fund_code}", exist_ok=True)
            plt.savefig(save_path + f"/{fund_code}/{fund_code}_{str(date).split(' ')[0]}.jpg", dpi=60)
            plt.close()
        print(fund_code)