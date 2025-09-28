import pandas as pd
import re
import os
# 用于清理回答中的冗余标注
# 使用相对路径或从命令行参数获取
file_path = "deepseek_results.xlsx"  # 相对路径
if not os.path.exists(file_path):
    print(f"错误: 文件 {file_path} 不存在")
    exit(1)

df = pd.read_excel(file_path)

# 确保第三列存在
if len(df.columns) >= 3:
    # 获取第三列的列名
    third_column_name = df.columns[2]  # 应该是"压缩后回答"
    
    # 处理第三列数据
    def clean_text(text):
        if isinstance(text, str):
            # 去掉"精简后的推理过程"文本
            text = re.sub(r'精简后的推理过程[：:]*\s*', '', text)
            
            # 去掉**符号
            text = re.sub(r'\*\*\s*([^*]*)\s*\*\*', r'\1', text)
            text = re.sub(r'\*\*\s*([^*]*)', r'\1', text)
            
            # 去掉###符号，但保留内容
            text = re.sub(r'###\s*', '', text)
            text = re.sub(r'\s*###', '', text)
            # 去掉多余的空行
            text = re.sub(r'\n\s*\n', '\n', text)
            
            # 在"最终答案"前后加上##符号
            text = re.sub(r'(最终答案[：:]?\s*)', r'##\1', text)
            text = re.sub(r'(最终答案[：:]?\s*.+?)(?=\n|$)', r'\1##', text)
            
            return text.strip()
        return text
    
    # 应用清理函数到第三列
    df[third_column_name] = df[third_column_name].apply(clean_text)
    
    # 保存处理后的Excel文件
    output_file = "deepseek_results_cleaned.xlsx"  # 相对路径
    df.to_excel(output_file, index=False)
    
    print(f"处理完成，已保存到 {output_file}")
else:
    print("Excel文件中没有第三列数据")