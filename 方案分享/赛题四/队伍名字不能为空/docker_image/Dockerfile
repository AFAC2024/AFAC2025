# 使用官方Python slim镜像作为基础
FROM python:3.12-slim

# 升级系统包以修复潜在漏洞
RUN apt-get update && apt-get upgrade -y && apt-get clean

# 设置Python环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 复制应用文件和requirements.txt
COPY ./app/ /app/

# 安装依赖并升级指定包
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --upgrade requests urllib3 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 确保python命令指向3.12
RUN ln -sf /usr/local/bin/python3 /usr/local/bin/python

# 暴露8000端口
EXPOSE 8000

# 设置指令启动研报生成
CMD ["sh","/app/docker_run.sh"]