import json

from json_repair import repair_json

import generator


def generate_catalogue(intent, theme=None, competitors=None):
    prompt_template = '''
    ## 角色
    你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的撰写方法。你的任务是根据研报类型，完成对应报告的分析要点设计。
    
    ## 要求
    1. 无需考虑研报的标题、摘要、免责声明，只输出正文部分的分析要点
    2. 分析要点的顺序需要和对应研报类型的常见分析顺序保持一致，确保研报的内容连贯、有逻辑
    3. 输出的内容是单个或多个JSON对象，每个JSON对象内需要包括：
    - 一级分析维度名称，放入"L1"字段，字段内使用纯文本
    - 下属二级分析维度信息，放入"L2"数组，数组内是单个或多个JSON对象
        - 二级分析维度名称，，放入"L2"字段，字段内使用纯文本
        - 二级分析维度的描述，，放入"desc"字段，字段内使用纯文本
    4. JSON格式直接输出最终结果，禁止添加额外说明
    
    ## 输出模版（JSON格式）
    ```json
    [
        {
            "L1": "",
            "L2": [
            {
                "title": "",
                "desc": ""
            },
            {
                "title": "",
                "desc": ""
            }
            ]
        }
    ]
    ```
    
    ## 研报类型
    ${intention}: ${report_title}
    ## 同行信息
    ${competitors}
    '''

    prompt = prompt_template.replace('{intention}', intent).replace('{competitors}', competitors).replace('{report_title}', theme)
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json



def generate_search_query(content):
    prompt_template = '''
    ## 任务
    根据描述内容${desc}，生成2~3个搜索问句
    
    ## 要求
    1. 问句内容简洁明了，能够准确描述描述内容，并能够引导用户获取到相关内容。
    2. JSON格式直接输出最终结果，禁止添加额外说明
    
    ## 输出模版（JSON格式）
    ```json
    [
        {
            "search_query1": ["", ""]
        },
        {
            "search_query2": ["", ""]
        }
    ]
    ```

    '''

    prompt = prompt_template.replace('{desc}', content)
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json
