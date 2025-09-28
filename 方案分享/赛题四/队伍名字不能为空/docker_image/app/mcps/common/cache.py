"""
缓存工具

1.0 @nambo 2025-07-20
"""
import hashlib
import os
from pathlib import Path
import time

current_dir = os.path.dirname(os.path.abspath(__file__) ) 
cache_dir = os.path.join(current_dir, '_cache')

# 检查目录是否存在，如果不存在则创建
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

# 计算key值的md5
def get_md5(input_string):
	# 创建一个md5 hash对象
	md5_hash = hashlib.md5()
	
	# 向hash对象提供要哈希的数据。
	# 需要先将字符串编码为字节串，因为md5()函数需要字节串作为输入。
	md5_hash.update(input_string.encode())
	
	# 获取十六进制格式的哈希值
	digest = md5_hash.hexdigest()
	
	return digest

# 保存缓存
def setCache(key_str, data_str, prefix=''):
	if data_str == None or len(data_str) <= 0 or key_str == None or len(key_str) <= 0:
		print("缓存失败：key_str获data_str为空")
		return
	md5 = get_md5(key_str)

	if prefix is not None and len(prefix) > 0:
		md5 = prefix + '_' + md5
		
	old_cache_path = os.path.join(cache_dir, md5)
	print("开始缓存数据，", old_cache_path)
	
	if os.path.exists(old_cache_path):
		os.remove(old_cache_path)
	
	with open(old_cache_path, 'w') as file:
		file.write(data_str)

# 加载缓存
def getCache(key_str, prefix=''):
	md5 = get_md5(key_str)
	if prefix is not None and len(prefix) > 0:
		md5 = prefix + '_' + md5
	old_cache_path = os.path.join(cache_dir, md5)
	if os.path.exists(old_cache_path):
		with open(old_cache_path, 'r') as file:  
			print("获取到缓存数据，", old_cache_path)
			content = file.read()
			return content
	else:
		return None

# 删除缓存
def removeCache(key_str):
	md5 = get_md5(key_str)
	old_cache_path = os.path.join(cache_dir, md5)
	if os.path.exists(old_cache_path):
		os.remove(old_cache_path)
		
	return True

def clear_cache_with_time(clean_time):
	global cache_dir
	target_time = time.mktime(time.strptime(clean_time, "%Y-%m-%d %H:%M:%S"))
	cache_path = cache_dir = Path(cache_dir)
	for file in cache_path.rglob("*"):
			if file.is_file():
					file_time = file.stat().st_mtime  # 或者 st_ctime
					if file_time > target_time:
							file.unlink()
							print(f"已删除: {file}")

if __name__ == '__main__':
	clear_cache_with_time('2025-07-24 03:00:00')