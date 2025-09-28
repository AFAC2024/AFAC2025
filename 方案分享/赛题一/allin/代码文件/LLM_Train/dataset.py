from torch.utils.data import Dataset
import pandas as pd
import json

class GRPODataset(Dataset):
    def __init__(self,data_path,cot=False):
        super().__init__()
        with open(data_path,"r") as f:
            data = json.load(f)
        self.data = data
        self.SYSTEM_PROMPT = """你是一个金融新闻情感分析专家"""
        self.cot = cot

    def __len__(self):
        return len(self.data)
    def __getitem__(self, index):
        if self.cot==False:
            USER_PROMPT_PREFIX = """你的任务是对给定的金融新闻进行情感分析，并输出相应的情感标签。
请仔细阅读以下金融新闻：
<金融新闻>
{}
</金融新闻>
情感标签分为以下三种类型：积极、消极、中性，分别对应positive、negative、neutral。
请在<情感标签>标签中输出相应的情感标签(positive、negative、neutral中的一个)。
<情感标签></情感标签>/no_think"""
        else:
            USER_PROMPT_PREFIX = """你的任务是对给定的金融新闻进行情感分析，并输出相应的情感标签。
请仔细阅读以下金融新闻：
<金融新闻>
{}
</金融新闻>
情感标签分为以下三种类型：积极、消极、中性，分别对应positive、negative、neutral。
请在<情感标签>标签中输出相应的情感标签(positive、negative、neutral中的一个)。
<情感标签></情感标签>"""
        prompt = [
            {'role':'system','content':self.SYSTEM_PROMPT},
            {'role':'user','content':USER_PROMPT_PREFIX.format(self.data[index]['sentence'])}
        ]
        return {
            'prompt':prompt,
            'polarity':self.data[index]['polarity']
        }

