from json_repair import repair_json

import generator


def generate_headline_abstract(intent, content, date, finance_data, theme=""):
    prompt_template = '''
        ## 角色
        你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的撰写方法
        
        ## 任务
        1. 合理调整研报内容的顺序和表达方式，使其更连贯、有逻辑；
        2. 保留正文各标题的markdown格式，禁止修改标题层级，只在标题中加入数字标序；
        3. 为研报生成标题和摘要。 
        
        ## 要求
        1. 输出的JSON对象需要包括：
        1）研报标题：
        - 提炼出研报内容的核心观点
        - 放入"title"字段，字段内使用markdown格式，标题层级为h1
        2）研报基础信息
        - 放入"info"字段，字段内容为"证券研究报告｜${report_type}\n发布时间：${date}\n分析师：AI Analyst"
        3）摘要内容：
        - 包含下面两类内容：
            - 分标题：标题即为"## 投资要点"
            - 摘要内容：包括核心观点、投资价值（3-5点）、风险提示（1-3点）、投资建议与目标价
        - 放入"abstract"字段，字段内使用markdown格式
        4）正文内容：
        - 调整过的研报正文
        - 放入"content"字段，字段内使用markdown格式；字段内标题层级最大为h2，且必定有h2
        2. 语言风格：
        - 专业简练，注意语句通顺，避免结构化表述
        - 逻辑严密，保证分析深入且具有前瞻性
        - 引用重要数据（如财务数据、市场规模数据等）时必须说明对应的年份信息
        3. JSON格式直接输出最终结果，禁止添加额外说明
        
        ## 输出模版（JSON格式）
        {
            "title": "",
            "info": "",
            "abstract": "",
            "content": ""
        }
        
        ## 研报主题
        ${report_type}：${theme}
        
        ## 研报内容
        ${report_content}
        
        ## 财务数据
        ${finance_data}
    '''
    prompt = (prompt_template.replace('{report_type}', intent)
              .replace('{report_content}', content)
              .replace('{finance_data}', finance_data)
              .replace('{date}', date)
              .replace('{theme}', theme))
    result = generator.generate(prompt, False)
    repaired_json = repair_json(result, ensure_ascii=False)
    return repaired_json
