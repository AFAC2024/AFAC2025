import pandas as pd
import numpy as np
import markdown
import asyncio
import os
import inspect   
from typing import Optional, Callable
from datetime import datetime
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

class Prompt:
    """
    提示词构建类
    """
    def __init__(self,root_path="Data/unprocessed_data"):
        # root_path (str): 需要读取的数据的根路径
        self.root_path = root_path
        # 读取基金申购赎回数据
        self.apply_redeem = pd.read_csv(f"{root_path}/fund_apply_redeem_series.csv")
        # 读取上证指数数据
        self.stock_index = pd.read_csv(f"{root_path}/上证指数.csv")
        # 读取东方财富新闻摘要数据
        self.news = pd.read_csv(f"{root_path}/东方财富新闻摘要.csv")
        # 处理各类数据
        self._process_apply_redeem()
        self._process_stock_index()
        self._process_news()
        # 计算数据长度（用于进度条显示）
        self.len = len(self.apply_redeem.loc[self.apply_redeem['fund_code']==86]) - 2
    
    def _process_apply_redeem(self):
        """
        处理基金申购赎回数据
        """
        # 重命名列名
        self.apply_redeem.columns = ['fund_code','date','apply_amt','redeem_amt',
                                     'uv_key_page_1','uv_key_page_2','uv_key_page_3']
        # 只保留需要的列
        self.apply_redeem = self.apply_redeem[['fund_code','date','apply_amt','redeem_amt']]
        # 将日期列转换为datetime格式
        self.apply_redeem['date'] = pd.to_datetime(self.apply_redeem['date'],format="%Y%m%d")
        # 过滤掉未来日期的数据
        today = datetime.now().strftime("%Y-%m-%d")
        self.apply_redeem = self.apply_redeem.loc[self.apply_redeem['date']<=today]
    def _process_stock_index(self):
        """
        处理上证指数数据
        """
        # 将日期列转换为datetime格式
        self.stock_index['date'] = pd.to_datetime(self.stock_index['date'])
    def _process_news(self):
        """
        处理新闻数据
        """
        # 将日期列转换为datetime格式
        self.news['date'] = pd.to_datetime(self.news['date'])
        # 按日期排序
        self.news.sort_values(by=['date'],inplace=True)
    def _process_review(self,review_data,str_fund_code):
        """
        特殊基金股吧评论数据的日期的处理（补全缺失年份）
        参数:
            review_data (DataFrame): 原始股吧评论数据
            str_fund_code (str): 基金代码字符串
        返回:
            DataFrame: 处理后的股吧评论数据
        """
        # 特殊基金代码的日期处理逻辑（这些基金的股吧评论文件中日期缺失了年份）
        if str_fund_code == "001338" or str_fund_code == "100050" or str_fund_code=="164906":
            data = review_data['评论时间']
            date_results = []
            change_flag = 0
            for d in data:
                month, day_time = d.split("-", 1)
                day, time = day_time.split(" ", 1)
                month = int(month)
                day = int(day)
                tmp_date = '2025' + '-' + str(month) + '-' + str(day)
                # 判断年份，处理跨年情况
                if month == 12 or change_flag == 1:
                    change_flag = 1
                    tmp_date = '2024' + '-' + str(month) + '-' + str(day)
                # 过滤掉过早的数据
                if pd.to_datetime(tmp_date) < pd.to_datetime('2024-4-8'):
                    break
                date_results.append(tmp_date)
            # 统一用2023-12-1补全其余数据，之后可以被筛选掉
            for i in range(len(review_data) - len(date_results)):
                date_results.append('2023-12-1')
            review_data['评论时间'] = date_results
        # 重命名列并转换日期格式
        review_data.columns = ['review','date']
        review_data['date'] = pd.to_datetime(review_data['date'])
        # 过滤掉2024年4月8日之前的数据
        review_data = review_data[review_data['date'] >= pd.to_datetime('2024-04-08')].copy()
        review_data['date'] = review_data['date'].dt.date
        review_data['date'] = pd.to_datetime(review_data['date'])
        return review_data
        
    
    def build_prompt(self,fund_code):
        """
        构建基金分析提示词
        参数:
            fund_code (int): 基金代码
        生成:
            tuple: (提示词字符串, 日期)
        """
        # 格式化基金代码为6位字符串
        str_fund_code = "0" * (6 - len(str(fund_code))) + str(fund_code)
        # 获取基金申购赎回数据
        fund_apply_redeem = self.apply_redeem[self.apply_redeem['fund_code']==fund_code]
        fund_apply_redeem.reset_index(drop=True,inplace=True)

        # 获取基金净值信息
        net_value = pd.read_csv(f"{self.root_path}/net_values/{str_fund_code}.csv")
        net_value['date'] = pd.to_datetime(net_value['date'])
         # 合并各类数据
        data = pd.merge(fund_apply_redeem,self.stock_index,on=['date'],how='left')
        data = pd.merge(data,self.news,on=['date'],how='left')
        data = pd.merge(data,net_value,on=['date'],how='left')
        # 用前一个值填充缺失值
        data.ffill(inplace=True)
        # data.to_excel("data.xlsx")  
        # 获取基金描述文本
        file_path = f"{self.root_path}/基金描述/{str_fund_code}.html.md" 
        with open(file_path, "r", encoding="utf-8") as file:
            fund_info = file.read()
        # 获取基金持仓信息
        position_info = pd.read_csv(f"{self.root_path}/持仓信息/{str_fund_code}.csv",usecols=[1,2,3])
        position_info = position_info.to_dict("records")
        # 获取股吧信息
        import csv
        review_data = pd.read_csv(f'{self.root_path}/股吧/list,of{str_fund_code}.csv')
        review_data.dropna(inplace=True)
        review_data = self._process_review(review_data,str_fund_code)
        # 设置分析时间窗口为3天
        time_delta = 3
        for i in range(len(data)-time_delta + 1):
            # 获取当前时间窗口的数据
            data_range = data.iloc[i:i+time_delta,:]
            # 获取当前时间窗口内的股吧评论
            review = review_data[(review_data['date']>=data_range.iloc[0]['date']) & (review_data['date']<=data_range.iloc[-1]['date'])]
            prompt = f"""你的任务是对提供的基金相关信息进行综合分析，生成摘要，并分析这些信息对基金未来7天申购量和赎回量的影响，特别注意时间范围问题，不能利用到超出当前时间范围的数据。
请仔细阅读以下信息：
<当前信息日期范围>
从{data_range.iloc[0]['date']}到{data_range.iloc[-1]['date']}
</当前信息日期范围>
<基金描述>
{fund_info}
</基金描述>
<基金持仓信息>
{position_info}
</基金持仓信息>
<过去三天的宏观市场新闻>
{data_range[['date','summary']].to_dict('records')}
</过去三天的宏观市场新闻>
<基金申购量>
{data_range[['date','apply_amt']].to_dict('records')}
</基金申购量>
<基金赎回量>
{data_range[['date','redeem_amt']].to_dict('records')}
</基金赎回量>
<基金单位净值和增长率>
{data_range[['date','net_asset_value','growth_rate']].to_dict('records')}
</基金单位净值和增长率>
<上证指数收盘价和成交量>
{data_range[['date','close','volume']].to_dict('records')}
</上证指数收盘价和成交量>
<可能存在的基金股吧评论>
{review if len(review)>0 else '无'}
</可能存在的基金股吧评论>
在进行分析时，请按照以下步骤：
1. 对这些信息进行综合考量，分析它们如何相互作用以及对基金的申购和赎回情况可能产生的影响。
2. 其中如果有重复的信息，那说明是非交易日复制的上一个最近交易日的信息。
3. 对于<可能存在的基金股吧评论></可能存在的基金股吧评论>中的内容，要注意有些内容可能是其他无关基金的广告或其他明显意义的简单公告标题，遇到这些内容需要忽略。
请在<summary>标签中生成客观信息摘要，不要加入过多的主观观点(比如对未来可能的影响)，摘要简洁明了(少于400个中文字)
<summary>
[在此生成生成信息摘要]
</summary>
"""
            yield prompt,data_range.iloc[-1]['date']
# 加载模型和tokenzier
model_name = "Qwen3-4B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
def main(prompt: str):
    """
    使用大语言模型生成基金分析摘要
    参数:
        prompt (str): 输入提示词
    返回:
        str: 模型生成的内容
    """
    prompt = prompt
    messages = [
        {"role":"system","content":"你是一个基金分析助手/"},
        {"role": "user", "content": prompt}
    ]
    # 应用chat模板
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )
    # 编码输入并生成响应
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=32768
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 

    try:
        index = len(output_ids) - output_ids[::-1].index(151668)
    except ValueError:
        index = 0
     # 解码生成的内容
    thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
    content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
    print(content)
    return content

def summary_data(existed_data=False):
    """
    生成基金摘要数据的主函数，供data_acquire_main.py调用
    参数:
        existed_data (bool): 是否已有部分数据，默认为False
    """
    # 数据保存路径
    save_path = "Data/summary_data"
    FUND_CODES = [86,192,385,402,965,1016,1316,1338,1407,1480,50027,100050,160717,161024,
        161028,164402,164906,166016,168204,530028]
    prompt_class = Prompt()
    # 如果没有已有数据，则从头开始生成
    if existed_data == False:
        for fund_code in FUND_CODES:
            result = []
            cnt = 0
            # 遍历构建的提示词并生成响应
            for prompt,date in tqdm(prompt_class.build_prompt(fund_code),total=prompt_class.len):
                response = main(prompt)
                result.append({"date":date,"response":response})
                # 每50条数据保存一次中间结果
                if cnt % 50 == 1:
                    print(response)
                    df = pd.DataFrame(result)
                    df.to_csv(f'{save_path}/{fund_code}_{cnt}.csv',index=False)
                cnt += 1
            # 保存最终结果
            df = pd.DataFrame(result)
            df.to_csv(f'{save_path}/{fund_code}.csv',index=False)
    else:
        # 如果已有部分数据，则只生成新增数据
        for fund_code in FUND_CODES:
            exist_data = pd.read_csv(f"{save_path}/{str(fund_code)}.csv")
            last_data = pd.to_datetime(exist_data.iloc[-1]['date'])
            result = []
            cnt = 0
            # 只处理新数据
            for prompt,date in tqdm(prompt_class.build_prompt(fund_code),total=prompt_class.len):
                if pd.to_datetime(date) > last_data:
                    print(date)
                    response = main(prompt)
                    result.append({"date":date,"response":response})
            df = pd.DataFrame(result)
            # 合并新旧数据
            if len(df) != 0:
                df['date'] = pd.to_datetime(df['date']).dt.date
                exist_data['date'] = pd.to_datetime(exist_data['date']).dt.date
                final_data = pd.concat([exist_data, df])
                final_data.to_csv(f'{save_path}/{fund_code}.csv', index=False)
            else:
                print("所有数据均存在")
        
    