from vllm import LLM, SamplingParams
import base64
import re
import glob
import pandas as pd



def encode_image(image_path):
    """
    将图像文件编码为base64字符串
    
    参数:
        image_path (str): 图像文件路径
    
    返回:
        str: base64编码的图像字符串
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
def vlm_features(save_path):
    """
    使用视觉语言模型分析基金申购赎回图表，提取特征并保存结果
    
    参数:
        save_path (str): 结果保存路径（CSV文件）
    """
    # 创建空的DataFrame用于存储结果
    df = pd.DataFrame(columns=['file', 'apply', 'redeem'])
    # 初始化视觉语言模型
    llm = LLM(model="Qwen2.5-VL-7B-Instruct")
    # 设置采样参数
    sampling_params = SamplingParams(temperature=0.5,max_tokens=2048)
    # 递归查找所有jpg图像文件
    for image_path in sorted(glob.glob('**/*.jpg', recursive=True)):
        # 将图像编码为base64字符串
        base64_image = encode_image(image_path)
        print(image_path)
        # 构建对话内容，包含系统提示和用户请求
        conversation = [
            {
                "role": "system",
                "content": "You are a helpful assistant"
            },
            {
                "role": "user",
                "content": [
                {"type": "text", "text": '''你的任务是对给定的K线图进行分析，分别对申购量(蓝色)和赎回量(橙色)给出未来趋势的预测。
    在分析K线图时，请考虑以下几个方面：
    1. 蜡烛图形态：如十字星、锤子线、吞没形态等，这些形态能反映多空双方力量对比和市场情绪。
    2. 均线系统：短期、中期和长期均线的排列和交叉情况，可判断市场的趋势方向和强度。
    3. 成交量：成交量的变化能验证价格趋势的可靠性。
    4. 支撑位和阻力位：确定价格可能遇到的支撑和阻力水平。
    请先在<思考>标签中详细分析K线图的特征，结合上述几个方面阐述你的分析过程。然后在<预测>标签中给出对未来趋势的预测，1表示上涨，-1表示下跌，0表示无明确指向，如果无法分析也用0表示。请确保你的分析和预测基于K线图的实际情况，回答要丰富、全面。 
    回答格式：
    <思考>
    [在此详细分析K线图的特征和分析过程]
    </思考>
    <申购量预测>
    0,1或-1
    </申购量预测>
    <赎回量预测>
    0,1或-1
    </赎回量预测>
    '''},
                    {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                    },
                ],
            },
        ]
        # 使用模型进行推理
        outputs = llm.chat(conversation,
                        sampling_params=sampling_params,
                        use_tqdm=False)
        text = outputs[0].outputs[0].text
        # 使用正则表达式提取申购量预测结果
        pattern = r'<申购量预测>(.*?)</申购量预测>'
        matches1 = re.findall(pattern, text, re.DOTALL)
        # 使用正则表达式提取赎回量预测结果
        pattern = r'<赎回量预测>(.*?)</赎回量预测>'
        matches2 = re.findall(pattern, text, re.DOTALL)
        # 构建新数据记录
        new_data = {
            'file': f'{image_path}'[4:],
            'apply': f'{matches1[0] if matches1 else 0}',
            'redeem': f'{matches2[0] if matches2 else 0}'
        }
        # 将新数据添加到DataFrame中
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    # 将结果保存为CSV文件
    df.to_csv(save_path, index=False)
