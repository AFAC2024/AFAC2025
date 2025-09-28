import pandas as pd
import numpy as np
import os
import requests


class FundPosition:
    """
    基金持仓信息获取类
    用于获取基金的股票和债券持仓信息
    """
    def __init__(self):
        # 数据存储根路径
        self.root_path = "Data/unprocessed_data"
        # 基金代码列表
        self.FUND_CODE_LIST = [86,192,385,402,965,1016,1316,1338,1407,1480,50027,100050,160717,161024,
        161028,164402,164906,166016,168204,530028]
    
    def get_public_dates(self, fund_code):
        """
        获取基金持仓公开日期列表，是获取持仓信息的先决要求
        参数:
            fund_code (str): 基金代码
        返回:
            list: 持仓公开日期列表
        """
        params = (
            ('FCODE', fund_code),
            ('OSVersion', '14.3'),
            ('appVersion', '6.3.8'),
            ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.3.6'),
            ('version', '6.3.8'),
        )
        url = 'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNIVInfoMultiple'
        headers = {
            'User-Agent': 'EMProjJijin/6.2.8 (iPhone; iOS 13.6; Scale/2.00)',
            'GTOKEN': '98B423068C1F4DEF9842F82ADF08C5db',
            'clientInfo': 'ttjj-iPhone10,1-iOS-iOS13.6',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'fundmobapi.eastmoney.com',
            'Referer': 'https://mpservice.com/516939c37bdb4ba2b1138c50cf69a2e1/release/pages/FundHistoryNetWorth',
        }
        json_response = requests.get(
            url,
            headers=headers,
            params=params).json()
        if json_response['Datas'] is None:
            return []
        return json_response['Datas']
    def get_inverst_postion(self, code, date=None):
        """
        获取基金在指定日期的持仓信息
        参数:
            code (str): 基金代码
            date (str, optional): 指定日期，格式为'YYYY-MM-DD'
        返回:
            tuple: (债券持仓列表, 股票持仓列表)
        """
        EastmoneyFundHeaders = {
            'User-Agent': 'EMProjJijin/6.2.8 (iPhone; iOS 13.6; Scale/2.00)',
            'GTOKEN': '98B423068C1F4DEF9842F82ADF08C5db',
            'clientInfo': 'ttjj-iPhone10,1-iOS-iOS13.6',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'fundmobapi.eastmoney.com',
            'Referer': 'https://mpservice.com/516939c37bdb4ba2b1138c50cf69a2e1/release/pages/FundHistoryNetWorth',
        }
        params = [
            ('FCODE', code),
            ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('OSVersion', '14.3'),
            ('appType', 'ttjj'),
            ('appVersion', '6.2.8'),
            ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
            ('plat', 'Iphone'),
            ('product', 'EFund'),
            ('serverVersion', '6.2.8'),
            ('version', '6.2.8'),
        ]
        if date is not None:
            params.append(('DATE', date))
        params = tuple(params)

        response = requests.get('https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition',
                                headers=EastmoneyFundHeaders, params=params)
        json_data = response.json()['Datas']
        bond_list = []
        stock_list = []
        # 持仓债券信息提取
        if json_data['fundboods'] != []:
            for i,zq in enumerate(json_data['fundboods']):
                bond_info = {'债券名称':zq['ZQMC'],"持仓占比":zq['ZJZBL']}
                bond_list.append(bond_info)
                # 只取前五的持仓债券
                if i >= 5:
                    break
        # 持仓股票信息提取
        if json_data['fundStocks'] != []:
            for i,stock in enumerate(json_data['fundStocks']):
                stock_info = {'股票名称':stock['GPJC'],"持仓占比":stock['JZBL']}
                stock_list.append(stock_info)
                # 只取前五的持仓股票
                if i >= 5:
                    break
        return bond_list,stock_list
    
def fund_position():
    """
    主函数：获取所有基金的持仓信息并保存到CSV文件
    遍历基金代码列表，获取每只基金的持仓信息，并保存到对应的CSV文件中
    """
    da = FundPosition()
    for fund_code in da.FUND_CODE_LIST:
        # 格式化基金代码为6位数字格式
        code = "0"*(6-len(str(fund_code)))+str(fund_code)
        # 获取基金公开持仓日期
        public_dates = da.get_public_dates(code)
        # 遍历全部公开日期，获取该日期公开的持仓信息
        fund_info = []
        for date in public_dates:
            # 较早的数据不需要，设置时间过滤条件
            if date<='2024-03-31':
                break
            print(f'正在获取 {date} 的持仓信息......')
            bond_list,stock_list = da.get_inverst_postion(code, date=date)
            fund_info.append(
                {
                    "日期":date,
                    "债券持仓":bond_list,
                    "股票持仓":stock_list,
                }
            )
        print(f'{date} 的持仓信息获取成功')
        fund_info = pd.DataFrame(fund_info)
        # 创建持仓信息目录（如果不存在）
        if not os.path.exists(da.root_path+"/持仓信息"):
            os.mkdir(da.root_path+"/持仓信息")
        # 保存数据到CSV文件
        fund_info.to_csv(da.root_path + f"/持仓信息/{code}.csv")