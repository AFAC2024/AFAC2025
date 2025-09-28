import pandas as pd

date = "0726"
# 读取两个预测结果文件
file1_path = f'results/predict_result.csv'
file2_path = f'results/predict_result_roll.csv'

df1 = pd.read_csv(file1_path, dtype={'fund_code': str})
df2 = pd.read_csv(file2_path, dtype={'fund_code': str})

# 确保两个文件的基金代码和交易日期一致
assert df1['fund_code'].equals(df2['fund_code']), "基金代码不一致"
assert df1['transaction_date'].equals(df2['transaction_date']), "交易日期不一致"

# 创建结果DataFrame，复制基金代码和交易日期
result_df = df1.copy()

# 计算申购和赎回的加权平均值（各50%权重）
result_df['apply_amt_pred'] = df1['apply_amt_pred'] * 0.5 + df2['apply_amt_pred'] * 0.5
result_df['redeem_amt_pred'] = df1['redeem_amt_pred'] * 0.5 + df2['redeem_amt_pred'] * 0.5

# 保存结果到新的CSV文件
output_path = f'results/predict_result_final.csv'
result_df.to_csv(output_path, index=False)

print(f"整合完成，结果已保存到: {output_path}")