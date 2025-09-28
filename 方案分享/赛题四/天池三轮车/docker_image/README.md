# 金融研报自动生成系统

🤖 **基于AI大模型的智能金融研报生成平台**

## 📋 项目简介

本项目是一个基于AI大模型的金融研报自动生成系统，专为金融分析师、投资者和研究机构设计。通过整合多源数据采集、智能数据分析和专业报告生成功能，实现了从数据获取到研报输出的全流程自动化。
（由于第一次限定提交时间为7月24日中午12点，为了赶在截止时间前提交，三轮车小伙伴通宵达旦赶进度，因此项目中包含有诸多未清理的代码文件和片段，望海涵。且由于公司研报中，公司名4Paradigm即第四范式，用4Paradigm去search的效果不是很好，因此改成了第四范式，并无意针对特定b榜题目进行优化，特此说明。）

### 🎯 核心功能

- **📊 多维度数据采集**：自动获取公司财务报表、股权结构、行业信息等多源数据
- **🤖 智能财务分析**：基于AI的财务分析、同业对比和趋势预测
- **📈 可视化图表生成**：自动生成专业的财务图表和数据可视化
- **📝 深度研报生成**：生成包含投资建议的完整金融研究报告
- **🔄 工作流引擎**：支持行业分析和宏观经济研究的自动化流程

## 🏗️ 系统架构

### 系统架构图

![](report_frame.png)

### 项目目录结构

```
app/
├── 📄 核心生成器
│   ├── run_company_research_report.py          # 公司研报生成器
│   ├── run_industry_research_report.py         # 行业研报生成器
│   └── run_macro_research_report.pyy           # 宏观研报生成器
│
├── 📄 子生成器
│   ├── abstract_generator.py                   # 财报信息摘要生成器
│   ├── catelogue_generator.py                  # 研报目录生成器
│   ├── competitor_result_generator.py          # 竞对生成器
│   ├── section_generator.py                    # 段落内容生成器
│   ├── headline_abstract_generator.py          # 标题摘要生成器
│   ├── react_generator.py                      # 配图位置生成器
│   └── word_generator.py                       # word生成器
├
├── 📁 工具
│   ├── agent_api/
│   │   ├── app.py                              # RAG：PDF数据Embedding及财报检索查询接口
│   │   ├── easy_demo.py                        # mineru2.0抽取PDF章节
│   │   ├── metrics_draw.py                     # 绘制图智能体
│   │   ├── output                              # PDF抽取输出目录
│   │   ├── parse_pdf_v1.py                     # flask提供的PDF目录章节识别及内容抽取接口
│   │   ├── pdf_path                            # PDF下载存储路径
│   │   ├── rag_2025-07-23.log                  # RAG接口日志
│   │   ├── toc.png                             # PDF目录页图
│   │   └── utils.py                            # 工具函数
│   │
│   ├── search_api.py                           # 搜索API，基于src内的函数封装
│   ├── src/                                    
│       ├── config.py                           # 配置读取代码
│       ├── console.py
│       ├── environment
│       ├── exceptions.py
│       ├── __init__.py
│       ├── logger.py                           # 日志记录
│       ├── tool
│           ├── search
│           │   ├── baidu_search.py             # baidu爬虫   
│           │   ├── base.py                     # 搜索工具基类
│           │   ├── bing_search.py              # bing爬虫
│           │   ├── duckduckgo_search.py        # duckduckgo爬虫
│           │   ├── google_search.py            # Google爬虫
│           │   ├── __init__.py
│           └── web_search.py                   # 基于search封装的web_search接口
├── strategies.py                               # es查询bug修复，构建docker时拷贝至elasticsearch库中
├── 📁 输出结果
│   ├── reports/                                # 生成的报告的目录
│   └── workspace/                              # 绘图智能体生成的工作目录
└── 📄 文档
    └── README.md                               # 项目说明文档
```
其余未说明代码，为冗余代码、测试代码、未完成代码等，请忽略


## 环境

### 模型
均可通过modelscope下载，下载命令已在Dockerfile中体现
bge-large-zh Embedding模型
bge-reranker-base rerank模型
OpenDataLab/MinerU2.0-2505-0.9B pdf抽取模型
OpenDataLab/PDF-Extract-Kit-1.0 同上
大模型调用使用阿里云百炼平台，使用模型有deepseek-r1-0528，qwen-vl-max

### 数据
combined_results文件夹：爬虫从巨潮抓取的财报链接，通过agent_api中的Embedding接口将Excel中的数据向量化存储到阿里云的es库

如果agent_api中app.py和parse_pdf_v1.py未通过start.sh运行，则需手动运行

## 迭代过程
在研报生成的迭代过程中，最初采用的是模版生成方案。该方案预设了三类模版，通过 prompt 参考模版格式来生成研报，但存在明显不足：一是生成的研报字数较少，内容不够充实；二是模版中的内容会被直接带入研报，造成研报存在重复内容；三是生成的内容较为单调，且缺乏必要的图表支撑。​
参考 baseline 之后，团队对方案进行了优化。首先提取了其中的取数逻辑，同时增加了竞对公司信息的获取渠道。针对一次性生成字数较少的问题，调整了生成策略：先构建框架并明确分析要点，每个分析要点下设置两到三个子要点，依据这些分析要点去搜索相关信息，再结合搜索结果分段生成研报。研报生成完成后，统一生成摘要、标题以及表格，并将它们拼接整合输出。​
在信息获取方面，通过爬虫爬取巨潮资讯上上市公司近五年的财报链接，将其存储为 Excel 文件，随后进行 Embedding 处理并存储到 es 库中。生成公司研报时，通过公司名检索查询出该公司最新的财报，再借助 parse_pdf_v1.py 接口解析出财报的目录和内容，获取管理层讨论与分析章节的信息。由于该章节信息字数较多，会超出模型的最大长度限制，因此使用大模型对这部分内容进行精简提炼，将其作为研报生成的背景信息。此外，通过东方财富、akshare、新浪财经等公开 API 获取上市公司近五年的财务信息，如市盈率、市净率、市销率等，作为研报中财务分析部分的素材。同时，将分析要点作为 web_search 的 query，通过百度、必应、搜狗等搜索引擎获取相关背景信息。​
研报正文生成完成后，交由大模型判断适合插入图片的位置以及图片的类型（如单双折线图、柱状图等）。之后调用绘图 Agent，向其提供数据和图片类型，由其自动生成图片并返回图片地址，再将图片插入到研报的相应位置。最后，将 markdown 格式的研报转换为 docx 格式，输出到 reports 文件夹中。

## TODO
- 生成完成后研报review修改(内容修改、图表修改)
- 个股与恒生指数、沪深指数对比
- 行业和宏观增加图
- 搜索问句更加细化，增加AI Search智能体
- planner全局调度