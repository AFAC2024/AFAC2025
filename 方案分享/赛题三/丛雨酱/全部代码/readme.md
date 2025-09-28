# 金融领域长思维链压缩项目 - 环境安装与使用指南
## 环境要求

### 系统要求
- Python 3.8 或更高版本
- Windows/Linux/macOS 操作系统
- 建议使用 GPU 进行模型训练（可选）

### Python 依赖包安装

#### 方法一：使用 requirements.txt（推荐）

pip install -r requirements.txt

#### 方法二：手动安装依赖包

pip install pandas>=1.5.0
pip install requests>=2.28.0
pip install openai>=1.0.0
pip install openpyxl>=3.1.0
如果需要进行DPO训练，还需要安装以下依赖：

# Swift框架（用于模型训练）
pip install ms-swift

# 深度学习框架
pip install torch torchvision torchaudio

# 其他需要的包
pip install transformers
pip install datasets
pip install accelerate

使用的最终数据集是dpo_dataset_combined.json