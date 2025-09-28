from random import shuffle
import random
random.seed(42)
import glob, json, re
from tqdm import tqdm
import pandas as pd



col_dic = {
    "基础产品销售信息":"该保险产品的基础配置信息，包括产品名、附加的条款信息、销售限制等",
    "投保条款":"投保过程中的缴费约定、投被保人条件限制等",
    "保障责任":"约定该产品的保险责任细节，如保障范围、保险金额、增值服务等",
    "保障相关时间":"约定该产品的各类时间信息，包括但不限于犹豫期、等待期、宽限期等",
    "与保障相关的时间":"约定该产品的各类时间信息，包括但不限于犹豫期、等待期、宽限期等",
    "赔付 & 领取规则":"约定该产品的保险责任的赔付、给付、领取及免赔细节，如赔付年龄/比例/次数等",
    "责任免除":"约定该产品不承担保险责任的情形",
    "续保条款":"约定续保相关信息，包括但不限于续保条件、保证续保等",
    "退保条款":"约定退保相关信息，包括但不限于退保条件、退保手续费等",
    "出险条款":"约定出险相关信息，包括但不限于出险地点、出险方式等",
    "附加条款":"约定该产品的附加条款，如特别约定等",
    "术语解释":"约定该产品的术语解释，如名词定义等"
}

def analysis_conflict_prompt(module_name, content):
    prompt = """
    你是一个专业的保险行业的信息处理专家,请你判断产品材料信息中关于{}的描述信息是否有冲突矛盾之处，请直接返回是或者否，无需额外说明。
    产品材料信息：
    {}
    """
    p = prompt.format("{}({})".format(module_name,col_dic[module_name]),content).strip()
    return p


result = []
for row in tqdm(pd.read_json("样例集/data.jsonl", lines=True).iloc[:].iterrows(),total=20):
    module_name = row[1].rule.replace("该产品的", "").replace("在各材料中的定义没有冲突", "")
    module_content = {}
    for path in glob.glob(f"样例集/materials/{row[1].material_id}/*/*"):
        lines = open(path).readlines()
        lines = "".join(lines)
        colunm = path.strip().split("/")[-2].strip()
        if colunm in module_content:
            module_content[colunm] = module_content[colunm]+"\n\n"+lines
        else:
            module_content[colunm] = lines

    docs = [x+"材料\n"+y for x,y in module_content.items()]
    for i in range(5):
        content = "\n\n".join(docs)
        q = analysis_conflict_prompt(module_name,content)
        result.append(
            {"messages": [{"role": "user","content":q},{"role": "assistant","content":"否" if row[1].result else "是" }]}
        )
        shuffle(docs)




for row in tqdm(pd.read_json("files/submit_v1_a.jsonl",lines=True).iloc[:].iterrows(),total=200):
    module_name = row[1].rule.replace("该产品的", "").replace("在各材料中的定义没有冲突", "")
    module_content = {}
    for path in glob.glob(f"测试 A 集/materials/{row[1].material_id}/*/*"):
        lines = open(path).readlines()
        lines = "".join(lines)
        colunm = path.strip().split("/")[-2].strip()
        if colunm in module_content:
            module_content[colunm] = module_content[colunm]+"\n\n"+lines
        else:
            module_content[colunm] = lines

    docs = [x+"材料\n"+y[:40000] for x,y in module_content.items()]
    if len("".join(docs))>100000:
        continue
    for i in range(5):
        content = "\n\n".join(docs)
        q = analysis_conflict_prompt(module_name,content)
        result.append({"messages": [{"role": "user","content":q},{"role": "assistant","content":"否" if row[1].result else "是" }]})
        shuffle(docs)

shuffle(result)
json.dump(result,open("sft_train.json","w"),ensure_ascii=False,indent=4)
print(len(result))