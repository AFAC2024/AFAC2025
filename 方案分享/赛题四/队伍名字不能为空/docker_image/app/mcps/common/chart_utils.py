"""
图表绘制工具

1.0 @nambo 2025-07-20
"""
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import gridspec
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter
import mplfinance as mpf
from matplotlib.ticker import LinearLocator
from io import StringIO
import os
import sys
import time
import random
import json

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

SAVE_DIR = os.path.join(current_dir, '_imgs')

# 加载字体
IMG_FONTS = []
for name in ['Songti.ttc', 'Times New Roman.ttf']:
  # 手动注册字体
  fm.fontManager.addfont(os.path.join(current_dir, 'fonts') + '/' + name)
  # fm.fontManager.addfont('/usr/local/share/fonts/custom/Times New Roman.ttf')

  IMG_FONTS.append(fm.FontProperties(fname=os.path.join(current_dir, 'fonts') + '/' + name).get_name())

# 刷新缓存
fm._get_font.cache_clear()

# 设置专业财经图表样式
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("deep")
COLORS = sns.color_palette('deep')

# 颜色
MAIN_COLOR = COLORS[0]
MAIN_COLOR_APHLA = "#D9E0F6"
SECOND_COLOR = COLORS[1]

# 设置全局字体

# 定义一个函数来创建类似东方财富的样式  
def create_eastmoney_style():  
	# 创建一个空字典来存储样式设置  
	style = mpf.make_mpf_style(base_mpf_style='binance', rc={'font.size': 8}, y_on_right=False)  
	  
	# 修改蜡烛图的颜色  
	style.update(  
		candlestick_ohlc=dict(  
			upcolor='#FF3333',  # 东方财富上涨颜色可能接近绿色  
			downcolor='#008B45',  # 东方财富下跌颜色可能接近红色  
			edgecolor='#333333',  # 蜡烛图边缘颜色  
			wickcolor='#333333',  # 影线颜色  
			alpha=0.8  # 透明度  
		)  
	)  
	  
	# 修改成交量柱状图的颜色  
	style.update(  
		volume_candlestick_ohlc=dict(  
			upcolor='#FF3333',  # 成交量上涨颜色（可能不同于蜡烛图）  
			downcolor='#008B45',  # 成交量下跌颜色  
			edgecolor='none',  # 成交量柱状图边缘颜色  
			alpha=0.4  # 成交量柱状图透明度  
		)  
	)  
	  
	# 修改图表背景色、网格线等（根据东方财富风格自行调整）  
	style.update(  
		rc={
      'axes.facecolor': 'white',  # 背景色  
			'grid.color': '#CCCCCC',  # 网格线颜色  
			'grid.linestyle': '--',  # 网格线样式  
			'grid.linewidth': 0.5  # 网格线宽度  
		}  
	)
	  
	# 返回自定义样式  
	return style 

# 创建一个自定义的日期格式化器  
def my_date_formatter(x, pos=None):  
	# 将x（matplotlib的日期浮点数）转换为datetime对象  
	date = mdates.num2date(x)  
	# 格式化日期为月-日格式  
	return date.strftime('%m-%d')

def number_split_2len(num):
  v_len = len(str(int(num)))
  if v_len > 2:
    unit = 10 ** (v_len - 2)
    unit_name = {
      '10': '十',
      '100': '百',
      '1000': '千',
      '10000': '万',
      '100000': '十万',
      '1000000': '百万',
      '10000000': '千万',
      '100000000': '亿',
      '1000000000': '十亿',
      '10000000000': '百亿',
      '100000000000': '千亿'
    }
    return unit, unit_name[str(unit)]
  
  return 1, ''

# 绘制股票K线图
def plot_stock_kline(dates, closes, opens, highs, lows, volumes, title=None):
  if title == None:
    title= ''
  data = pd.DataFrame({
      'date': dates, 'open': opens, 
      'high': highs, 'low': lows, 
      'close': closes, 'volume': volumes
  })

  data = data.sort_values(by='date', ascending=True)

  data['date'] = pd.to_datetime(data['date'])

  # 将索引转换为 DatetimeIndex
  data.index = data['date']

  max_volume = data['volume'].max()
  volume_unit, volume_unit_name = number_split_2len(max_volume)
  data['volume'] = data['volume'] / volume_unit
  ylabel_lower = '成交量（{0}手）'.format(volume_unit_name)

  max_price = data['high'].max()
  unit, unit_name = number_split_2len(max_price)
  data['open'] = data['open'] / unit
  data['close'] = data['close'] / unit
  data['high'] = data['high'] / unit
  data['low'] = data['low'] / unit
  ylabel = '价格（{0}元）'.format(unit_name)
	
  # 计算移动平均线（7日和10日）
  data['ma7'] = data['close'].rolling(7).mean()
  data['ma10'] = data['close'].rolling(10).mean()

  # 创建自定义均线图（设置颜色和粗细）
  ap0 = mpf.make_addplot(data['ma7'], color=SECOND_COLOR, width=1.2)   # 白色7日均线
  ap1 = mpf.make_addplot(data['ma10'], color=MAIN_COLOR, width=1.2) # 黄色10日均线
  
  fig, ax = mpf.plot(data, type='candle',
    volume=True,
    style=create_eastmoney_style(),
    title=title,
    ylabel=ylabel,  
    ylabel_lower=ylabel_lower,
    addplot=[ap0, ap1],
    show_nontrading=False,
    returnfig=True,
    update_width_config={
        'volume_width': 0.8,
        'candle_linewidth': 1,
        'volume_width': 0.8,
        'volume_linewidth': 1
    }
  )  

  # 优化x轴标签显示 - 只显示部分标签
  n = len(data)
  step = max(1, n // 6)  # 每6个数据点显示一个标签

  # 创建索引位置和对应的日期标签
  xticks = list(range(0, n, step))
  xticklabels = [data['date'].iloc[i].strftime('%m-%d') for i in xticks]
  # 设置x轴刻度（主图ax[0]和副图ax[1]）
  ax[1].set_xticks(xticks)
  ax[1].set_xticklabels(xticklabels, rotation=80)

  plt.rcParams['axes.labelsize'] = 12  # 默认 ylabel 字号
  plt.rcParams['xtick.labelsize'] = 10  # x 轴刻度字号
  plt.rcParams['ytick.labelsize'] = 10  # y 轴刻度字号
  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False

  filepath = SAVE_DIR + '/' + f"kline_{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')
  return filepath

# 2. 财务数据表格
def plot_table(csv_string, sep=',', title=None):
  # 将字符串转换为DataFrame
  data = pd.read_csv(StringIO(csv_string), sep=sep)

  # 创建图形和轴
  fig, ax = plt.subplots(figsize=(8, 3))          # 设置图形大小
  ax.axis('off')                                  # 隐藏坐标轴

  # 创建表格并设置样式
  table = plt.table(
    cellText=data.values,                       # 表格数据
    colLabels=data.columns,                     # 列标题
    loc='center',                               # 表格位置
    cellLoc='center'                            # 单元格对齐方式
  )

  # 使用seaborn样式
  sns.set_theme(style="whitegrid")                # 设置seaborn主题
  table.set_fontsize(12)                          # 字体大小
  table.scale(1.2, 2)                           # 缩放表格（宽度，高度）

  # ===== 样式设置 =====
  # 1.设置列标题背景色
  for i, _ in enumerate(data.columns):
    cell = table[0, i]
    cell.set_facecolor('#40466e')               # 深蓝色背景
    cell.set_text_props(color='white')          # 白色文字

  # 3. 设置边框样式
  for key, cell in table.get_celld().items():
    # 所有单元格边框
    cell.set_edgecolor('gray')
    cell.set_linewidth(0)
    cell.set_edgecolor(None)
    # 交替行颜色
    for i in range(len(data)):
      if i % 2 == 0:
        for j in range(len(data.columns)):
          table.get_celld()[(i+1, j)].set_facecolor(MAIN_COLOR_APHLA)  # +1因为第0行是标题

  if title is not None and title != '':
    plt.title(title, fontsize=12)

  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False

  filepath = SAVE_DIR + '/' + f"table_{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')
  return filepath

# 3. 业务结构饼图
def plot_pie(labels, datas, title=None):
  
  fig, ax = plt.subplots(figsize=(8, 8))
  # explode = (0.05, 0.02, 0.02, 0.02, 0.02)
  
  json_data = {
      'labels': labels,
      'datas': datas
  }
  df = pd.DataFrame(json_data)
  df = df.sort_values(by='datas', ascending=False)
  labels = df['labels'].tolist()
  datas = df['datas'].tolist()

  ax.pie(
    datas, 
    labels=labels, 
    autopct='%1.1f%%',
    startangle=90,
    # explode=explode,
    # shadow=True,
    colors=COLORS,
    textprops={'fontsize': 12}
  )

  if title is not None and title != '':
    plt.title(title, fontsize=12)

  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False
  
  filepath = SAVE_DIR + '/' + f"pie_{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')
  return filepath

# 4. 季度营收+增长率组合图
def plot_bar_line(dates, bar_datas, line_datas, bar_name=None, line_name=None, title=None):
  
  fig, ax1 = plt.subplots(figsize=(12, 6))

  df = pd.DataFrame({
      'dates': dates,
      'bar_datas': bar_datas,
      'line_datas': line_datas
  })
  df = df.sort_values(by='dates', ascending=True)
  dates = df['dates'].tolist()
  bar_datas = df['bar_datas'].tolist()
  line_datas = df['line_datas'].tolist()
  
  # 柱状图 - 营收
  sns.barplot(x=dates, y=bar_datas, ax=ax1, color=COLORS[0])
  if bar_name is not None and bar_name != '':
    ax1.set_ylabel(bar_name, fontsize=12)
    ax1.set_ylim(0, 450)

  ax1.yaxis.set_major_locator(LinearLocator(numticks=5))  # 固定5个刻度
  ax1.tick_params(axis='y', width=1, color='grey')        # 设置刻度样式
  ax1.xaxis.set_major_locator(LinearLocator(numticks=10))
  # 折线图 - 增长率
  if line_datas is not None:
    ax2 = ax1.twinx()
    sns.lineplot(x=dates, y=line_datas, ax=ax2, 
        marker='o', linewidth=2.5, color=COLORS[1])
    if line_name is not None and line_name != '':
      ax2.set_ylabel(line_name, fontsize=12)
    # 数值标签
    for i, v in enumerate(line_datas):
      if v < 0:
        ax2.text(i, v+0.005, f'{v*100:.1f}%', 
            ha='center', fontsize=9)
      else:
        ax2.text(i, v+0.005, f'{v:.1f}', 
            ha='center', fontsize=9)
    ax2.grid(False)
    for spine in ax2.spines.values():
      spine.set_visible(False)

    ax2.yaxis.set_major_locator(LinearLocator(numticks=5))  # 固定5个刻度
    ax2.tick_params(axis='y', width=1, color='grey')        # 设置刻度样式
    ax2.xaxis.set_major_locator(LinearLocator(numticks=10))
  
  ax1.grid(axis='y',  # 仅显示y轴方向的网格线
        color='gray',  # 网格线颜色
        linestyle='--',  # 网格线样式（虚线）
        linewidth=0.5,  # 网格线宽度
        alpha=0.7)  # 透明度
  
  # 移除所有边框（上、下、左、右）
  for spine in ax1.spines.values():
    spine.set_visible(False)

  if title is not None and title != '':
    plt.title(title, fontsize=12)

  if len(dates) > 5:
    plt.xticks(rotation=45)
  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False
  
  filepath = SAVE_DIR + '/' + f"bar_line__{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')

  return filepath

# 5. 股票表现雷达图
def plot_radar(categories, datas, labels, title=None):
  N = len(categories)
  angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
  angles += angles[:1]
  
  fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(8, 8))
  
  idx = 0
  max_data = 0
  min_data = 9999999999999
  for data in datas:
    data += data[:1]
    if labels is not None and idx < len(labels):
      label = labels[idx]
    else:
      label = '系列' + str(idx)
    
    ax.plot(angles, data, 'o-', linewidth=2, color=COLORS[idx], 
            label=label)
    ax.fill(angles, data, alpha=0.25, color=COLORS[idx])

    if max_data < max(data):
      max_data = max(data)
    if min_data > min(data):
      min_data = min(data)

    idx += 1
  
  if max_data / (min_data+0.000001) > 100:
    raise ValueError("数据值差值过大，无法绘制雷达图。请检查数据单位是否统一或更换数据字段。当前最小值={0}, 当前最大值={1}".format(min_data, max_data))
  # 设置标签
  ax.set_xticks(angles[:-1])
  ax.set_xticklabels(categories, fontsize=12)
  ax.set_rlabel_position(0)

  t_ticks = []
  y_tick_names = []
  step = round(max_data / 8, 1)
  for i in range(0, 9):
    if i > 0:
      t_ticks.append(i * step)
      y_tick_names.append(str(round(i * step, 1)))

  plt.yticks(t_ticks, y_tick_names, 
              color="gray", fontsize=10)
  plt.ylim(0, max_data + step)
  
  if title is not None and title != '':
    plt.title(title, fontsize=12)

  plt.legend(loc='lower center',
      bbox_to_anchor=(0.5, -0.1),
      ncol=2,
    )
  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False
  
  filepath = SAVE_DIR + '/' + f"radar_{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')

  return filepath

# 6. 专业柱状图（机构持仓）
def plot_bar_heng_chart(names, values, changes=None, title=None):
  # 创建图形
  json_data = {
      'names': names,
      'values': values
  }
  if changes is not None and len(changes) > 0:
    json_data['changes'] = changes

  df = pd.DataFrame(json_data)
  df = df.sort_values(by='values', ascending=True)

  names = df['names'].tolist()
  values = df['values'].tolist()
  if changes is not None and len(changes) > 0:
    changes = df['changes'].tolist()

  fig, ax = plt.subplots(figsize=(10, 6))
  y_pos = np.arange(len(names))

  # 绘制柱状图（使用渐变色）
  colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(names)))
  bars = ax.barh(y_pos, values, color=colors, height=0.6)

  # 设置标签和标题
  ax.set_yticks(y_pos)
  ax.set_yticklabels(names, fontsize=12)
  # ax.set_xlabel('数值大小', fontsize=12)
  ax.xaxis.grid(True, linestyle='--', alpha=0.7)

  if title is not None and title != '':
    ax.set_title(title, fontsize=14, pad=15)

  # 在柱子末端添加数值标签
  for i, bar in enumerate(bars):
    width = bar.get_width()
    ax.text(width + 1,  # 值标签位置（柱子右侧）
            i, 
            f'{values[i]}', 
            va='center', 
            ha='left',
            fontsize=11)
    if changes is None:
      continue
    # 添加变化值标签（带颜色区分）
    change_value = round(changes[i], 1)
    change_color = '#2ca02c' if change_value >= 0 else '#d62728'  # 绿涨红跌
    change_txt = f'↑{change_value}%' if change_value >= 0 else f'↓{-change_value}%'
    
    if change_value == 0:
       change_color = '#333333'
       change_txt = ''
    ax.text(width + 2.1,  # 变化值位置（值标签右侧）
            i, 
            change_txt,
            va='center', 
            ha='left',
            color=change_color,
            fontsize=11,
            fontweight='bold')

  ax.grid(False)
  plt.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
  for spine in ax.spines.values():
    spine.set_visible(False)

  # 美化布局
  plt.tight_layout()
  ax.spines[['top', 'right']].set_visible(False)
  plt.subplots_adjust(left=0.2)  # 为长名称留出空间
  
  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False
  
  filepath = SAVE_DIR + '/' + f"bar_heng_chart_{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')

  return filepath

# 7. 折线图（价格趋势）
def plot_linechart(dates, values, x_label=None, y_label=None, title=None):
  
  keys = values.keys()

  json_data = {
    "dates": dates
  }
  for i, key in enumerate(keys):
    json_data[key] = values[key]
  
  df = pd.DataFrame(json_data)
  df = df.sort_values(by='dates', ascending=True)
  dates = df['dates'].tolist()
  for key in keys:
    values[key] = df[key].tolist()

  fig, ax = plt.subplots(figsize=(12, 6))

  legends = []
  for i, key in enumerate(keys):
    legends.append(key)
    sns.lineplot(x=dates, y=values[key], ax=ax, linewidth=2.5, 
                  color=COLORS[i], marker='o', markersize=5, label=key)
      
    ax.grid(False)
    for spine in ax.spines.values():
      spine.set_visible(False)

  ax.yaxis.set_major_locator(LinearLocator(numticks=8)) 
  if len(dates) > 10:
    ax.xaxis.set_major_locator(LinearLocator(numticks=10)) 
  ax.tick_params(axis='y', width=1, color='grey' ) 
  
  # 设置格式
  x_label = ''
  if x_label is not None:
    plt.xlabel(x_label)

  if y_label is not None:
    plt.ylabel(y_label)
  
  if title is not None and title != '':
    plt.title(title, fontsize=12)

  if len(dates) > 5:
    plt.xticks(rotation=45)
  
  plt.grid(axis='y',  # 仅显示y轴方向的网格线
        color='gray',  # 网格线颜色
        linestyle='--',  # 网格线样式（虚线）
        linewidth=0.5,  # 网格线宽度
        alpha=0.7)  # 透明度

  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False

  plt.legend(
    loc='lower center',          # 底部中间位置
    bbox_to_anchor=(0.5, -0.22), # 调整垂直位置 (y坐标负值表示向下移动)
    ncol=8,                      # 一行显示2个图例项（根据你的图例数量调整）
    borderaxespad=0.5            # 图例与轴的距离
  )
  
  # plt.legend()  # 显示图例
  
  filepath = SAVE_DIR + '/' + f"linechart_{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')

  return filepath

def plot_barchart(dates, values, x_label=None, y_label=None, title=None):
  json_data = {
    'date': dates
  }

  for idx, key in enumerate(values):
    json_data[key] = values[key]
  df = pd.DataFrame(json_data)
  df = df.sort_values(by='date', ascending=True)
  df = df.melt(id_vars='date', var_name='series', value_name='value')

  fig, ax = plt.subplots(figsize=(12, 6))
  sns.barplot(x='date', y='value', hue='series', ax=ax, data=df, palette=COLORS[:len(values)],
              dodge=True,
              gap=0.1,
              width=0.7)

  ax.grid(False)
  for spine in ax.spines.values():
    spine.set_visible(False)

  ax.yaxis.set_major_locator(LinearLocator(numticks=8))
  if len(dates) > 10:
    ax.xaxis.set_major_locator(LinearLocator(numticks=10))
  ax.tick_params(axis='y', width=1, color='grey' )        # 设置刻度样式
  
  # 设置格式
  x_label = ''
  if x_label is not None:
    plt.xlabel(x_label)

  if y_label is not None:
    plt.ylabel(y_label)
  
  if title is not None and title != '':
    plt.title(title, fontsize=12)

  if len(dates) > 5:
    plt.xticks(rotation=45)
  
  plt.grid(axis='y',  # 仅显示y轴方向的网格线
        color='gray',  # 网格线颜色
        linestyle='--',  # 网格线样式（虚线）
        linewidth=0.5,  # 网格线宽度
        alpha=0.7)  # 透明度

  plt.rcParams['font.sans-serif'] = IMG_FONTS
  plt.rcParams['axes.unicode_minus'] = False

  plt.legend(
    loc='lower center',          # 底部中间位置
    bbox_to_anchor=(0.5, -0.22), # 调整垂直位置 (y坐标负值表示向下移动)
    ncol=8,                      # 一行显示2个图例项（根据你的图例数量调整）
    borderaxespad=0.5            # 图例与轴的距离
  )
  
  filepath = SAVE_DIR + '/' + f"barchart_{time.time()}{random.randint(0, 9999)}.png"
  plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1, dpi=300)
  plt.close('all')

  return filepath

def to_json_array(data, precision=None):
    if isinstance(data, pd.Series):
        data = data.values
    if precision is not None:
        data = np.round(data, precision)
    return json.dumps(data.tolist(), indent=2, ensure_ascii=False)

if __name__ == '__main__':
  dates = pd.date_range('2023-01-01', periods=30)
  closes = pd.Series(np.cumsum(np.random.randn(30)) + 100)
  highs = closes + np.abs(np.random.randn(30))
  lows = closes - np.abs(np.random.randn(30))
  opens = closes.shift(1).fillna(closes[0])
  volumes = np.random.randint(1000, 5000, size=30)
  img = plot_stock_kline(
    dates, closes, opens, highs, lows, volumes, title=None
  )
  print(to_json_array(dates.strftime('%Y-%m-%d')).replace('\n', ''))
  print(to_json_array(opens, 2).replace('\n', ''))
  print(to_json_array(highs, 2).replace('\n', ''))
  print(to_json_array(lows, 2).replace('\n', ''))
  print(to_json_array(closes, 2).replace('\n', ''))
  print(to_json_array(volumes).replace('\n', ''))
  csv_data = "ID,Name,Department,Salary,Bonus %,Start Date,Performance\n1,Alice,Engineering,85000,15.0,2023-01-15,这是汉子\n2,Bob,Marketing,72000,12.5,2022-11-30,这是汉子\n3,Charlie,Sales,68000,20.0,2023-03-22,这是汉子\n4,Diana,HR,65000,10.0,2021-09-01,这是汉子\n5,Evan,Engineering,92000,18.0,2020-06-15,这是汉子\n6,Fiona,Marketing,78000,14.5,2023-05-10,这是汉子"
  plot_table(csv_data, ',', title='标题标题标题标题标题3如3134feaf')


  sectors = {
      '智能手机': 45,
      '云服务': 20,
      'IOT设备': 15,
      '广告服务': 12,
      '其他': 8,
      '21331': 11
  }
  plot_pie(sectors.keys(), sectors.values(), title='标题标题标题标题标题3如3134feaf')


  dates = ['2020Q4', '2021Q1', '2021Q2', '2021Q3', '2021Q4', '2022Q1', '2022Q2', '2022Q3', '2022Q4', '2023Q1']
  bar_datas = [230, 245, 260, 280, 290, 305, 318, 330, 350, 380]
  line_datas = [0.05, 0.07, 0.06, 0.08, 0.04, 0.05, 0.04, 0.06, 0.07, 0.10]
  plot_bar_line(
    [ "2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06", "2023-01-07", "2023-01-08", "2023-01-09", "2023-01-10", "2023-01-11", "2023-01-12", "2023-01-13", "2023-01-14", "2023-01-15", "2023-01-16", "2023-01-17", "2023-01-18", "2023-01-19", "2023-01-20", "2023-01-21", "2023-01-22", "2023-01-23", "2023-01-24", "2023-01-25", "2023-01-26", "2023-01-27", "2023-01-28", "2023-01-29", "2023-01-30"],
    [ 100.15, 100.15, 101.21, 99.83, 99.59, 100.58, 99.85, 100.7, 100.91, 100.45, 101.12, 101.6, 101.98, 101.39, 99.64, 101.28, 101.01, 101.88, 100.11, 99.6, 97.62, 98.48, 97.49, 97.53, 98.57, 97.11, 96.45, 95.51, 95.56, 94.64],
    [ 0.15, 0.15, -0.21, 0.83, 0.59, -0.58, 0.85, 0.7, 0.91, -0.45, 0.12, 0.6, 0.98, -0.39, 0.64, 0.28, 0.01, 0.88, 0.11, 0.6, 0.62, 0.48, 0.49, 0.53, 0.57, 0.11, 0.45, 0.51, 0.56, 0.64],
    title='标题标题标题标题标题3如3134feaf')


  plot_radar([
"流动比率",
"速动比率",
"资产负债率"
],
      [
        [
1.62,
1.37,
0.64
]
      ],
      [
        '宁德时代'
      ], title='资金链稳定性分析'
  )

  plot_bar_heng_chart(
    ['国家队', '公募基金', 'QFII', '保险', '券商', '社保'],
    [12.5, 25.3, 8.7, 15.2, 4.5, 3.8],
    # [0.2, -1.5, 0.8, 1.2, -0.3, 0.4],
    title='标题标题标题标题标题3如3134feaf'
  )

  # 生成模拟数据
  plot_linechart(pd.date_range('2022-01-01', periods=60), 
      {
        'key1': 50 + np.cumsum(np.random.randn(60)),
        'key2': 50 + np.cumsum(np.random.randn(60)),
      }, title='标题标题标题标题标题3如3134feaf')
  
  print(plot_barchart(
    [ "2023-01-01"], 
    {
      "数据系列1": [ 100.15],
      "数据系列2": [ 100.29]
    },
    title='标题标题标题标题标题3如3134feaf'))