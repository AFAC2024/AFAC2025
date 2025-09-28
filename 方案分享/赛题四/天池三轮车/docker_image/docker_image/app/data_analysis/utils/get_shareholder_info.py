import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional


def get_shareholder_info(stock_code: str = "HK0020",
                         ) -> Dict:
    """
    获取股票的股东信息
    
    Args:
        stock_code (str): 股票代码，默认为"HK0020"
        verbose (bool): 是否打印详细信息，默认为True
    
    Returns:
        Dict: 包含股东信息的字典，包含以下键：
            - success (bool): 是否成功获取数据
            - status_code (int): HTTP状态码
            - title (str): 页面标题
            - tables (List[str]): 表格HTML内容列表
            - tables_text (List[str]): 表格纯文本内容列表
            - error (str): 错误信息（如果有）
    """
    # 设置请求头，模拟浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    url = f"https://basic.10jqka.com.cn/{stock_code}/holder.html"
    
    result = {
        'success': False,
        'status_code': None,
        'title': None,
        'tables': [],
        'tables_text': [],
        'error': None
    }


    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    response.encoding = 'utf-8'
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    result['success'] = True
    result['status_code'] = response.status_code
    result['title'] = soup.title.string if soup.title else '无标题'
    

    # 查找股权结构相关的表格或内容
    tables = soup.find_all('table')
    if tables:
        # 保存HTML格式的表格
        result['tables'] = [str(table) for table in tables]
        # 保存纯文本格式的表格（用于显示）
        result['tables_text'] = [table.get_text(strip=True) for table in tables]


    return result


def get_table_content(tables_html: List[str]):
    html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>股东信息表格</title>
                <style>
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 20px 0;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                    .table-container {{
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <h1>股东信息表格</h1>
                {''.join([f'<div class="table-container">{table}</div>' for table in tables_html])}
            </body>
            </html>
            """
    return html_content


def save_tables_to_html(tables_html: List[str], 
                        filename: str = "shareholder_tables.html") -> None:
    """
    将表格HTML保存到文件
    
    Args:
        tables_html (List[str]): HTML表格列表
        filename (str): 保存的文件名
    """
    html_content = get_table_content(tables_html)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"表格已保存到 {filename}")


# 如果直接运行此文件，则执行默认查询
if __name__ == "__main__":
    info = get_shareholder_info()
    print(f"\n返回结果: {info['success']}")
    if info['tables']:
        print(f"获取到 {len(info['tables'])} 个表格的数据")
        # 保存HTML表格到文件
        save_tables_to_html(info['tables'])