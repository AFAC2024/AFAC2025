from openai import OpenAI

##### API 配置 #####


functions = [
    {
        "name": "profitability_line",
        "description": "盈利能力指标图",
        "parameters": {
            "type": "object",
            "properties": {
                "x_data": {
                    "type": "string",
                    "description": "报告期"
                },
                "line1_data": {
                    "type": "float",
                    "description": "净利率数据列表"
                },
                "line2_data": {
                    "type": "float",
                    "description": "毛利率数据列表"
                },
                "line3_data": {
                    "type": "float",
                    "description": "ROE数据列表"
                }
            },
            "required": ["x_data", "line1_data", "line2_data", "line3_data"]
        }
    },
    {
        "name": "debt_paying_ability_line",
        "description": "偿债能力指标图",
        "parameters": {
            "type": "object",
            "properties": {
                "x_data": {
                    "type": "string",
                    "description": "报告期"
                },
                "line1_data": {
                    "type": "float",
                    "description": "净利率数据列表"
                },
                "line2_data": {
                    "type": "float",
                    "description": "毛利率数据列表"
                },
            },
            "required": ["x_data", "line1_data", "line2_data"]
        }
    },
    {
        "name": "operating_receipt_line",
        "description": "营业总收入图",
        "parameters": {
            "type": "object",
            "properties": {
                "x_data": {
                    "type": "string",
                    "description": "报告期"
                },
                "bar1_data": {
                    "type": "float",
                    "description": "营业总收入数据列表"
                },
                "line1_data": {
                    "type": "float",
                    "description": "同步增长率数据列表"
                },
            },
            "required": ["x_data", "bar1_data", "line1_data"]
        }
    }
]

# openai_api_key = "OGQ0ZTVkODdiNWUyYzA0NDljZmRlOGNiZDg3YmE2ZjYyOGMyMTI0ZQ=="
# openai_api_base = "http://1218137459707574.cn-beijing.pai-eas.aliyuncs.com/api/predict/jf_ds_r1_server/v1"

# openai_api_key = "empty"
# openai_api_base = "http://47.117.133.205:8000/v1"

openai_api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "deepseek-r1"
openai_api_key = "Bearer sk-3HBpGkNspl"

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

# models = ["DeepSeek-R1"]
# model = models.data[0].id
# model="DeepSeek-R1"
# model = "deepseek-r1"


def generate(prompt, stream_flag):
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
        model=model,
        functions=functions,
        function_call="auto",
        max_completion_tokens=32768,
        stream=stream_flag,
        temperature=0.6
    )

    if stream_flag:
        # print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")

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
        return answer_content
    else:
        result = stream.choices[0].message.content
        return result
