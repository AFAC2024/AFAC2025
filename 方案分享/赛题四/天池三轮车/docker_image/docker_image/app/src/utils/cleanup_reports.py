#!/usr/bin/env python3
"""
优化的报告清理脚本
适用于新的SimpleReportManager系统
支持三种报告类型：HTML、辩论对话、投票结果
"""

import argparse
import os
import sys
import time
from datetime import datetime

# 添加项目路径到 Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import schedule
except ImportError:
    schedule = None

from src.logger import logger
from src.utils.report_manager import report_manager


def cleanup_reports():
    """清理过期报告"""
    try:
        logger.info("开始清理过期报告...")
        
        # 获取清理前的存储统计
        before_stats = report_manager.get_storage_stats()
        logger.info(f"清理前统计: 总文件数 {before_stats['total_files']}, 总大小 {before_stats['total_size']} 字节")
        
        # 按类型显示统计
        for report_type, stats in before_stats.get("by_type", {}).items():
            logger.info(f"  {report_type}: {stats['file_count']} 个文件, {stats['total_size']} 字节")
        
        # 执行清理
        cleanup_result = report_manager.cleanup_old_reports()
        
        # 显示清理结果
        deleted_files = cleanup_result.get("deleted_files", 0)
        saved_space = cleanup_result.get("saved_space", 0)
        
        if deleted_files > 0:
            logger.info(f"清理完成: 删除 {deleted_files} 个文件, 节省 {saved_space} 字节")
        else:
            logger.info("没有找到需要清理的过期文件")
        
        # 获取清理后的存储统计
        after_stats = report_manager.get_storage_stats()
        logger.info(f"清理后统计: 总文件数 {after_stats['total_files']}, 总大小 {after_stats['total_size']} 字节")
        
    except Exception as e:
        logger.error(f"清理过期报告失败: {str(e)}")


def show_storage_stats():
    """显示存储统计信息"""
    try:
        stats = report_manager.get_storage_stats()
        
        if "error" in stats:
            logger.error(f"获取存储统计失败: {stats['error']}")
            return
        
        print("\n=== 报告存储统计 ===")
        print(f"总文件数: {stats['total_files']}")
        print(f"总大小: {format_bytes(stats['total_size'])}")
        print(f"平均文件大小: {format_bytes(stats['total_size'] / stats['total_files'] if stats['total_files'] > 0 else 0)}")
        
        print("\n按类型统计:")
        for report_type, type_stats in stats.get("by_type", {}).items():
            print(f"  {report_type}:")
            print(f"    文件数: {type_stats['file_count']}")
            print(f"    总大小: {format_bytes(type_stats['total_size'])}")
            print(f"    平均大小: {format_bytes(type_stats['avg_size'])}")
        
    except Exception as e:
        logger.error(f"显示存储统计失败: {str(e)}")


def list_recent_reports(report_type=None, limit=10):
    """列出最近的报告"""
    try:
        reports = report_manager.list_reports(report_type=report_type, limit=limit)
        
        if not reports:
            print("没有找到报告文件")
            return
        
        print(f"\n=== 最近的报告 ({len(reports)} 个) ===")
        for report in reports:
            print(f"文件: {report['filename']}")
            print(f"  类型: {report['type']}")
            print(f"  股票代码: {report['stock_code']}")
            print(f"  创建时间: {report['created_at']}")
            print(f"  文件大小: {format_bytes(report['file_size'])}")
            print(f"  路径: {report['path']}")
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"列出报告失败: {str(e)}")


def find_stock_reports(stock_code):
    """查找特定股票的报告"""
    try:
        reports = report_manager.find_reports_by_stock(stock_code)
        
        if not reports:
            print(f"没有找到股票 {stock_code} 的报告")
            return
        
        print(f"\n=== 股票 {stock_code} 的报告 ({len(reports)} 个) ===")
        for report in reports:
            print(f"文件: {report['filename']}")
            print(f"  类型: {report['type']}")
            print(f"  创建时间: {report['created_at']}")
            print(f"  文件大小: {format_bytes(report['file_size'])}")
            print("-" * 50)
        
    except Exception as e:
        logger.error(f"查找股票报告失败: {str(e)}")


def format_bytes(bytes_count):
    """格式化字节数为可读格式"""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.1f} GB"


def schedule_cleanup():
    """安排定期清理"""
    print("注意：schedule库未安装，无法使用定期清理功能")
    print("请手动运行清理命令：python src/utils/cleanup_reports.py --cleanup")


def run_cleanup_daemon():
    """运行清理守护进程"""
    if schedule is None:
        print("错误：schedule库未安装，无法运行守护进程")
        print("请安装：pip install schedule")
        print("或手动定期运行：python src/utils/cleanup_reports.py --cleanup")
        return
    
    schedule_cleanup()
    logger.info("清理守护进程已启动，按 Ctrl+C 停止")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("清理守护进程已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="报告清理和管理工具")
    parser.add_argument("--cleanup", action="store_true", help="立即执行一次清理")
    parser.add_argument("--daemon", action="store_true", help="以守护进程模式运行")
    parser.add_argument("--stats", action="store_true", help="显示存储统计")
    parser.add_argument("--list", action="store_true", help="列出最近的报告")
    parser.add_argument("--type", choices=["html", "debate", "vote"], help="指定报告类型")
    parser.add_argument("--limit", type=int, default=10, help="限制报告列表数量")
    parser.add_argument("--stock", help="查找特定股票的报告")
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_reports()
    elif args.daemon:
        run_cleanup_daemon()
    elif args.stats:
        show_storage_stats()
    elif args.list:
        list_recent_reports(report_type=args.type, limit=args.limit)
    elif args.stock:
        find_stock_reports(args.stock)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 