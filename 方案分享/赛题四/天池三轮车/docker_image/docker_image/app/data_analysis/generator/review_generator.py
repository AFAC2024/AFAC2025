from json_repair import repair_json

import generator


def generator_reviews(content, competitors):
    prompt_template = '''
    ## 角色
    你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的撰写方法。请判断这份报告分析框架的不足之处，给出具体可行的优化建议
    
    ## 要求
    只输出优化建议，不需要返回优化后的
    
    ## 研报主题
    ${report_type}：${theme}
    
    ## 分析框架
    ### 阅读说明
    {
        "L1": "这里是一级分析维度名称",
        "L2": [
        {
            "title": "这里是二级分析维度名称1",
            "desc": "这里是二级分析维度1的描述"
        },
        {
            "title": "这里是二级分析维度名称2",
            "desc": "这里是二级分析维度2的描述"
        }
        ]
    }
    ### 具体内容
    ${analysis_frame}
    
    ## 竞对公司信息
    ${competitor_info}
    '''
    prompt = prompt_template.replace('{analysis_frame}', content).replace('{competitor_info}', competitors)
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json
