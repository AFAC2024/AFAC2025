#合并lora权重
sh export_eval.sh

#数据预处理
python run_rag_ans_b.py

# 方案一 结果推理
python run_classify_v1_b.py 4

# 方案二 结果推理
python run_infer_b.py 4

#方案1和2的结果融合，生成提交文件
python merge_files.py

