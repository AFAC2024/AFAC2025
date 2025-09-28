# 金融保险场景下多源文件长上下文一致性校验-clife团队B榜代码

## 整体方案

![](assets/image-20250729232907109.png)



## 代码结构

```bash
│- data_process.py  # 文档抽取处理脚本
│- llm.py  # 大模型调用函数
│- main.py # 主程序入口，动态规则一致性比对
└─config
      -  config.py  # 提示词、规则描述文件
      -  key.py  # api_key
      -  __init__.py
      -  规则文件映射.xlsx  # 规则映射文件
```

## 使用说明

1、安装依赖，项目目录下运行安装命令

```
pip install -r requirements.txt
```

2、设置阿里百炼平台API_KEY（确保能调用qwen3-30b-a3b模型），修改config/key.py文件

```
api_key='真实api_key'
```

3、运行代码, 结果文件写入项目目录submit.jsonl文件

```
python main.py
```

