import asyncio
from Data_Acquire.fund_position import fund_position
from Data_Acquire.mcp_data import DataAcquire

#控制是否进行相应流程
do_mcp = True               # MCP数据获取开关
do_fund_position = False   # 基金持仓数据获取开关
do_summary = False          # 文本摘要生成开关
do_sentiment = False        # 情感分析数据获取开关
do_draw = False             # 数据可视化（VLM输入图片）绘图开关
do_vlm = False              # VLM数据特征开关
sentiment_cot = False       # 是否开启情感分析的思维链


if do_mcp:
    #MCP获取相关数据  -> MCP客户端代码在Data_Acquire/mcp_data.py中，服务端代码在Data_Acquire/MCP/server.py中
    da = DataAcquire()
    asyncio.run(da.mcp_get_data())
    
if do_fund_position:
    #获取基金持仓信息 -> 数据获取具体代码实现在Data_Acquire/fund_position.py中
    fund_position()
    
if do_summary:
    from Data_Acquire.summary_data import summary_data
    # 获取摘要数据。由于基金和市场数据众多，所以使用大模型综合这些数据生成摘要，具体实现代码在Data_Acquire/summary_data.py中
    # existed_data=True表示在已有一部分摘要数据的情况下只生成新增数据
    summary_data(existed_data = False)
    
if do_sentiment:
    from Data_Acquire.sentiment import get_sentiment
    # 基于生成的摘要，利用大模型分析情感，生成情感特征
    # cot参数控制是否开启模型的COT（开启COT -> 清晰的推理过程与可能更准确的结果，关闭COT -> 大大提升情感特征生成速度）
    # 具体代码实现在Data_Acquire/sentiment.py
    get_sentiment(cot = sentiment_cot)
    
if do_draw:
    from VLM.draw import draw
    #获取可视化数据
    # 读取基金申购赎回数据并生成可视化图像，具体代码在VLM/draw.py中
    draw(data_path = "Data/unprocessed_data/fund_apply_redeem_series.csv",save_path = "VLM/images/")
    
if do_vlm:
    from VLM.img_template import vlm_features
    #VLM分析可视化图像生成相关特征，具体代码在VLM/img_template.py中
    vlm_features(save_path="Data/VLM.csv")