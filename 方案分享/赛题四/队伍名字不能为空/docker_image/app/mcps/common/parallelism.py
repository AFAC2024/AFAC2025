"""
并行计算工具

1.0 @nambo 2025-07-20
"""
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import os
import sys
import asyncio
from typing import Callable, List, Tuple, Any, Awaitable
import traceback

current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

class ConcurrentExecutor:
    """
    同步方法的并行执行
    """
    def __init__(self, max_concurrent=5):
        self.max_concurrent = max_concurrent
        self.result_queue = []  # 存储所有结果的列表
        self.lock = threading.Lock()
    
    def execute(self, task_list):
        """执行并发任务
        
        :param task_list: 任务列表，每个元素是元组(func, args, kwargs)
                          func: 要执行的函数
                          args: 位置参数元组
                          kwargs: 关键字参数字典
        :return: 合并后的结果列表
        """
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = []
            for task in task_list:
                func = task[0]
                args = task[1] if len(task) > 1 else ()
                kwargs = task[2] if len(task) > 2 else {}
                futures.append(executor.submit(self._worker, func, args, kwargs))
            
            # 等待所有任务完成
            for future in futures:
                future.result()
        
        # 合并结果
        return [item for sublist in self.result_queue for item in sublist]
    
    def _worker(self, func, args, kwargs):
        """工作线程函数"""
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 确保结果是列表
            if not isinstance(result, list):
                result = [result]
                
        except Exception as e:
            print(f"Error executing {func.__name__}: {e}")
            # print(traceback.format_exc())
            raise e
            result = []
        
        # 线程安全地将结果添加到共享队列
        with self.lock:
            self.result_queue.append(result)
        
        return result
    
class AsyncConcurrentExecutor:
    """
    异步方法的并行执行
    """
    def __init__(self, max_concurrent=5):
        """
        异步并发执行器
        
        :param max_concurrent: 最大并发任务数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute(self, task_list: List[Tuple[Callable, tuple, dict]]) -> List[Any]:
        """
        并发执行异步任务并合并结果
        
        :param task_list: 任务列表，每个元素为元组(func, args, kwargs)
                          func: 异步函数，返回Awaitable[list]
                          args: 位置参数元组
                          kwargs: 关键字参数字典
        :return: 所有任务结果的合并列表
        """
        # 创建包装任务
        wrapped_tasks = [self._worker(func, args, kwargs) for func, args, kwargs in task_list]
        
        # 并发执行所有任务并等待完成
        results = await asyncio.gather(*wrapped_tasks)
        
        # 合并结果
        return [item for sublist in results for item in sublist]
    
    async def _worker(self, func: Callable[..., Awaitable[List[Any]]], args: tuple, kwargs: dict) -> List[Any]:
        """异步工作函数，执行单个任务并处理异常"""
        async with self.semaphore:
            try:
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                
                if not isinstance(result, list):
                    print(f"警告: {func.__name__}返回了非列表类型: {type(result)}，已自动封装")
                    result = [result]
                
                print(f"任务 {func.__name__} 完成, 耗时 {elapsed:.2f}秒, 返回 {len(result)} 个结果")
                return result
            except asyncio.CancelledError:
                print(f"任务 {func.__name__} 被取消")
                return []
            except Exception as e:
                print(f"任务 {func.__name__} 执行失败: {e}")
                # print(traceback.format_exc())
                raise e
                # 添加详细错误信息到结果中，便于调试
                return [f"ERROR: {func.__name__} failed with {str(e)}"]