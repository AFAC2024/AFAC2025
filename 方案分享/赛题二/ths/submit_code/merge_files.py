import json
sft_data  = [json.loads(x.strip()) for x in open("files/submit_v3_b.jsonl","r")]
raw_data = [json.loads(x.strip()) for x in open("files/submit_v1_b.jsonl","r")]
result = []
col_dic = set()
tgt_col = ["责任免除","基础产品销售信息","保障责任"]
for i in range(len(sft_data)):
    rule = sft_data[i]["rule"].replace("该产品的", "").replace("在各材料中的定义没有冲突", "")
    if rule in tgt_col:
        sft_data[i]["result"] = raw_data[i]["result"]
        col_dic.add(rule)

    result.append(sft_data[i])

with open("files/merge.jsonl","w") as f:
    for x in result:
        if "context_length" in x:
            del x["context_length"]
        f.write("{}\n".format(json.dumps(x,ensure_ascii=False)))

print(col_dic)