import os
import re
import json
import logging
from typing import Dict, List, Optional

MATERIAL_TYPE_MAP = {
    "CLAUSE": "条款", "INSURE_NOTICE": "投保须知", "HEALTH_INFORM": "健康告知",
    "HEAD_IMG": "头图", "INTRODUCE_IMG": "图文说明", "H5": "H5资料",
    "INSURANCE_POLICY": "电子保单", "PRODUCT_MANUAL": "产品说明书",
    "ADDITIONAL_AGREEMENT": "特别约定", "LIABILITY_EXCLUSION": "免责说明"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RuleExtractorTool:
    def _parse_rule_core_concept(self, rule_text: str) -> str:
        patterns = [
            r"^(?:该产品的|产品的)?(.*?)(?:在各材料中的定义没有冲突)"
        ]

        for pattern in patterns:
            match = re.search(pattern, rule_text)
            if match:
                core_concept = match.group(1).strip()
                logging.info(f"成功解析规则核心概念: '{rule_text}' -> '{core_concept}'")
                return core_concept
        
        logging.warning(f"无法从规则 '{rule_text}' 中解析出核心概念，将使用原始文本。")
        return rule_text
    
    def get_rule_text_by_id(self, rule_id: str, rules_file_path: str) -> Optional[str]:
        """
        根据指定的 rule_id 从 .jsonl 文件中查找规则，
        然后解析其核心概念，并返回精简后的文本。
        """
        logging.info(f"正在根据 rule_id '{rule_id}' 从文件 '{rules_file_path}' 中查找并解析规则...")
        if not os.path.exists(rules_file_path):
            logging.error(f"规则文件未找到: {rules_file_path}")
            return None
        
        with open(rules_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rule_data = json.loads(line)
                    if rule_data.get("rule_id") == rule_id:
                        # 1. 找到匹配的规则，获取原始文本
                        original_rule_text = rule_data.get("rule")
                        if not original_rule_text:
                            logging.warning(f"找到 rule_id '{rule_id}'，但其规则文本为空。")
                            return None
                        
                        logging.info(f"成功找到 rule_id '{rule_id}' 对应的原始规则文本。")
                        
                        # 2. 调用 _parse_rule_core_concept 方法进行精简
                        parsed_core_concept = self._parse_rule_core_concept(original_rule_text)
                        
                        # 3. 返回精简后的文本
                        return parsed_core_concept
                        
                except json.JSONDecodeError:
                    logging.warning(f"无法解析规则文件中的行: {line}")
                    continue
        
        logging.warning(f"未在文件 '{rules_file_path}' 中找到 rule_id '{rule_id}' 的任何匹配规则。")
        return None

    def _find_rules_for_material(self, material_id: str, rules_file_path: str) -> List[Dict]:
        """
        根据 material_id 从 .jsonl 文件中查找【所有】对应的规则。
        现在返回一个包含所有匹配规则的列表，而不是单个字典。
        """
        matching_rules = [] # 初始化一个空列表来存储所有匹配的规则
        if not os.path.exists(rules_file_path):
            logging.warning(f"规则文件未找到: {rules_file_path}")
            return matching_rules
            
        with open(rules_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rule = json.loads(line)
                    # 如果 material_id 匹配，则将规则添加到列表中，而不是立即返回
                    if rule.get("material_id") == material_id:
                        logging.info(f"为 material_id '{material_id}' 找到匹配规则: {rule.get('rule_id')}")
                        matching_rules.append(rule)
                except json.JSONDecodeError:
                    logging.warning(f"无法解析规则文件中的行: {line}")
                    continue
        
        if not matching_rules:
            logging.info(f"未找到 material_id '{material_id}' 的任何匹配规则。")
            
        return matching_rules # 返回包含所有找到的规则的列表

    def _run(self, tool_input: str) -> str:
        """
        Agent调用的主方法。
        处理一个 material_id 对应的所有规则，并将它们打包成列表返回。
        """
        logging.info(f"工具接收到输入: {tool_input}")
        
        try:
            paths = json.loads(tool_input)
            batch_file_path = paths["batch_file_path"]
            rules_file_path = paths["rules_file_path"]
        except (json.JSONDecodeError, KeyError):
            error_msg = "错误: 工具输入必须是一个包含 'batch_file_path' 和 'rules_file_path' 键的JSON字符串。"
            logging.error(error_msg)
            return error_msg

        try:
            with open(batch_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except FileNotFoundError:
            error_msg = f"错误: 文件未找到 {batch_file_path}"
            logging.error(error_msg)
            return error_msg
        
        material_type_code = "未知"
        material_type_name = "未知"
        material_type_keys = "|".join(MATERIAL_TYPE_MAP.keys())
        match = re.search(r"## 文档:.*?/(" + material_type_keys + r")/.*", file_content, re.IGNORECASE)
        if match:
            material_type_code = match.group(1).upper()
            material_type_name = MATERIAL_TYPE_MAP.get(material_type_code, "未知")

        material_id_match = re.search(r'/(m_\d+[a-z]?)/', batch_file_path)
        material_id = material_id_match.group(1) if material_id_match else None
        
        all_rules_analysis = [] # 初始化一个空列表来存储所有规则的分析结果
        if material_id:
            # 获取规则列表
            list_of_raw_rules = self._find_rules_for_material(material_id, rules_file_path)
            
            for raw_rule_data in list_of_raw_rules:
                original_rule_text = raw_rule_data.get("rule", "")
                parsed_core_concept = self._parse_rule_core_concept(original_rule_text)
                
                rule_analysis_result = {
                    "rule_id": raw_rule_data.get("rule_id"),
                    "rule_original_text": original_rule_text, # 保留原始规则文本
                    "rule": parsed_core_concept # 使用解析后的核心概念
                }
                all_rules_analysis.append(rule_analysis_result)
        else:
            logging.warning(f"无法从路径 {batch_file_path} 中提取 material_id。")

        # 使用新键 "all_matching_rules" 来存储规则列表
        output_data = {
            "document_content": file_content,
            "material_type_code": material_type_code,
            "material_type_name": material_type_name,
            "all_matching_rules": all_rules_analysis # 返回一个列表，而不是单个对象
        }
        
        return json.dumps(output_data, ensure_ascii=False)
    
class FewshotExtractorTool:
    """
    一个用于从Markdown格式的few-shot文件中提取指定规则示例的工具。
    它在初始化时解析文件，并将规则块缓存到字典中，以便快速检索。
    """
    def __init__(self, fewshot_file_path: str):
        """
        初始化工具，并预加载和解析few-shot文件。

        Args:
            fewshot_file_path (str): few-shot .md文件的路径。
        """
        self.file_path = fewshot_file_path
        self._blocks = {}
        self._load_and_parse_file()

    def _load_and_parse_file(self):
        """
        读取文件内容，并将其解析为以核心概念为键的字典。
        """
        logging.info(f"正在从 '{self.file_path}' 加载并解析 few-shot 示例...")
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            logging.error(f"Few-shot 文件未找到: {self.file_path}")
            return

        # 使用正向先行断言 `(?=...)` 来分割文件，这样分隔符（#### 标题）会保留在每个块的开头
        # `\n`确保我们只在行首匹配标题
        blocks = re.split(r'\n(?=#### 规则\d+:\s*)', content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
            
            # 从每个块的第一行提取核心概念
            first_line = block.split('\n', 1)[0]
            match = re.search(r'#### 规则\d+:\s*(.*)', first_line)
            
            if match:
                core_concept = match.group(1).strip()
                # 将核心概念与整个块的文本（包含标题）关联起来
                self._blocks[core_concept] = block.strip()
                logging.info(f"缓存了核心概念 '{core_concept}' 的 few-shot 示例。")
            else:
                 logging.warning(f"无法从块中解析核心概念: {first_line}")

    def run(self, core_concept: str) -> str:
        """
        Agent调用的主方法。根据核心概念查找并返回对应的few-shot示例块。

        Args:
            core_concept (str): 需要查找的核心概念，例如 "保障相关时间"。

        Returns:
            str: 匹配到的完整few-shot示例块文本，如果未找到则返回错误信息。
        """
        logging.info(f"工具接收到输入，正在查找核心概念: '{core_concept}'")
        
        if not core_concept or not isinstance(core_concept, str):
            error_msg = "错误: 输入的核心概念必须是一个非空字符串。"
            logging.error(error_msg)
            return error_msg
            
        # 从预处理的字典中直接获取内容，非常高效
        result = self._blocks.get(core_concept)
        
        if result:
            logging.info(f"成功为 '{core_concept}' 找到匹配的 few-shot 示例。")
            return result
        else:
            error_msg = f"错误: 未在文件 '{self.file_path}' 中找到核心概念为 '{core_concept}' 的规则示例。"
            logging.warning(error_msg)
            return error_msg

