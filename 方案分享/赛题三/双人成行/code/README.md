1. SFT文件内包含了训练的配置脚本。
docker路径为：https://modelscope-registry.cn-beijing.cr.aliyuncs.com/modelscope-repo/modelscope:ubuntu22.04-cuda12.4.0-py310-torch2.6.0-vllm0.8.5.post1-modelscope1.27.1-swift3.5.3

2. RL文件夹内包含了训练的环境和代码，以及对应的README.md和requirements.txt文件，以及verl的可安装代码。

我们主要修改了reward_manager文件夹内的naive.py文件，修改了对应的奖励设置。

3. Inference文件夹内包含了推理所需要的代码。我们将推理的代码从huggingface backend改成了vllm backend。

4. data文件夹内包含了SFT和RL阶段需要的训练数据，分别是json格式的parquet格式。