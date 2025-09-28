import akshare as ak
import pandas as pd
from typing import Dict, Optional
import os


def get_balance_sheet(stock_code: str = "00020", market: str = "HK", period: str = "年度", verbose: bool = False) -> Optional[pd.DataFrame]:
    """
    获取公司的资产负债表
    
    Args:
        stock_code (str): 股票代码
        market (str): 股票市场，"HK"为港股，"A"为A股
        period (str): 报告期间，可选"年度"或"中期"（仅港股适用），默认为"年度"
        verbose (bool): 是否打印详细信息，默认为False
    
    Returns:
        pd.DataFrame: 资产负债表数据，如果获取失败则返回None
    """
    try:
        if verbose:
            print(f"正在获取{market}股票代码 {stock_code} 的{period}资产负债表...")
        
        if market == "HK":
            df_balance_sheet = ak.stock_financial_hk_report_em(
                stock=stock_code, 
                symbol="资产负债表", 
                indicator=period
            )
        elif market == "A":
            df_balance_sheet = ak.stock_balance_sheet_by_yearly_em(symbol=stock_code)
        else:
            raise ValueError(f"不支持的市场类型: {market}，请使用 'HK' 或 'A'")
        
        if verbose:
            print(f"成功获取资产负债表，共 {len(df_balance_sheet)} 行数据")
            print(f"数据列名: {list(df_balance_sheet.columns)}")
            print("\n数据预览:")
            print(df_balance_sheet.head())
        
        return df_balance_sheet
    
    except Exception as e:
        if verbose:
            print(f"获取资产负债表失败: {e}")
        return None


def get_income_statement(stock_code: str = "00020", market: str = "HK", period: str = "年度", verbose: bool = False) -> Optional[pd.DataFrame]:
    """    获取公司的利润表
    
    Args:
        stock_code (str): 股票代码
        market (str): 股票市场，"HK"为港股，"A"为A股
        period (str): 报告期间，可选"年度"或"中期"（仅港股适用），默认为"年度"
        verbose (bool): 是否打印详细信息，默认为False
    
    Returns:
        pd.DataFrame: 利润表数据，如果获取失败则返回None
    """
    try:
        if verbose:
            print(f"正在获取{market}股票代码 {stock_code} 的{period}利润表...")
        
        if market == "HK":
            df_income_statement = ak.stock_financial_hk_report_em(
                stock=stock_code, 
                symbol="利润表", 
                indicator=period
            )
        elif market == "A":
            df_income_statement = ak.stock_profit_sheet_by_yearly_em(symbol=stock_code)
        else:
            raise ValueError(f"不支持的市场类型: {market}，请使用 'HK' 或 'A'")
        
        if verbose:
            print(f"成功获取利润表，共 {len(df_income_statement)} 行数据")
            print(f"数据列名: {list(df_income_statement.columns)}")
            print("\n数据预览:")
            print(df_income_statement.head())
        
        return df_income_statement
    
    except Exception as e:
        if verbose:
            print(f"获取利润表失败: {e}")
        return None


def get_cash_flow_statement(stock_code: str = "00020", market: str = "HK", period: str = "年度", verbose: bool = False) -> Optional[pd.DataFrame]:
    """
    获取公司的现金流量表
    
    Args:
        stock_code (str): 股票代码
        market (str): 股票市场，"HK"为港股，"A"为A股
        period (str): 报告期间，可选"年度"或"中期"（仅港股适用），默认为"年度"
        verbose (bool): 是否打印详细信息，默认为True
    
    Returns:
        pd.DataFrame: 现金流量表数据，如果获取失败则返回None
    """
    try:
        if verbose:
            print(f"正在获取{market}股票代码 {stock_code} 的{period}现金流量表...")
        
        if market == "HK":
            df_cash_flow = ak.stock_financial_hk_report_em(
                stock=stock_code, 
                symbol="现金流量表", 
                indicator=period
            )
        elif market == "A":
            df_cash_flow = ak.stock_cash_flow_sheet_by_yearly_em(symbol=stock_code)
        else:
            raise ValueError(f"不支持的市场类型: {market}，请使用 'HK' 或 'A'")
        
        if verbose:
            print(f"成功获取现金流量表，共 {len(df_cash_flow)} 行数据")
            print(f"数据列名: {list(df_cash_flow.columns)}")
            print("\n数据预览:")
            print(df_cash_flow.head())
        
        return df_cash_flow
    
    except Exception as e:
        if verbose:
            print(f"获取现金流量表失败: {e}")
        return None


def get_all_financial_statements(stock_code: str = "00020", market: str = "HK", period: str = "年度", verbose: bool = False) -> Dict[str, Optional[pd.DataFrame]]:
    """
    获取公司的所有三大财务报表
    
    Args:
        stock_code (str): 股票代码
        market (str): 股票市场，"HK"为港股，"A"为A股
        period (str): 报告期间，可选"年度"或"中期"（仅港股适用），默认为"年度"
        verbose (bool): 是否打印详细信息，默认为True
    
    Returns:
        Dict[str, Optional[pd.DataFrame]]: 包含三大报表的字典
            - 'balance_sheet': 资产负债表
            - 'income_statement': 利润表
            - 'cash_flow_statement': 现金流量表
    """
    if verbose:
        print(f"开始获取{market}股票代码 {stock_code} 的所有{period}财务报表...")
        print("=" * 60)
    
    financial_statements = {
        'balance_sheet': get_balance_sheet(stock_code, market, period, verbose),
        'income_statement': get_income_statement(stock_code, market, period, verbose),
        'cash_flow_statement': get_cash_flow_statement(stock_code, market, period, verbose)
    }
    
    if verbose:
        print("=" * 60)
        success_count = sum(1 for df in financial_statements.values() if df is not None)
        print(f"财务报表获取完成，成功获取 {success_count}/3 个报表")
    
    return financial_statements


def save_financial_statements_to_csv(financial_statements: Dict[str, Optional[pd.DataFrame]], 
                                   stock_code: str = "00020", 
                                   market: str = "HK",
                                   period: str = "年度",
                                   company_name: str = None,
                                   save_dir: str = ".") -> None:
    """
    将财务报表保存为CSV文件
    
    Args:
        financial_statements (Dict): 包含财务报表的字典
        stock_code (str): 股票代码，用于文件命名
        market (str): 股票市场，"HK"为港股，"A"为A股
        period (str): 报告期间，用于文件命名
        company_name (str): 公司名称，用于文件命名，如果为None则只使用股票代码
        save_dir (str): 保存文件的目录，默认为当前目录
    """
    for statement_type, df in financial_statements.items():
        if df is not None:
            if company_name:
                filename = f"{company_name}_{market}_{stock_code}_{statement_type}_{period}.csv"
            else:
                filename = f"{market}_{stock_code}_{statement_type}_{period}.csv"
            
            # 使用指定目录保存文件
            filepath = os.path.join(save_dir, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"已保存 {statement_type} 到文件: {filepath}")
        else:
            print(f"跳过保存 {statement_type}，因为数据获取失败")



# 如果直接运行此文件，则执行默认查询
if __name__ == "__main__":
    # 获取百度(09888)的年度财务报表
    print("开始获取百度(09888)的年度财务报表...\n")
    
    # 获取单个报表示例
    print("1. 获取资产负债表:")
    balance_sheet = get_balance_sheet(stock_code="09888")
    
    print("\n" + "="*80 + "\n")
    
    print("2. 获取利润表:")
    income_statement = get_income_statement(stock_code="09888")
    
    print("\n" + "="*80 + "\n")
    
    print("3. 获取现金流量表:")
    cash_flow = get_cash_flow_statement(stock_code="09888")
    
    print("\n" + "="*80 + "\n")
    
    # 获取所有报表
    print("4. 一次性获取所有财务报表:")
    all_statements = get_all_financial_statements(stock_code="09888")
    
    # 保存到CSV文件
    print("\n保存财务报表到CSV文件:")
    save_financial_statements_to_csv(all_statements, stock_code="09888", company_name="百度")
    
    # A股示例
    print("\n" + "="*80 + "\n")
    a_statements = get_all_financial_statements(stock_code="SZ000001", market="A", verbose=True)
    save_financial_statements_to_csv(a_statements, stock_code="SZ000001", market="A", company_name="平安银行")
