import re
import os
import json
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RuleDefinitionFinderTool:
    """
    一个为Agent设计的工具，负责根据规则的核心概念，
    从一个指定的Markdown知识库文件中查找并返回该规则的详细释义。
    """
    def __init__(self, knowledge_base_path: str):
        if not os.path.exists(knowledge_base_path):
            raise FileNotFoundError(f"规则知识库文件未找到: {knowledge_base_path}")
        self.knowledge_base_path = knowledge_base_path
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """将整个知识库文件加载到内存中。"""
        logging.info(f"正在从 {self.knowledge_base_path} 加载规则知识库...")
        with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
            self.knowledge_content = f.read()
        logging.info("规则知识库加载完成。")

    def _run(self, tool_input: str) -> str:
        """
        Agent调用的主方法。

        Args:
            tool_input: 一个JSON格式的字符串，必须包含 'core_concept' 键。
                        例如: '{"core_concept": "基础产品销售信息"}'

        Returns:
            一个字符串，包含找到的规则详细释义，如果未找到则返回提示信息。
        """
        try:
            input_data = json.loads(tool_input)
            core_concept = input_data["core_concept"]
        except (json.JSONDecodeError, KeyError):
            error_msg = "错误: 工具输入必须是一个包含 'core_concept' 键的JSON字符串。"
            logging.error(error_msg)
            return error_msg
        
        logging.info(f"正在为核心概念 '{core_concept}' 查找详细释义...")

        # 使用正则表达式查找对应的规则段落
        # 模式解释:
        # - `####\s+规则\d+:\s*` : 匹配标题行，如 "#### 规则1: "
        # - `re.escape(core_concept)`: 安全地匹配核心概念，避免特殊字符问题
        # - `\s*\n`: 匹配标题行末尾的换行符
        # - `(.*?)`: 非贪婪地捕获所有内容...
        # - `(?=\n####|\Z)`: ...直到下一个 "####" 标题或文件末尾（这是一个正向先行断言，不消耗匹配内容）
        pattern = re.compile(
            r"####\s+规则\d+:\s*" + re.escape(core_concept) + r"\s*\n(.*?)(?=\n####|\Z)",
            re.DOTALL  # 让 . 匹配换行符
        )
        
        match = pattern.search(self.knowledge_content)
        
        if match:
            definition = match.group(1).strip()
            logging.info(f"成功找到 '{core_concept}' 的详细释义。")
            return definition
        else:
            not_found_msg = f"未在知识库中找到关于“{core_concept}”的详细释义。"
            logging.warning(not_found_msg)
            return not_found_msg