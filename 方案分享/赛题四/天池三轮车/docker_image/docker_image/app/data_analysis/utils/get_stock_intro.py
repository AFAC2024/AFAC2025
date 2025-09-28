import akshare as ak
import pandas as pd
from typing import Optional, Literal

def get_stock_intro(symbol: str = "000066", market: Literal["A", "HK"] = "A") -> Optional[str]:
    """
    获取股票的基本介绍信息，包括主营业务、经营范围等。
    支持区分A股、港股。
    :param symbol: 股票代码（如 '000066'、'00700'）
    :param market: 市场类型（'A'、'HK'）
    :return: 返回pandas表格的字符串，若获取失败则返回None
    """
    # A股
    if market == "A":
        # 去掉A股代码的SH/SZ前缀
        clean_symbol = symbol.replace('SH', '').replace('SZ', '')
        try:
            df = ak.stock_zyjs_ths(symbol=clean_symbol)
            if df is not None and not df.empty:
                return df.to_string(index=False)
        except Exception as e:
            print(f"AkShare A股获取失败 ({clean_symbol}): {e}")
            return None      # 港股
    elif market == "HK":
        # 去掉港股代码的HK前缀
        clean_symbol = symbol.replace('HK', '')
        try:
            df = ak.stock_hk_company_profile_em(symbol=clean_symbol)
            if df is not None and not df.empty:
                return df.to_string(index=False)
        except Exception as e:
            print(f"AkShare 港股获取失败 ({clean_symbol}): {e}")
            return None
    
    return None

def save_stock_intro_to_txt(symbol: str, market: Literal["A", "HK"], save_path: str) -> None:
    """
    获取股票介绍信息并保存到txt文件。
    :param symbol: 股票代码
    :param market: 市场类型
    :param save_path: 保存的txt文件路径
    """
    info_str = get_stock_intro(symbol, market)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(info_str if info_str else "未获取到相关信息")

if __name__ == "__main__":
    # 示例：A股
    print(get_stock_intro("000066", market="A"))
    # 示例：港股
    print(get_stock_intro("00700", market="HK"))
    # 获取百度的：9888
    print(get_stock_intro("09888", market="HK"))
    # 保存示例
    save_stock_intro_to_txt("000066", "A", "000066_A.txt")
    save_stock_intro_to_txt("00700", "HK", "00700_HK.txt")
    save_stock_intro_to_txt("09888", "HK", "09888_HK.txt")

