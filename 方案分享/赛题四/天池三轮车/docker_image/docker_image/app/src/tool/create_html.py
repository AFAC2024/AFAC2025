"""
HTML generation tool - Uses LLM to generate complete web pages
based on user requirements including styling and JavaScript interactions.
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from src.logger import logger
from src.prompt.create_html import CREATE_HTML_TEMPLATE_PROMPT, CREATE_HTML_TOOL_PROMPT


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.llm import LLM
from src.tool.base import BaseTool, ToolResult
from src.utils.report_manager import report_manager

"""
数据缓存与实时更新策略
"""
import json
import time
import os
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

class DataCacheManager:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
        
        # 缓存配置
        self.cache_config = {
            "chip_analysis": {"ttl": 300, "max_age": 900},      # 5分钟TTL，15分钟最大age
            "stock_info": {"ttl": 60, "max_age": 180},           # 1分钟TTL，3分钟最大age
            "sentiment_data": {"ttl": 600, "max_age": 1800},     # 10分钟TTL，30分钟最大age
            "technical_analysis": {"ttl": 180, "max_age": 600},  # 3分钟TTL，10分钟最大age
            "risk_control": {"ttl": 120, "max_age": 360},        # 2分钟TTL，6分钟最大age
        }
    
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def get_cache_key(self, data_type: str, stock_code: str, **kwargs) -> str:
        """生成缓存键"""
        params = "_".join([f"{k}={v}" for k, v in sorted(kwargs.items())])
        return f"{data_type}_{stock_code}_{params}" if params else f"{data_type}_{stock_code}"
    
    def get_cache_file(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def get_cached_data(self, data_type: str, stock_code: str, **kwargs) -> Optional[Dict]:
        """获取缓存数据"""
        try:
            cache_key = self.get_cache_key(data_type, stock_code, **kwargs)
            cache_file = self.get_cache_file(cache_key)
            
            if not os.path.exists(cache_file):
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # 检查缓存是否过期
            cache_time = cached_data.get('cache_time', 0)
            current_time = time.time()
            
            config = self.cache_config.get(data_type, {"ttl": 300, "max_age": 900})
            
            # 硬过期检查
            if current_time - cache_time > config['max_age']:
                self.remove_cache(cache_key)
                return None
            
            # 软过期检查 - 返回但标记为过期
            if current_time - cache_time > config['ttl']:
                cached_data['is_stale'] = True
            else:
                cached_data['is_stale'] = False
            
            return cached_data
            
        except Exception as e:
            print(f"获取缓存数据失败: {str(e)}")
            return None
    
    def set_cached_data(self, data_type: str, stock_code: str, data: Any, **kwargs):
        """设置缓存数据"""
        try:
            cache_key = self.get_cache_key(data_type, stock_code, **kwargs)
            cache_file = self.get_cache_file(cache_key)
            
            cache_data = {
                "cache_time": time.time(),
                "data_type": data_type,
                "stock_code": stock_code,
                "data": data,
                "metadata": kwargs
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"设置缓存数据失败: {str(e)}")
    
    def remove_cache(self, cache_key: str):
        """删除缓存"""
        try:
            cache_file = self.get_cache_file(cache_key)
            if os.path.exists(cache_file):
                os.remove(cache_file)
        except Exception as e:
            print(f"删除缓存失败: {str(e)}")
    
    def cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            current_time = time.time()
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            cached_data = json.load(f)
                        
                        cache_time = cached_data.get('cache_time', 0)
                        data_type = cached_data.get('data_type', 'unknown')
                        
                        config = self.cache_config.get(data_type, {"ttl": 300, "max_age": 900})
                        
                        if current_time - cache_time > config['max_age']:
                            os.remove(file_path)
                            
                    except Exception:
                        # 如果文件损坏，删除它
                        os.remove(file_path)
                        
        except Exception as e:
            print(f"清理过期缓存失败: {str(e)}")

# 全局缓存管理器实例
cache_manager = DataCacheManager()

def with_cache(data_type: str):
    """缓存装饰器"""
    def decorator(func):
        async def wrapper(self, stock_code: str, **kwargs):
            # 尝试从缓存获取数据
            cached_data = cache_manager.get_cached_data(data_type, stock_code, **kwargs)
            
            if cached_data and not cached_data.get('is_stale', False):
                print(f"使用缓存数据: {data_type}_{stock_code}")
                return cached_data['data']
            
            # 执行原始函数
            try:
                result = await func(self, stock_code, **kwargs)
                
                # 缓存结果
                if result:
                    cache_manager.set_cached_data(data_type, stock_code, result, **kwargs)
                
                return result
                
            except Exception as e:
                # 如果有过期但可用的缓存，返回缓存数据
                if cached_data and cached_data.get('is_stale', False):
                    print(f"使用过期缓存数据作为fallback: {data_type}_{stock_code}")
                    return cached_data['data']
                
                raise e
        
        return wrapper
    return decorator


class CreateHtmlTool(BaseTool):
    """HTML generation tool that creates beautiful and functional HTML pages
    with complex layouts, styling, and interactive features based on user requirements.
    """

    name: str = "create_html"
    description: str = (
        "创建美观、功能齐全的HTML页面，支持复杂的布局设计、样式和交互效果。可以根据需求生成各种类型的网页，如数据展示、报表、产品页等。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "request": {
                "type": "string",
                "description": "详细描述需要生成的HTML页面需求",
            },
            "data": {
                "type": "object",
                "description": "需要在页面中展示的数据，JSON格式",
                "default": None,
            },
            "output_path": {
                "type": "string",
                "description": "输出HTML文件的路径 /to/path/file.html",
                "default": "",
            },
            "reference": {
                "type": "string",
                "description": "参考设计或布局说明",
                "default": "",
            },
            "additional_requirements": {
                "type": "string",
                "description": "其他额外要求",
                "default": "",
            },
        },
        "required": ["request", "output_path"],
    }

    # LLM instance for generating HTML
    llm: LLM = Field(default_factory=LLM)

    async def _generate_html(
        self, request: str, additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a complete HTML page based on user request"""
        logger.info(f"Starting HTML page generation: {request[:100]}...")

        # Build the complete prompt
        prompt = f"""请根据以下需求和HTML模板生成一个完整的HTML页面：

# 需求
{request}

# HTML模板
{CREATE_HTML_TEMPLATE_PROMPT}

# 重要要求
请确保在HTML页面的footer区域包含AI生成报告的免责声明，说明本报告由人工智能系统自动生成，仅供参考，不构成投资建议。
"""
        # Add additional context if provided
        if additional_context:
            if data := additional_context.get("data"):
                prompt += f"\n\nData to display:\n{json.dumps(data, ensure_ascii=False, indent=2)}"

            if reference := additional_context.get("reference"):
                prompt += f"\n\nReference design or layout:\n{reference}"

            if requirements := additional_context.get("requirements"):
                prompt += f"\n\nAdditional requirements:\n{requirements}"

        # Generate HTML using LLM
        messages = [
            {"role": "system", "content": CREATE_HTML_TOOL_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm.ask(messages=messages)
            html_code = self._extract_html_code(response)
            logger.info(
                f"HTML generation completed, length: {len(html_code)} characters"
            )
            return html_code
        except Exception as e:
            logger.error(f"Error generating HTML: {e}")
            raise

    def _extract_html_code(self, response: str) -> str:
        """Extract HTML code from LLM response"""
        # Check for code block
        if "```html" in response and "```" in response.split("```html", 1)[1]:
            code_block = response.split("```html", 1)[1].split("```", 1)[0]
            return self._fix_encoding(code_block.strip())
        
        # Check for direct HTML response
        elif "<!DOCTYPE" in response or "<html" in response:
            start_pos = response.find("<!DOCTYPE")
            if start_pos == -1:
                start_pos = response.find("<html")

            if start_pos != -1:
                return self._fix_encoding(response[start_pos:].strip())

        # Return full response if no clear HTML markers found
        return self._fix_encoding(response)
    
    def _inject_data_into_html(self, html_content: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Inject actual data into the HTML template"""
        if not data:
            return html_content
        
        try:
            # 确保数据格式正确
            safe_data = json.dumps(data, ensure_ascii=False, indent=2)
            
            # 查找数据注入点并替换
            if "window.pageData = {};" in html_content:
                html_content = html_content.replace(
                    "window.pageData = {};",
                    f"window.pageData = {safe_data};"
                )
                logger.info("Successfully injected data into HTML")
            else:
                logger.warning("Data injection point not found in HTML")
                
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to inject data into HTML: {e}")
            return html_content

    def _fix_encoding(self, html_content: str) -> str:
        """Fix potential encoding issues in HTML content"""
        try:
            # Ensure <meta charset> tag exists and is UTF-8
            if "<meta charset=" in html_content.lower():
                html_content = re.sub(
                    r'<meta\s+charset=["\']?[^"\'>\s]+["\']?',
                    '<meta charset="UTF-8">',
                    html_content,
                    flags=re.IGNORECASE,
                )
            else:
                # Add charset tag after <head> if it doesn't exist
                html_content = re.sub(
                    r"(<head[^>]*>)",
                    r'\1\n    <meta charset="UTF-8">',
                    html_content,
                    flags=re.IGNORECASE,
                )

            return html_content
        except Exception as e:
            logger.error(f"Error fixing HTML encoding: {e}")
            return html_content

    def _is_report_path(self, filepath: str) -> bool:
        """检查是否为报告路径"""
        return filepath.startswith("report/") or "report" in filepath
    
    def _save_with_report_manager(self, html_content: str, filepath: str, data: Optional[Dict] = None) -> str:
        """使用报告管理器保存HTML"""
        try:
            # 从数据中提取股票代码
            stock_code = "unknown"
            if data and isinstance(data, dict):
                stock_code = data.get("stock_code", "unknown")
            
            # 准备元数据
            metadata = {
                "original_path": filepath,
                "content_type": "html",
                "data_size": len(html_content.encode('utf-8')),
                "has_data": bool(data),
                "generated_by": "create_html_tool"
            }
            
            if data:
                metadata["data_keys"] = list(data.keys()) if isinstance(data, dict) else []
            
            # 使用新的HTML报告保存方法
            success = report_manager.save_html_report(
                stock_code=stock_code,
                html_content=html_content,
                metadata=metadata
            )
            
            if success:
                # 生成预期的文件路径
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"html_{stock_code}_{timestamp}.html"
                saved_path = report_manager.get_report_path("html", filename)
                logger.info(f"HTML report saved to: {saved_path}")
                return f"HTML report saved to: {saved_path}"
            else:
                return "Failed to save HTML report"
                
        except Exception as e:
            error_msg = f"Failed to save HTML report: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _save_html_to_file(self, html_content: str, filepath: str) -> str:
        """Save generated HTML to a file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

            # Save with UTF-8 encoding
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            return f"HTML successfully saved to: {filepath}"
        except Exception as e:
            logger.error(f"Error saving HTML file: {e}")
            return f"Failed to save HTML file: {e}"

    async def execute(
        self,
        request: str,
        data: Optional[Dict[str, Any]] = None,
        output_path: str = "",
        reference: str = "",
        additional_requirements: str = "",
        **kwargs,
    ) -> ToolResult:
        """Execute HTML generation operation

        Args:
            request: Detailed description of the HTML page requirements
            data: Optional data to display in the page
            output_path: Optional path to save the HTML file
            reference: Optional reference design or layout
            additional_requirements: Optional additional requirements

        Returns:
            ToolResult: Result containing the generated HTML or error message
        """
        try:
            # Prepare additional context
            additional_context = {}
            if data:
                additional_context["data"] = data
            if reference:
                additional_context["reference"] = reference
            if additional_requirements:
                additional_context["requirements"] = additional_requirements

            # Generate HTML
            html_content = await self._generate_html(
                request=request,
                additional_context=additional_context if additional_context else None,
            )
            
            # Inject data into HTML if available
            if data:
                html_content = self._inject_data_into_html(html_content, data)

            # Save to file if path provided
            result_message = ""
            if output_path:
                # 优先使用报告管理器保存
                if self._is_report_path(output_path):
                    save_result = self._save_with_report_manager(
                        html_content, output_path, data
                    )
                else:
                    save_result = await self._save_html_to_file(
                        html_content=html_content, filepath=output_path
                    )
                result_message = f"\n{save_result}"

            # Return success result
            return ToolResult(
                output={
                    "html_content": html_content,
                    "saved_to": output_path if output_path else None,
                    "message": f"HTML generation successful, length: {len(html_content)} characters{result_message}",
                }
            )

        except Exception as e:
            error_msg = f"HTML generation failed: {str(e)}"
            logger.error(error_msg)
            return ToolResult(error=error_msg)
