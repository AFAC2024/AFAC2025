# import os
# from openai import OpenAI
# os.environ['OPENAI_API_KEY'] = ""
# client = OpenAI(base_url="http://v2.open.venus.oa.com/llmproxy")
# def resres(text,temperature):
#     response = client.chat.completions.create(
#     model="qwen3-235b-a22b-fp8-local-II",
#     temperature=temperature,
#     messages=[{"role": "user", "content": text}]
#     )
#     result = {
#         'content': '',
#         'reasoning': ''
#     }
    
#     if hasattr(response, 'choices'):
#         for choice in response.choices:
#             if hasattr(choice, 'message'):
#                 result['content'] = getattr(choice.message, 'content', '')
#                 result['reasoning'] = getattr(choice.message, 'reasoning_content', '')
    
#     return result
# print(resres('''请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，你要给出解决问题的思考过程和最终答案。你要首先在头脑中思考推理过程，然后向用户提供答案。我保证问题拥有明确的唯一答案，能够基于规则客观评估正确性，最后，答案要用 \\boxed{A/B/C/D} 的形式输出。\n问题：\n甲公司2020年度进行了如下投资：\n（1）甲公司和A公司为同一母公司最终控制下的两家公司。2020年1月1日，甲公司向其母公司支付现金500万元，取得母公司拥有A公司100%的股权，于当日起能够对A公司实施控制。合并日A公司的净资产账面价值450万元，合并后A公司仍维持其独立法人地位继续经营，甲公司、A公司在合并前采用的会计政策相同。\n（2）2月10日，委托证券公司从二级市场购入B公司股票400万股，支付价款1 224万元（含已宣告但尚未发放的现金股利24万元），另支付相关交易费用8万元。甲公司取得B公司股票后，将其作为交易性金融资产核算。2月18日，收到价款中包含的现金股利24万元。\n（3）7月1日，购入C公司股票580万股，支付价款4 600万元，每股价格中包含已宣告但尚未发放的现金股利0.25元。占C公司有表决权股份的25%，对C公司的财务和经营决策具有重大影响，甲公司将其作为长期股权投资核算。\n同日C公司净资产的账面价值（与其公允价值不存在差异）为18 000万元。2020年7月1日至12月31日，C公司实现净利润600万元，宣告分配现金股利400万元。\n（4）12月31日，甲公司将持有的C公司股票出售，取得价款5 000万元。\n要求：根据上述资料，不考虑其他相关因素，分析回答下列小题。（答案中的金额单位用万元表示）\n根据资料（3），针对C公司长期股权投资说法正确的是（　　）。\nA.长期股权投资入账价值为4 500万元\nB.应确认投资收益180万元\nC.应确认其他综合收益100万元\nD.12月31日账面价值4 712万元(你只需要简单的思考，这个问题很简单，不要想复杂了)''',0.8))

from multiprocessing import Process, Queue
import csv
import re
from tqdm import tqdm
import os
from openai import OpenAI
import time
os.environ['OPENAI_API_KEY'] = ""
client = OpenAI(base_url="http://v2.open.venus.oa.com/llmproxy")
def resres(query, temperature):
    response = client.chat.completions.create(
    model="deepseek-r1-local-III", # deepseek-v3-local-II
    temperature=temperature,
    messages=[{"role": "user", "content": query}]
    )
    result = {
        'content': '',
        'reasoning': ''
    }
    #print(response)
    if hasattr(response, 'choices'):
        for choice in response.choices:
            if hasattr(choice, 'message'):
                result['content'] = getattr(choice.message, 'content', '')
                result['reasoning'] = getattr(choice.message, 'reasoning_content', '')
    if result['content']:
        return result['content']
    else:
        return result['reasoning']

def extract_boxed_content(text):
    """
    从文本中提取最后一个\boxed{}内的内容
    """
    pattern = r'\\boxed{([^{}]+)}'
    matches = re.findall(pattern, text)
    return matches[-1] if matches else ""

import csv
prompt='''\n值得注意的是，思考过程应该简洁，不要复述输入和条件，不要进行反思
'''
p='''请你扮演一位金融和会计领域专家，你会面临用户提出的一些问题，请你使用一句话进行解释，然后向用户提供答案。例如：\n        input: 中国金融市场上现有的金融衍生产品不包括____。\nA,风险类\nB,利率类\nC,权益类\nD,货币类,\n        output: 按照利率类、权益类、货币类、商品类和信用类五个分类标准，中国现有的衍生产品包括以下几类。\\boxed{A}\n        input: ____不是金融衍生工具的特征之一。\nA,依赖于原生性金融工具\nB,表现为一种合约\nC,合约上载明交易品种、价格、数量、交割时间及地点等\nD,可以作为支付工具进行交易,\n        output: 金融衍生工具是指价值依赖于原生性金融工具的一类金融产品，在形式上均表现为一种合约，在合约上载明买卖双方同意的交易品种、价格、数量、交割时间及地点等。\\boxed{D}\n我保证问题有且只有唯一答案，能够基于规则客观评估正确性，最后，答案要用 \\boxed{A/B/C/D} 的形式输出。
'''
def process_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')
        
        for row in reader:
            if len(row) >= 3:  # 确保有第四列
                original_text = row[2]
                
                processed_text = resres(p+original_text+prompt, 0.25).replace("\n", "")
                time.sleep(1)
                new_text = processed_text
                
                # 更新第四列
                row[2] = new_text
            
            # 立即写入当前行
            writer.writerow(row)
            outfile.flush()  # 确保立即写入磁盘

# input_filename = 'input-ds.csv'
# output_filename = 'input-ds-output.csv'
input_filename = 'self-instruct.csv'
output_filename = 'self-instruct-output.csv'
process_file(input_filename, output_filename)
