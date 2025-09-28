import json

# 获取字符串中的json数组
# data 字符串
# return res_json json数组
def getStrJsonArray(data):
	json_start  = data.find('[')
	json_end = data.rfind(']')

	if json_start == -1 or json_end == -1 or json_start >= json_end:
		return []

	res_json = json.loads(data[json_start:json_end + 1])
	return res_json

# 获取字符串中的json数据
# data 字符串
# return res_json json数组
def getStrJson(data):
	json_start  = data.find('{')
	json_end = data.rfind('}')

	if json_start == -1 or json_end == -1 or json_start >= json_end:
		return {}

	res_json = json.loads(data[json_start:json_end + 1])
	return res_json