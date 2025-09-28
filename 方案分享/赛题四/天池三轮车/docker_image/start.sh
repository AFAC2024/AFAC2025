#!/bin/bash

# 定义工作目录（根据实际情况修改）
WORK_DIR="/workspace/code/docker_image/app/agent_api"

# 启动 app.py (端口 5000)
start_app() {
    echo "🚀 启动 app.py (端口 5000)..."
    nohup python3 app.py > app.log 2>&1 &
    APP_PID=$!
    echo "🟢 app.py 已启动 (PID: $APP_PID), 日志: $WORK_DIR/app.log"
}

# 启动 parse.py (端口 5001)
start_parse() {
    echo "🚀 启动 parse.py (端口 5001)..."
    nohup python3 parse_pdf_v1.py > parse.log 2>&1 &
    PARSE_PID=$!
    echo "🟢 parse.py 已启动 (PID: $PARSE_PID), 日志: $WORK_DIR/parse.log"
}

# 检查并安装必要依赖
check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        echo "❌ 错误: Python3 未安装"
        exit 1
    fi
}

# 切换到工作目录
change_directory() {
    if [ ! -d "$WORK_DIR" ]; then
        echo "❌ 错误: 目录 '$WORK_DIR' 不存在"
        exit 1
    fi
    
    echo "📂 切换到工作目录: $WORK_DIR"
    cd "$WORK_DIR" || exit 1
    echo "  当前路径: $(pwd)"
}

# 主函数
main() {
    change_directory
    check_dependencies
    
    start_app
    start_parse
    
    echo -e "\n================================="
    echo "✅ 服务已全部启动"
    echo "---------------------------------"
    echo "app.py  : http://localhost:5000"
    echo "parse_pdf_v1.py: http://localhost:5001"
    echo "---------------------------------"
    echo "查看日志: tail -f $WORK_DIR/app.log $WORK_DIR/parse.log"
    echo "================================="
}

# 执行主函数
main