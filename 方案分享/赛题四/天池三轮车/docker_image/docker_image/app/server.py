import datetime
import json
import os

import efinance as ef

from data_analysis.generator.abstract_generator import generate_abstract
from data_analysis.generator.catalogue_generator import generate_catalogue
from data_analysis.generator.competitor_result_generator import generate_competitor_result
from data_analysis.generator.headline_abstract_generator import generate_headline_abstract
from data_analysis.generator.section_generator import section_catalogue
from data_analysis.generator.word_generator import word_generator, format_markdown
from data_analysis.utils.finance_extract_tool import extract_markdown
from data_analysis.utils.get_info import get_stock_hk_financial_info
from data_analysis.utils.search_engine import SearchEngine
from test import web_search

PROMPT = '''
    ## 角色
    你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的分析框架，你的任务是生成研报，必须保证分析有深度。
    
    ## 研报要求
    格式：与示例研报类似
    字数：3000字左右
    内容：与给定的金融数据和企业背景信息相关
    其他：加入有价值的图表，实现图文结合。
    
    ## 工作流
    1. 确认研报中插入图表的地方，在段落的末尾添加图表标签。标签的格式："<${图表名称}end>"。
    2. 将包含图表标签的研报内容放入"{report_content}"字段，字段内使用markdown语言。
    3. 说明每张图表的设计规则，放入"{chart}"字段，字段内使用markdown语言。
    - 字段内的格式如下：
    | 标签名称 | 所需数据名称 | 图表类型 |
    | :-- | :-- | :-- |
    | <${图表名称}end> | ${所需数据名称} | ${图表类型} |
    - 字段输出示例：
    | 图表名称 | 所需数据名称 | 图表类型 |
    | :-- | :-- | :-- |
    | <营业收入end> | 营业收入、营业收入同比 | 柱状折线图 |
    
    ## 输出格式
    {
        "{report_content}": "",
        "{chart}": ""
    }
    
    ## 限制
    1. 绘图时只允许使用已提供的金融数据，禁止自行拓展。
    2. 除了添加图表标签之外，禁止自行修改研报内容。
    
    ## 企业背景信息
    {background_msg}
    
    ## 给定金融数据
    {finance_data}
    
'''


def concatenate_files(directory_path):
    if not os.path.isdir(directory_path):
        raise ValueError(f"'{directory_path}' 不是有效目录。")

    # 获取目录下所有文件并按文件名排序
    file_names = sorted([
        f for f in os.listdir(directory_path)
        if os.path.isfile(os.path.join(directory_path, f))
    ])

    combined = ''
    for file_name in file_names:
        file_path = os.path.join(directory_path, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            combined += f.read()
    return combined


def common_stock_research_report(code=None, name=None):
    research_report = ""
    # 获取竞对信息
    competitors = generate_competitor_result(name)
    # 获取目录
    catalogue = generate_catalogue("股票分析", competitors)
    # 根据不同目录搜索+rag，分别生成研报
    catalogue_json = json.loads(catalogue)

    year = str(datetime.datetime.now().year)
    finance_message = str(extract_markdown(code, name, year, name + year + "年度报告"))
    print("finance_message:" + finance_message)
    # 抽取rag内容合并目录分析
    catalogue_rag = generate_abstract("股票分析", catalogue, finance_message)
    # catalogue_rag = "###1.**核心业绩总结(PerformanceSummary)**-**关键财务指标**：-营收37.72亿元，同比增长10.8%。-毛利率42.9%（2023年：44.1%），主因硬件及智算中心（AIDC）成本上升。-年度亏损43.07亿元，同比缩窄33.7%，运营效率提升驱动减亏。-现金储备127.5亿元（含现金等价物及定期存款），流动性稳健。-**业务板块表现**：-**生成式AI**：收入24.04亿元（+103.1%），占比63.7%，成为最大收入源；驱动因素为模型训练/推理需求爆发及AI应用商业化（如企业助手、金融工具）。-**智能汽车**：收入2.56亿元（-33.2%），因战略重心转向智能座舱及端到端自动驾驶研发，传统V2X业务收缩。-**视觉AI**：收入11.12亿元（-39.5%），因聚焦高质量客户并向其迁移生成式AI能力。-**与预期对比**：-生成式AI超额达成目标（连续两年三位数增长），视觉AI因战略收缩低于预期。-**管理层定性评价**：>**“生成式AI驱动业务结构跃迁，公司处于AI发展的关键窗口期”**，转型成效显著但成本控制仍具挑战。---###2.**业务驱动因素与挑战(Drivers&Challenges)**-**增长驱动因素**：-**市场需求爆发**：生成式AI模型训练/推理需求激增，客户付费意愿增长6倍。-**技术效能领先**：大装置推理效率优于行业15-25%（如DeepSeekR1），联合优化降低模型成本。-**战略协同效应**：“大装置-大模型-应用”三位一体闭环形成，应用场景渗透率提升（交互工具使用量增8倍）。-**主要挑战**：-**智能汽车业务转型阵痛**：OEM合作模式调整导致研发服务收入下滑。-**传统业务收缩**：视觉AI主动优化客户结构致收入短期承压。-**成本压力**：硬件及AIDC扩张推高销售成本，毛利率承压。---###3.**战略重点与未来展望(Strategy&Outlook)**-**核心战略方向**：-**三位一体深化**：推动大装置、大模型（日日新）、应用的深度协同，目标每年降低训练/推理成本一个数量级。-**多模态商业化**：重点开发生成式AI在具身智能、超级个人助手等场景的落地。-**全球算力网络**：以上海临港AIDC为核心，向粤港澳、京津冀等区域扩展轻资产运营。-**资本配置计划**：-资金优先投向AI基础设施（占配售款项35%）及生成式AI研发（30%）。-2024年研发开支41.32亿元（+19.2%），聚焦大模型训练与优化。-**未来展望**：-**2025年预期**：生成式AI应用将“规模化爆发”，传统计算机视觉同步受益。-**行业趋势**：多模态大模型（如日日新6.0对标Gemini2.0Pro）是商业化突破关键。-**长期目标路径**：通过“1+X”架构重组（1=核心AI业务，X=生态企业），释放协同效应；目标2027年实现盈利。---###4.**关键风险提示(KeyRisks)**-**应收款账期压力**：2年以上账期应收款占比46.9%，公营客户预算限制或影响现金流。-**算力军备竞赛**：行业Capex投入加剧，若软件优化能力不足恐削弱成本优势。-**模型同质化竞争**：开源模型（如DeepSeek）普及可能挤压市场份额。-**技术国产化风险**：国产芯片适配虽推进（训练成本降40%），但性能稳定性待验证。-**政策监管不确定性**：全球AI伦理及数据合规政策趋严，影响跨区域部署。---###5.**管理层基调与信心(Tone&Confidence)**-**整体基调**：**“积极乐观”**。-定性表述：生成式AI是“驱动公司业务结构跃迁的引擎”，技术普惠与商业价值正形成共振。-**信心程度**：**高度自信**。-行动佐证：董事长徐立及执行董事徐冰增持1000万股（涉资1490万港元）。-公开声明：>**“推理效率领先带来15-25%利润空间，联合优化是商汤不可复制的护城河”**。"

    for category in catalogue_json:
        print(category)
        message = "##基本信息" + "\n" + str(ef.stock.get_base_info(code)) + "\n"
        # sogou_engine = SearchEngine(engine="sogou")
        search_result = str(web_search(name + str(category["L2"])))
        search_result += str(get_stock_hk_financial_info(code, "年度"))
        message += "##背景信息" + "\n" + search_result + "\n"
        # message += "##财务数据" + "\n" + finance_data + "\n"
        message += "##同行信息" + "\n" + competitors + "\n"
        # message += catalogue_rag

        research_report += str(
            section_catalogue("股票分析", str(category), catalogue_rag, message)) + "\n"

    # print(research_report)
    # 图表生成

    # 公司单季度营收及增速
    # bar1 = get_abstract_stock_financial_info("归母净利润", code)
    # bar2 = get_abstract_stock_financial_info("扣非净利润", code)
    # double_bar_line(x_data, bar1, bar2)
    # 公司单季度营收及增速
    # 公司盈利能力指标

    # 公司运营能力指标
    # 公司偿债能力指标

    # 选择研报的位置插入图表
    # research_report_chart = generate_complete_report(research_report)

    # 标题、摘要生成
    headline_abstract = generate_headline_abstract("股票分析", research_report, str(datetime.datetime.now().date()), name + code)
    headline_abstract_json = json.loads(headline_abstract)

    # 拼接免责声明
    title = headline_abstract_json["title"]
    info = headline_abstract_json["info"]
    abstract = headline_abstract_json["abstract"]
    content = headline_abstract_json["content"]
    final_report = title + "\n" + info + "\n" + abstract + "\n" + content + "\n" + '''
    ## 免责声明
    本文所涉及内容由AI生成，仅供参考学习使用，不构成具体的投资建议。虽然我们努力确保所用数据的准确性和来源的可靠性，但AI无法完全排除信息错误或遗漏的可能性。投资者应自行验证所有数据的准确性，自主做出投资决策，自行承担投资风险和损失。投资有风险，入市需谨慎。
    '''

    print("finalReport"+final_report)
    with open("./reports/reports.md", "w", encoding="utf-8") as file:
        file.write(final_report)
    # 转word，图表插入
    # format_markdown("./reports/reports.md")
    word_generator("./reports/reports.md", "./reports/Company_Research_Report.docx")


def common_industry_research_report(name=None):
    research_report = ""
    catalogue = generate_catalogue("行业分析")
    catalogue_json = json.loads(catalogue)
    for category in catalogue_json:
        print(category)
        message = "##基本信息" + "\n" + str(ef.stock.get_base_info(code)) + "\n"
        sogou_engine = SearchEngine(engine="sogou")
        search_result = str(sogou_engine.search(name + str(category["L2"])))
        message += "##背景信息" + "\n" + search_result + "\n"
        # message += finance_message

        research_report += "###" + category["L1"] + "\n" + str(
            section_catalogue("股票分析", str(category), message)) + "\n"


common_stock_research_report("00020", "商汤科技")
