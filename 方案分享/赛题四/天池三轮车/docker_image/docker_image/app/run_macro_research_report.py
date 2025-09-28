import datetime
import json
import os

import efinance as ef

from data_analysis.generator.abstract_generator import generate_abstract
from data_analysis.generator.catalogue_generator import generate_catalogue, generate_search_query
from data_analysis.generator.competitor_result_generator import generate_competitor_result
from data_analysis.generator.headline_abstract_generator import generate_headline_abstract
from data_analysis.generator.section_generator import section_catalogue
from data_analysis.generator.word_generator import format_markdown, convert_md_to_docx, fix_markdown_table
from data_analysis.utils.finance_extract_tool import extract_markdown
from data_analysis.utils.get_info import get_stock_hk_financial_info, get_stock_A_financial_info
from data_analysis.utils.search_engine import SearchEngine
from agent_api.metrics_draw import get_macro_metrics
from search_api import bing_search

import argparse


def common_macro_research_report(name, time):
    research_report = ""
    name = name + "\t" + time
    catalogue = generate_catalogue("宏观分析", theme=name, competitors="")
    catalogue_json = json.loads(catalogue)
    print("catalogue_json: {}".format(catalogue_json))
    # metric_data = get_macro_metrics(report_frame=catalogue_json)

    for category in catalogue_json:
        # search_query = generate_search_query(content=str(category["L2"]))
        # search_query_json = json.loads(search_query)
        # print("search_query_json: {}".format(search_query_json))

        # for query in search_query_json:
        #     for key, value in query.items():
        search_result = str(bing_search(name + str(category["L2"])))
        print("search_result: {}".format(search_result))
        research_report += str(
            section_catalogue("宏观分析", str(category), "", search_result, name)) + "\n"
    # 标题、摘要生成
    headline_abstract = generate_headline_abstract("宏观分析", research_report, str(datetime.datetime.now().date()),
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
    with open("./reports/macro_report.md", "w", encoding="utf-8") as file:
        file.write(final_report)
        # 转word，图表插入
    format_markdown("./reports/macro_report.md")
    convert_md_to_docx("./reports/macro_report.md", "./reports/Macro_Research_Report.docx")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="金融研究报告生成器")
    parser.add_argument("--marco_name", default="国家级“人工智能+”政策效果评估",type=str, help="股票名称")
    parser.add_argument("--time", default="2023-2025", type=str, help="报告时间")

    args = parser.parse_args()
    common_macro_research_report(args.marco_name, args.time)