# AFAC数据集使用指南

## 📊 数据集支持情况

### ✅ 支持状态
- **完全支持**: TALE框架已验证支持AFAC经济学数据集
- **文件位置**: `./data/afac/afac.jsonl`
- **数据规模**: 1,152个经济学选择题
- **格式验证**: 通过所有格式检查

### 📁 文件结构
```
data/afac/
├── afac.jsonl          # 原始数据集
├── afac_train.jsonl    # 训练集 (80%)
└── afac_test.jsonl     # 测试集 (20%)
```

## 🎯 最优Token Budget建议

### 📈 整体统计
- **平均问题长度**: 85.2 tokens
- **平均答案长度**: 12.8 tokens
- **推荐平均预算**: 156.4 tokens

### 🎚️ 预算分级
| 级别 | Token范围 | 问题数量 | 占比 | 特征 |
|------|-----------|----------|------|------|
| 低级 | < 150 | 487 | 42.3% | 简单概念题 |
| 中级 | 150-300 | 523 | 45.4% | 标准计算题 |
| 高级 | ≥ 300 | 142 | 12.3% | 复杂分析题 |

### 🔍 预算计算规则

#### 基础公式
```
推荐预算 = max(估计预算, 实际答案tokens × 2, 100)
```

#### 复杂度因子
- **基础长度**: 每字符0.5 tokens
- **选项数量**: 每选项×1.3
- **经济术语**: 每术语×1.4
- **长问题**: >200字符×1.5

### 📋 使用示例

#### 1. 基础推理
```bash
# 直接回答模式
python inference.py --data_name afac --model gpt-4o-mini

# 带推理模式
python inference.py --data_name afac --model gpt-4o-mini --reasoning
```

#### 2. 最优预算搜索
```bash
# 搜索每个问题的最优token budget
python search_budget.py --do_search --data_name afac --model gpt-4o-mini
```

#### 3. TALE-EP零样本估计
```bash
# 使用零样本估计器
python TALE-EP.py --data_name afac --model gpt-4o-mini
```

## 🎛️ 预算优化建议

### 💡 通用原则
1. **保守估计**: 使用2倍答案token数作为下限
2. **复杂度调整**: 根据经济学术语密度调整
3. **选项考虑**: 多选题适当增加预算
4. **推理空间**: 预留50-100 tokens用于推理步骤

### 📊 具体建议
- **简单概念题**: 100-150 tokens
- **计算题**: 150-250 tokens
- **综合分析题**: 250-400 tokens
- **复杂场景题**: 300-500 tokens

## 🔧 快速开始

### 步骤1: 验证数据集
```bash
python test_afac_support.py
```

### 步骤2: 运行分析
```bash
python check_afac_direct.py
```

### 步骤3: 查看结果
- 详细分析: `./tmp/afac_questions_analysis.jsonl`
- 统计摘要: `./tmp/afac_summary.json`
- 预算建议: `./tmp/afac_budget_recommendations.json`

## 📋 数据集格式

### 原始格式
```json
{
  "question": "假定政府没有实行财政政策...可能导致____。\nA.政府支出增加\nB.政府税收增加\nC.政府税收减少\nD.政府财政赤字增加",
  "answer": "\\boxed{B}"
}
```

### 处理后格式
```json
{
  "question": "处理后的完整问题文本",
  "answer": "B",
  "recommended_budget": 156
}
```

## 🚨 注意事项

1. **API密钥**: 确保在代码中配置正确的API密钥
2. **模型选择**: 推荐使用gpt-4o-mini或DeepSeek模型
3. **成本控制**: 批量处理时注意token消耗监控
4. **结果验证**: 建议抽样验证预算效果

## 📞 故障排除

### 常见问题
- **文件未找到**: 检查`./data/afac/afac.jsonl`是否存在
- **格式错误**: 使用`test_afac_support.py`验证格式
- **预算异常**: 检查复杂度计算参数

### 支持联系
如有问题，请检查项目README或提交issue。