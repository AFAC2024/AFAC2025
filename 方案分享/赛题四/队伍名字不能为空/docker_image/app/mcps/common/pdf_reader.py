"""
读取PDF内容的工具

1.0 @nambo 2025-07-20
"""
import pdfplumber
import os
import logging

def parse_pdf(pdf_path):
    # 存储结果
    full_text = ""
    tables = []
    file_size = os.path.getsize(pdf_path)
    if file_size > 1024 * 1024:
        logging.warning('文件过大，跳过加载,' + pdf_path)
        return full_text, tables
    with pdfplumber.open(pdf_path) as pdf:
        # 逐页处理
        for page in pdf.pages:
            # 提取文本
            text = page.extract_text()
            if text:
                full_text += text + "\n\n"
            
            # 提取表格
            for table in page.extract_tables():
                tables.append(table)
    
    return full_text, tables

# 使用示例
if __name__ == "__main__":
    pdf_path = "公告.pdf"
    pdf_path = '/Users/nambo/Downloads/公告/002208_合肥城建_合肥城建：2024年年度报告_2025-04-10.pdf'
    pdf_path = '/Users/nambo/Downloads/公告/002208_合肥城建_合肥城建：关于全资子公司签署增资合作协议的公告_2025-07-12.pdf'
    pdf_path = '/Users/nambo/Downloads/公告/09961_攜程集團－Ｓ_攜程集團－Ｓ股份（HK09961）2024年度報告_2025-04-11.pdf'
    pdf_path = '/Users/nambo/Downloads/公告/09961_攜程集團－Ｓ_攜程集團－Ｓ股份（HK09961）2025年股東週年大會的結果_2025-06-30.pdf'
    # pdf_path = '/Users/nambo/Downloads/公告/601128_常熟银行_江苏常熟农村商业银行股份有限公司2024年年度报告_2025-03-28.pdf'
    # pdf_path = '/Users/nambo/Downloads/公告/601128_常熟银行_江苏常熟农村商业银行股份有限公司可转债转股结果暨股份变动的公告_2025-07-02.pdf'
    full_text, tables = parse_pdf(pdf_path)
    
    # 打印前500个字符的文本
    print(full_text)
    

    print('\n\n下面是表格\n\n')
    # 打印第一个表格（转换为DataFrame）
    import pandas as pd
    if tables:
        df = pd.DataFrame(tables[0][1:], columns=tables[0][0])
        print(df.head())