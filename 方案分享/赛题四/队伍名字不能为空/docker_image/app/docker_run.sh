# 启动股票信息mcp
echo 'STEP1 start stock mcp'
nohup python /app/mcps/server_stock.py &

# 启动绘图mcp
echo 'STEP2 start chart mcp'
nohup python /app/mcps/server_chart.py &

# 休眠5秒等待mcp启动成功
echo 'STEP3 wait 10s'
sleep 10

# 开始生产要求的三份研报
echo 'STEP4 start generate'
sh run.sh

# 将生成结果复制到宿主机
echo 'STEP5 copy res'
cp results/* /res

echo 'finish.'