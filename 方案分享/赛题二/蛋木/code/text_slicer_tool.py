import re
import json
import logging
from langchain.tools import BaseTool
from typing import Type, Dict, Any, List
from pydantic import BaseModel, Field


class SlicerInput(BaseModel):
    document_content: str = Field(description="需要进行切片的原始文档全文。")
    rule_validation: Dict[str, Any] = Field(description="包含规则ID、文本和相关性判断的字典。")
    slice_instructions: List[Dict[str, Any]] = Field(description="包含start_keyword和end_keyword的切片指令列表。")

class TextSlicerTool(BaseTool):
    
    name: str = "AdvancedTextSlicerTool"
    description: str = "根据开始和结束关键词，使用强大的模糊正则表达式，从文档中提取精确的文本片段，能有效处理换行符和多余空格。"
    args_schema: Type[BaseModel] = SlicerInput

    def _normalize_text_for_regex(self, text: str) -> str:
        if not text:
            return ""

        cleaned_text = re.sub(r'\s+', '', text)
        
        escaped_text = re.escape(cleaned_text)
        
        fuzzy_regex_parts = []
        i = 0
        while i < len(escaped_text):
            if escaped_text[i] == '\\':
                fuzzy_regex_parts.append(escaped_text[i:i+2])
                i += 2
            else:
                fuzzy_regex_parts.append(escaped_text[i])
                i += 1
        
        fuzzy_regex = r'\s*'.join(fuzzy_regex_parts)
        
        return fuzzy_regex

    def _run(self, tool_input: str) -> str:
        try:
            data = json.loads(tool_input)
            document_content = data.get("document_content", "")
            rule_validation = data.get("rule_validation", {})
            slice_instructions = data.get("slice_instructions", [])
            
            final_slices = []
            last_match_end = 0 # 用于支持从上一次匹配结束的位置继续搜索

            if not rule_validation.get("is_related") or not slice_instructions:
                return json.dumps({
                    "rule_validation": rule_validation,
                    "extracted_features": []
                }, ensure_ascii=False, indent=2)

            for i, instruction in enumerate(slice_instructions):
                location = instruction.get("location", {})
                start_keyword = location.get("start_keyword")
                end_keyword = location.get("end_keyword")

                if not start_keyword:
                    continue

                start_regex_part = self._normalize_text_for_regex(start_keyword)
                end_regex_part = self._normalize_text_for_regex(end_keyword)

                # 构建完整的搜索模式
                # re.DOTALL 让 '.' 可以匹配包括换行符在内的任意字符
                if end_regex_part:
                    # (.*?) 是非贪婪匹配，匹配从start到end之间的最短内容
                    pattern_str = f"({start_regex_part})(.*?)({end_regex_part})"
                else:
                    # 如果没有end_keyword，就只匹配start_keyword本身
                    pattern_str = f"({start_regex_part})"
                
                pattern = re.compile(pattern_str, re.DOTALL)

                # 从上一次匹配结束的位置开始搜索，避免重复匹配相同内容
                match = pattern.search(document_content, pos=last_match_end)

                if match:
                    # 提取完整的匹配内容，这包含了原始的换行和空格
                    extracted_text = match.group(0) 
                    final_slices.append({
                        "source_keywords": {
                            "start_keyword": start_keyword,
                            "end_keyword": end_keyword
                        },
                        "extracted_text": extracted_text.strip()
                    })
                    # 更新下一次搜索的起始位置
                    last_match_end = match.end()
                else:
                    logging.warning(f"指令 #{i+1}: 未能使用关键词定位内容。Start: '{start_keyword}', End: '{end_keyword}'")
                    # 如果一次匹配失败，重置搜索位置，以防后续指令能从头匹配
                    last_match_end = 0


            result = {
                "rule_validation": rule_validation,
                "extracted_features": final_slices
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)

        except json.JSONDecodeError:
            logging.error("工具接收到的输入不是有效的JSON字符串。")
            return json.dumps({"error": "Invalid JSON input"}, ensure_ascii=False)
        except Exception as e:
            logging.error(f"TextSlicerTool 在执行时发生未知错误: {e}", exc_info=True)
            return json.dumps({"error": str(e)}, ensure_ascii=False)