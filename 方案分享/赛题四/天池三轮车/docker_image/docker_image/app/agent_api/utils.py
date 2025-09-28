import os
from loguru import logger
import base64
from openai import OpenAI
import requests
import re
import fitz  # PyMuPDF
import json

def download_pdf(url, pdf_path):
    download_command = f"wget -O {pdf_path} {url}"
    os.system(download_command)
    # 判断是否下载成功
    assert os.path.getsize(pdf_path) > 0, "PDF文件下载失败"
    logger.info(f"PDF文件下载成功：{pdf_path}")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


get_toc_prompt = """
                **任务指令：**
                请仔细分析以下目录图片内容，按照以下规则提取章节信息并输出为 JSON 格式，只需要输出json即可，禁止附带其他说明：

                ---

                **输入**：
                - 一张包含目录内容的图片（可能包含多列、跨页章节等复杂排版）

                **处理逻辑**：
                1. **表格解析**：
                - 识别章节标题（可能包含中英文混合）及其对应的页码范围，每一章节可能有1页，
                    可能有多页，每一章节之后的数字为其起始页，下一章节之后的数字-1为前一章节的末尾页。
                - 处理合并单元格（如章节标题跨多行/列）。
                - 合并连续页码（例如“第3-5页”应解析为 [3,5]）。
                - 处理特殊符号（如“…”表示延续上一章节的页码）。
                - 校验页码有效性（起始页 ≤ 结束页）。
                - 如果中文标题和英文标题重复，则只保留中文标题。
                - 如果是繁体字，则转换为简体字。
                3. **输出格式**：
                ```json
                {
                    "章节名": [起始页码, 结束页码]
                    ...
                }
                """

def get_toc_info_llm(pdf_path):
    doc = fitz.open(pdf_path)
    for page_num in range(0, 10):
        page = doc.load_page(page_num)
        text = page.get_text()
        if "............." in text or "目錄" in text:
            toc_page_id = page_num
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            pix.save("toc.png")
            break
    API_KEY = "sk-fb3239e97df9477f8c754e52fc1a014d"
    client = OpenAI(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key=API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    base64_image = encode_image("toc.png")
    completion = client.chat.completions.create(
    model="qwen-vl-max",  # 可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    messages=[{"role": "user","content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
            {"type": "text", "text": get_toc_prompt},
            ]}]
    )
    toc_info = completion.choices[0].message.content
    logger.info("toc_info: {}".format(toc_info))
    
    return toc_info

def parse_response(prompt: str, url: str, task: str="toc")-> dict:
    payload = json.dumps({
        "system_prompt": "",
        "prompt": prompt,
        "stream": False,
        "sampling_parameters": "{\"temperature\": 0, \"max_tokens\": 10000}"
        })
    headers = {
        'Content-Type': 'application/json'
        }
    response = requests.request("POST", url, headers=headers, data=payload)
    result = response.json()["response"]
    if task == "toc":
        if result.startswith("```"):
            toc_info = eval(result[7:-3])["toc_info"]
        else:
            toc_info = eval(result)["toc_info"]
        return toc_info
    elif task == "relevance":
        if result.startswith("```"):
            relevance = eval(result[7:-3])
        else:
            relevance = eval(result)
        return relevance

def get_llm_answer(prompt: str):
    stream_flag = True
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""  # 定义完整回复
    is_answering = False  # 判断是否结束思考过程并开始回复
    openai_api_key = "Nzc1NDAxNGI4MDFkNzkyNmY0OWIzNGM1ZDQyZmZhYjUwY2NkZWIzMA=="
    openai_api_base = "http://1218137459707574.cn-beijing.pai-eas.aliyuncs.com/api/predict/jf_ds_r1_server/v1"
    client = OpenAI(api_key=openai_api_key, base_url=openai_api_base)
    models = client.models.list()
    model = models.data[0].id
    stream = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
        max_completion_tokens=4096,
        stream=stream_flag,
    )

    if stream_flag:
        print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

        for chunk in stream:
            # 如果chunk.choices为空，则打印usage
            if not chunk.choices:
                print("\nUsage:")
                print(chunk.usage)
            else:
                delta = chunk.choices[0].delta
                # 打印思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                    print(delta.reasoning_content, end='', flush=True)
                    reasoning_content += delta.reasoning_content
                else:
                    # 开始回复
                    if delta.content != "" and is_answering == False:
                        print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                        is_answering = True
                    # 打印回复过程
                    print(delta.content, end='', flush=True)
                    answer_content += delta.content
        result = answer_content
    else:
        result = stream .choices[0].message.content
    # if result.startswith("```"):
    #     relevance = eval(result[7:-3])
    # else:
    #     relevance = eval(result)
    return result