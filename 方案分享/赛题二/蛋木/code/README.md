
# 前置条件：
1. 使用conda env create -f environment.yml创建环境
2. .env设置apikey和url
3. 需要把测试 B 集放到当前文件夹路径（若使用别的数据集，需要修改file_chunk_processor.py、relevance_marker_agent.py、conflict_detection_agent.py、cqbl.py里面对应的文件路径）
4. 数据集data.jsonl中，需要把所有的"该产品的与保障相关的时间在各材料中的定义没有冲突"都改成"该产品的保障相关时间在各材料中的定义没有冲突"

# 处理流程：

## 数据预处理

1. md_cleaner.py
2. file_chunk_processor.py
    开始分析
3. relevance_marker_agent.py
4. conflict_detection_agent.py
5. 分析完毕后，在第三步“相关性标记”的时候若规则对应文件标记都为false，不会在result.jsonl结果文件里展示，需要调用cqbl.py进行查缺补漏，手动将result.jsonl里缺失的rule_id补充到result.jsonl中



## 具体文件说明可以参考技术报告内容