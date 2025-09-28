"""
Prompt templates for various question types and datasets.

This module provides prompt templates and functions to create prompts for:
- Single choice questions (with/without reasoning)
- Cloze questions (fill in the blank)
- GSM8K math problems
- GPQA questions

Templates are available in both English and Chinese, with options for
including step-by-step reasoning or direct answers.
"""

single_choice_prompts = {
    'single_choice_cn_with_reasoning': '{question}\n请严格按照如下格式回答：[[选项]]，例如：选项: [[A]]。\n让我们一步一步思考：\n',
    'single_choice_cn': '{question}\n请直接回答下面的问题并直接给出答案的选项序号。请严格按照如下格式回答：[[选项]]，例如：选项: [[A]]。\n',
    'single_choice_en_with_reasoning': "{question}\nPlease Give the response by strictly following this format: [[choice]],for example: Choice: [[A]].\nLet's think step by step:\n",
    'single_choice_en': 'Please answer the following question directly and give the answer directly without any reasoning process. Please strictLy follow the format: [[choice]],for example: Choice: [[A]].\n{question}\n',
}

cloze_prompts = {
    'cloze_cn': [
        dict(role='HUMAN', prompt='请直接回答下面的问题并直接给出答案\nQ: {question}'),
        dict(role='BOT', prompt='A: {answer}'),
    ],
    'cloze_en': [
        dict(role='HUMAN', prompt='Please answer the following question and give the answer directly\nQ: {question}'),
        dict(role='BOT', prompt='A: {answer}'),
    ],
    'cloze_cn_with_reasoning': [
        dict(role='HUMAN', prompt='Q: {question}\n让我们一步一步思考来回答这个问题：\n'),
        dict(role='BOT', prompt='A: {answer}'),
    ],
    'cloze_en_with_reasoning': [
        dict(role='HUMAN', prompt="""Q: {question}\nLet's think step by step:\n"""),
        dict(role='BOT', prompt='A: {answer}'),
    ],
}

gsm8k_prompts = {
    'reasoning': [
        dict(role='HUMAN', prompt="""Q: {question}\nPlease Give the response by strictly following this format: [[answer]], for example: Answer: [[50]].Let's think step by step:\n"""),
        dict(role='BOT', prompt='A: {answer}'),
        dict(role='HUMAN', prompt='{reasoning_process_main}'),
        dict(role='HUMAN', prompt='{reasoning_process_socratic}'),
    ],
    'no_reasoning': [
        dict(role='HUMAN', prompt='Please answer the following question and give the answer directly without any reasoning process. Please Give the response by strictly following this format: [[answer]], for example: Answer: [[50]].\nQ: {question}'),
        dict(role='BOT', prompt='A: {answer}'),
        dict(role='HUMAN', prompt='{reasoning_process_main}'),
        dict(role='HUMAN', prompt='{reasoning_process_socratic}'),
    ],
}

gpqa_prompts = {
    'reasoning': [
        dict(role='HUMAN', prompt="""Q: {question}\nPlease Give the response by strictly following this format: [[choice]],for example: Choice: [[A]].\nLet's think step by step:\n"""),
        dict(role='BOT', prompt='A: {answer}'),
    ],
    'no_reasoning': [
        dict(role='HUMAN', prompt='Please answer the following question directly and give the answer directly without any reasoning process. Please strictly follow the format: [[choice]],for example: Choice: [[A]].\n{question}\n'),
        dict(role='BOT', prompt='A: {answer}'),
    ],
    # 'no_reasoning': [
    #     dict(role='HUMAN', prompt='Please answer the following question and give the answer directly\nQ: {question}'),
    #     dict(role='BOT', prompt='A: {answer}'),
    # ],
}

mathbench_sets = {
    # Practice Part
    # 'college': ['single_choice_en'],
    'college': ['single_choice_cn', 'single_choice_en'],
    'high': ['single_choice_cn', 'single_choice_en'],
    'middle': ['single_choice_cn', 'single_choice_en'],
    'primary': ['cloze_cn', 'cloze_en'],
    'arithmetic': ['cloze_en'],
    # Theory part
    'college_knowledge': ['single_choice_cn', 'single_choice_en'],
    'high_knowledge': ['single_choice_cn', 'single_choice_en'],
    'middle_knowledge': ['single_choice_cn', 'single_choice_en'],
    'primary_knowledge': ['single_choice_cn', 'single_choice_en'],
}


def create_prompt(budget=512):
    """
    Create single choice prompts with token budget constraints.
    
    Args:
        budget: Token limit for response (default: 512)
        
    Returns:
        dict: Modified single_choice_prompts with budget constraints added
    """
    new = single_choice_prompts['single_choice_en_with_reasoning'] \
        .replace("Let's think step by step:\n", f"Let's think step by step and use less than {budget} tokens:\n")
    single_choice_prompts['single_choice_en_with_reasoning'] = new
    new = single_choice_prompts['single_choice_cn_with_reasoning'] \
        .replace("让我们一步一步思考：\n", f"让我们一步一步思考并使用少于 {budget} tokens:\n")
    single_choice_prompts['single_choice_cn_with_reasoning'] = new
    return single_choice_prompts


def create_cloze_prompt(budget=512):
    """
    Create cloze question prompts with token budget constraints.
    
    Args:
        budget: Token limit for response (default: 512)
        
    Returns:
        dict: Modified cloze_prompts with budget constraints added
    """
    new = cloze_prompts['cloze_en_with_reasoning'][0]['prompt'] \
        .replace("Let's think step by step:\n", f"Let's think step by step and use less than {budget} tokens:\n")
    cloze_prompts['cloze_en_with_reasoning'][0]['prompt'] = new
    new = cloze_prompts['cloze_cn_with_reasoning'][0]['prompt'] \
        .replace("让我们一步一步思考来回答这个问题：\n", f"让我们一步一步思考并使用少于 {budget} tokens来回答这个问题:\n")
    cloze_prompts['cloze_cn_with_reasoning'][0]['prompt'] = new
    return cloze_prompts


def create_gsm8k_prompt(budget=512):
    """
    Create GSM8K math problem prompts with token budget constraints.
    
    Args:
        budget: Token limit for response (default: 512)
        
    Returns:
        dict: Modified gsm8k_prompts with budget constraints added
    """
    new = gsm8k_prompts['reasoning'][0]['prompt'] \
        .replace("Let's think step by step:\n", f"Let's think step by step and use less than {budget} tokens:\n")
    gsm8k_prompts['reasoning'][0]['prompt'] = new
    return gsm8k_prompts


def create_gpqa_prompt(budget=512):
    """
    Create GPQA question prompts with token budget constraints.
    
    Args:
        budget: Token limit for response (default: 512)
        
    Returns:
        dict: Modified gpqa_prompts with budget constraints added
    """
    new = gpqa_prompts['reasoning'][0]['prompt'] \
        .replace("Let's think step by step:\n", f"Let's think step by step and use less than {budget} tokens:\n")
    gpqa_prompts['reasoning'][0]['prompt'] = new
    return gpqa_prompts
