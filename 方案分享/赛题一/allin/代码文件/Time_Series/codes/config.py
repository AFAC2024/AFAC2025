import torch.nn as nn
import pandas as pd
import numpy as np

class CommonConfig:
    def __init__(self):
        #数据集划分比例
        self.data_split = [0.987,0.013]
        #回看窗口长度
        self.seq_len = 30
        #预测窗口长度
        self.pred_len = 7
        #使用到的特征 (包含line_apply和line_redeem)
        self.fea_nums = 14
        #目标预测数
        self.target_nums = 2
        #基金数量
        self.fund_num = 20
        #是否启用归一化
        self.norm = True
        #学习率
        self.lr = 1e-2
        #训练轮次
        self.epochs = 100
        
        
class SimpleTMConfig:
    """
    属性:
        seq_len (int): 输入序列长度
        pred_len (int): 预测序列长度
        output_attention (bool): 是否输出注意力权重
        use_norm (bool): 是否使用归一化
        geomattn_dropout (float): GeomAttention层的dropout率
        alpha (float): GeomAttention的缩放因子
        kernel_size (int): 卷积核大小
        embed (str): 嵌入类型
        freq (str): 时间频率
        dropout (float): 通用dropout率
        d_model (int): 模型维度
        factor (int): 注意力因子
        requires_grad (bool): 是否需要梯度计算
        wv (str): 波形类型
        m (int): 参数m
        d_channel (int): 通道维度
        e_layers (int): 编码器层数
        d_ff (int): 前馈网络维度
        activation (str): 激活函数类型
    """
    
    def __init__(self, 
                 output_attention: bool = False,
                 use_norm: bool = True,
                 geomattn_dropout: float = 0.0,
                 alpha: float = 1.0,
                 kernel_size: int = None,
                 embed: str = 'timeF',
                 freq: str = 'd',
                 dropout: float = 0.0,
                 d_model: int = 32,
                 factor: int = 1,
                 requires_grad: bool = True,
                 wv: str = 'db1',
                 m: int = 6,
                 e_layers: int = 1,
                 d_ff: int = 64,
                 activation: str = 'gelu',
                 config = CommonConfig()):
        
        self.seq_len = config.seq_len
        self.pred_len = config.pred_len
        self.output_attention = output_attention
        self.use_norm = use_norm
        self.geomattn_dropout = geomattn_dropout
        self.alpha = alpha
        self.kernel_size = kernel_size
        self.embed = embed
        self.freq = freq
        self.dropout = dropout
        self.d_model = d_model
        self.factor = factor
        self.requires_grad = requires_grad
        self.wv = wv
        self.m = m
        self.dec_in = config.fea_nums
        self.e_layers = e_layers
        self.d_ff = d_ff
        self.activation = activation
        

