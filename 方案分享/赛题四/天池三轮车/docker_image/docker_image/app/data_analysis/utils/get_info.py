import json

import efinance as ef
import akshare as ak
from typing import Optional, Literal

from akshare import stock_financial_hk_report_em, stock_zh_a_minute

from data_analysis.generator.react_generator import generator_pic
from data_analysis.generator.word_generator import format_markdown, convert_md_to_docx


def get_base_info(stock_code: str = "00020"):
    """获取股票基础信息"""

    return ef.stock.get_base_info(stock_code)


def get_hq_data(symbol, period: str = "60"):
    return stock_zh_a_minute(symbol, period)


def get_stock_financial_info(stock_code: str = "00020", symbol: str = "现金流量表"):
    return ak.stock_financial_report_sina(stock_code, symbol)


# 获取港股重要指标数据
def get_stock_hk_financial_info(stock_code: str = "00020", indicator: str = "年度"):
    return ak.stock_financial_hk_analysis_indicator_em(stock_code, indicator)


def get_abstract_stock_HK_financial_info(indicator, x_data, stock_code: str = "600059"):
    index_json = {"毛利率": "GROSS_PROFIT_RATIO", "净利率": "NET_PROFIT_RATIO", "ROE": "ROE_AVG",
                  "资产负债率": "DEBT_ASSET_RATIO", "流动比率": "CURRENT_RATIO", "营业收入": "OPERATE_INCOME",
                  "同比增长": "OPERATE_INCOME_YOY"}

    table = ak.stock_financial_hk_analysis_indicator_em(stock_code)
    data = {}
    for year in x_data:
        data[year] = table[table["REPORT_DATE"] == year + " 00:00:00"][index_json[indicator]].item()
    return list(data.values())


# 获取A股重要指标数据
def get_stock_A_financial_info(stock_code: str = "600059"):
    return ak.stock_financial_abstract(stock_code)


def get_abstract_stock_A_financial_info(indicator, year_list, stock_code: str = "600059"):
    table = ak.stock_financial_abstract(stock_code)
    print(table)
    data = {}
    for year in year_list:
        if len(table[table["指标"] == indicator][year]) == 1:
            data[year] = table[table["指标"] == indicator][year].values.item()
        else:
            data[year] = table[table["指标"] == indicator][year].values[0].item()
    # return ak.stock_financial_abstract(stock_code)
    return list(data.values())


def get_stock_intro(symbol: str = "000066", market: Literal["A", "HK"] = "A") -> Optional[str]:
    """
    获取股票的基本介绍信息，包括主营业务、经营范围等。
    支持区分A股、港股。
    :param symbol: 股票代码（如 '000066'、'00700'）
    :param market: 市场类型（'A'、'HK'）
    :return: 返回pandas表格的字符串，若获取失败则返回None
    """
    # A股
    if market == "A":
        # 去掉A股代码的SH/SZ前缀
        clean_symbol = symbol.replace('SH', '').replace('SZ', '')
        try:
            df = ak.stock_zyjs_ths(symbol=clean_symbol)
            if df is not None and not df.empty:
                return df.to_string(index=False)
        except Exception as e:
            print(f"AkShare A股获取失败 ({clean_symbol}): {e}")
            return None  # 港股
    elif market == "HK":
        # 去掉港股代码的HK前缀
        clean_symbol = symbol.replace('HK', '')
        try:
            df = ak.stock_hk_company_profile_em(symbol=clean_symbol)
            if df is not None and not df.empty:
                return df.to_string(index=False)
        except Exception as e:
            print(f"AkShare 港股获取失败 ({clean_symbol}): {e}")
            return None

    return None


if __name__ == '__main__':
    #
    # from agent_api.metrics_draw import draw_metrics
    #
    # code = "00020"
    # x_data = ["2020-12-31", "2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31"]
    # line1_data = get_abstract_stock_HK_financial_info("毛利率", x_data, code)
    # line2_data = get_abstract_stock_HK_financial_info("净利率", x_data, code)
    # line3_data = get_abstract_stock_HK_financial_info("ROE", x_data, code)
    # chart_dir1 = draw_metrics("三折线", chart_data={"date": x_data, "毛利率": line1_data,
    #                                                 "净利率": line2_data, "ROE": line3_data}, chart_name="盈利能力.png")
    # print(chart_dir1)

    headline_abstract_json = {"title": "# 商汤-W（00020.HK）：生成式AI驱动业务重构，技术壁垒构筑核心护城河",
     "info": "证券研究报告｜商汤-W（00020.HK）股票分析\n发布时间：2025-07-24\n分析师：AI Analyst",
     "abstract": "## 投资要点\n**核心观点**：商汤科技通过生成式AI业务实现收入结构质变，2024年该业务收入同比激增103.1%至24.04亿元，带动整体营收增长10.8%。公司依托\"日日新\"大模型技术突破和临港AIDC算力基建，在智慧城市、智能汽车等领域形成差异化竞争优势。\n\n**投资价值**：\n1. 生成式AI业务毛利率突破60%，标准化产品收入占比翻倍\n2. 智能汽车领域装机量突破600万台，L4级自动驾驶方案实现12个园区商业化运营\n3. 算力规模达23,000PetaFlops，模型生产效率提升至5.24个/人年\n4. 智慧城市项目复购率87%，覆盖全国150+城市形成深度客户粘性\n\n**风险提示**：\n1. 政府订单占比仍达48%，数字化预算增速下滑至9.8%\n2. 经营性现金流连续三个季度为负，现金储备仅可维持5个季度运营\n3. 数据安全法实施后模型迭代周期延长至14个月\n\n**投资建议**：给予\"增持\"评级，目标价5.8港元（对应2025年PS 12X）\n\n**图表说明**：生成式AI业务收入占比趋势图（2023-2025Q1）已通过pyecharts绘制并保存",
     "content": "## 1. 业务结构战略性调整\n商汤科技2024年完成\"生成式AI+传统AI+智能汽车\"三大战略重组，生成式AI收入占比从34.8%跃升至63.7%。2025Q1营收达42.6亿元，其中智慧商业（46.5%）、智慧城市（28.9%）、生成式AI标准化产品（18.0%）构成新增长三角。\n\n## 2. 技术研发持续突破\n\"日日新\"大模型6.0版本在SuperCLUE评测得分率突破85%，推理成本降至0.12元/千次（行业均值0.35元）。临港AIDC算力规模达23,000PetaFlops，支持8B参数模型车端部署，医疗影像系统落地300+三甲医院。\n\n## 3. 商业化能力升级\n订阅制收入占比提升至35%，企业客户合同金额增长32%。智能汽车领域签约30家车企，定点车型超150款，单车价值量达2,300元。智慧城市业务市占率68%，覆盖700+地铁站场景。\n\n## 4. 财务健康度分析\n2025Q1毛利率提升至45.6%，但应收账款周转天数延长至126天。经营性现金流-3.8亿元，现金储备85亿元对应5个季度运营安全边际。建议关注沙特2.3亿美元订单回款进展。\n\n## 5. 行业竞争格局\n对比海康威视（毛利率42.3%）、云从科技（PS 18.3X），商汤在软件收入占比（65%）、政企客单价（520万元）、研发投入强度（48%）等维度建立显著优势。智能汽车装机量增速（45%）超行业均值2倍。\n\n## 6. 核心风险预警\n智慧城市招标量同比减少32%，AI解决方案单价降至行业均价的65%。数据脱敏成本占研发投入23%，模型开发合规成本增加40%。\n\n## 7. 估值重构机遇\n当前PS 9.2X显著低于同业，城市大脑4.0项目（20-30亿元订单）带来15%估值弹性。算力储备（9,100PFlops）和技术路线图兑现有望推动估值中枢上移30%。"}

    # 拼接免责声明
    title = headline_abstract_json["title"]
    info = headline_abstract_json["info"]
    abstract = headline_abstract_json["abstract"]
    content = headline_abstract_json["content"]
    # 生成图片标签
    # 替换标签
    chart_dir1 = "/Users/macadmin/PycharmProjects/easy_financial_report/workspace/tools/code_interpreter/盈利能力.png"
    chart_dir2 = "/Users/macadmin/PycharmProjects/easy_financial_report/workspace/tools/code_interpreter/营业总收入.png"
    chart_dir3 = "/Users/macadmin/PycharmProjects/easy_financial_report/workspace/tools/code_interpreter/偿债能力.png"
    report_with_pic = {"content": "## 1. 业务结构战略性调整\n商汤科技2024年完成\"生成式AI+传统AI+智能汽车\"三大战略重组，生成式AI收入占比从34.8%跃升至63.7%。2025Q1营收达42.6亿元，其中智慧商业（46.5%）、智慧城市（28.9%）、生成式AI标准化产品（18.0%）构成新增长三角。<营业总收入end>\n\n## 2. 技术研发持续突破\n\"日日新\"大模型6.0版本在SuperCLUE评测得分率突破85%，推理成本降至0.12元/千次（行业均值0.35元）。临港AIDC算力规模达23,000PetaFlops，支持8B参数模型车端部署，医疗影像系统落地300+三甲医院。\n\n## 3. 商业化能力升级\n订阅制收入占比提升至35%，企业客户合同金额增长32%。智能汽车领域签约30家车企，定点车型超150款，单车价值量达2,300元。智慧城市业务市占率68%，覆盖700+地铁站场景。\n\n## 4. 财务健康度分析\n2025Q1毛利率提升至45.6%，但应收账款周转天数延长至126天。经营性现金流-3.8亿元，现金储备85亿元对应5个季度运营安全边际。建议关注沙特2.3亿美元订单回款进展。<盈利能力end>\n\n## 5. 行业竞争格局\n对比海康威视（毛利率42.3%）、云从科技（PS 18.3X），商汤在软件收入占比（65%）、政企客单价（520万元）、研发投入强度（48%）等维度建立显著优势。智能汽车装机量增速（45%）超行业均值2倍。\n\n## 6. 核心风险预警\n智慧城市招标量同比减少32%，AI解决方案单价降至行业均价的65%。数据脱敏成本占研发投入23%，模型开发合规成本增加40%。\n\n## 7. 估值重构机遇\n当前PS 9.2X显著低于同业，城市大脑4.0项目（20-30亿元订单）带来15%估值弹性。算力储备（9,100PFlops）和技术路线图兑现有望推动估值中枢上移30%。"}
    content_ = report_with_pic["content"].replace("<营业总收入end>", f"![营业总收入]({chart_dir2})").replace(
        "<盈利能力end>", f"![盈利能力]({chart_dir1})").replace("<偿债能力end>", f"![偿债能力]({chart_dir3})")
    print(report_with_pic)

    final_report = title + "\n" + info + "\n" + abstract + "\n" + content_ + "\n" + (
        "## 免责声明\n本文所涉及内容由AI生成，仅供参考学习使用，不构成具体的投资建议。虽然我们努力确保所用数据的准确性和来源的可靠性，但AI无法完全排除信息错误或遗漏的可能性。投资者应自行验证所有数据的准确性，自主做出投资决策，自行承担投资风险和损失。投资有风险，入市需谨慎。")

    print("finalReport" + final_report)
    # fix_markdown_table(final_report)
    with open("./reports/company_report.md", "w", encoding="utf-8") as file:
        file.write(final_report)
    # 转word，图表插入
    format_markdown("./reports/company_report.md")
    convert_md_to_docx("./reports/company_report.md", "./reports/Company_Research_Report.docx")