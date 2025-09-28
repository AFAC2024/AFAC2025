from http import client
import json
import yaml
from typing import Dict, List

import openai

def identify_competitors_with_ai(api_key,
                                 base_url,
                                 model_name, 
                                 company_name: str, 
                                 ) -> List[Dict[str, str]]:
    """使用AI识别同行竞争对手"""    
    prompt = f"""
    请分析以下公司的竞争对手：
    
    公司名称: {company_name}
    
    请根据以下标准识别该公司的主要竞争对手：
    1. 同行业内的主要上市公司
    2. 业务模式相似的公司
    3. 市值规模相近的公司
    4. 主要业务重叠度高的公司
    
    请返回3-5个主要竞争对手，按竞争程度排序，以YAML格式输出。
    格式要求：包含公司名称、股票代码和上市区域信息。
      **股票代码格式要求**：
    - A股：6位数字（如 000001、688327）
    - 港股：5位数字，不足5位前面补0（如 00700、09888）
    - 未上市公司：留空""
    
    **重要说明**：只关注A股和港股市场的竞争对手，不包括美股市场。
    
    上市区域包括：A股、港股，如果是未上市公司请标明"未上市"。
    
    请用```yaml包围你的输出内容。输出格式示例：
    ```yaml
    competitors:
      - name: "云从科技"
        code: "688327"
        market: "A股"
      - name: "寒武纪"
        code: "688256"
        market: "A股"
      - name: "百度"
        code: "09888"
        market: "港股"
      - name: "科大讯飞"
        code: "002230"
        market: "A股"
      - name: "某AI初创公司"
        code: ""
        market: "未上市"
    ```
    """
    # 正确的客户端创建方式
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "你是一个专业的金融分析师，擅长识别公司的竞争对手。请严格按照YAML格式返回结果。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    competitors_text = response.choices[0].message.content.strip()
    
    # 使用split方法提取```yaml和```之间的内容
    if '```yaml' in competitors_text:
        competitors_text = competitors_text.split('```yaml')[1].split('```')[0].strip()
    elif '```' in competitors_text:
        competitors_text = competitors_text.split('```')[1].split('```')[0].strip()
    
    try:
        # 解析YAML格式
        data = yaml.safe_load(competitors_text)
        competitors = data.get('competitors', [])
        return competitors[:5]
    except yaml.YAMLError:
        # 如果YAML解析失败，返回空列表
        return []

