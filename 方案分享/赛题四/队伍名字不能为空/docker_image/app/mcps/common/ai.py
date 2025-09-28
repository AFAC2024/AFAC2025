from .cache import setCache, getCache
from autogen import ConversableAgent, AssistantAgent, UserProxyAgent, config_list_from_json

config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

agent = ConversableAgent(
	"companyInfoBot",
	llm_config={"config_list": config_list},
	human_input_mode="NEVER"
)

# 送入提示词获取大模型响应
# prompt 提示词
# return reply 大模型响应
def getAiReply(prompt):
	print("【User】" + prompt)
	is_cache = True
	reply = getCache(prompt)
	if reply == None:
		count = 1
		while count > 0:
			try:
				reply = agent.generate_reply(messages=[{"content": prompt, "role": "user"}])
				count = -1
			except Exception as e:
				print(e)
				print("获取AI结果失败，将重试：", count)
				count += 1
		is_cache = False

	if reply == None or len(reply) == 0:
		reply = ''
		print("【Assistant】无回复")
	else:
		print("【Assistant】" + reply)
		if is_cache == False:
			setCache(prompt, reply)

	return reply