import datetime
import json

from data_analysis.generator.catalogue_generator import generate_catalogue
from data_analysis.generator.competitor_result_generator import generate_bellwether_result
from data_analysis.generator.headline_abstract_generator import generate_headline_abstract
from data_analysis.generator.section_generator import section_catalogue
from data_analysis.generator.word_generator import format_markdown, convert_md_to_docx
from data_analysis.utils.get_info import get_stock_hk_financial_info, get_stock_A_financial_info
from test import web_search
import argparse

def common_industry_research_report(name):
    research_report = ""
    catalogue = generate_catalogue("行业分析")
    catalogue_json = json.loads(catalogue)

    bellwether_companies = generate_bellwether_result(name)
    # 龙头股金融数据
    finance_data = ""
    bellwether_companies_json = json.loads(bellwether_companies)
    for company in bellwether_companies_json:
        if len(company['股票代码']) == 5:
            finance_data += company["公司名称"] + str(get_stock_hk_financial_info(company["股票代码"], "年度")) + "\n"
        if len(company['股票代码']) == 6:
            finance_data += company["公司名称"] + str(get_stock_A_financial_info(company["股票代码"])) + "\n"
        # 龙头股产业链数据

    for category in catalogue_json:
        message = "##龙头股金融数据:" + finance_data
        search_result = str(web_search(name + str(category["L2"])))
        research_report += str(
            section_catalogue("行业分析", str(category), "", search_result, name)) + "\n"
    # 标题、摘要生成
    headline_abstract = generate_headline_abstract("行业分析", research_report, str(datetime.datetime.now().date()),
                                                   "", name)
    headline_abstract_json = json.loads(headline_abstract)

    # 拼接免责声明
    title = headline_abstract_json["title"]
    info = headline_abstract_json["info"]
    abstract = headline_abstract_json["abstract"]
    content = headline_abstract_json["content"]
    final_report = title + "\n" + info + "\n" + abstract + "\n" + content + "\n" + (
        "## 免责声明\n本文所涉及内容由AI生成，仅供参考学习使用，不构成具体的投资建议。虽然我们努力确保所用数据的准确性和来源的可靠性，但AI无法完全排除信息错误或遗漏的可能性。投资者应自行验证所有数据的准确性，自主做出投资决策，自行承担投资风险和损失。投资有风险，入市需谨慎。")

    print("finalReport" + final_report)
    with open("./reports/industry_report.md", "w", encoding="utf-8") as file:
        file.write(final_report)
        # 转word，图表插入
    format_markdown("./reports/industry_report.md")
    convert_md_to_docx("./reports/industry_report.md", "./reports/Industry_Research_Report.docx")




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run industry research reports')
    parser.add_argument('--industry_name', type=str, help='industry_name')
    args = parser.parse_args()
    # common_industry_research_report("中国智能服务机器人产业")
    common_industry_research_report(args.industry_name)