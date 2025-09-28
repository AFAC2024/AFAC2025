import traceback

from openai import OpenAI
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config.key as key

client = OpenAI(
    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
    # base_url='http://10.6.16.121:8082/v1',
    # 必需但被忽略
    # api_key='ollama',
    api_key=key.api_key,
)

def LLM(query, system_prompt=None):
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1), retry=retry_if_exception_type((Exception,)))
    def _llm2_with_retry(query, system_prompt):
        if system_prompt is None:
            system_prompt = "你作为一名AI助手，请回答问题。"
        try:
            completion = client.chat.completions.create(
                model="qwen3-30b-a3b",
                # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                stream=True,
                timeout=600,
                stream_options={"include_usage": True}
            )
            res = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    # print(content, end="", flush=True)  # 实时打印流式输出
                    res += content  # 拼接到完整结果
            return res
        except Exception as e:
            # print(f"大模型调用错误：{query}")
            print(f"大模型调用失败: {str(e)}\n{traceback.format_exc()}")
            raise  # 重新抛出异常以触发重试机制

    try:
        return _llm2_with_retry(query, system_prompt)
    except Exception:
        return "错误"


if __name__ == '__main__':
    print(LLM('A是红色，B是蓝色，A和B混合后是什么颜色？', '你是一名人工智能助手，请回答问题。'))
    # print(LLM('A是红色，B是蓝色，A和B混合后是什么颜色？/think'))