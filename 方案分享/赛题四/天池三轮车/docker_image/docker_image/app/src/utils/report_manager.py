"""
简化的报告管理器
专门处理FinGenius的三种核心报告类型：
1. HTML报告 - 使用create_html生成的美观报告
2. 辩论对话JSON - 所有辩论发言记录
3. 投票结果JSON - 按票数统计的投票结果
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logger import logger


class SimpleReportManager:
    """简化的报告管理器"""
    
    def __init__(self, base_dir: str = "report"):
        self.base_dir = Path(base_dir)
        self.ensure_directories()
        
        # 报告类型配置
        self.report_types = {
            "html": {"extension": "html", "subdir": "html"},
            "debate": {"extension": "json", "subdir": "debate"},
            "vote": {"extension": "json", "subdir": "vote"}
        }
        
        # 保留期限（天）
        self.retention_days = 30
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建三个子目录
        for report_type in ["html", "debate", "vote"]:
            (self.base_dir / report_type).mkdir(parents=True, exist_ok=True)
    
    def generate_filename(self, report_type: str, stock_code: str, 
                         timestamp: str | None = None) -> str:
        """生成报告文件名"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        extension = self.report_types[report_type]["extension"]
        return f"{report_type}_{stock_code}_{timestamp}.{extension}"
    
    def get_report_path(self, report_type: str, filename: str) -> Path:
        """获取报告文件的完整路径"""
        subdir = self.report_types[report_type]["subdir"]
        return self.base_dir / subdir / filename
    
    def save_html_report(self, stock_code: str, html_content: str, 
                        metadata: Optional[Dict] = None) -> bool:
        """保存HTML报告"""
        return self._save_report("html", stock_code, html_content, metadata)
    
    def save_debate_report(self, stock_code: str, debate_data: Dict, 
                          metadata: Optional[Dict] = None) -> bool:
        """保存辩论对话JSON"""
        content = json.dumps(debate_data, ensure_ascii=False, indent=2)
        return self._save_report("debate", stock_code, content, metadata)
    
    def save_vote_report(self, stock_code: str, vote_data: Dict, 
                        metadata: Optional[Dict] = None) -> bool:
        """保存投票结果JSON"""
        content = json.dumps(vote_data, ensure_ascii=False, indent=2)
        return self._save_report("vote", stock_code, content, metadata)
    
    def _save_report(self, report_type: str, stock_code: str, content: str, 
                    metadata: Optional[Dict] = None) -> bool:
        """通用的报告保存方法"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.generate_filename(report_type, stock_code, timestamp)
            file_path = self.get_report_path(report_type, filename)
            
            # 保存报告内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 保存元数据
            if metadata:
                meta_filename = filename.replace(f".{self.report_types[report_type]['extension']}", ".meta.json")
                meta_path = self.get_report_path(report_type, meta_filename)
                
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        **metadata,
                        "report_type": report_type,
                        "stock_code": stock_code,
                        "created_at": datetime.now().isoformat(),
                        "file_size": len(content.encode('utf-8')),
                        "filename": filename
                    }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存{report_type}报告成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存{report_type}报告失败: {str(e)}")
            return False
    
    def load_report(self, report_type: str, filename: str) -> Optional[Dict]:
        """加载报告"""
        try:
            file_path = self.get_report_path(report_type, filename)
            if not file_path.exists():
                return None
            
            # 读取报告内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 读取元数据
            meta_filename = filename.replace(f".{self.report_types[report_type]['extension']}", ".meta.json")
            meta_path = self.get_report_path(report_type, meta_filename)
            
            metadata = {}
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            return {
                "filename": filename,
                "content": content,
                "metadata": metadata,
                "path": str(file_path),
                "type": report_type
            }
            
        except Exception as e:
            logger.error(f"加载{report_type}报告失败: {str(e)}")
            return None
    
    def list_reports(self, report_type: str | None = None, limit: int = 20) -> List[Dict]:
        """列出报告"""
        reports = []
        
        # 如果指定了类型，只列出该类型的报告
        types_to_check = [report_type] if report_type else self.report_types.keys()
        
        for rtype in types_to_check:
            try:
                subdir = self.report_types[rtype]["subdir"]
                type_path = self.base_dir / subdir
                
                if not type_path.exists():
                    continue
                
                extension = self.report_types[rtype]["extension"]
                for file_path in type_path.glob(f"*.{extension}"):
                    # 跳过元数据文件
                    if file_path.name.endswith('.meta.json'):
                        continue
                    
                    meta_filename = file_path.name.replace(f".{extension}", ".meta.json")
                    meta_path = type_path / meta_filename
                    
                    metadata = {}
                    if meta_path.exists():
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                        except:
                            pass
                    
                    reports.append({
                        "filename": file_path.name,
                        "type": rtype,
                        "stock_code": metadata.get("stock_code", ""),
                        "created_at": metadata.get("created_at", ""),
                        "file_size": metadata.get("file_size", file_path.stat().st_size),
                        "path": str(file_path)
                    })
                    
            except Exception as e:
                logger.error(f"列出{rtype}报告失败: {str(e)}")
                continue
        
        # 按创建时间排序
        reports.sort(key=lambda x: x["created_at"], reverse=True)
        return reports[:limit]
    
    def cleanup_old_reports(self) -> Dict[str, int]:
        """清理过期报告"""
        cleanup_stats = {"deleted_files": 0, "saved_space": 0}
        
        try:
            cutoff_time = datetime.now() - timedelta(days=self.retention_days)
            
            for report_type in self.report_types.keys():
                subdir = self.report_types[report_type]["subdir"]
                type_path = self.base_dir / subdir
                
                if not type_path.exists():
                    continue
                
                for file_path in type_path.glob("*"):
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_time < cutoff_time:
                            try:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                cleanup_stats["deleted_files"] += 1
                                cleanup_stats["saved_space"] += file_size
                            except Exception as e:
                                logger.warning(f"删除文件失败: {file_path}, {str(e)}")
            
            if cleanup_stats["deleted_files"] > 0:
                logger.info(f"清理完成: 删除 {cleanup_stats['deleted_files']} 个文件, "
                           f"节省 {cleanup_stats['saved_space']} 字节")
            
        except Exception as e:
            logger.error(f"清理过期报告失败: {str(e)}")
        
        return cleanup_stats
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        stats = {
            "total_files": 0,
            "total_size": 0,
            "by_type": {}
        }
        
        try:
            for report_type in self.report_types.keys():
                subdir = self.report_types[report_type]["subdir"]
                type_path = self.base_dir / subdir
                
                if not type_path.exists():
                    stats["by_type"][report_type] = {
                        "file_count": 0,
                        "total_size": 0
                    }
                    continue
                
                files = [f for f in type_path.glob("*") if f.is_file()]
                file_count = len(files)
                total_size = sum(f.stat().st_size for f in files)
                
                stats["by_type"][report_type] = {
                    "file_count": file_count,
                    "total_size": total_size,
                    "avg_size": total_size / file_count if file_count > 0 else 0
                }
                
                stats["total_files"] += file_count
                stats["total_size"] += total_size
            
            return stats
            
        except Exception as e:
            logger.error(f"获取存储统计失败: {str(e)}")
            return {"error": str(e)}
    
    def find_reports_by_stock(self, stock_code: str) -> List[Dict]:
        """查找特定股票的所有报告"""
        all_reports = self.list_reports(limit=100)
        return [r for r in all_reports if r["stock_code"] == stock_code]
    
    def get_latest_report(self, stock_code: str, report_type: str | None = None) -> Optional[Dict]:
        """获取最新的报告"""
        if report_type:
            reports = self.list_reports(report_type=report_type, limit=50)
        else:
            reports = self.list_reports(limit=50)
        
        stock_reports = [r for r in reports if r["stock_code"] == stock_code]
        return stock_reports[0] if stock_reports else None


# 全局报告管理器实例
report_manager = SimpleReportManager()


# 便捷函数
def save_html_report(stock_code: str, html_content: str, 
                    metadata: Optional[Dict] = None) -> bool:
    """保存HTML报告的便捷函数"""
    return report_manager.save_html_report(stock_code, html_content, metadata)


def save_debate_report(stock_code: str, debate_data: Dict, 
                      metadata: Optional[Dict] = None) -> bool:
    """保存辩论对话的便捷函数"""
    return report_manager.save_debate_report(stock_code, debate_data, metadata)


def save_vote_report(stock_code: str, vote_data: Dict, 
                    metadata: Optional[Dict] = None) -> bool:
    """保存投票结果的便捷函数"""
    return report_manager.save_vote_report(stock_code, vote_data, metadata)


def get_stock_reports(stock_code: str) -> List[Dict]:
    """获取特定股票的所有报告"""
    return report_manager.find_reports_by_stock(stock_code)


def cleanup_reports() -> Dict[str, int]:
    """清理过期报告"""
    return report_manager.cleanup_old_reports() 