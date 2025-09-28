FROM nvcr.io/nvidia/tritonserver:24.01-trtllm-python-py3

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN chmod 777 /tmp
RUN apt-get update && apt-get install -y tzdata
# 设置中文显示
ENV LANG C.UTF-8

# 设置工作目录
WORKDIR /workspace/code

RUN echo $(ls /workspace/)
COPY requirements.txt requirements.txt
COPY docker_image docker_image
# 设置清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --upgrade pip && pip install --ignore-installed -U blinker && pip install -r requirements.txt
RUN cp /workspace/code/docker_image/app/strategies.py /usr/local/lib/python3.10/dist-packages/elasticsearch/helpers/vectorstore/_async/strategies.py

RUN modelscope download --model BAAI/bge-reranker-base --local_dir  bge-reranker-base
RUN modelscope download --model BAAI/bge-large-zh --local_dir  bge-large-zh
RUN modelscope download --model OpenDataLab/MinerU2.0-2505-0.9B
RUN modelscope download --model OpenDataLab/PDF-Extract-Kit-1.0

COPY start.sh ./start.sh

ENTRYPOINT ["bash", "start.sh"]
