import pprint
import urllib.parse
import json
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.utils.output_beautify import typewriter_print
from loguru import logger
from openai import OpenAI
import re


agent_llm_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
agent_llm_name = "deepseek-r1"
agent_llm_key = "Bearer sk-3HBpGkNspl"

client = OpenAI(
    api_key=agent_llm_key,
    base_url=agent_llm_url,
)

# 步骤 2：配置您所使用的 LLM。
llm_cfg = {
    # 使用 DashScope 提供的模型服务：
    'model': agent_llm_name,
    'model_type': 'qwen_dashscope',
    'api_key': agent_llm_key,
}

tools = ['code_interpreter']
Bot = Assistant(llm=llm_cfg, function_list=tools)

def get_llm_answer(prompt):
    stream_flag = True
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""  # 定义完整回复
    is_answering = False  # 判断是否结束思考过程并开始回复

    stream = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=agent_llm_name,
        max_completion_tokens=4096,
        stream=stream_flag,
    )

    if stream_flag:
        print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

        for chunk in stream:
            # 如果chunk.choices为空，则打印usage
            if not chunk.choices:
                print("\nUsage:")
                print(chunk.usage)
            else:
                delta = chunk.choices[0].delta
                # 打印思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                    print(delta.reasoning_content, end='', flush=True)
                    reasoning_content += delta.reasoning_content
                else:
                    # 开始回复
                    if delta.content != "" and is_answering == False:
                        print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                        is_answering = True
                    # 打印回复过程
                    print(delta.content, end='', flush=True)
                    answer_content += delta.content
        final_answer = answer_content
    else:
        final_answer = stream.choices[0].message.content
        logger.info(final_answer)
    return final_answer

def get_metrics_data(value, metric):
    prompt = """
                ## Task
                当前时间是2025年07月，请使用akshare（已安装，pandas已安装）的接口{}获取{}指标最近五年（2021~2025）数据输出到json中；
                如果是季度或月度数据，则先求和再求平均输出到json中，禁止其他任何说明

                ## Output
                ```json
                {{data:{{}}}}
                ```
                """.format(value, metric)
    messages = [{'role': 'user', 'content': prompt}]
    try:
        for response in Bot.run(messages=messages):
            pass
        logger.info("response: {}".format(response))
        content = response[-1]['content'].replace("\n","")
        if content.startswith("```json") and content.endswith("```"):
            json_data = eval(content[7:-3])
        else:
            # 正则表达式匹配
            pattern = r"\{[\s\S]*\}"
            match = re.search(pattern, content)
            if match:
                json_data = eval(match.group())
    except:
        json_data = {"data": None}
    return json_data

def get_macro_metrics(report_frame):    
    with open("macro_interfaces.json", "r", encoding="utf-8") as f:
        macro_metrics = json.load(f)

    get_ak_indexs_prompt = """
    ## 任务
    结合研报框架和宏观数据要求，在akshare api中筛选出需要的宏观数据指标(akshare已安装完成)，如果没有，则忽略，json格式输出,禁止其他任何说明

    ## output
    ```json
    {{
        data: [
            {{"中国宏观杠杆率": "macro_cnbs"}},
            ...
        ]
    }}
    ```
    ## akshare api
    {}
    
    ## 研报框架
    {}

    ## 宏观数据要求
    |分析模块|数据大类|具体数据指标|数据维度与特征|
    |:---:|:---:|:---:|:---:|
    |1.核心指标自动抽取与呈现|宏观经济指标|经济增长：GDP 及其分项、工业增加值、发电量、货运量\n通货膨胀：CPI、PPI、核心 CPI\n就业与收入：城镇调查失业率、新增就业人数、居民可支配收入\n消费：社会消费品零售总额\n投资：固定资产投资（FAI）、房地产开发投资贸易：进出口总额、贸易差额、主要商品进出口量价|频率：月度 / 季度 / 年度\n地域：国家 / 省份 / 主要城市类型：数值型时间序列|
    ||金融市场指标|利率：央行政策利率（MLF、LPR）、银行间市场利率（SHIBOR、DR007）、国债收益率曲线\n汇率：人民币兑主要货币汇率（USD/EUR/JPY）、人民币汇率指数（CFETS）\n货币供应：M0、M1、M2信贷：新增人民币贷款、社会融资规模（社融）及其分项|频率：每日 / 每周 / 每月\n地域：全国类型：数值型时间序列|
    |2.政策报告与关键口径解读|政策文件与官方表态|政府工作报告、中央经济工作会议公报、政治局会议公报\n央行货币政策执行报告、金融稳定报告\n部委（发改委、财政部等）政策文件新闻发布会实录、官方答记者问、领导讲话|频率：事件驱动\n地域：国家级类型：文本 / 事件型|
    ||政策操作|央行公开市场操作（OMO）规模与利率\n存款准备金率（RRR）调整历史\n中期借贷便利（MLF）操作规模与利率财政存款、国库现金管理等|频率：每日 / 每周 / 事件驱动类型：数值 / 事件型|
    |3.政策联动与区域对比分析|传导路径分析数据|综合模块 1 和 2 数据，例如 “降准→出口与 CPI” 路径：\n降准公告（政策事件）\nSHIBOR/DR007（流动性）\nM2 / 社融（信用扩张）\n固定资产投资 / PMI（实体经济）\n汇率（出口影响）\n出口同比（结果）7. PPI/CPI（结果）|频率：高频（日 / 月）\n地域：全国及省份对比类型：数值 / 事件型|
    ||区域经济数据|各省市 GDP、工业增加值、固投、消费、进出口、财政收支、房价等|频率：月度 / 季度 / 年度\n地域：省 / 自治区 / 直辖市类型：数值型|
    |4.全球视野的模拟建模|全球宏观经济|主要经济体（美 / 欧 / 日 / 英等）GDP、CPI、失业率、PMI 等核心指标|频率：月度 / 季度\n地域：全球主要国家类型：数值型|
    ||全球金融市场|利率：美联储利率、欧央行利率、日央行利率、10 年期国债收益率\n汇率：美元指数（DXY）、主要货币对汇率\n资本流动：全球 FDI、证券投资、国际收支平衡表大宗商品：原油价格、LME 铜价、BDI 指数|频率：每日 / 每周 / 每月\n地域：全球类型：数值型|
    |5.“灰犀牛” 事件风险预警|房地产风险|70 城 / 百城房价指数、商品房销售数据\n房企债务（美元债）规模与到期情况居民杠杆率、个人住房贷款余额、土地出让金收入|频率：月度 / 季度\n地域：全国 / 重点城市类型：数值型|
    ||地方政府债务风险|地方政府债券发行量与收益率\n地方融资平台（LGFV）有息债务规模、债券利差地方财政自给率、土地财政依赖度|频率：月度 / 季度 / 年度\n地域：各省市类型：数值型（部分|
    ||金融系统风险|商业银行不良贷款率（NPL）、拨备覆盖率\n银行间市场信用利差（如 AA + 城投债 - 国债）影子银行规模估算、企业债券违约数据|频率：月度 / 季度\n地域：全国类型：数值型|
    ||外部冲击与供应链风险|主要贸易伙伴经济状况、地缘政治风险指数\n关键技术 / 商品进口依赖度港口吞吐量、集装箱运价指数（如 SCFI）|频率：每日 / 每周 / 每月\n地域：全球 / 特定国家类型：数值 / 指数 / 文本型|

    """.format(macro_metrics, report_frame)
    metrics = get_llm_answer(get_ak_indexs_prompt)
    metrics = metrics.replace("\n", "")
    if metrics.startswith("```json") and metrics.endswith("```"):
        metrics = eval(metrics[7:-3])
    else:
        # 正则表达式匹配
        pattern = r"\{[\s\S]*\}"
        match = re.search(pattern, metrics)
        if match:
            metrics = eval(match.group())
    logger.info("metrics: {}".format(metrics))

    for metric_data in metrics["data"]:
        for key, value in metric_data.items():
            metric = key
        prompt = """
                ## Task
                当前时间是2025年07月，请使用akshare（已安装，pandas已安装）的接口{}获取{}指标最近五年（2021~2025）数据输出到json中；
                如果是季度或月度数据，则先求和再求平均输出到json中，禁止其他任何说明

                ## Output
                ```json
                {{data:{{}}}}
                ```
                """.format(value, metric)
        bot = Assistant(llm=llm_cfg, function_list=tools)
        messages = [{'role': 'user', 'content': prompt}]
        try:
            for response in bot.run(messages=messages):
                print(response)
            print(response)
            content = response[-1]['content'].replace("\n","")
            if content.startswith("```json") and content.endswith("```"):
                json_data = eval(content[7:-3])
            else:
                # 正则表达式匹配
                pattern = r"\{[\s\S]*\}"
                match = re.search(pattern, content)
                if match:
                    json_data = eval(match.group())
        except:
            json_data = {"data": None}
        metric_data["data"] = json_data["data"]

    return metric_data


def confirm_metrics(theme, report_content, financial_data):
    prompt = """
            ## 角色
            你是一位首席金融分析师，掌握个股研报、行业研报、宏观研报的撰写方法。你的任务是在正文中合适的位置插入图表，实现图文结合。你需要：
            1. 在需要插图的段落末尾添加图表标签，格式“<${{图表名称}}end>”
            2. 明确每张图表所用的金融指标名称、图表形式

            ## 要求
            1. 输出的JSON对象需要包括：
            1）**正文内容**
            - 包含图表标签的正文内容
            - 放入"content"字段，字段内使用markdown格式
            2）**图表设计规范**
            - 按照以下格式输出：
                | 图表标签 | 图表名称 | 所用金融指标名称（中） | 图表形式 |
                | :--- | :--- | :--- | :--- |
                | ${{图表标签}} | ${{图表名称}} | ${{所用金融指标名称}} | ${{图表形式}} |
            - 输出示例：
                | 图表标签 | 图表名称 | 所用金融指标名称（中） | 图表形式 |
                | :--- | :--- | :--- | :--- |
                | <盈利能力end> | 盈利能力 | 净利率、毛利率、ROE | 折线图 |
            - 放入"diagram"字段，字段内使用markdown格式
            2. JSON格式直接输出最终结果，禁止添加额外说明

            ## 要求
            1. 只允许使用所提供的金融指标，禁止自行拓展；一个图表中可以使用多个指标
            2. 图表形式禁止设计为简单的数据表格
            3. 除了添加图表标签外，禁止修改研报内容

            ## 输出模版（JSON格式）
            {{
                "content": "",
                "diagram": ""
            }}

            ## 研报主题
            宏观：{}

            ## 研报内容
            {}

            ## 可用金融数据
            ### 阅读说明
            {{
                "这里是指标名称（中）": "这里是指标名称（英）"
                "data": "这里是数据详情"
            }}

            ### 具体数据
            {}
            """.format(theme, report_content, financial_data)
    # result = get_llm_answer(prompt)
    # logger.info("result: {}".format(result))
    # diagram = eval(result)["diagram"]
    diagram = {"diagram": "| 图表标签 | 图表名称 | 所用金融指标名称（中） | 图表形式 |\n| :--- | :--- | :--- | :--- |\n| <中美云厂商资本开支对比end> | 中美云厂商资本开支 | 中国城镇固定资产投资、美国GDP | 对比柱状图 |\n| <算力需求驱动因素end> | 算力需求驱动因素 | 工业增加值增长、社会消费品零售总额 | 雷达图 |\n| <中美技术国产化率对比end> | 中美技术国产化率 | 以美元计算进口年率、以美元计算出口年率 | 双折线图 |\n| <融资缺口结构end> | 融资缺口结构 | 社会融资规模增量、新增人民币贷款 | 堆叠面积图 |\n| <AI投资对GDP贡献end> | AI投资对GDP贡献 | 美国GDP、中国城镇固定资产投资 | 组合折线图 |\n| <政策驱动投资增长end> | 政策驱动投资增长 | 中国城镇固定资产投资、工业品出厂价格指数（PPI） | 组合柱状图 |\n| <估值溢价变动趋势end> | 估值溢价变动趋势 | 美国CPI月率、城镇调查失业率 | 双轴折线图 |"}
    diagram2json_prompt = """
        将输入的markdown表格内容{}转换为json格式，输出json对象，禁止任何说明
        输出格式：
        {{"chart_label": "图片名称", "indicators": "金融指标名称", "chart_type": "图表形式"}}
    """.format(diagram)
    diagram2json_result = get_llm_answer(diagram2json_prompt)
    logger.info("diagram2json_result: {}".format(diagram2json_result))
    try:
        diagram2json_result = eval(diagram2json_result)
    except:
        pattern = r"\{[\s\S]*\}"
        match = re.search(pattern, diagram2json_result)
        if match:
            diagram2json_result = eval(match.group())
    return diagram2json_result
    


def draw_metrics(chart_type, chart_data, chart_name):
    prompt = """
        ## ENV
        matplotlib已安装
        ## Task
        使用给定数据绘图,并标明数据类别，图表类型为{},图片名为{}，绘制完成后输出图片的绝对路径地址，以json格式输出，禁止任何说明

        ## Output
        ```json
        {{chart_dir: "绝对路径"}}
        ```
        ## data
        {}
        
        """.format(chart_type, chart_name, chart_data)
    bot = Assistant(llm=llm_cfg, function_list=tools)
    messages = [{'role': 'user', 'content': prompt}]
    print(messages)
    try:
        for response in bot.run(messages=messages):
            print(response)
        print(response)
        content = response[-1]['content'].replace("\n","")
        if content.startswith("```json") and content.endswith("```"):
            json_data = eval(content[7:-3])
        else:
            # 正则表达式匹配
            pattern = r"\{[\s\S]*\}"
            match = re.search(pattern, content)
            if match:
                json_data = eval(match.group())
    except:
        json_data = {"chart_dir": None}
    logger.info("json_data: {}".format(json_data))
    return json_data

