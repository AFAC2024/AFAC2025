import os

from json_repair import repair_json

import generator


def generate_complete_report(content):
    prompt_template = '''
        ## 角色
        你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的撰写方法。你的任务是通读研报内容，为图表找到合适的插入位置，实现图文结合
        
        ## 要求
        1. 确认研报中插入图表的地方，在段落的末尾添加图表的名称
        2. 将包含图表标签的研报内容放入"content"字段，字段内使用markdown语言
        3. JSON格式直接输出最终结果，禁止添加额外说明
        
        ## 输出模版（JSON格式）
        {
            "content": ""
        }
        
        ## 限制
        1. 只允许插入提供的图表，禁止自行拓展。
        2. 除了添加图表标签之外，禁止自行修改研报内容。
        
        ## 可用图表
        | 图表名称 | 图表信息描述 |
        | :--- | :--- |
        ${chart_message}
        
        ## 研报内容
        ${report_content}
        '''

    chart_message = "";
    charts = os.listdir("../charts")
    for chart in charts:
        chart_message += "|" + chart + "|" + "" + "|\n"

    prompt = prompt_template.replace("chart_message", chart_message).replace("report_content", content)
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json
