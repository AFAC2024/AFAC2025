@echo off
REM AFAC数据集压缩批处理脚本
REM 提供多种压缩选项

echo ========================================
echo AFAC数据集思维链压缩工具
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Python未安装或未添加到PATH
    echo 请安装Python 3.7+并确保python命令可用
    pause
    exit /b 1
)

REM 设置路径
set "PROJECT_DIR=%~dp0"
set "DATASET_PATH=%PROJECT_DIR%datasets\afac\fineval-train-ds-cot.json"

echo 项目目录: %PROJECT_DIR%
echo 数据集路径: %DATASET_PATH%
echo.

REM 检查数据集文件
if not exist "%DATASET_PATH%" (
    echo 错误: 数据集文件不存在
    echo 请确保文件位于: %DATASET_PATH%
    pause
    exit /b 1
)

echo 数据集文件检查通过
echo.

:menu
echo 请选择压缩方式:
echo 1. 验证数据集格式
echo 2. 基于规则的简单压缩 (推荐)
echo 3. 基于LLMLingua的AI压缩 (需要模型)
echo 4. 退出
echo.

set /p choice=请输入选项(1-4): 

if "%choice%"=="1" goto validate
if "%choice%"=="2" goto simple_compress
if "%choice%"=="3" goto ai_compress
if "%choice%"=="4" goto exit
echo 无效选项，请重新选择
goto menu

:validate
echo.
echo 正在验证数据集格式...
python validate_afac_dataset.py
pause
goto menu

:simple_compress
echo.
echo 正在执行基于规则的简单压缩...
echo 这将创建压缩比例: 90%, 80%, 70%, 60%, 50%, 40%, 30%
python simple_compress_afac.py
echo.
echo 压缩完成！文件保存在: datasets\afac\simple_compressed\
pause
goto menu

:ai_compress
echo.
echo 正在执行基于LLMLingua的AI压缩...
echo 注意: 首次运行会下载约1.5GB的模型文件
echo 这可能需要一些时间，请耐心等待...
python compress_afac_cot.py
echo.
echo 压缩完成！文件保存在: datasets\afac\compressed\
pause
goto menu

:exit
echo 感谢使用！
pause
exit /b 0