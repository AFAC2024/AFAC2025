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
    request_config = RequestConfig(max_tokens=5000, temperature=2)
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
    content1 = get_res(content1)
    content2 = get_res(content2)
    p = prompt.format("{}({})".format(module_name,col_dic[module_name]),content1,content2).strip()
    return p


if __name__ == '__main__':
    model = "/mnt/model/Qwen2.5-14B-Instruct-1M"
    engine = VllmEngine(model,gpu_memory_utilization=0.9,tensor_parallel_size=4,seed=42)
    
    data = json.load(open("files/rag_answer_a.json","r"))
    result = []
    for x in tqdm(data):
        new_compare = []
        docs = x["summary"]
        docs = [x for x in docs if "没有相关信息" not in x]
        for i in range(len(docs)):
            for j in range(i+1,len(docs)):
                p = analysis_conflict_prompt(x["module_name"],docs[i],docs[j])
                r = infer_batch([p])[0]
                new_compare.append({"pos":[i,j],"result":r})
        x["compare"] = new_compare
        result.append(x)
    
    json.dump(result,open("files/result_info_v1_a.json","w"),ensure_ascii=False,indent=4)
        
    
    data = [json.loads(x.strip()) for x in open("测试 A 集/data.jsonl")]
    info = json.load(open("files/result_info_v1_a.json","r"))
    
    n=0
    tmp = []
    result = []
    for i in range(len(data)):
        item = data[i]
        r = [1 if "是"==x["result"][:1] else 0 for x in info[i]["compare"]]
        if not r:
            r = [0]
        ratio = sum(r)/len(r)
        tmp.append(ratio)
        if ratio>0:
        # if ratio>0.3:
            item["result"] = False
        else:
            n+=1
            item["result"] = True
        result.append(item)
    
    with open("files/submit_v1_a.jsonl","w") as f:
        for x in result:
            f.write("{}\n".format(json.dumps(x,ensure_ascii=False)))
    print(n)
