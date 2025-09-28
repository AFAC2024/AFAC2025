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