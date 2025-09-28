import torch.nn as nn
import torch
from torch.utils.data import DataLoader
import pandas as pd
import numpy as np
from Time_Series.codes.config import CommonConfig,SimpleTMConfig
from Time_Series.codes.dataset import FundDataset
from tqdm import tqdm
from Time_Series.codes.utils import wmape,pd_out_func
import matplotlib.pyplot as plt
from Time_Series.codes.SimpleTM.SimpleTM import SimpleTMModel
from Time_Series.codes.utils import pd_out_func,StandardScaler3D
import csv
import os

class DeepLearning:
    """
    时间序列模型训练和预测类
    
    参数说明:
    data_path: 数据路径
    model: 模型类
    common_config: 所有模型通用设置
    plt_show:是否展示验证集上的预测结果
    save_val_wmape:是否保存验证集上的wmape结果
    """
    def __init__(self, data_path, model, common_config, model_name, 
                 plt_show = False, save_val_wmape = False):
        super().__init__()
        # 模型设备配置（GPU或CPU）
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.data_path = data_path
        self.model = model
        # 将模型移至指定设备
        self.model.to(self.device)
        self.common_config = common_config
        self.plt_show = plt_show
        self.save_val_wmap = save_val_wmape
        self.model_name = model_name
        # 定义优化器和学习率调整策略
        self._optimizer_and_scheduler()
    def _optimizer_and_scheduler(self):
        """
        配置优化器
        """
        optimizer = torch.optim.AdamW(self.model.parameters(),lr=self.common_config.lr)
        self.optimizer = optimizer
        
    def train(self):
        """
        模型训练函数
        """
        print(self.model_name)
        # 初始化最佳WMAPE为无穷大
        best_wmape = float('inf')
        # 创建训练数据集和数据加载器
        train_dataset = FundDataset(self.data_path,self.common_config,"train")
        train_dataloader = DataLoader(train_dataset,batch_size=1,shuffle=True)
        train_steps = len(train_dataloader)
        # 学习率调整策略
        lr_scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer = self.optimizer,
                                            steps_per_epoch = train_steps,
                                            pct_start = 0.3,
                                            epochs = self.common_config.epochs,
                                            max_lr = self.common_config.lr)
        self.lr_scheduler = lr_scheduler
        # 开始训练循环
        for i in range(self.common_config.epochs):
            epoch_loss = 0
            count = 0
            self.model.train()
            # 遍历训练数据
            for batch_x,batch_y in tqdm(train_dataloader):
                # 去除批次维度并移至设备
                batch_x = batch_x.squeeze(0).to(self.device)
                batch_y = batch_y.squeeze(0).to(self.device)
                _,loss = self.model(batch_x,batch_y)
                
                epoch_loss += loss.item()
                count += 1
                # 梯度清零、反向传播、参数更新、学习率调整
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                self.lr_scheduler.step()
            print("epoch:",i,"loss:",epoch_loss/count)
            # 验证模型并获取平均WMAPE
            avg_wmape = self.val()
            # 如果当前WMAPE更好，则保存模型
            if avg_wmape < best_wmape:
                best_wmape = avg_wmape
                torch.save(self.model.state_dict(), f'Time_Series/saves/best_model_{self.model_name}.pth')  # 保存模型参数到文件
                print(f"New best model saved with max WMAPE: {best_wmape}")
    def val(self):
        """
        模型验证函数
        返回:
            float: 平均WMAPE值
        """
        # 创建验证数据集和数据加载器
        val_dataset = FundDataset(self.data_path,self.common_config,"val")
        val_dataloader = DataLoader(val_dataset,batch_size=1,shuffle=False)
        self.model.eval()
        with torch.no_grad():
            WMAPE_list = []
            # 遍历验证数据
            for i, (batch_x,batch_y) in enumerate(val_dataloader):
                # 去除批次维度并移至设备
                batch_x = batch_x.squeeze(0).to(self.device)
                batch_y = batch_y.squeeze(0).to(self.device)
                # 模型前向传播
                out,_ = self.model(batch_x,batch_y)
                # 转回numpy
                out = out.cpu().detach().numpy()
                batch_y = batch_y.cpu().detach().numpy()
                # 反归一化
                out = val_dataset.scaler.inverse_transform(out)
                batch_y = val_dataset.scaler.inverse_transform(batch_y)
                # 取出对应特征
                out = out[:,:,-self.common_config.target_nums:]
                batch_y = batch_y[:,:,-self.common_config.target_nums:]
                # apply_amt_pred和redeem_amt_pred维度是[20,7],分别表示20只基金未来7天的apply_amt和redeem_amt的预测结果
                apply_amt_pred = out[:,:,0]
                redeem_amt_pred = out[:,:,1]
                # apply_amt_true和redeem_amt_true维度是[20,7],分别表示20只基金未来7天的apply_amt和redeem_amt的真实结果
                apply_amt_true = batch_y[:,:,0]
                redeem_amt_true = batch_y[:,:,1]
                # 如果需要展示预测结果，则在最后一个批次绘制图表
                if self.plt_show:
                    if i == len(val_dataloader)-1:
                        self.plot_fund_predictions(apply_amt_pred, apply_amt_true, redeem_amt_pred, redeem_amt_true)
                # 计算WMAPE
                WMAPE_apply = wmape(apply_amt_pred,apply_amt_true)
                WMAPE_redeem = wmape(redeem_amt_pred,redeem_amt_true)
                WMAPE_list.append(WMAPE_apply*0.5+WMAPE_redeem*0.5)
            # 保存基金代码映射和最后日期
            self.fund_code_map = val_dataset.fund_code_map
            date = val_dataset.date
            date.reset_index(drop=True, inplace=True)
            self.last_date = date.iloc[-1]
            # 输出最大、最小、平均WMAPE
            max_wmape = max(WMAPE_list)
            min_wmape = min(WMAPE_list)
            avg_wmape = sum(WMAPE_list) / len(WMAPE_list)
            print("最大WMAPE:",max_wmape)
            print("最小WMAPE:",min_wmape)
            print("平均WMAPE:",avg_wmape)
            # 如果需要保存验证WMAPE结果
            if self.save_val_wmap:
                # 文件名
                filename = f'model_logs/{self.model_name}_seq{self.common_config.seq_len}_pred{self.common_config.pred_len}_epoch{self.common_config.epochs}_lr{self.common_config.lr}.csv'
                file_exists = os.path.isfile(filename)
                with open(filename, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    if not file_exists:
                        # 如果文件不存在，则写入表头
                        writer.writerow(['Max_WMAPE', 'Min_WMAPE', 'Avg_WMAPE'])
                    writer.writerow([max_wmape, min_wmape, avg_wmape])
            # 如果需要展示WMAPE柱状图
            if self.plt_show:
                plt.bar(range(len(WMAPE_list)),WMAPE_list)
                plt.show()
            return avg_wmape
    def plot_fund_predictions(self,apply_pred, apply_true, redeem_pred, redeem_true, num_funds=20, pred_len=7):
        """
        绘制每只基金的申购金额和赎回金额预测与真实值对比图
        参数:
            apply_pred (np.ndarray): 预测的申购金额，形状为 [num_funds, pred_len]
            apply_true (np.ndarray): 真实的申购金额，形状为 [num_funds, pred_len]
            redeem_pred (np.ndarray): 预测的赎回金额，形状为 [num_funds, pred_len]
            redeem_true (np.ndarray): 真实的赎回金额，形状为 [num_funds, pred_len]
            num_funds (int): 基金数量，默认为20
            pred_len (int): 预测时间步长度
        """
        fig, axes = plt.subplots(nrows=5, ncols=4, figsize=(20, 15))
        axes = axes.flatten()
        # 创建两个空的线条对象用于共享图例
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='blue', linestyle='--', label='Apply True'),
            Line2D([0], [0], color='blue', linestyle='-', label='Apply Pred'),
            Line2D([0], [0], color='orange', linestyle='--', label='Redeem True'),
            Line2D([0], [0], color='orange', linestyle='-', label='Redeem Pred')
        ]
        for i in range(num_funds):
            ax = axes[i]
            # 创建时间序列 x 轴
            x = range(pred_len)
            # 画出申购金额
            ax.plot(x, apply_true[i], label='Apply True', color='blue', linestyle='--')
            ax.plot(x, apply_pred[i], label='Apply Pred', color='blue')
            # 画出赎回金额
            ax.plot(x, redeem_true[i], label='Redeem True', color='orange', linestyle='--')
            ax.plot(x, redeem_pred[i], label='Redeem Pred', color='orange')
            # 设置标题和图例
            ax.set_title(f'Fund {i+1}')
            ax.grid(True)
        for j in range(num_funds, len(axes)):
            fig.delaxes(axes[j])
        fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1), fontsize=12)
        plt.tight_layout()
        plt.show()
    def get_predict_result(self,model_path,data_path):
        """
        得到未来7天的预测result.csv文件
        
        参数:
            model_path (str): 模型路径
            data_path (str): 数据路径
        """
        # 得到未来7天的预测result.csv文件
        model_name = "SimpleTM"
        common_config = CommonConfig()
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = SimpleTMModel(SimpleTMConfig())
        # 加载模型权重
        model.load_state_dict(torch.load(model_path))
        model.to(device)
        model.eval()
        # 读取数据
        data = pd.read_csv(data_path)
        fund_code_list = data.drop_duplicates('fund_code')['fund_code'].values.tolist()
        fund_data_list = []
        # 顺序索引和基金代码的映射
        fund_code_map = {}
        # 处理每只基金的数据
        for i,fund_code in enumerate(fund_code_list):
            fund_data = data.loc[data['fund_code']==fund_code].copy()
            # 转换日期格式
            fund_data['transaction_date'] = pd.to_datetime(fund_data['transaction_date'], format='%Y%m%d')
            date = fund_data['transaction_date']
            fund_data.reset_index(drop=True, inplace=True)
            fund_data = fund_data.sort_values(by='transaction_date')
            fund_data.dropna(inplace=True)         
            # 重新排列列顺序
            redeem_amt_index = fund_data.columns.get_loc("redeem_amt") + 1
            date_index = fund_data.columns.get_loc('transaction_date') + 1
            fund_data = fund_data[list(fund_data.columns[redeem_amt_index:]) + list(fund_data.columns[date_index:redeem_amt_index])] 
            fund_data_list.append(fund_data.values)
            fund_code_map[i] = fund_code
        # 转换为numpy数组
        fund_data_numpy = np.array(fund_data_list)
        # 训练集和验证集划分
        data_split = common_config.data_split
        train_len = int(fund_data_numpy.shape[1] * data_split[0])
        border_0 = [0,train_len - common_config.seq_len]
        border_1 = [train_len,fund_data_numpy.shape[1]]
        # 归一化处理
        if common_config.norm:
            scaler = StandardScaler3D()
            # 用训练集拟合归一化参数
            scaler.fit(fund_data_numpy[:,border_0[0]:border_1[0],:])
            # 归一化
            fund_data_numpy = scaler.transform(fund_data_numpy)
        # 选择最后seq_len条数据作为输入
        input_data = fund_data_numpy[:,-common_config.seq_len:,:]
        input_data = torch.from_numpy(input_data).float().to(device)
        # 模型预测
        output,loss = model(input_data,None)
        output = output.cpu().detach().numpy()
        # 反归一化
        output = scaler.inverse_transform(output)
        # 取出目标特征
        output = output[:,:,-common_config.target_nums:]
        # 获取最后日期并生成预测结果文件
        last_date = date.iloc[-1]
        pd_out_func(fund_code_map,last_date,output)
               
if __name__ == "__main__": 
    # 选择模型
    model_name = "SimpleTM"
    common_config = CommonConfig()
    model = SimpleTMModel(SimpleTMConfig())
    
    dl = DeepLearning(data_path='Data/train_set.csv',
                model=model,
                common_config=common_config,
                model_name=model_name,
                plt_show=False,
                save_val_wmape=False)

    # 训练模型,当is_train为True时，训练模型
    is_train = False
    if is_train:
        dl.train()
        
    # 模型推理获得结果,当reproduction为True时，使用先前训练好的模型权重，可以复现推理结果
    # 当reproduction为False时，使用新训练的模型权重
    reproduction = True
    if reproduction:
        model = "Time_Series/trained_model/best_model_SimpleTM.pth"
    else:
        model = "Time_Series/saves/best_model_SimpleTM.pth"
    # 获取预测结果predict_result.csv
    dl.get_predict_result(model_path=model,data_path='Data/train_set.csv')