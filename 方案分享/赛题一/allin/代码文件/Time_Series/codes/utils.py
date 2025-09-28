import numpy as np
import pandas as pd
import torch
import torch.nn as nn

class StandardScaler3D:
    """
    三维数据标准化器 (num_samples, seq_len, num_features)
    在时间维度(seq_len)上独立进行标准化
    """
    def __init__(self):
        self.means = None
        self.stds = None
    
    def fit(self, data):
        # 计算每个样本每个特征的均值和标准差
        self.means = np.mean(data, axis=1, keepdims=True)
        self.stds = np.std(data, axis=1, keepdims=True)
        self.stds[self.stds == 0] = 1.0
        return self
    
    def transform(self, data):
        if self.means is None or self.stds is None:
            raise RuntimeError("Scaler has not been fitted yet. Call fit() first.")
        
        return (data - self.means) / self.stds
    
    def fit_transform(self, data):
        self.fit(data)
        return self.transform(data)
    
    def inverse_transform(self, normalized_data):
        if self.means is None or self.stds is None:
            raise RuntimeError("Scaler has not been fitted yet. Call fit() first.")
        return (normalized_data * self.stds) + self.means
    

def wmape(pred:np.ndarray, label:np.ndarray):
    #pred是numpy数组,维度是[20,7]表示20只基金未来7天的预测结果
    #label是numpy数组,维度是[20,7]表示20只基金未来7天的真实结果
    #对于每只基金
    wampei = []
    for i in range(len(pred)):
        pred_i = pred[i]
        label_i = label[i]
        #计算WMAPEi
        weights = label_i / np.sum(label_i)
        mape_i = np.abs((pred_i - label_i) / label_i)
        wampei.append(np.dot(mape_i,weights))
    wampei = np.array(wampei)
    #计算WMAPE
    fund_weights = np.sum(label,axis=1) / np.sum(label)
    WMAPE = np.dot(wampei,fund_weights) / pred.shape[0]
    return WMAPE



def pd_out_func(fund_code_map,last_date,pred):
    fund_code_map = fund_code_map
    next_7_days = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=7, freq='D')
    pd_out = pd.DataFrame(columns=['fund_code','transaction_date','apply_amt_pred','redeem_amt_pred'])
    for i in range(pred.shape[0]):
        fund_code = fund_code_map[i]
        apply_amt_pred = pred[i,:,0]
        redeem_amt_pred = pred[i,:,1]
        formatted_date = next_7_days.strftime('%Y%m%d')
        for j in range(7):
            pd_out = pd_out._append({'fund_code':fund_code,'transaction_date':formatted_date[j],
                                    'apply_amt_pred':apply_amt_pred[j],'redeem_amt_pred':redeem_amt_pred[j]},
                                   ignore_index=True)
    pd_out['transaction_date'] = pd_out['transaction_date'].astype('Int64')
    pd_out.to_csv("predict_result.csv",index=False)
    
class RevIN(nn.Module):
    def __init__(self, num_features: int, eps=1e-5, affine=True, subtract_last=False):
        """
        :param num_features: the number of features or channels
        :param eps: a value added for numerical stability
        :param affine: if True, RevIN has learnable affine parameters
        """
        super(RevIN, self).__init__()
        self.num_features = num_features
        self.eps = eps
        self.affine = affine
        self.subtract_last = subtract_last
        if self.affine:
            self._init_params()

    def forward(self, x, mode:str):
        if mode == 'norm':
            self._get_statistics(x)
            x = self._normalize(x)
        elif mode == 'denorm':
            x = self._denormalize(x)
        else: raise NotImplementedError
        return x

    def _init_params(self):
        # initialize RevIN params: (C,)
        self.affine_weight = nn.Parameter(torch.ones(self.num_features))
        self.affine_bias = nn.Parameter(torch.zeros(self.num_features))

    def _get_statistics(self, x):
        dim2reduce = tuple(range(1, x.ndim-1))
        if self.subtract_last:
            self.last = x[:,-1,:].unsqueeze(1)
        else:
            self.mean = torch.mean(x, dim=dim2reduce, keepdim=True).detach()
        self.stdev = torch.sqrt(torch.var(x, dim=dim2reduce, keepdim=True, unbiased=False) + self.eps).detach()

    def _normalize(self, x):
        if self.subtract_last:
            x = x - self.last
        else:
            x = x - self.mean
        x = x / self.stdev
        if self.affine:
            x = x * self.affine_weight
            x = x + self.affine_bias
        return x

    def _denormalize(self, x):
        if self.affine:
            x = x - self.affine_bias
            x = x / (self.affine_weight + self.eps*self.eps)
        x = x * self.stdev
        if self.subtract_last:
            x = x + self.last
        else:
            x = x + self.mean
        return x