"""
基于数据绘图的mcp服务

1.0 @nambo 2025-07-20
"""
import sys

from mcp.server.fastmcp import FastMCP
from data_types import StockPrice, Doc, StockInfo
from typing import Optional
import common.chart_utils as chart
import os
import sys
import matplotlib
matplotlib.use('Agg')

mcp = FastMCP("ChartServer")


@mcp.tool()
def chart_kline(dates: list[str], closes: list[float], opens: list[float], highs: list[float], lows: list[float], volumes: list[int], title: Optional[str] = None) -> str:
  """
  绘制K线图，返回绘制生成的图片保存路径。
  展示个股或市场指数在特定时间段（日/周/月等）内价格波动、开盘价、收盘价、最高价、最低价及涨跌情况，直观反映多空双方力量对比和市场趋势，比如：每日股价、每日指数数值等等。

  参数：
    dates: K线的日期列表(格式yyyy-mm-dd)
    closes: 日期对应的收盘价格列表，长度需和dates一致
    opens: 日期对应的开盘价格列表，长度需和dates一致
    highs: 日期当日最高价格列表，长度需和dates一致
    lows: 日期当日最低价格列表，长度需和dates一致
    volumes: 日期当日成交量列表，长度需和dates一致
    title: 生成图表的标题(非必须)
  """
  values = [len(dates), len(closes), len(opens), len(highs), len(lows), len(volumes)]
  if max(values) != min(values):
    raise ValueError("参数：dates、closes、opens、highs、lows、volumes，需要包含相同数量的元素，当前元素数量分别是:{0}，请调整参数后重试".format("、".join(map(str, values))))

  return chart.plot_stock_kline(dates, closes, opens, highs, lows, volumes, title)

@mcp.tool()
def chart_pie(categorys: list[str], values: list[float], title:str= None) -> str:
  """
  根据传入的数据，绘制饼图，返回绘制生成的图片保存路径
  清晰呈现一个整体中各组成部分（如不同业务收入、不同资产类别、不同竞争者份额）所占的相对比例，比如：主营业务构成等等。

  参数：
    categorys: 饼图的数据分类列表
    values: 饼图的数据值列表，长度需和categorys一致
    title: 生成图表的标题(非必须)
  """
  check_len = [len(categorys), len(values)]
  if max(check_len) != min(check_len):
    raise ValueError("参数：categorys、values，需要包含相同数量的元素，当前元素数量分别是:{0}，请调整参数后重试".format("、".join(map(str, check_len))))

  return chart.plot_pie(categorys, values, title)

@mcp.tool()
def chart_bar_line(x_labels: list[str], bar_values: list[float], line_values: list[float], bar_name: Optional[str] = None, line_name: Optional[str] = None, title: Optional[str] = None) -> str:
  """
  根据传入的数据，绘制柱状图和折线图的复合图形，返回绘制生成的图片保存路径
  ​​在同一坐标轴（通常双纵轴）结合柱状图展示规模/数量型数据（如营收、产量）和折线图展示比率/趋势型数据（如增长率、利润率），揭示规模与效率的关系或同时对比不同类型指标，比如：企业每年营收与对应增长情况等等。

  参数：
    x_labels: 图表X轴的标签列表
    bar_values: X轴标签对应的柱状图数据列表，长度需和x_labels一致
    line_values: X轴标签对应的折线图数据列表，长度需和x_labels一致
    bar_name: 柱状图的图例名称(非必须)
    line_name: 折线图的图例名称(非必须)
    title: 生成图表的标题(非必须)
  """
  check_len = [len(x_labels), len(bar_values), len(line_values)]
  if max(check_len) != min(check_len):
    raise ValueError("参数：x_labels、bar_values、line_values，需要包含相同数量的元素，当前元素数量分别是:{0}，请调整参数后重试".format("、".join(map(str, check_len))))
  
  return chart.plot_bar_line(x_labels, bar_values, line_values, bar_name, line_name, title)

@mcp.tool()
def chart_radar(dimensios: list[str], label: str, data: list[float]
                , label2: Optional[str] = None, data2: Optional[list[float]] = None
                , label3: Optional[str] = None, data3: Optional[list[float]] = None
                , label4: Optional[str] = None, data4: Optional[list[float]] = None
                , label5: Optional[str] = None, data5: Optional[list[float]] = None
                , title: Optional[str] = None) -> str:
  """
  根据传入的数据，绘制雷达图（最多支持同时展示5个数据序列），返回绘制生成的图片保存路径
  综合评估一个或多个主体在多个维度的表现，便于直观识别其相对优势和劣势（竞争力短板），比如：不同企业竞争力对比等等。​

  参数：
    dimensios: 雷达图的顶点（维度）名称列表(至少需要3个及以上)
    label: 雷达图第1数据系列的名称
    data: 雷达图第1个数据系列数据，长度需和dimensios长度一致
    label2: 雷达图第2个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data2: 雷达图第2个数据系列数据，长度需和dimensios长度一致（非必须，如果没有第2个系列可以不传）
    label3: 雷达图第3个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data3: 雷达图第3个数据系列数据，长度需和dimensios长度一致（非必须，如果没有第3个系列可以不传）
    label4: 雷达图第4个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data4: 雷达图第4个数据系列数据，长度需和dimensios长度一致（非必须，如果没有第4个系列可以不传）
    label5: 雷达图第5个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data5: 雷达图第5个数据系列数据，长度需和dimensios长度一致（非必须，如果没有第5个系列可以不传）
    title: 生成图表的标题(非必须)
  """
  check_len = []
  cols = []
  labels = [label]
  check_len.append(len(dimensios))
  cols.append('dimensios')
  if label2 is not None:
    labels.append(label2)
  if label3 is not None:
    labels.append(label3)
  if label4 is not None:
    labels.append(label4)
  if label5 is not None:
    labels.append(label5)

  datas = [data]
  check_len.append(len(data))
  cols.append('data')
  if data2 is not None:
    labels.append(data2)
    check_len.append(len(data2))
    cols.append('data2')
  if data3 is not None:
    labels.append(data3)
    check_len.append(len(data3))
    cols.append('data3')
  if data4 is not None:
    labels.append(data4)
    check_len.append(len(data4))
    cols.append('data4')
  if data5 is not None:
    labels.append(data5)
    check_len.append(len(data5))
    cols.append('data5')

  if max(check_len) != min(check_len):
    raise ValueError("参数：{0}，需要包含相同数量的元素，当前元素数量分别是:{1}，请调整参数后重试".format("、".join(cols), "、".join(map(str, check_len))))

  return chart.plot_radar(dimensios, datas, labels, title)

@mcp.tool()
def chart_bar_heng(names: list[str], values: list[float], changes: list[float] | None = None, title: Optional[str] = None) -> str:
  """
  根据传入的数据，绘制横版柱状图，返回绘制生成的图片保存路径
  特别适用于比较类别名称较长或类别数量较多时，不同类别的数值大小差异以及近期变化趋势，比如：股东持股比例与变化情况等等。​

  参数：
    names: 柱状图数据标签列表（建议2个及以上）
    values: 数据标签对应的数据值列表，长度需和names一致
    changes: 数据标签对应的数据变化百分比(非必须)
    title: 生成图表的标题(非必须)
  """
  check_len = [len(names), len(values)]
  cols = ['names', 'values']
  if changes is not None:
    check_len.append(len(changes))
    cols.append('changes')
  if max(check_len) != min(check_len):
    raise ValueError("参数：{0}，需要包含相同数量的元素，当前元素数量分别是:{1}，请调整参数后重试".format("、".join(cols), "、".join(map(str, check_len))))
  
  return chart.plot_bar_heng_chart(names, values, changes, title)

@mcp.tool()
def chart_line(dates: list[str]
                , label: str, data: list[float]
                , label2: Optional[str] = None, data2: Optional[list[float]] = None
                , label3: Optional[str] = None, data3: Optional[list[float]] = None
                , label4: Optional[str] = None, data4: Optional[list[float]] = None
                , label5: Optional[str] = None, data5: Optional[list[float]] = None
                , x_label: Optional[str] = None, y_label: Optional[str] = None, title: Optional[str] = None) -> str:
  """
  根据传入的数据，绘制折线图（可同时展示多条折线，最多5条），返回绘制生成的图片保存路径
  最佳呈现单一或多个数据序列随时间（年份、季度、月份）变化的连续趋势、波动性、增长或下降规律，比如：商品、原材料价格趋势等等。

  参数：
    dates: 折线图数据标签列表（建议5个及以上）
    label: 折线图第1数据系列的名称
    data: 折线图第1个数据系列数据，长度需和dates长度一致
    label2: 折线图第2个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data2: 折线图第2个数据系列数据，长度需和dates长度一致（非必须，如果没有第2个系列可以不传）
    label3: 折线图第3个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data3: 折线图第3个数据系列数据，长度需和dates长度一致（非必须，如果没有第3个系列可以不传）
    label4: 折线图第4个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data4: 折线图第4个数据系列数据，长度需和dates长度一致（非必须，如果没有第4个系列可以不传）
    label5: 折线图第5个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data5: 折线图第5个数据系列数据，长度需和dates长度一致（非必须，如果没有第5个系列可以不传）
    x_label: x轴的名称(非必须)
    y_label: y轴的名称(非必须)
    title: 生成图表的标题(非必须)
  """
  map_data = {}
  map_data[label] = data

  check_len = [len(dates), len(data)]
  cols = ['dates', 'data']
  
  if label2 is not None and data2 is not None:
    map_data[label2] = data2 
    check_len.append(len(data2))
    cols.append('data2')
  if label3 is not None and data3 is not None:
    map_data[label3] = data3
    check_len.append(len(data3))
    cols.append('data3')
  if label4 is not None and data4 is not None:  
    map_data[label4] = data4
    check_len.append(len(data4))
    cols.append('data4')
  if label5 is not None and data5 is not None:
    map_data[label5] = data5
    check_len.append(len(data5))
    cols.append('data5')

  if max(check_len) != min(check_len):
    raise ValueError("参数：{0}，需要包含相同数量的元素，当前元素数量分别是:{1}，请调整参数后重试".format("、".join(cols), "、".join(map(str, check_len))))

  return chart.plot_linechart(dates, map_data, x_label, y_label, title)

@mcp.tool()
def chart_bar(x_labels: list[str]
              , label: str, data: list[float]
              , label2: Optional[str] = None, data2: Optional[list[float]] = None
              , label3: Optional[str] = None, data3: Optional[list[float]] = None
              , label4: Optional[str] = None, data4: Optional[list[float]] = None
              , label5: Optional[str] = None, data5: Optional[list[float]] = None
              , x_label: Optional[str] = None, y_label: Optional[str] = None, title: Optional[str] = None) -> str:
  """
  根据传入的数据，绘制柱状图（可同时展示多条柱子，最多5条），返回绘制生成的图片保存路径
  有效比较不同离散类别（如不同月份、不同产品线、不同竞争对手）的数量或数值大小，比如：按季度展示不同成本/营收数据等等

  参数：
    x_labels: 柱状图x轴的数据列表（建议3个及以上）
    label: 柱状图第1数据系列的名称
    data: 柱状图第1个数据系列数据，长度需和x_labels长度一致
    label2: 柱状图第2个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data2: 柱状图第2个数据系列数据，长度需和x_labels长度一致（非必须，如果没有第2个系列可以不传）
    label3: 柱状图第3个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data3: 柱状图第3个数据系列数据，长度需和x_labels长度一致（非必须，如果没有第3个系列可以不传）
    label4: 柱状图第4个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data4: 柱状图第4个数据系列数据，长度需和x_labels长度一致（非必须，如果没有第4个系列可以不传）
    label5: 柱状图第5个数据系列的名称（非必须，如果没有第2个系列可以不传）
    data5: 柱状图第5个数据系列数据，长度需和x_labels长度一致（非必须，如果没有第5个系列可以不传）
    x_label: x轴的名称(非必须)
    y_label: y轴的名称(非必须)
    title: 生成图表的标题(非必须)
  """
  map_data = {}
  map_data[label] = data

  check_len = [len(x_labels), len(data)]
  cols = ['x_labels', 'data']
  
  if label2 is not None and data2 is not None:
    map_data[label2] = data2 
    check_len.append(len(data2))
    cols.append('data2')
  if label3 is not None and data3 is not None:
    map_data[label3] = data3
    check_len.append(len(data3))
    cols.append('data3')
  if label4 is not None and data4 is not None:  
    map_data[label4] = data4
    check_len.append(len(data4))
    cols.append('data4')
  if label5 is not None and data5 is not None:
    map_data[label5] = data5
    check_len.append(len(data5))
    cols.append('data5')

  if max(check_len) != min(check_len):
    raise ValueError("参数：{0}，需要包含相同数量的元素，当前元素数量分别是:{1}，请调整参数后重试".format("、".join(cols), "、".join(map(str, check_len))))
  
  return chart.plot_barchart(x_labels, map_data, x_label, y_label, title)

@mcp.tool()
def chart_table(csv_string: str, sep: Optional[str] = ',', title: Optional[str] = None) -> str:
  """
  根据传入的csv字符串内容，绘制成表格图片，返回绘制生成的图片保存路径
  可以用来展示有多个字段或非数值类型列表数据，包括但不限于：管理层列表、股东列表、大事件列表等

  参数：
    csv_string: 需要生成表格的csv图片
    sep: csv的字段间隔符(非必须，默认：,)
    title: 生成图表的标题(非必须)
  """
  return chart.plot_table(csv_string, sep, title)

if __name__ == "__main__":
  mcp.run()
  # # K线图
  # chart_kline(
  #   dates=[ "2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06", "2023-01-07", "2023-01-08", "2023-01-09", "2023-01-10", "2023-01-11", "2023-01-12", "2023-01-13", "2023-01-14", "2023-01-15", "2023-01-16", "2023-01-17", "2023-01-18", "2023-01-19", "2023-01-20", "2023-01-21", "2023-01-22", "2023-01-23", "2023-01-24", "2023-01-25", "2023-01-26", "2023-01-27", "2023-01-28", "2023-01-29", "2023-01-30"]
  #   , closes=[ 100.15, 100.15, 101.21, 99.83, 99.59, 100.58, 99.85, 100.7, 100.91, 100.45, 101.12, 101.6, 101.98, 101.39, 99.64, 101.28, 101.01, 101.88, 100.11, 99.6, 97.62, 98.48, 97.49, 97.53, 98.57, 97.11, 96.45, 95.51, 95.56, 94.64]
  #   , opens=[ 100.29, 101.63, 100.52, 100.1, 101.09, 101.36, 100.89, 102.91, 103.1, 101.67, 102.53, 102.28, 101.4, 99.79, 102.19, 101.97, 101.9, 100.21, 100.28, 98.82, 100.11, 97.61, 99.08, 98.66, 97.44, 97.09, 96.41, 96.3, 94.66, 94.77]
  #   , highs=[ 100.13, 100.71, 99.47, 99.23, 99.82, 99.15, 100.4, 100.73, 99.81, 100.23, 99.79, 101.8, 101.38, 99.46, 100.78, 100.28, 101.22, 98.14, 98.2, 97.57, 98.08, 97.05, 95.39, 97.8, 96.89, 96.14, 95.37, 94.59, 92.95, 94.5]
  #   , lows=[ 100.15, 101.21, 99.83, 99.59, 100.58, 99.85, 100.7, 100.91, 100.45, 101.12, 101.6, 101.98, 101.39, 99.64, 101.28, 101.01, 101.88, 100.11, 99.6, 97.62, 98.48, 97.49, 97.53, 98.57, 97.11, 96.45, 95.51, 95.56, 94.64, 94.73]
  #   , volumes=[ 3568, 2569, 2409, 2104, 2041, 2667, 2106, 3159, 4566, 3769, 3205, 1473, 1354, 2443, 2689, 3315, 3964, 3150, 1986, 1171, 1576, 1212, 2844, 3816, 2757, 1109, 3463, 1022, 2784, 4267]
  # )

  # #饼图
  # chart_pie(
  #   categorys=["智能手机","云服务","IOT设备"]
  #   , values=[45, 20, 15]
  # )

  # # 柱状+折线
  # chart_bar_line(
  #   x_labels=[ "2023-01-01", "2023-01-02", "2023-01-03"]
  #   , bar_values=[ 100.15, 100.15, 101.21]
  #   , line_values=[ 0.15, 0.15, -0.21]
  # )

  # # 雷达图
  # chart_radar(
  #   dimensios=["盈利能力", "成长能力", "偿债能力"]
  #   , label = "企业1"
  #   , data=[0.85, 0.75, 0.90]
  #   , label2 = "企业2"
  #   , data2=[0.70, 0.65, 0.85]
  # )

  # # 横柱状图
  # chart_bar_heng(
  #   names=["国家队", "公募基金", "QFII"]
  #   , values=[12.5, 25.3, 8.7]
  #   , changes=[0.2, -1.5, 0.8]
  # )

  # # 折线图
  
  # chart_line(
  #   **{
  #     "dates":["2025-04-29","2025-05-01","2025-05-02","2025-05-05","2025-05-06","2025-05-07","2025-05-08","2025-05-09","2025-05-12","2025-05-13","2025-05-14","2025-05-15","2025-05-16","2025-05-19","2025-05-20","2025-05-21","2025-05-22","2025-05-23","2025-05-26","2025-05-27","2025-05-28","2025-05-29","2025-05-30","2025-06-02","2025-06-03","2025-06-04","2025-06-05","2025-06-06","2025-06-09","2025-06-10","2025-06-11","2025-06-12","2025-06-13","2025-06-16","2025-06-17","2025-06-18","2025-06-19","2025-06-20","2025-06-23","2025-06-24","2025-06-25","2025-06-26","2025-06-27","2025-06-30","2025-07-01","2025-07-02","2025-07-03","2025-07-04","2025-07-07","2025-07-08","2025-07-09","2025-07-10","2025-07-11","2025-07-14","2025-07-15","2025-07-16","2025-07-17","2025-07-18","2025-07-21","2025-07-22"]
  #     ,"label":"港币兑离岸人民币"
  #     ,"data":[0.9391,0.9393,0.9397,0.9369,0.9374,0.9382,0.9305,0.9292,0.93,0.9313,0.9318,0.9308,0.924,0.923,0.9236,0.9231,0.9227,0.9224,0.9217,0.9198,0.9206,0.9157,0.9158,0.9174,0.9177,0.9168,0.919,0.919,0.9167,0.9139,0.9145,0.9154,0.916,0.9171,0.9139,0.9157,0.9151,0.9163,0.9165,0.9155,0.9122,0.9141,0.9136,0.9121,0.9137,0.9118,0.9122,0.9123,0.9134,0.913,0.9146,0.9148,0.9152,0.9139,0.913,0.9118,0.9135,0.9147,0.9151,0.9138]
  #     ,"label2":"美元人民币中间价"
  #     ,"data2":[7.2116,7.2098,7.2066,7.2043,7.2029,7.2014,7.2073,7.2095,7.2066,7.2008,7.2005,7.2073,7.2095,7.2066,7.1991,7.1963,7.1938,7.1916,7.1931,7.1937,7.1903,7.1919,7.1848,7.1894,7.1876,7.1907,7.1848,7.1833,7.1869,7.1886,7.1865,7.1845,7.1855,7.184,7.1815,7.1803,7.1772,7.1789,7.1746,7.1761,7.1729,7.1695,7.171,7.1656,7.1668,7.162,7.1627,7.1586,7.1534,7.1546,7.1541,7.151,7.1475,7.1491,7.1498,7.1526,7.1461,7.1498,7.1522,7.146]
  #     ,"title":"汇率波动"
  #     ,"x_label":"日期"
  #     ,"y_label":"汇率"}
  # )

  # # 柱状图
  # chart_bar(
  #   x_labels=[ "2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
  #   , label="数据系列1"
  #   , data=[ 100.15, 100.15, 101.21, 99.83, 99.59 ]
  #   , label2="数据系列2"
  #   , data2=[ 100.29, 101.63, 100.52, 100.1, 101.09 ]
  # )

  # # 表格
  # chart_table(
  #   csv_string="ID,Name,Department\n1,Alice,这是汉子\n2,Bob,这是汉子\n3,Charlie,这是汉子"
  # )