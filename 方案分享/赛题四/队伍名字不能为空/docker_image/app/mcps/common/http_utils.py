"""
网络请求工具

1.0 @nambo 2025-07-20
"""
import requests
import os
import sys
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
current_file_path = os.path.abspath(__file__)  
current_dir = os.path.dirname(current_file_path)  
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
default_save_path = os.path.join(current_dir, '_cache')

from common.cache import setCache, getCache, removeCache

def get_header(url, headers={}, cookies=None, cache_key=''):
  if cache_key == None or cache_key == '':
    cache_key = url
  cache_key = cache_key + '_header'
  cache = getCache(cache_key)
  if cache != None:
    print("从缓存中获取到结果")
    return json.loads(cache)
  
  if 'User-Agent' not in headers:
     headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

  response = requests.get(url, headers=headers)

  if response.status_code == 200:
    headers = dict(response.headers)
    setCache(cache_key, json.dumps(headers, ensure_ascii=False))
  
  return headers

def get(url, headers={}, cache_key='', sleep=0, retry=5, timeout=60):
  if cache_key is not False:
    if cache_key == None or cache_key == '':
      cache_key = url
    cache = getCache(cache_key)
  if cache != None:
    print("从缓存中获取到结果")
    return cache

  if 'User-Agent' not in headers:
     headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

  if sleep > 0:
     time.sleep(sleep)

  try_count = 1
  response = None
  while try_count <= retry:
    try:
      response = requests.get(url, headers=headers, timeout=timeout)
      break;
    except Exception as e:
      if try_count + 1 > retry:
        print('超出重试次数，抛出异常，次数：{}/{}'.format(try_count, retry), e)
        raise e
      else:
        print('接口调用失败，将重试，次数{}/{}'.format(try_count, retry), e)
        try_count += 1
        time.sleep(3)

  response.encoding = 'utf-8' 

	# 检查请求是否成功
  if response.status_code == 200:
    res_txt = response.text

    if res_txt != None and res_txt != '':
      if cache_key is not False:
        setCache(cache_key, res_txt)
      return res_txt
    else:
      print(res_txt)
      raise ValueError('响应结果为空')
  else:
    print(f"状态码: {response.status_code}")
    print(response.text)
    raise ValueError("响应失败")
  
def post(url, data={}, headers={
    'Content-Type': 'application/x-www-form-urlencoded'
  }, cache_key='', sleep=0, retry=5, timeout=60):
   # 发送POST请求

  if cache_key == None or cache_key == '':
    cache_key = url + json.dumps(data, ensure_ascii=False)
  cache = getCache(cache_key)
  if cache != None:
    print("从缓存中获取到结果")
    return cache
  
  if 'User-Agent' not in headers:
    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

  try:
    if sleep > 0:
       time.sleep(sleep)
    # 使用data参数发送表单数据

    try_count = 1
    response = None
    while try_count <= retry:
      try:
        if 'Content-Type' in headers and 'application/json' in headers['Content-Type']:
          print(url, data, headers)
          response = requests.post(url, json=data, headers=headers, timeout=timeout)
        else:
          response = requests.post(url, data=data, headers=headers, timeout=timeout)

        break;
      except Exception as e:
        if try_count + 1 > retry:
          print('超出重试次数，抛出异常，次数：{}/{}'.format(try_count, retry), e)
          raise e
        else:
          print('接口调用失败，将重试，次数{}/{}'.format(try_count, retry), e)
          try_count += 1
          time.sleep(3)
    
    # 检查响应状态码
    if response.status_code == 200:
      res_txt = response.text

      if res_txt != None and res_txt != '':
        setCache(cache_key, res_txt)
        return res_txt
      else:
        print(res_txt)
        raise ValueError('响应结果为空')
    else:
      print(f"请求失败，状态码: {response.status_code}")
      print("错误信息:", response.text)
      raise ValueError('请求失败：' + response.text)

  except requests.exceptions.RequestException as e:
    print("请求发生异常:", e)
    raise e

def download_with_selenium(url, save_path, filename, retry=5):
  res = None
  try_count = 1
  while try_count <= retry:
    try:
      res = download_pdf_with_selenium(url, save_path, filename)
      break;
    except Exception as e:
      if try_count + 1 > retry:
        print('超出重试次数，抛出异常，次数：{}/{}'.format(try_count, retry), e)
        raise e
      else:
        print('接口调用失败，将重试，次数{}/{}'.format(try_count, retry), e)
        try_count += 1
        time.sleep(3)
  
  return res

def download_pdf_with_selenium(url, save_path, filename, timeout=60):
  """
  使用Selenium下载PDF文件并保存到指定路径
  
  参数:
  url: PDF文件的直接URL
  save_path: 保存文件的目录路径
  filename: 保存后的文件名（包含.pdf扩展名）
  
  返回:
  file_path: 最终保存的文件路径
  """
  print('下载文件', url)
  cache = getCache(url)
  if cache != None:
    print("从缓存中获取到结果")
    return cache

  # 确保保存目录存在
  os.makedirs(save_path, exist_ok=True)
  
  # 配置Chrome选项
  chrome_options = Options()
  chrome_options.add_argument("--headless")  # 无头模式
  chrome_options.add_experimental_option('prefs', {
    "download.default_directory": save_path,  # 设置下载目录
    "download.prompt_for_download": False,    # 禁用下载提示
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True  # 总是外部打开PDF
  })
  
  try:
    # 初始化WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.command_executor._commands["send_command"] = (
        "POST", '/session/$sessionId/chromium/send_command'
    )
    
    # 启用下载管理
    params = {'cmd': 'Page.setDownloadBehavior', 
              'params': {'behavior': 'allow', 'downloadPath': save_path}}
    driver.execute("send_command", params)
    
    # 导航到PDF URL
    driver.get(url)
    
    # 等待下载完成 - 检查目录中是否出现了PDF文件
    start_time = time.time()
    downloaded = False
    
    while time.time() - start_time < timeout:
      time.sleep(1)  # 每秒检查一次
      files = os.listdir(save_path)
      if any(file.endswith('.pdf') or file.endswith('.crdownload') for file in files):
        # 检查下载是否完成
        if any(file.endswith('.pdf') for file in files) and not any(
          file.endswith('.crdownload') for file in files):
          downloaded = True
          break
    
    if not downloaded:
      raise TimeoutError("PDF下载超时或未完成")
    
    # 找到下载的PDF文件（可能会自动重命名）
    files = [f for f in os.listdir(save_path) if f.endswith('.pdf')]
    if not files:
      raise FileNotFoundError("下载的PDF文件未找到")
    
    # 获取实际下载的文件名和路径
    original_file = files[0]
    original_path = os.path.join(save_path, original_file)
    
    # 构造目标路径
    file_path = os.path.join(save_path, filename)
    
    # 重命名文件
    os.rename(original_path, file_path)

    file_size = os.path.getsize(file_path)
    if file_size < 30720:
        removeCache(url)
        raise ValueError('下载失败，文件小于30kb')
    
    print(f"已成功下载至: {file_path}")
    setCache(url, file_path)
    return file_path
      
  except Exception as e:
    raise Exception(f"下载失败: {str(e)}")
  finally:
    driver.quit()

def download(url, save_path=None, filename=None, headers={}, retry=5, timeout=300, sleep=0):
  """
    下载 HTTPS 的 PDF 文件
    
    参数:
    url: PDF 文件的 HTTPS URL
    save_path: 保存路径（默认为当前目录，使用 URL 中的文件名）
    """
  print('下载文件', url)
  cache = getCache(url)
  if cache != None:
    print("从缓存中获取到结果")
    return cache
  try:
      # 添加浏览器头部避免被拒绝
      if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

      
      # 发起 HTTPS 请求
      try_count = 1
      response = None
      while try_count <= retry:
        try:
          if sleep > 0:
            time.sleep(sleep)
          response = requests.get(url, headers=headers, stream=True, timeout=timeout)
          break;
        except Exception as e:
          if try_count + 1 > retry:
            print('超出重试次数，抛出异常，次数：{}/{}'.format(try_count, retry), e)
            raise e
          else:
            print('接口调用失败，将重试，次数{}/{}'.format(try_count, retry), e)
            try_count += 1
      response.raise_for_status()  # 检查请求是否成功
      
      # 从 URL 提取文件名
      if filename is None or filename == '':
        filename = url.split('/')[-1] if '/' in url else 'download.pdf'

      # 获取文件名
      if not save_path:
          save_path = default_save_path + '/' + filename
      else:
          save_path = save_path + filename
      
      # 写入文件（二进制模式）
      with open(save_path, 'wb') as f:
          for chunk in response.iter_content(chunk_size=8192):
              if chunk:  # 过滤掉 keep-alive 数据块
                  f.write(chunk)

      file_size = os.path.getsize(save_path)
      print(f"已成功下载至: {os.path.abspath(save_path)}")

      if file_size < 30720:
         removeCache(url)
         raise ValueError('下载失败，文件小于30kb')
         
      print(f"已成功下载至: {os.path.abspath(save_path)}")

      setCache(url, save_path)
      return save_path
  except Exception as e:
      print(f"下载失败: {str(e)}")
      raise e


def download_pdf(url, save_path=None):
    """
    下载 HTTPS 的 PDF 文件
    
    参数:
    url: PDF 文件的 HTTPS URL
    save_path: 保存路径（默认为当前目录，使用 URL 中的文件名）
    """
    try:
        # 添加浏览器头部避免被拒绝
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 发起 HTTPS 请求
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        
        # 获取文件名
        if not save_path:
            # 从 URL 提取文件名
            filename = url.split('/')[-1] if '/' in url else 'download.pdf'
            # 确保文件名以 .pdf 结尾
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            save_path = filename
        
        # 写入文件（二进制模式）
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # 过滤掉 keep-alive 数据块
                    f.write(chunk)
        
        print(f"PDF 已成功下载至: {os.path.abspath(save_path)}")
        return True
    
    except Exception as e:
        print(f"下载失败: {str(e)}")
        return False

if __name__ == '__main__':
   url = 'https://static.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-03-28/601128_20250328_QKK8.pdf'
   save_path = '/Users/nambo/Documents/project/tianchi/AFAC2025挑战组-赛题四：智能体赋能的金融多模态报告自动化生成/common/_cache/'
   filename = '01128_常熟银行_江苏常熟农村商业银行股份有限公司2024年年度报告_2025-03-28.pdf'
   res = download_pdf_with_selenium(url, save_path, filename)
   print(json.dumps(res, ensure_ascii=False))