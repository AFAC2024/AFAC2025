# -*- coding: utf-8 -*-
"""
LLM调用辅助模块
"""

import asyncio
import yaml
from ..config.llm_config import LLMConfig
from .fallback_openai_client import AsyncFallbackOpenAIClient

class LLMHelper:
    """LLM调用辅助类，支持同步和异步调用"""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config
        self.client = AsyncFallbackOpenAIClient(
            primary_api_key=config.api_key,
            primary_base_url=config.base_url,
            primary_model_name=config.model
        )
    
    async def async_call(self, prompt: str, system_prompt: str = None, max_tokens: int = None, temperature: float = None) -> str:
        """异步调用LLM"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {}
        if max_tokens is not None:
            kwargs['max_tokens'] = max_tokens
        else:
            kwargs['max_tokens'] = self.config.max_tokens
            
        if temperature is not None:
            kwargs['temperature'] = temperature
        else:
            kwargs['temperature'] = self.config.temperature
            
        try:
            response = await self.client.chat_completions_create(
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return ""
    def call(self, prompt: str, system_prompt: str = None, max_tokens: int = None, temperature: float = None) -> str:
        """同步调用LLM"""
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行（如在Jupyter中），使用nest_asyncio
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    return asyncio.run(self.async_call(prompt, system_prompt, max_tokens, temperature))
                except ImportError:
                    # 如果没有nest_asyncio，使用create_task
                    task = asyncio.create_task(self.async_call(prompt, system_prompt, max_tokens, temperature))
                    # 等待任务完成
                    import concurrent.futures
                    import threading
                    
                    result = None
                    exception = None
                    
                    def run_task():
                        nonlocal result, exception
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            result = new_loop.run_until_complete(self.async_call(prompt, system_prompt, max_tokens, temperature))
                            new_loop.close()
                        except Exception as e:
                            exception = e
                    
                    thread = threading.Thread(target=run_task)
                    thread.start()
                    thread.join()
                    
                    if exception:
                        raise exception
                    return result
            else:
                # 如果事件循环未运行，直接使用asyncio.run
                return asyncio.run(self.async_call(prompt, system_prompt, max_tokens, temperature))
        except RuntimeError:
            # 如果没有事件循环，创建新的
            return asyncio.run(self.async_call(prompt, system_prompt, max_tokens, temperature))
    
    def parse_yaml_response(self, response: str) -> dict:
        """解析YAML格式的响应"""
        try:
            # 提取```yaml和```之间的内容
            if '```yaml' in response:
                start = response.find('```yaml') + 7
                end = response.find('```', start)
                yaml_content = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                yaml_content = response[start:end].strip()
            else:
                yaml_content = response.strip()
            
            return yaml.safe_load(yaml_content)
        except Exception as e:
            print(f"YAML解析失败: {e}")
            print(f"原始响应: {response}")
            return {}
    
    async def close(self):
        """关闭客户端"""
        await self.client.close()