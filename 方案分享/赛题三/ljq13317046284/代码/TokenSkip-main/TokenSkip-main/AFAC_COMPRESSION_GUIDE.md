# AFAC数据集思维链压缩指南

## 项目概述

TokenSkip项目支持对AFAC数据集（fineval-train-ds-cot.json）进行思维链压缩，通过LLMLingua-2技术裁剪不重要的token，生成压缩后的思维链数据集。

## 数据集格式验证

### 当前数据集格式
- **文件路径**: `datasets/afac/fineval-train-ds-cot.json`
- **格式**: JSON数组，每条记录包含：
  - `instruction`: 指令文本
  - `input`: 问题输入
  - `output`: 包含思维链和答案的完整输出

### 思维链格式示例
```json
{
  "instruction": "请你扮演一位金融和会计领域专家...",
  "input": "下列不属于我国商业银行业务范围的是____。\\nA,发行金融债券\\nB,监管其他金融机构\\nC,买卖政府债券\\nD,买卖外汇",
  "output": "### 思考过程：1. **理解题目**：题目问的是...### 最终答案：\\boxed{B}"
}
```

## 使用步骤

### 1. 验证数据集
```bash
python validate_afac_dataset.py
```

### 2. 安装依赖（如需要）
```bash
pip install llmlingua tqdm transformers torch
```

### 3. 运行压缩脚本
```bash
python compress_afac_cot.py
```

## 压缩功能说明

### 支持的压缩比例
- 90% (保留90%内容)
- 80% (保留80%内容)
- 70% (保留70%内容)
- 60% (保留60%内容)
- 50% (保留50%内容)
- 40% (保留40%内容)
- 30% (保留30%内容)

### 输出文件
压缩后的文件将保存在 `datasets/afac/compressed/` 目录下：
- `fineval-train-ds-cot-compressed-90.json`
- `fineval-train-ds-cot-compressed-80.json`
- `fineval-train-ds-cot-compressed-70.json`
- ...以此类推

### 输出格式
每条记录包含：
- `instruction`: 原始指令
- `input`: 原始问题
- `original_output`: 原始完整输出
- `compressed_output`: 压缩后的输出
- `original_cot`: 原始思维链
- `compressed_cot`: 压缩后的思维链
- `original_tokens`: 原始token数
- `compressed_tokens`: 压缩后token数
- `compression_ratio`: 实际压缩比例

## 技术实现

### 使用的模型
- **LLMLingua-2**: `microsoft/llmlingua-2-xlm-roberta-large-meetingbank`
- **技术原理**: 基于信息熵的token重要性评估，保留关键信息token

### 特殊处理
- 保留中文关键词：思考、过程、因为、所以、因此、但是、然而
- 保留数字信息
- 保持答案格式完整性（\boxed{}格式）

## 验证结果

### 数据集验证
- ✅ 文件存在且格式正确
- ✅ 包含802条记录
- ✅ 每条记录包含必要字段
- ✅ 思维链格式标准化

### 压缩效果预期
- 平均压缩比例：30%-70%
- 保留关键推理步骤
- 维持答案准确性

## 使用示例

### 原始思维链（示例）
```
### 思考过程：
1. **理解题目**：题目问的是"不属于我国商业银行业务范围"的选项...
2. **商业银行的业务范围**：根据《中华人民共和国商业银行法》...
3. **分析选项**：
   - A. 发行金融债券：属于商业银行的业务范围...
   - B. 监管其他金融机构：监管职能属于中国人民银行...
   - C. 买卖政府债券：属于商业银行的业务范围...
   - D. 买卖外汇：属于商业银行的业务范围...
4. **排除法**：A、C、D均为商业银行的合法业务，只有B不属于...
5. **验证**：监管职能属于金融监管机构...
```

### 压缩后思维链（50%压缩比例）
```
### 思考过程：
商业银行法规定业务范围包括发行债券、买卖政府债券和外汇，但监管其他金融机构属于央行职责，因此B选项不属于商业银行业务范围。
```

## 注意事项

1. **模型下载**: 首次运行会自动下载LLMLingua-2模型（约1.5GB）
2. **内存需求**: 建议至少8GB内存
3. **处理时间**: 802条记录预计需要5-10分钟
4. **错误处理**: 压缩失败时会保留原始内容并记录错误信息

## 故障排除

### 常见问题
1. **模型加载失败**: 检查网络连接，确保能访问HuggingFace
2. **内存不足**: 减小批处理大小或关闭其他应用
3. **文件不存在**: 检查数据集路径是否正确

### 调试模式
在压缩脚本中添加调试信息：
```python
# 在compress_afac_cot.py中添加
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展使用

### 自定义压缩比例
修改compress_afac_cot.py中的compression_ratios参数：
```python
compression_ratios=[0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35]
```

### 批量处理
可以处理多个数据集文件：
```python
files = ["fineval-train-ds-cot.json", "fineval-test-ds-cot.json"]
for file in files:
    compress_afac_cot(file, output_dir)
```