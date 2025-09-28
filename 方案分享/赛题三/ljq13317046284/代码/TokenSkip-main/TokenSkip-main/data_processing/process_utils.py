import regex

from data_processing.answer_extraction import extract_math_answer, strip_string

def process_gsm8k_test(item):
    sample = {
        'dataset': 'gsm8k-cot',
        'id': item['id'],
        'messages': [
            {'role': 'user', 'content': item['question']},
            {'role': 'assistant', 'content': regex.sub(r"<<[^<>]*>>", "", item['cot']) + "\nSo the answer is $\\boxed{" + item['answer'].strip() + "}$."}
        ],
        'answer': item['answer'].replace(',', '')
    }
    yield sample

def process_math_test(item):
    question = item["problem"]
    try:
        answer = extract_math_answer(question, item['solution'], task="cot")
    except:
        return
    sample = {
        "dataset": "math-cot",
        "id": item['id'],
        "level": item["level"],
        "type": item["type"],
        # "category": item["category"],
        "messages": [
            {"role": "user", "content": question},
            {"role": "assistant", "content": "\n".join(regex.split(r"(?<=\.) (?=[A-Z])", item["solution"]))}
        ],
        "answer": answer
    }
    yield sample

def process_afac_cot(item):
    """处理AFAC数据集的CoT格式"""
    # 从output中提取答案部分
    output_text = item.get('output', '')
    
    # 查找boxed答案
    import re
    boxed_match = re.search(r'\\boxed{([A-Z])}', output_text)
    if boxed_match:
        answer = boxed_match.group(1)
    else:
        # 如果没有boxed格式，尝试从最后找答案
        answer_lines = [line.strip() for line in output_text.split('\n') if line.strip()]
        for line in reversed(answer_lines):
            if line in ['A', 'B', 'C', 'D']:
                answer = line
                break
        else:
            answer = 'A'  # 默认答案
    
    sample = {
        'dataset': 'afac-cot',
        'id': item.get('id', 'unknown'),
        'messages': [
            {'role': 'user', 'content': item.get('input', '')},
            {'role': 'assistant', 'content': output_text}
        ],
        'answer': answer
    }
    yield sample