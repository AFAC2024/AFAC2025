import requests
from openai import OpenAI
import json
import os

class MCPClient:
    def __init__(self, mcp_base_url="http://127.0.0.1:8080"):
        self.mcp_base_url = mcp_base_url
        self.client = OpenAI(
            api_key="sk-b157d2837ecf4af484079352c80c7978", 
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )

    def get_mcp_manifest(self):
        """获取MCP工具的manifest描述"""
        try:
            response = requests.get(f"{self.mcp_base_url}/mcp_manifest", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取MCP清单失败: {str(e)}")
            return None
    
    def call_mcp_tool(self, tool_name, params):
        """调用MCP工具接口"""
        endpoint = f"{self.mcp_base_url}/{tool_name}"
        try:
            response = requests.post(endpoint, json=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"调用MCP工具失败: {str(e)}")
            return {"error": str(e)}
    
    def process_user_input(self, user_input):
        """
        处理用户输入，动态解析是否需要调用MCP工具
        """
        mcp_manifest = self.get_mcp_manifest()
        if not mcp_manifest:
            return {"error": "无法获取MCP工具描述"}

        # 构建工具描述
        tools = [{
            "type": "function",
            "function": {
                "name": mcp_manifest["name"],
                "description": mcp_manifest["description"],
                "parameters": mcp_manifest["parameters"]
            }
        }]

        try:
            # 将用户输入发送给大模型解析
            response = self.client.chat.completions.create(
                model="qwen3-32b",
                messages=[{"role": "user", "content": user_input}],
                tools=tools,
                tool_choice="auto",
                extra_body={"enable_thinking": False}  # 添加这一行
            )
            
            # 检查是否需要调用MCP工具
            if response.choices and response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                if tool_call.function.name == mcp_manifest["name"]:
                    # 解析参数并调用MCP工具
                    tool_args = json.loads(tool_call.function.arguments)
                    return self.call_mcp_tool(mcp_manifest["api_endpoint"], tool_args)
            
            # 如果没有触发工具调用，返回原始响应
            return {"response": response.choices[0].message.content}
            
        except Exception as e:
            print(f"处理用户输入失败: {str(e)}")
            return {"error": str(e)}

if __name__ == "__main__":
    mcp_integration = MCPClient()
    
    data_path = './data/20250721_update/'
    user_input = f"请帮我对{data_path}目录下的数据添加特征"
    result = mcp_integration.process_user_input(user_input)
    print(f"处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
