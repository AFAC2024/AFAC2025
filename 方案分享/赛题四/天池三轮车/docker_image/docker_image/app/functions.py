from pyecharts import options as opts
from pyecharts.charts import Bar, Line
from pyecharts.globals import ThemeType


# 营业总收入图
def operating_receipt_line(x_data, bar1_data, line1_data):
    bar = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis(
            series_name="营业额（亿元）",
            y_axis=bar1_data,
            yaxis_index=0,  # 指定使用第一个Y轴
            color="#5793f3",
        )
        .extend_axis(  # 添加次Y轴
            yaxis=opts.AxisOpts(
                name="增长率 (%)",
                type_="value",
                min_=0,
                max_=50,
                position="right",
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(color="#d14a61")
                ),
                axislabel_opts=opts.LabelOpts(formatter="{value}%"),
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="销售额与增长率对比"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
            xaxis_opts=opts.AxisOpts(axispointer_opts=opts.AxisPointerOpts(type_="shadow")),
            yaxis_opts=opts.AxisOpts(
                name="销售额（万元）",
                min_=0,
                max_=250,
                position="left",
                axisline_opts=opts.AxisLineOpts(
                    linestyle_opts=opts.LineStyleOpts(color="#5793f3")
                ),
            ),
        )
    )

    # 创建折线图
    line = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis(
            series_name="增长率",
            y_axis=line1_data,
            yaxis_index=1,  # 指定使用第二个Y轴
            color="#d14a61",
            label_opts=opts.LabelOpts(formatter="{c}%"),
        )
    )

    # 组合图表
    bar.overlap(line)

    # 组合图表
    overlap_chart = bar.overlap(line)
    overlap_chart.render("operating_receipt_line.html")


# 盈利能力折线
def profitability_line(x_data, line1_data=None, line2_data=None, line3_data=None):
    (
        (
            Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="800px", height="400px"))
            .add_xaxis(x_data)
            .add_yaxis(
                "净利率",
                line1_data,
                is_smooth=True,
                symbol="circle",
                symbol_size=8,
                linestyle_opts=opts.LineStyleOpts(width=3),
                label_opts=opts.LabelOpts(is_show=False),
                color="#5793f3",
            )
            .add_yaxis(
                "毛利率",
                line2_data,
                is_smooth=True,
                symbol="diamond",
                symbol_size=8,
                linestyle_opts=opts.LineStyleOpts(width=3),
                label_opts=opts.LabelOpts(is_show=False),
                color="#d14a61",
            )
            .add_yaxis(
                "ROE",
                line3_data,
                is_smooth=True,
                symbol="triangle",
                symbol_size=8,
                linestyle_opts=opts.LineStyleOpts(width=3),
                label_opts=opts.LabelOpts(is_show=False),
                color="#675bba",
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="盈利能力指标"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                yaxis_opts=opts.AxisOpts(
                    name="数值",
                    type_="value",
                    axislabel_opts=opts.LabelOpts(formatter="{value} 单位"),
                ),
                xaxis_opts=opts.AxisOpts(name="时间"),
                legend_opts=opts.LegendOpts(pos_top="5%"),
                datazoom_opts=[
                    opts.DataZoomOpts(range_start=0, range_end=100),  # 添加数据缩放
                    opts.DataZoomOpts(type_="inside"),  # 添加内置缩放
                ],
            )
            .set_series_opts(
                areastyle_opts=opts.AreaStyleOpts(opacity=0.1)  # 设置区域填充样式
            )
        ).render("profitability_line.html")
    )


# 偿债能力折线
def debt_paying_ability_line(x_data, line1_data=None, line2_data=None):
    (
        (
            Line(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="800px", height="400px"))
            .add_xaxis(x_data)
            .add_yaxis(
                "流动比率(倍)",
                line1_data,
                is_smooth=True,
                symbol="circle",
                symbol_size=8,
                linestyle_opts=opts.LineStyleOpts(width=3),
                label_opts=opts.LabelOpts(is_show=False),
                color="#5793f3",
            )
            .add_yaxis(
                "资产负债率(%)",
                line2_data,
                is_smooth=True,
                symbol="diamond",
                symbol_size=8,
                linestyle_opts=opts.LineStyleOpts(width=3),
                label_opts=opts.LabelOpts(is_show=False),
                color="#d14a61",
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="偿债能力指标"),
                tooltip_opts=opts.TooltipOpts(trigger="axis"),
                yaxis_opts=opts.AxisOpts(
                    name="数值",
                    type_="value",
                    axislabel_opts=opts.LabelOpts(formatter="{value} 单位"),
                ),
                xaxis_opts=opts.AxisOpts(name="时间"),
                legend_opts=opts.LegendOpts(pos_top="5%"),
                datazoom_opts=[
                    opts.DataZoomOpts(range_start=0, range_end=100),  # 添加数据缩放
                    opts.DataZoomOpts(type_="inside"),  # 添加内置缩放
                ],
            )
            .set_series_opts(
                areastyle_opts=opts.AreaStyleOpts(opacity=0.1)  # 设置区域填充样式
            )
        ).render("debt_paying_ability_line.html")
    )



# x_data = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"]
# line1_data = [2.0, 2.2, 3.3, 4.5, 6.3, 10.2, 20.3, 23.4]  # 折线1数据
# line2_data = [2.5, 1.7, 2.5, 3.2, 5.4, 8.7, 18.3, 21.2]  # 折线2数据
# line3_data = [1.8, 2.8, 3.8, 5.0, 7.2, 12.1, 22.0, 25.0]
# triple_line(x_data, line1_data, line2_data, line3_data)
