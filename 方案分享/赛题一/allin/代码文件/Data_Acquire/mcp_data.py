"""
利用MCP工具获取数据代码
该MCP服务需要安装ollama，ollama中使用的模型为qwen3:8b
对应的MCP服务端文件代码在Data_Acquire/MCP/server.py中
"""
from fastmcp import Client
from openai import OpenAI
from typing import List,Dict
import asyncio
import json
import time
from tqdm import tqdm
import pandas as pd
import os
from datetime import datetime

class UserClient:
    """
    用户客户端类，用于与MCP服务进行交互
    """
    def __init__(self,mcp_script = "Data_Acquire/MCP/server.py"):
        #初始化mcp client
        self.mcp_client = Client(mcp_script)
        #初始化OpenAI client用于与大语言模型交互
        #需要启动ollama
        self.openai_client = OpenAI(
            base_url="http://127.0.0.1:11434/v1",
            api_key="None"
        )
        # 初始化对话消息历史，包含系统角色的初始提示
        self.msg = [
            {
                "role": "system",
                "content": "你是一个AI助手，需要借助相关工具来回答用户的问题。"
            }
        ]
        # 指定使用的模型名称
        self.model = "qwen3:8b"
    #准备工具
    async def prepare_tools(self):
        #准备MCP工具列表，将其转换为OpenAI工具调用所需的格式
        tools = await self.mcp_client.list_tools()
        """
        OpenAI工具要求传入的MCP工具格式为:
        {
            "type":"function",
            "function":{
                "name":"xxx",
                "description":"xxxxx",
                "input_schema":{}
            }
        }
        """
        tools = [
            {
                "type": "function",
                "function":{
                    "name":tool.name,
                    "description":tool.description,
                    "input_schema":tool.inputSchema
                }
            }
            for tool in tools
        ]
        return tools
    async def chat(self,messages:List[Dict]):
        """
        与AI模型进行对话，支持工具调用
        参数:
            messages (List[Dict]): 对话消息列表
        返回:
            tuple: (响应消息, 消息类型) - 消息类型为"message"或"tool_call"
        """
        async with self.mcp_client:
            tools = await self.prepare_tools()
            response = self.openai_client.chat.completions.create(
                model = self.model,
                messages=messages,
                tools=tools
            )
            #没有调用工具的情况，直接返回模型响应文本
            if response.choices[0].finish_reason != "tool_calls":
                return response.choices[0].message,"message"
            else:
                #调用工具并执行相应操作
                print("调用的工具名称为:",response.choices[0].message.tool_calls[0].function.name)
                print("传入的参数为:",response.choices[0].message.tool_calls[0].function.arguments)
                for tool_call in response.choices[0].message.tool_calls:
                    res = await self.mcp_client.call_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                return res,"tool_call"
    #用户对话
    async def user_loop(self):
        """
        用户交互循环，持续接收用户输入并返回AI响应
        """
        while True:
            query = input(">: ")
            user_msg = {
                "role":"user",
                "content":query
            }
            self.msg.append(user_msg)
            response_msg,msg_type = await self.chat(self.msg)
            if msg_type == "message":
                print(response_msg.content)
            else:
                print(response_msg)
                
    #获取市场相关信息
    async def get_market_info(self,content:str):
        """
        获取所需要的基金与市场相关信息
        参数:
            content (str): 查询内容
        返回:
            str: 获取到的文本信息(json文本)
        """
        user_msg = {
                "role":"user",
                "content":content
            }
        tmp_msg = self.msg.copy()
        tmp_msg.append(user_msg)
        print(tmp_msg)
        response_msg,msg_type = await self.chat(tmp_msg)
        if msg_type == "message":
            print(response_msg.content)
        else:
            text = response_msg.content[0].text
            print(text.encode('utf-8').decode('unicode_escape'))
            return text

class DataAcquire:
    """
    数据获取类，用于从各种数据源获取金融数据
    """
    def __init__(self):
        # 数据存储根路径
        self.root_path = "Data/unprocessed_data"
        # 基金代码列表，用于批量获取基金数据
        self.FUND_CODE_LIST = [86,192,385,402,965,1016,1316,1338,1407,1480,50027,100050,160717,161024,
        161028,164402,164906,166016,168204,530028]
    def save_mcp_data(self, text, file_name, path_name = None):
        """
        保存从MCP获取的数据为CSV文件
        参数:
            text (str): JSON格式的原始数据
            file_name (str): 保存的文件名（不含扩展名）
            path_name (str, optional): 保存路径，默认为None
        """
        data_dict = json.loads(text)
        data = data_dict['msg']
        data = pd.DataFrame(data)
        if path_name is not None:
            if not os.path.exists(path_name):
                os.mkdir(path_name)
        data.to_csv(f'{path_name}/{file_name}.csv',index=False)
    #MCP获取数据
    async def mcp_get_data(self):
        """
        通过MCP协议获取各类金融数据
        包括：上证指数历史数据、财经新闻、基金净值数据、基金排名数据等
        """
        user_cilent = UserClient()
        # #获取上证指数数据
        today = str(datetime.today().date())
        mcp_prompt = f"请获取上证指数，指数代码为sh000001的历史交易数据，开始日期为2024-4-8，结束日期为{today}"
        text = await user_cilent.get_market_info(mcp_prompt)
        self.save_mcp_data(text,"上证指数",self.root_path)
        
        #获取每日财经新闻
        mcp_prompt = f"请获取每日的财经新闻，开始日期为2024-4-8，结束日期为{today}"
        text = await user_cilent.get_market_info(mcp_prompt)
        self.save_mcp_data(text,"东方财富新闻摘要",self.root_path)
        
        #获取基金净值数据
        mcp_prompt = "请获取基金净值数据，基金代码为{}，开始日期为2024-4-8，结束日期为{}"
        for fund_code in self.FUND_CODE_LIST:
            text = await user_cilent.get_market_info(mcp_prompt.format("0"*(6-len(str(fund_code)))+str(fund_code),today))
            self.save_mcp_data(text,"0"*(6-len(str(fund_code)))+str(fund_code),self.root_path + "/net_values")
            
        #获取基金同类型排名数据
        mcp_prompt = "请获取基金的同类排名百分比历史数据，基金代码为{}，开始日期为2024-4-8，结束日期为{}"
        for fund_code in self.FUND_CODE_LIST:
            text = await user_cilent.get_market_info(mcp_prompt.format("0"*(6-len(str(fund_code)))+str(fund_code),today))
            self.save_mcp_data(text,"0"*(6-len(str(fund_code)))+str(fund_code),self.root_path + "/rank")


    
        
    

