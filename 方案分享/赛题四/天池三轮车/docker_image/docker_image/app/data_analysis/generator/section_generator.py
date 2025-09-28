from json_repair import repair_json

import generator


def section_catalogue(intent, catalogue_json, finance_summary_rag, search_result, theme):
    prompt_template = '''
        ## 角色
        你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的撰写方法。你的任务是根据研报主题、分析要点、参考信息，生成研报中某个段落的内容。
        
        1. 输出的JSON对象需要包括：
        1）**小结标题**
        - 提炼出研报内容的核心观点（禁止使用"L1"字段作为小结标题）
        - 放入"title"字段，字段内使用markdown格式，标题层级为h2
        2）**研报内容**
        - 包含下面两类内容：
        - **分标题**：
        - 包含层级（最大为h3，可根据实际情况继续拆分出h4、h5等标题）、标题内容
        - 标题内容提炼出研报内容的核心观点（禁止使用"L2"的"title"字段作为分标题）
        - **分析段落**：
        - 具体的分析内容，字数不限
        - 分析中合理插入表格辅助文字说明；表格上方需有名称，表格下方需标注数据来源，格式“数据来源：贵州茅台2024年度报告”
        - 表格示例：
        
        | **指标名称** | **2024年** | **2023年** |
        | :--- | :--- | :--- |
        | 营业收入 | 2.3亿元 | 5.5亿元 |

        *数据来源：公司年报（2024）*

        - 放入"content"字段，字段内使用markdown格式
        2. 语言风格：
        - 专业简练，注意语句通顺，避免结构化表述
        - 逻辑严密，保证分析深入且具有前瞻性
        - 引用重要数据（如财务数据、市场规模数据等）时必须说明对应的年份信息，并确保优先使用最新数据
        3. JSON格式直接输出最终结果，禁止添加额外说明
        
        ## 输出模版（JSON格式）
        {
            "title": "",
            "content": ""
        }
        
        ## 研报主题
        ${intention}：${theme}
        
        ## 分析要点
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
        
        ## 参考信息
        ### ${financial_report_file_name}
        ${financial_report_rag_summary}
        ### 相关资讯
        ${search_result}
    '''
    prompt = (prompt_template.replace('{intention}', intent)
              .replace('{analysis_frame}', catalogue_json)
              .replace('{financial_report_file_name}', theme)
              .replace('{financial_report_rag_summary}', finance_summary_rag)
              .replace('{search_result}', search_result))

    result = generator.generate(prompt, False)

    repaired_json = repair_json(result, ensure_ascii=False)
    print(catalogue_json+":"+repaired_json)
    return repaired_json
