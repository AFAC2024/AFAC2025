import json

from json_repair import repair_json

import generator


def generate_summary(intent, content):
    prompt_template = '''
    ## 角色
    你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的撰写方法。你的任务是根据研报类型、分析要点、研报内容，为研报生成标题和摘要。
    
    ## 要求
    1. 输出的JSON对象需要包括：
    - 研报标题：
        - 使用h1标题，标题内容为研报所有内容的总结
        - 放入"title"字段，字段内使用markdown格式
    - 摘要内容：
        - 包含下面两类内容：
            - 分标题：标题即为“## 投资要点”
            - 摘要内容：包括报告核心结论概述、关键投资亮点（3-5点）、主要风险提示（1-3点）、核心投资建议与目标价
        - 放入"content"字段，字段内使用markdown格式
    2. JSON格式直接输出最终结果，禁止添加额外说明
    
    ## 输出模版（JSON格式）
    {
        "title": "",
        "content": ""
    }
    
    ## 研报类型
    ${report_type}
    
    ## 研报内容
    ${report_content}
    '''

    prompt = prompt_template.replace('{report_type}', intent).replace('{report_content}', content)
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json
