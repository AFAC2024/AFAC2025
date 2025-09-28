from flask import Flask, request, jsonify
from easy_demo import parse_doc
from utils import parse_response, get_llm_answer
from pathlib import Path
from loguru import logger
import os
from openai import OpenAI

app = Flask(__name__)

@app.route('/parse_pdf', methods=['POST'])
def parse_pdf():
    data = request.get_json()
    pdf_path = "pdf_path"
    toc_info = data.get('toc_info')
    extract_prompt = """
                    ## Task
                    根据需求，抽取目录信息中需要的章节信息，并返回抽取后的目录信息

                    ## Remember
                    1、JSON格式输出目录信息
                    2、只输出结果，不需要说明原因

                    ## Instruction
                    抽取目录章节信息中的管理层讨论与分析的章节信息，以元祖格式输出抽取后的目录信息
                    

                    ## Output Example
                    {{'toc_info': 
                        {{'管理层讨论与分析': (这里是章节的页码范围)}}
                    }}

                    ## toc info
                    {}
                    """.format(toc_info)
    qwen_url = "https://jf-ai-llm.techgp.cn/jf-qwen-72b-server/v2/models/inference/generate"
    disscussion_analysis_info = parse_response(extract_prompt, qwen_url)
    logger.info("disscussion_analysis_info: {}".format(disscussion_analysis_info))
    pdf_suffixes = [".pdf"]
    image_suffixes = [".png", ".jpeg", ".jpg"]
    __dir__ = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(__dir__, "output")
    doc_path_list = []
    for doc_path in Path(pdf_path).glob('*'):
        if doc_path.suffix in pdf_suffixes + image_suffixes:
            doc_path_list.append(doc_path)
    # logger.info("doc_path_list: {}".format(doc_path_list))
    """如果您由于网络问题无法下载模型，可以设置环境变量MINERU_MODEL_SOURCE为modelscope使用免代理仓库下载模型"""
    os.environ['MINERU_MODEL_SOURCE'] = "modelscope"
    for key, value in disscussion_analysis_info.items():
        start_page_id = value[0]
        end_page_id = value[1]
    """Use pipeline mode if your environment does not support VLM"""
    logger.info("start_page_id: {}, end_page_id: {}".format(start_page_id, end_page_id))
    md_content = parse_doc(doc_path_list, output_dir, backend="pipeline", start_page_id=start_page_id, end_page_id=end_page_id)
    result = {"md_content": md_content}
    return jsonify(result)
    

@app.route('/get_financial_metrics', methods=['POST'])
def get_financial_metrics():
    data = request.get_json()
    pdf_path = "pdf_path"
    toc_info = data.get('toc_info')
    extract_prompt = """
                    ## Task
                    根据需求，抽取目录信息中需要的章节信息，并返回抽取后的目录信息

                    ## Remember
                    1、JSON格式输出目录信息
                    2、只输出结果，不需要说明原因

                    ## Instruction
                    抽取目录章节信息中有关财务指标的章节信息，以元祖格式输出抽取后的目录信息
                    如果有多个财务指标章节，请全部输出

                    ## Output Example
                    {{'toc_info':
                        {{'财务指标': (这里是章节的页码范围)}}
                    }}

                    ## toc info
                    {}
                    """.format(toc_info)
    qwen_url = "https://jf-ai-llm.techgp.cn/jf-qwen-72b-server/v2/models/inference/generate"
    financial_metrics_info = parse_response(extract_prompt, qwen_url)
    logger.info("financial_metrics_info: {}".format(financial_metrics_info))

    pdf_suffixes = [".pdf"]
    image_suffixes = [".png", ".jpeg", ".jpg"]
    __dir__ = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(__dir__, "output")
    doc_path_list = []
    for doc_path in Path(pdf_path).glob('*'):
        if doc_path.suffix in pdf_suffixes + image_suffixes:
            doc_path_list.append(doc_path)
    # logger.info("doc_path_list: {}".format(doc_path_list))
    """如果您由于网络问题无法下载模型，可以设置环境变量MINERU_MODEL_SOURCE为modelscope使用免代理仓库下载模型"""
    os.environ['MINERU_MODEL_SOURCE'] = "modelscope"
    financial_metrics_content = ""
    for key, value in financial_metrics_info.items():
        start_page_id = value[0]
        end_page_id = value[1]
        if end_page_id - start_page_id > 50:
            end_page_id = start_page_id + 50
        logger.info("start_page_id: {}, end_page_id: {}".format(start_page_id, end_page_id))
        md_content = parse_doc(doc_path_list, output_dir, backend="pipeline", start_page_id=start_page_id, end_page_id=end_page_id)
        financial_metrics_content += md_content
    logger.info("financial_metrics_content: {}".format(financial_metrics_content[:1000]))
    get__metrics_prompt = """
                            ## 任务
                            从以下内容：{}
                            提取以下财务指标，其中“期末”指本报告期末，“期初”指本报告期初（即，上报告期末）
                            1. 基本每股收益
                            2. 总资产
                            3. 负债合计
                            4. 归母净利润
                            5. 扣非净利润
                            6. 营业收入
                            7. 营业成本
                            8. 归属于母公司的股东权益
                            9. 营业总收入 （注：营业总收入=营业收入+营业外收入）
                            10. 期初总资产
                            11. 期末总资产
                            12. 期初存货余额
                            13. 期末存货余额
                            14. 期初应收账款余额
                            15. 期末应收账款余额
                            16. 流动资产合计
                            17. 流动负债合计
                            18. 净利率

                            ## 要求
                            1. 金额指标的单位统一处理为“元”，比例指标的单位统一处理为“%”，其余指标沿用原有单位
                            2. 将财务指标的值放入同名json字段内，字段内包括具体数值和单位。例如：3.06%，19.16元/股，45,775,517,043.29元
                            3. JSON格式直接输出最终结果，禁止添加额外说明
                            4. 如果某个指标无法提取，则该字段为空
                            5. 请注意判断某些指标是否可以为负数，如营业成本
                            6. 如无法直接提取，请根据已有指标进行计算

                            ## 输出模版（JSON格式）
                            {{
                                '基本每股收益': '',
                                '归母净利润': '',
                                '扣非净利润': '',
                                '营业收入': '',
                                '营业成本': '',
                                '归属于母公司的股东权益': '',
                                '营业总收入': '',
                                '期初总资产': '',
                                '期末总资产': '',
                                '期初存货余额': '',
                                '期末存货余额': '',
                                '期初应收账款余额': '',
                                '期末应收账款余额': '',
                                '流动资产合计': '',
                                '流动负债合计': '',
                                '净利率': ''
                            }}
                            """.format(financial_metrics_content)

    financial_metrics = get_llm_answer(get__metrics_prompt)

    return jsonify({"financial_metrics": financial_metrics})

if __name__ == '__main__':
    app.run(debug=False, port=5000)