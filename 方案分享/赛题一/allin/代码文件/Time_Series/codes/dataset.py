import torch.nn as nn
import torch
from torch.utils.data import Dataset,DataLoader
import pandas as pd
import numpy as np
from .utils import StandardScaler3D
from .config import CommonConfig

class FundDataset(Dataset):
    """
    基金数据集类，用于处理时间序列数据并提供给模型训练
    """
    def __init__(self,data_path,config,flag="train"):
        super().__init__()
        self.scaler = None
        # 读取基金数据
        data = pd.read_csv(data_path)
        # 获取不重复的基金代码列表
        fund_code_list = data.drop_duplicates('fund_code')['fund_code'].values.tolist()
        # 每只基金的历史数据
        fund_data_list = []
        # 顺序索引和基金代码的映射
        fund_code_map = {}
        # 处理每只基金的数据
        for i,fund_code in enumerate(fund_code_list):
            # 筛选当前基金的数据
            fund_data = data.loc[data['fund_code']==fund_code].copy()
            # 转换交易日期为datetime格式
            fund_data['transaction_date'] = pd.to_datetime(fund_data['transaction_date'], format='%Y%m%d')
            date = fund_data['transaction_date']
            # 重置索引
            fund_data.reset_index(drop=True, inplace=True)
            # 按交易日期排序
            fund_data = fund_data.sort_values(by='transaction_date')
            # 获取redeem_amt列的位置
            redeem_amt_index = fund_data.columns.get_loc("redeem_amt") + 1
            date_index = fund_data.columns.get_loc('transaction_date') + 1
            # 重新排列列的顺序，将特征列放在前面，日期列放在后面
            fund_data = fund_data[list(fund_data.columns[redeem_amt_index:]) + list(fund_data.columns[date_index:redeem_amt_index])]
            # 删除包含缺失值的行
            fund_data.dropna(inplace=True)    
            # 将数据转换为numpy数组并添加到列表中
            fund_data_list.append(fund_data.values)
            # 建立索引到基金代码的映射
            fund_code_map[i] = fund_code
        # 将所有基金数据转换为三维numpy数组 [基金数量, 时间步, 特征数量]
        fund_data_numpy = np.array(fund_data_list)
        # 训练集和验证集划分比例
        data_split = config.data_split
        train_len = int(fund_data_numpy.shape[1] * data_split[0])
        # 边界定义：[起始位置, 结束位置]
        border_0 = [0,train_len - config.seq_len]
        border_1 = [train_len,fund_data_numpy.shape[1]]
        # 标志到索引的映射
        flag_to_index = {"train":0,"val":1}
        # 数据归一化处理
        if config.norm:
            scaler = StandardScaler3D()
            # 用训练集数据拟合归一化参数
            scaler.fit(fund_data_numpy[:,border_0[0]:border_1[0],:])
            # 对所有数据进行归一化
            fund_data_numpy = scaler.transform(fund_data_numpy)
            self.scaler = scaler
        # 确定数据边界
        b0 = border_0[flag_to_index[flag]]
        b1 = border_1[flag_to_index[flag]]
        # 划分数据集
        splited_data = fund_data_numpy[:,b0:b1,:]
        
        self.data = splited_data
        self.fund_code_map = fund_code_map
        self.seq_len = config.seq_len
        self.pred_len = config.pred_len
        self.date = date
    def __len__(self):
        return self.data.shape[1] - self.seq_len - self.pred_len + 1
    def __getitem__(self, index):
        seq_start = index
        seq_end = seq_start + self.seq_len
        pre_start = seq_end
        pre_end = pre_start + self.pred_len
        
        seq = self.data[:,seq_start:seq_end,:]
        pre = self.data[:,pre_start:pre_end,:]
        return torch.from_numpy(seq).float(),torch.from_numpy(pre).float()

        
            

