import swift
from swift.llm import InferEngine, InferRequest, PtEngine, RequestConfig, load_dataset
from swift.plugin import InferStats
from swift.llm import VllmEngine
import sys
import os
import pandas as pd
import glob, json, re
import numpy as np
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3'
from tqdm import tqdm

model = "/mnt/model/Qwen2.5-14B-Instruct-1M"
model_name = model.strip().split("/")[-1]
print("load model weight：{}".format(model))
max_background_length =100000000000000 if "1m" in model_name or "1M" in model_name else 130000


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

def infer_batch(qs):
    infer_requests = [InferRequest(messages=[{'role': 'user', 'content':q}]) for q in qs]
    request_config = RequestConfig(max_tokens=5000, temperature=0)
    resp_list = engine.infer(infer_requests, request_config)
    res = [x.choices[0].message.content for x in resp_list]
    res = [get_res(x) for x in res]
    return res

def get_res(text):
    if "</think>" in text:
        text = text[text.find("</think>")+8:].strip().replace("<|endoftext|>","").strip()
    return text

def exteract_module_text_prompt(module_name, lines):
    prompt = """
    你是一个专业的保险行业的信息处理专家,请你基于产品背景材料回答用户问题。如果没有答案，请返回"没有相关信息",请直接返回答案，无需额外说明。
    用户问题：{}
    产品背景材料：{}
    """
    p = prompt.format("该产品的{}({})是什么？".format(module_name,col_dic[module_name]),lines).strip()
    return p[:max_background_length]

def analysis_conflict_prompt(module_name,content1, content2):
    prompt = """
    你是一个专业的保险行业的信息处理专家,请你判断产品1和产品2关于{}的描述信息是否有明显冲突，请直接返回是或者否，无需额外说明。
    产品1描述信息：{}
    
    产品2描述信息：{}
    """
    p = prompt.format("{}({})".format(module_name,col_dic[module_name]),content1,content2).strip()
    return p


if __name__ == '__main__':
    engine = VllmEngine(model,gpu_memory_utilization=0.9,tensor_parallel_size=4,seed=42)
    
    info = []
    for row in tqdm(pd.read_json("测试 A 集/data.jsonl", lines=True).iloc[:].iterrows(),total=200):
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
    
        qa_list = [exteract_module_text_prompt(module_name,module_content[col]) for col in module_content]
        qa_list = infer_batch(qa_list)        
        tmp_info = {"material_id":row[1].material_id,"module_name":module_name,"summary":qa_list}
        info.append(tmp_info)
    
    json.dump(info,open("files/rag_answer_a.json","w"),ensure_ascii=False,indent=4)

