import re
import numpy as np
import torch


def extract_answer(text):
    sentiment = re.search(r'<情感标签>\s*([^<]+?)\s*</情感标签>', text)
    return sentiment
def text_to_int(text):
    if 'positive' in text:
        return 1
    elif 'neutral' in text:
        return 0
    elif 'negative' in text:
        return -1

def sentiment_reward(prompts, completions, polarity, **kwargs):
    responses = [completion[0]['content'] for completion in completions]
    datas = [extract_answer(r) for r in responses]
    rewards = []
    for i,data in enumerate(datas):
        try:
            sen_pre = data.group(1)
            sen_pre = text_to_int(sen_pre)
            sen_label = polarity[i]
            sen_label = text_to_int(sen_label)
            print(sen_pre)
            reward = 0
            if sen_pre == sen_label:
                reward = 1
            else:
                reward = 0
        except:
            reward = 0
        rewards.append(reward)
    return rewards