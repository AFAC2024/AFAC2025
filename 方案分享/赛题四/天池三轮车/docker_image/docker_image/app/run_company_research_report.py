import datetime
import json
import os
import sys

import efinance as ef

from agent_api.metrics_draw import draw_metrics
from data_analysis.generator.abstract_generator import generate_abstract
from data_analysis.generator.catalogue_generator import generate_catalogue
from data_analysis.generator.competitor_result_generator import generate_competitor_result
from data_analysis.generator.headline_abstract_generator import generate_headline_abstract
from data_analysis.generator.react_generator import generator_pic
from data_analysis.generator.section_generator import section_catalogue
from data_analysis.generator.word_generator import format_markdown, convert_md_to_docx, fix_markdown_table
from data_analysis.utils.finance_extract_tool import extract_markdown
from data_analysis.utils.get_info import get_stock_hk_financial_info, get_stock_A_financial_info, \
    get_abstract_stock_HK_financial_info
from data_analysis.utils.search_engine import SearchEngine
from functions import profitability_line, operating_receipt_line, debt_paying_ability_line
from search_api import bing_search
import argparse


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
    global finance_data
    research_report = ""
    # 获取竞对信息
    competitors = generate_competitor_result(name)
    print(competitors)
    # 获取目录
    catalogue = generate_catalogue("股票分析", competitors, name)

    print(catalogue)
    # 根据不同目录搜索+rag，分别生成研报
    catalogue_json = json.loads(catalogue)

    year = str(datetime.datetime.now().year)
    if "." in str(code):
        code = code[:-3]
    finance_report = extract_markdown(code, name, year, name + year + "年度报告")

    finance_message = str(finance_report)
    print("finance_message:" + finance_message)
    # 抽取rag内容合并目录分析
    catalogue_rag = generate_abstract("股票分析", catalogue, finance_message)

    
    finance_data = ""
    if len(code) == 5:
        finance_data = str(get_stock_hk_financial_info(code, "年度"))
    elif len(code) == 6:
        finance_data = str(get_stock_A_financial_info(code))

    for category in catalogue_json:
        print(category)
        message = "##基本信息" + "\n" + str(ef.stock.get_base_info(code)) + "\n"
        # sogou_engine = SearchEngine(engine="sogou")
        search_result = str(bing_search(name + str(category["L2"])))

        search_result += finance_data
        message += "##背景信息" + "\n" + search_result + "\n"
        message += "##同行信息" + "\n" + competitors + "\n"

        research_report += str(
            section_catalogue("股票分析", str(category), catalogue_rag, message, finance_report["report_name"])) + "\n"

    # print(research_report)
    # 图表生成
    # 盈利能力
    x_data = ["2020-12-31", "2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31"]
    line1_data = get_abstract_stock_HK_financial_info("毛利率", x_data, code)
    line2_data = get_abstract_stock_HK_financial_info("净利率", x_data, code)
    line3_data = get_abstract_stock_HK_financial_info("ROE", x_data, code)
    chart_dir1 = draw_metrics("三折线", chart_data={"date": x_data, "毛利率": line1_data,
                                       "净利率": line2_data, "ROE": line3_data}, chart_name="盈利能力.png")["chart_dir"]
    print("chart_dir1:" + chart_dir1)
    # 营业总收入
    bar1_data = get_abstract_stock_HK_financial_info("营业收入", x_data, code)
    line1_data = get_abstract_stock_HK_financial_info("同比增长", x_data, code)
    chart_dir2 = draw_metrics("柱状图折线图", chart_data={"date": x_data, "营业收入": bar1_data, "同比增长": line1_data},
                              chart_name="营业总收入.png")["chart_dir"]

    # 偿债能力
    line1_data = get_abstract_stock_HK_financial_info("资产负债率", x_data, code)
    line2_data = get_abstract_stock_HK_financial_info("流动比率", x_data, code)
    chart_dir3 = draw_metrics("双折线", chart_data={"date": x_data, "资产负债率": line1_data, "流动比率": line2_data},
                              chart_name="偿债能力.png")["chart_dir"]

    # # 运营能力
    # line1_data = get_abstract_stock_HK_financial_info("总资产周转率", x_data, code)
    # line2_data = get_abstract_stock_HK_financial_info("存货周转率", x_data, code)
    # line3_data = get_abstract_stock_HK_financial_info("应收账款周转率", x_data, code)
    # chart_dir4 = draw_metrics("三折线", chart_data={"date": x_data, "总资产周转率": line1_data, "存货周转率": line2_data, "应收账款周转率": line3_data},
    #                           chart_name="运营能力.png")["chart_dir"]
    #
    # # 净利润
    # line1_data = get_abstract_stock_HK_financial_info("归母净利润", x_data, code)
    # line2_data = get_abstract_stock_HK_financial_info("扣非净利润", x_data, code)
    # chart_dir5 = draw_metrics("双折线", chart_data={"date": x_data, "归母净利润": line1_data, "扣非净利润": line2_data},
    #                           chart_name="净利润.png")["chart_dir"]

    # 标题、摘要生成
    headline_abstract = generate_headline_abstract("股票分析", research_report, str(datetime.datetime.now().date()),
                                                   finance_data, name + code)
    print("headline_abstract:" + headline_abstract)

    headline_abstract_json = json.loads(headline_abstract)

    # 拼接免责声明
    title = headline_abstract_json["title"]
    info = headline_abstract_json["info"]
    abstract = headline_abstract_json["abstract"]
    content = headline_abstract_json["content"]
    # 生成图片标签
    report_with_pic = generator_pic("股票分析", name, content)
    if isinstance(report_with_pic, str):
        report_with_pic = json.loads(report_with_pic)
    print(report_with_pic)
    # 替换标签
    # chart_dir1 = "/workspace/code/generate_report/easy_financial_report/workspace/tools/code_interpreter/盈利能力.png"
    # chart_dir2 = "/workspace/code/generate_report/easy_financial_report/workspace/tools/code_interpreter/营业总收入.png"
    # chart_dir3 = "/workspace/code/generate_report/easy_financial_report/workspace/tools/code_interpreter/偿债能力.png"
    report_with_pic_content = report_with_pic["content"].replace("<营业总收入end>", f"![营业总收入]({chart_dir2})").replace(
        "<盈利能力end>", f"![盈利能力]({chart_dir1})").replace("<偿债能力end>", f"![偿债能力]({chart_dir3})")
    print(report_with_pic)

    final_report = title + "\n" + info + "\n" + abstract + "\n" + report_with_pic_content + "\n" + (
        "## 免责声明\n本文所涉及内容由AI生成，仅供参考学习使用，不构成具体的投资建议。虽然我们努力确保所用数据的准确性和来源的可靠性，但AI无法完全排除信息错误或遗漏的可能性。投资者应自行验证所有数据的准确性，自主做出投资决策，自行承担投资风险和损失。投资有风险，入市需谨慎。")

    print("finalReport" + final_report)
    # fix_markdown_table(final_report)
    with open("./reports/company_report.md", "w", encoding="utf-8") as file:
        file.write(final_report)
    # 转word，图表插入
    format_markdown("./reports/company_report.md")
    convert_md_to_docx("./reports/company_report.md", "./reports/Company_Research_Report.docx")


# common_stock_research_report("06682.HK", "第四范式")
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='股票分析报告生成')
    parser.add_argument('--company_name', type=str, default="第四范式", help='股票名称')
    parser.add_argument('--company_code', type=str, default="06682.HK", help='股票代码')
    args = parser.parse_args()
    # common_stock_research_report("00020.HK", "商汤科技")
    if args.company_name == "4Paradigm":
        args.company_name = "第四范式"
    common_stock_research_report(args.company_code, args.company_name)
    