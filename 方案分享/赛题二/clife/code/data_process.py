# 导入所需的模块
from llm import LLM  # 导入大语言模型接口
import config.config as cfg  # 导入配置文件
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type  # 导入重试机制相关模块


def get_chunk_list(lst, chunk_size=400):
    """
    将列表分割成重叠的块

    参数:
        lst: 需要分割的列表
        chunk_size: 每块的大小，默认为400

    返回:
        包含重叠块的列表
    """
    result = []
    # 按指定块大小遍历列表
    for i in range(0, len(lst), chunk_size):
        # 每块前后各扩展5行，以确保上下文完整性
        result.append(lst[max(0, i - 5):min(i + chunk_size + 5, len(lst))])
    return result


def clean_text(text):
    """
    清理文本内容

    参数:
        text: 待清理的文本

    返回:
        清理后的文本
    """
    # 处理空文本
    if text is None:
        return ''

    # 去除首尾空白字符
    text = text.strip()

    # 按行分割，去除每行首尾空白字符
    lines = [line.strip() for line in text.split('\n')]

    # 过滤掉空行并重新组合文本
    return '\n'.join(line for line in lines if line)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1), retry=retry_if_exception_type((Exception,)))
def extract_module_raw_text(module_name, lines, path):
    """
    从文本行中提取指定模块的原始文本内容

    参数:
        module_name: 模块名称
        lines: 文本行列表
        path: 文件路径（用于调试信息）

    返回:
        提取的文本内容或文本数组
    """
    # 构造规则描述
    rule = module_name + ":" + cfg.rule_dict[module_name]

    # 将行列表合并为查询文本
    query = '\n'.join(lines)

    # 如果文本太短，直接返回"无"
    if len(query) < 20:
        return '无'

    try:
        # 根据不同模块类型使用不同的提示模板
        if module_name in ['术语解释', '续保条款', '出险条款', '附加条款']:
            # 使用特定提示模板提取内容
            text = LLM(query, cfg.extract_prompt2.format(rule=rule, all_rule=cfg.rule_dict, rule2=rule))
        elif module_name in ['保障相关时间']:
            # 使用时间相关提示模板提取内容
            text = LLM(query, cfg.extract_prompt_time)
        else:
            # 使用通用提示模板提取内容
            text = LLM(query, cfg.extract_prompt.format(rule=rule))

        # 清理提取的文本
        text = clean_text(text)

        # 如果提取的文本过长，进行拆分处理
        if len(text) > 10000:
            # 计算中间分割点
            mid_index = len(lines) // 2
            # 将行列表拆分为两部分
            lines_part1 = lines[:mid_index]
            lines_part2 = lines[mid_index:]

            # 递归调用函数分别处理两部分
            text1 = extract_module_raw_text(module_name, lines_part1, path)
            text2 = extract_module_raw_text(module_name, lines_part2, path)

            # 返回包含两个结果的数组
            return [text1, text2]

        return text
    except Exception as e:
        # 打印错误信息并重新抛出异常
        print(f"Error in extract_module_raw_text: {e}")
        raise


def analysis_conflict(module_name, content_list):
    """
    分析多个内容片段之间的一致性

    参数:
        module_name: 模块名称
        content_list: 待分析的内容片段列表

    返回:
        分析结果文本
    """
    # 构造规则字符串
    rule_str = module_name + ":" + cfg.rule_dict[module_name]

    # 获取推理链模板
    cot_str = cfg.cot_dict.get(module_name, '')
    # print(f"{module_name} cot_str:{cot_str}")

    # 构造输入文本，将所有内容片段按序号组织
    input_text = ''
    index = 1
    for content in content_list:
        input_text = input_text + f"文档片段{index}:\n{content}\n"
        index += 1

    # 根据模块类型选择不同的分析策略
    if module_name in ['出险条款', '附加条款', '术语解释', '退保条款', '保障相关时间']:
        # 使用推理链模板进行一致性分析
        text = LLM(input_text, cot_str)
    else:
        # 使用通用冲突检测提示模板进行分析
        text = LLM(input_text, cfg.conflict_prompt.format(rule=rule_str, cot=cot_str))

    return text
