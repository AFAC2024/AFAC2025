## 环境
### 硬件环境(训练)
H100 80G x 8
cpu x 128

### 软件环境
主要依赖包如下：
```
torch==2.5.1
ms-swift==3.5.0
accelerate==1.6.0
liger_kernel==0.5.10
transformers==4.51.3
vllm==0.7.3
vllm-flash-attn==2.6.1
```

## 代码tree
submit_code
├── README.md
├── eval_infer.sh  # b榜推理复现脚本
├── eval_model  #sft 之后的lora权重，后续推理需要和基座权重做merge
│   └── qwen2.5-14b
│       ├── checkpoint-882
├── export_eval.sh   # 权重merge脚本 
├── files   # 推理中间文件
├── gen_pseudo_train_data.py   # 生成伪标签脚本
├── merge_files.py   # 结果文件融合脚本，生成b榜最终提交文件
├── output   # sft 输出目录
├── requirements.txt
├── run.sh   # 复现训练脚本
├── run_classify_v1_a.py
├── run_classify_v1_b.py
├── run_classify_v3_b.py
├── run_infer_b.py
├── run_rag_ans_a.py
├── run_rag_ans_b.py
├── train.sh
├── 样例集
├── 测试 A 集
├── 测试 B 集


## 方案概述
这里主要描述下方案的主要思想，细节部分后续ppt会详细描述。
方案一：
i.使用qwen2.5-14B-1m模型对保险产品的每种类型材料进行内容精炼(根据校验规则进行精炼)；
ii.使用qwen2.5-14B-1m模型对保险产品材料的精炼内容进行两两规则冲突校验；
iii.基于上一步的两两材料间的校验结果，判断得到该产品最终的校验结果，得到一份结果文件；
效果：方案一在a榜得分85+，在b榜得分84+，完全无监督，无需训练。

方案二：
i.使用方案一可以在a榜得到一份测试集a的预测结果文件，使用这个结果作为伪标签，再结合官方提供的样例集的20条样本，通过数据增强的方式，构造1100条训练数据；
ii.基于上一步构造的训练数据，使用流水线并行的方式训练qwen2.5-14B-1m模型，然后在预测的时候，每条样本做过采样，预测多次，投票得到结果。
效果：a榜得分89+

方案融合：方案一的结果和方案二结果融合，a榜91+，b榜86+
融合细节：我们基于基于伪标签划分了验证集，发现方案一和方案二在不同的校验规则上的准确率标签不一样，一部分校验规则在方案一上准确率更好，
另一部分校验规则在方案二上准确率更好，预测我们把两个方案的结果根据校验规则的不同，做了结果的融合，在a榜和b榜都有1-2个点的提升。

其他方案：我们还尝试其他方案，这里不在赘述。

## 方案复现
### 数据准备
i.准备好 "测试 A 集"、"测试 B 集"和"样例集"三份数据放在当前目录
ii.把基座权重[Qwen2.5-14B-Instruct-1M]放在目录/mnt/model/Qwen2.5-14B-Instruct-1M中，后面统一读取这个目录的基座权重。

注意：
i.样例集中第六条数据：{"material_id": "m_00006s", "rule_id": "r_00006", "rule": "该产品的保障相关时间在各材料中的定义没有冲突", "result": false}，我手动改了(true改成false)
因为这条数据群里面有选手说这条样本结果不对，并且官方也出来确认了结果确实有误，由于后面用样本集构造训练数据，所以我改了这条样本。其他所有样本都没改动。
ii.Qwen2.5-14B-Instruct-1M基座权重地址：https://www.modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct-1M

### b榜结果复现
可以一键执行脚本：sh eval_infer.sh
也可以分步骤执行以下脚本：
```
# 合并lora权重
sh export_eval.sh

# 数据预处理
python run_rag_ans_b.py

# 方案一 结果推理
python run_classify_v1_b.py 4

#方案二 结果推理
python run_infer_b.py 4

#方案1和2的结果融合，生成提交文件
python merge_files.py
```
执行完成之后，files/merge.jsonl即为b榜最高分文件,得分为86+

注意：
i. python run_classify_v1_b.py 4 和 python run_infer_b.py 4  后面那个4是指定推理的卡数(指定为4或者2)，我们尝试了使用2卡推理和4卡推理，
    测试发现，在b榜上，4卡推理会比两卡推理高几个千分点，但是不管是2卡还是4卡，b榜得分排名并未改变，都是rank2。
    
ii. 方案一的结果文件为files/submit_v1_b.jsonl，b榜得分85分上下，
    方案二的结果文件为files/submit_v3_b.jsonl，b榜得分也在85分上下，
    方案一二融合文件为files/merge.jsonl,b榜得分为86+。

iii. 为了展示方案一和方案二各自的得分效果和整体方案的完整性，上述推理脚本中每个方案都跑完了b榜的所有样本(可独立测试每个方案效果)，实际上由于最终结果是方案1和2的结果融合，
融合规则：取方案一中["责任免除","基础产品销售信息","保障责任"]这三类校验规则的结果，再取方案二中除["责任免除","基础产品销售信息","保障责任"]这三类校验规则以外的规则的结果，二者合并得到最终
结果，也就是说方案一和方案二实际推理时，都只需要推理部分b榜的数据(而非全部)，真实耗时应该只有一半。


### 训练过程复现
一键执行脚本：sh run.sh
也可以分步骤执行以下脚本：
```
# 数据预处理
python run_rag_ans_a.py

# 方案一 a榜结果预测
python run_classify_v1_a.py

# 基于方案一 a榜结果和样例集构建训练数据
python gen_pseudo_train_data.py

#训练模型
sh train.sh

#合并lora权重
sh export.sh
```
上述脚本执行完之后，在目录output/qwen2.5-14b中会得到训练好的lora权重，有了这个权重，就可以走上述b榜结果复现的流程，注意：需要修改下lora权重的路劲。
由于方案一是基于开源基座(未经sft)推理的，方案二是基于微调之后的权重推理的，所以这里只需要把方案二的推理脚本[run_infer_b.py]中第74行代码改为model = "output/qwen2.5-14b/checkpoint-885-merged"
再重新跑一遍就行：
```
#方案二 结果推理
python run_infer_b.py 4

#方案1和2的结果融合，生成提交文件
python merge_files.py
```





















Total number of attention heads (40) must be divisible by tensor parallel size (3)