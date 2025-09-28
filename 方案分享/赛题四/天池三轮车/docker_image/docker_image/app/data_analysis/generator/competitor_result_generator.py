from json_repair import repair_json

import generator


def generate_competitor_result(name):
    prompt_template = '''
        请分析以下公司的竞争对手：
    
        公司名称: ${company_name}
    
        请根据以下标准识别该公司的主要竞争对手：
        1.
        同行业内的主要上市公司
        2.
        业务模式相似的公司
        3.
        市值规模相近的公司
        4.
        主要业务重叠度高的公司
    
        请返回3 - 5个主要竞争对手，按竞争程度排序，以JSON格式输出。
        格式要求：包含公司名称、股票代码和上市区域信息。
        ** 股票代码格式要求 **：
        - A股：6位数字（如000001、688327）
        - 港股：5位数字，不足5位前面补0（如00700、09888）
        - 未上市公司：留空
        ""
    
        ** 重要说明 **：只关注A股和港股市场的竞争对手，不包括美股市场。
    
        上市区域包括：A股、港股，如果是未上市公司请标明
        "未上市"。
    '''
    prompt = prompt_template.replace('{company_name}', name)
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json


def generate_bellwether_result(name):
    prompt_template = '''
        请分析以下行业的龙头股：

        行业名称: ${industry_name}

        请根据以下标准识别该行业的龙头股：
        1.
        行业内的主要上市公司
        2.
        公司规模在行业中排前列
        3.
        主要业务重叠度高的公司

        请返回3 - 5个龙头公司，按竞争程度排序，以JSON格式输出。
        格式要求：包含公司名称、股票代码和上市区域信息。
        ** 股票代码格式要求 **：
        - A股：6位数字（如000001、688327）
        - 港股：5位数字，不足5位前面补0（如00700、09888）
        - 未上市公司：留空
        ""

        ** 重要说明 **：只关注A股和港股市场的龙头股，不包括美股市场。

        上市区域包括：A股、港股，如果是未上市公司请标明
        "未上市"。
    '''
    prompt = prompt_template.replace('{industry_name}', name)
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json

#
# print(generate_bellwether_result("中国智能服务机器人产业"))
