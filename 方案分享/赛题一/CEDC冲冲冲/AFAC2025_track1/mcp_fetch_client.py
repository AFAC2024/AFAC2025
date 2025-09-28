import json
import pandas as pd
from pydantic import BaseModel
from typing import Optional, Dict, List # 添加 List 类型提示
from contextlib import AsyncExitStack, asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client
import os
import logging
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from colorama import init, Fore, Style
import traceback # 用于更详细的错误追踪
init()  # 初始化 colorama

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义 lifespan 上下文管理器 (用于 FastAPI)
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 从配置文件加载服务器配置
        server_urls = client.load_server_config()
        print("Lifespan - 加载的服务器配置:", server_urls)
        # 连接到所有配置的服务器
        await client.connect_to_sse_server(server_urls)
        logger.info("Lifespan - MCP 服务器已连接")
    except Exception as e:
        logger.error(f"Lifespan - 启动失败: {e}")
        # 可以选择在这里 raise 或者让应用继续启动（但可能功能不全）
        # raise HTTPException(status_code=500, detail=f"Failed to start: {str(e)}")
    yield
    # 应用关闭时清理资源
    await client.cleanup()
    logger.info("Lifespan - 资源已清理")

# Define FastAPI app
app = FastAPI(lifespan=lifespan)

class MCPFetch:
    def __init__(self):
        # Initialize session and client objects
        self.sessions = {}  # 存储多个服务器的会话
        # self.exit_stack = AsyncExitStack() # 不在 __init__ 中使用
        self.server_tools = {}  # 存储每个服务器的可用工具
        self.config_path = os.path.join(os.path.dirname(__file__), 'servers_config.json')
        self.client = OpenAI(
            api_key="sk-b157d2837ecf4af484079352c80c7978", 
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        # 移除了在 __init__ 中直接调用异步方法 connect_to_sse_server 的代码
        # 连接将在 lifespan (FastAPI) 或 main (直接运行) 中处理
        # self.server_urls = self.load_server_config() # 这行也移除
        # self.connect_to_sse_server(self.server_urls) # 这行是错误的，因为它是异步的

    def load_server_config(self) -> Dict[str, str]:
        """从配置文件加载服务器配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 修改这里以适配新的配置文件结构
                return {name: server["url"] for name, server in config["mcpServers"].items()}
        except FileNotFoundError:
            logger.error(f"找不到配置文件: {self.config_path}")
            raise HTTPException(status_code=500, detail="Server configuration file not found")
        except json.JSONDecodeError:
            logger.error("配置文件格式错误")
            raise HTTPException(status_code=500, detail="Invalid server configuration format")

    async def validate_server_config(self, server_urls: dict) -> bool:
        """验证服务器配置是否有效"""
        if not server_urls:
            logger.error("服务器配置为空")
            return False
        for name, url in server_urls.items():
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                logger.error(f"服务器 {name} 的URL格式无效: {url}")
                return False
        return True

    async def connect_to_sse_server(self, server_urls: dict):
        """Connect to multiple MCP servers running with SSE transport"""
        # 验证配置
        if not await self.validate_server_config(server_urls):
            raise HTTPException(status_code=500, detail="Invalid server configuration")

        # 使用 AsyncExitStack 来管理所有服务器的连接生命周期
        self.exit_stack = AsyncExitStack() # 在每次连接时创建新的 exit_stack
        await self.exit_stack.__aenter__() # 进入 AsyncExitStack 上下文

        for server_name, server_url in server_urls.items():
            try:
                # 为每个服务器创建连接上下文
                streams_context = sse_client(url=server_url)
                # 使用主 exit_stack 管理 streams_context 的生命周期
                streams = await self.exit_stack.enter_async_context(streams_context)

                session_context = ClientSession(*streams)
                # 使用主 exit_stack 管理 session_context 的生命周期
                session = await self.exit_stack.enter_async_context(session_context)

                # 保存会话 (现在只保存 session 本身，因为 exit_stack 会处理清理)
                self.sessions[server_name] = session

                # 初始化连接
                await session.initialize()

                # 获取该服务器的可用工具
                logger.info(f"初始化 SSE 客户端 {server_name}...")
                response = await session.list_tools()

                # 保存工具列表
                self.server_tools[server_name] = response.tools

                # 打印该服务器的可用工具
                print(f"\n{Fore.GREEN}=== {server_name} 可用工具列表 ==={Style.RESET_ALL}")
                for tool in response.tools:
                    print(f"\n{Fore.CYAN}工具名称:{Style.RESET_ALL} {tool.name}")
                    print(f"{Fore.YELLOW}描述:{Style.RESET_ALL} {tool.description}")
                print(f"{Fore.BLUE}{'='*50}{Style.RESET_ALL}")
                logger.info(f"服务器 {server_name} 已连接，支持工具: {[tool.name for tool in response.tools]}")
            except Exception as e:
                logger.error(f"连接服务器 {server_name} 失败: {str(e)}")
                logger.error(f"详细错误堆栈: {traceback.format_exc()}") # 添加详细错误信息
                # 继续连接其他服务器，而不是立即终止
                continue

        if not self.sessions:
            # 如果没有服务器连接成功，则退出 exit_stack
            await self.exit_stack.__aexit__(None, None, None)
            raise HTTPException(status_code=500, detail="No servers connected successfully")

    async def cleanup(self):
        """Properly clean up all sessions and streams using AsyncExitStack"""
        if hasattr(self, 'exit_stack'):
             try:
                 # 退出 AsyncExitStack 上下文，它会自动清理所有通过 enter_async_context 添加的资源
                 await self.exit_stack.__aexit__(None, None, None)
                 logger.info("所有服务器连接已清理")
             except Exception as e:
                 logger.error(f"清理资源时出错: {str(e)}")
        # 清空会话和工具字典
        self.sessions.clear()
        self.server_tools.clear()

    # --- 修改后的 call_tools 方法 ---
    async def call_tools(self, tool_name: str, tool_args) -> str:
        """Process a query using the appropriate server based on tool name"""
        if not self.sessions:
            raise HTTPException(status_code=500, detail="No active sessions")

        # 查找哪个服务器提供了该工具
        server_name = None
        session = None
        for srv_name, tools in self.server_tools.items():
            if any(tool.name == tool_name for tool in tools):
                server_name = srv_name
                session = self.sessions.get(srv_name)
                break

        if not server_name or not session:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found in any connected server")

        # 解析工具参数
        try:
            parsed_tool_args = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
        except json.JSONDecodeError as e:
            logger.error(f"工具参数 JSON 解析失败: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid tool arguments JSON: {str(e)}")

        try:
            # 执行工具调用
            logger.info(f"在服务器 {server_name} 上调用工具: {tool_name}，参数: {parsed_tool_args}")
            result = await session.call_tool(tool_name, parsed_tool_args)
            
            # --- 修改后的错误检查和内容提取逻辑 ---
            logger.debug(f"收到 MCP 工具调用结果对象: {result}") # 打印原始结果对象，便于调试
            
            # 1. 检查是否有明确的 isError 标志 (如果存在)
            # 注意：isError 可能是布尔值或不存在
            if getattr(result, 'isError', False): 
                 # 2. 如果 isError 为 True，尝试获取错误信息
                 # 错误信息可能在 error 属性、message 属性或其他地方
                 error_msg = "未知工具执行错误"
                 if hasattr(result, 'error') and result.error:
                     # 如果有 .error 属性且不为空
                     if hasattr(result.error, 'message'):
                         error_msg = result.error.message
                     else:
                         error_msg = str(result.error)
                 elif hasattr(result, 'message') and result.message:
                     # 如果有 .message 属性且不为空
                     error_msg = result.message
                 logger.error(f"工具 {tool_name} 在服务器 {server_name} 上执行返回错误 (isError=True): {error_msg}")
                 raise HTTPException(status_code=500, detail=f"Tool {tool_name} execution error: {error_msg}")

            # 3. 如果没有 isError 或 isError 为 False，尝试提取内容
            content = ""
            if hasattr(result, 'content') and result.content:
                # 遍历 content 列表，查找 TextContent
                for item in result.content:
                    if hasattr(item, 'text'): # 检查是否有 text 属性
                        content += item.text
                    # 可以在这里添加对其他类型内容的处理，如 ImageContent 等
                if content:
                    logger.info(f"工具执行结果 (前100字符): {content[:100]}...")
                else:
                    logger.warning(f"工具 {tool_name} 返回了 content，但其中没有找到文本内容。")
            else:
                 logger.warning(f"工具 {tool_name} 返回的响应中没有 content 或 content 为空。")
                 # 检查是否有其他信息，例如 isError=False 但也没有内容
                 # 这种情况可能表示工具执行了但没有输出，或者返回了非文本内容
                 content = "工具执行完成，但未返回可识别的文本内容。"

            logger.info(f"在服务器 {server_name} 上成功调用工具: {tool_name}")
            return content

        except HTTPException: # 重新抛出已知的 HTTP 异常
            raise
        except Exception as e:
            logger.error(f"工具调用失败: {str(e)}", exc_info=True) # 添加 exc_info=True 以获取完整堆栈跟踪
            raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")
    # --- 修改结束 ---

    async def process_user_query(self, query: str, model: str = "qwen3-32b", temperature: float = 0.7):
        """处理用户查询，使用 OpenAI 客户端发送请求"""
        try:
            # 准备可用工具列表
            available_tools = []
            for server_name, tools in self.server_tools.items():
                for tool in tools:
                    available_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    })

            # 创建请求参数
            request_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个有用的AI助手，可以使用提供的工具来帮助用户。"},
                    {"role": "user", "content": query}
                ],
                "temperature": temperature,
                "extra_body": {"enable_thinking": False}
            }

            # 只有当available_tools非空时才添加tools参数
            if available_tools:
                request_params["tools"] = available_tools
                request_params["tool_choice"] = "auto"

            # 发送请求到 OpenAI API
            # 注意：这里的 OpenAI SDK 调用是同步的，可能会阻塞事件循环。
            # 在生产环境中，考虑使用异步 HTTP 客户端或在执行器中运行。
            response = self.client.chat.completions.create(**request_params)

            # 处理响应
            message = response.choices[0].message
            logger.debug(f'OpenAI API 响应: {response}')

            # 检查是否有工具调用
            if message.tool_calls:
                tool_call_results = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = tool_call.function.arguments
                    logger.info(f"LLM 请求调用工具: {tool_name}, 参数: {tool_args}")
                    # 调用相应的工具
                    try:
                        result = await self.call_tools(tool_name, tool_args)
                        tool_call_results.append({
                            "tool_call_id": tool_call.id,
                            "result": result # result 现在已经是字符串
                        })
                    except Exception as tool_error:
                         # 如果工具调用失败，将错误信息作为结果返回给模型
                         logger.error(f"工具 {tool_name} 调用失败: {tool_error}")
                         tool_call_results.append({
                            "tool_call_id": tool_call.id,
                            "result": f"调用工具 {tool_name} 时发生错误: {str(tool_error)}"
                         })

                # 继续与模型对话，提供工具调用结果
                # 注意：这里的 OpenAI SDK 调用也是同步的。
                follow_up_response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是一个有用的AI助手，可以使用提供的工具来帮助用户。"},
                        {"role": "user", "content": query},
                        message.model_dump(), # 确保消息格式正确传递
                        *[{"role": "tool", "tool_call_id": result["tool_call_id"], "content": result["result"]} for result in tool_call_results]
                    ],
                    temperature=temperature,
                    extra_body={"enable_thinking": False}
                )
                return follow_up_response.choices[0].message.content
            else:
                # 如果没有工具调用，直接返回响应内容
                return message.content
        except Exception as e:
            logger.error(f"处理用户查询时出错: {str(e)}", exc_info=True) # 添加 exc_info=True 以获取完整堆栈跟踪
            raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

class ToolCallRequest(BaseModel):
    tool_name: str
    tool_args: str  # 注意是字符串格式的 JSON

# Create an instance of the client *after* the class definition (用于 FastAPI)
client = MCPFetch()

@app.post("/call_tools/")
async def call_tools_endpoint(request: ToolCallRequest):
    result = await client.call_tools(request.tool_name, request.tool_args)
    return {"result": result}

# --- 用于循环爬取网站的 Main 函数示例 ---
async def main():
    # 创建 MCPFetch 实例
    mcp_integration = MCPFetch()
    try:
        print(f"{Fore.MAGENTA}--- 开始初始化 MCP 连接 ---{Style.RESET_ALL}")
        # 1. 加载服务器配置并连接 (这一步是关键，确保正确 await)
        server_urls = mcp_integration.load_server_config()
        await mcp_integration.connect_to_sse_server(server_urls)
        print(f"{Fore.MAGENTA}--- MCP 连接初始化完成 ---{Style.RESET_ALL}")

        # --- 定义要爬取的多个网站 URL ---
        # 这里使用一些简单的 HTTPBin 测试端点来模拟不同的网站
        # 你可以将这些 URL 替换为你实际想爬取的目标网站
        TEST_URLS = [
            "https://httpbin.org/html",      # 返回 HTML
            "https://httpbin.org/json",      # 返回 JSON
            "https://httpbin.org/xml",       # 返回 XML
            # "https://example.com",
            # "https://httpbin.org/get",
            # "https://httpbin.org/user-agent",
            # 添加更多 URL 来测试并发或顺序爬取
        ]
        # --- 定义结束 ---

        # --- 循环爬取每个网站 ---
        results: List[Dict[str, str]] = [] # 存储结果
        for i, url in enumerate(TEST_URLS, start=1):
            print(f"\n{Fore.BLUE}--- 开始处理第 {i} 个网站: {url} ---{Style.RESET_ALL}")
            try:
                # 构造一个查询，指示 LLM 使用 fetch 工具获取指定 URL 的内容
                # 这里可以根据需要调整提示词，例如指定返回格式
                user_input = f"""
                请使用 'fetch' 工具获取以下网址的内容:
                {url}
                如果内容是 HTML，请提取页面的标题和主要内容。
                如果内容是 JSON，请将其转换为易读的文本摘要。
                如果内容是 XML，请提取主要的数据节点。
                请简洁明了地总结你获取到的信息。
                """

                # 调用 process_user_query，它会通过 LLM 决定调用 fetch 工具并返回结果
                result = await mcp_integration.process_user_query(user_input, model="qwen3-32b", temperature=0.5)
                
                print(f"{Fore.GREEN}第 {i} 个网站 {url} 的处理结果:{Style.RESET_ALL}")
                print(result)
                print("-" * 40)
                
                # 将结果存储到列表中
                results.append({"url": url, "summary": result})

                # --- 可选：添加小延迟以避免对目标服务器造成过大压力 ---
                # import asyncio
                # await asyncio.sleep(1) 

            except Exception as e:
                # 捕获单个 URL 处理过程中的错误，避免整个循环中断
                logger.error(f"处理第 {i} 个网站 {url} 时出错: {e}")
                print(f"{Fore.RED}处理第 {i} 个网站 {url} 时出错: {e}{Style.RESET_ALL}")
                results.append({"url": url, "summary": f"处理出错: {e}"})
                continue # 继续处理下一个 URL
        # --- 循环结束 ---
        
        print(f"\n{Fore.MAGENTA}--- 所有网站处理完成，汇总结果 ---{Style.RESET_ALL}")
        for res in results:
            print(f"URL: {res['url']}\n摘要: {res['summary']}\n{'='*50}")

    except Exception as e:
        logger.error(f"Main 函数执行出错: {e}", exc_info=True)
        print(f"{Fore.RED}Main 函数执行出错: {e}{Style.RESET_ALL}")
    finally:
        # 确保资源被正确清理
        print(f"{Fore.MAGENTA}--- 开始清理资源 ---{Style.RESET_ALL}")
        await mcp_integration.cleanup()
        print(f"{Fore.MAGENTA}--- 资源清理完成 ---{Style.RESET_ALL}")

# --- 如何运行 ---
# 确保你的 if __name__ == "__main__": 部分是这样设置的来运行这个 main 函数：
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    # 如果要运行 FastAPI 应用，请注释掉上面两行，并取消下面的注释
    # import uvicorn
    # uvicorn.run(app, host="127.0.0.1", port=3002)
