import requests


def bbb():
  import ssl
  import json

  # 创建上下文忽略SSL证书验证
  ssl_context = ssl.create_default_context()
  ssl_context.check_hostname = False
  ssl_context.verify_mode = ssl.CERT_NONE

  params = {
      'wd': '宁德时代',
      'skip_login': '1',
      'finClientType': 'pc'
  }

  headers = {
      'Cookie': 'BAIDUID=DAECC9F862E73705E9CE99DF9314CD17:FG=1',
      # 必须添加 User-Agent
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
      # 建议添加 Referer
      'Referer': 'https://finance.baidu.com/'
  }

  cookie = {
    'BAIDUID': 'BAIDUID=3DB0ACF63952AAE8C8195D2A0B6F6A80:FG=1; BAIDUID_BFESS=3DB0ACF63952AAE8C8195D2A0B6F6A80:FG=1',
  }

  try:
      response = requests.get(
          'https://finance.pae.baidu.com/selfselect/sug',
          params=params,
          # headers=headers,
          cookies=cookie,
          timeout=5
      )
      # 检查状态码
      if response.status_code == 200:
          print("请求成功，响应内容:")
          print(response.text)
      else:
          print(f"请求失败，状态码: {response.status_code}")
  except requests.exceptions.RequestException as e:
      print(f"请求异常: {e}")




def aaa():
  import urllib.parse
  import urllib.request
  import ssl
  import json

  # 创建上下文忽略SSL证书验证
  ssl_context = ssl.create_default_context()
  ssl_context.check_hostname = False
  ssl_context.verify_mode = ssl.CERT_NONE

  # 准备参数和URL
  params = {
      'wd': '宁德时代',
      'skip_login': '1',
      'finClientType': 'pc'
  }
  base_url = 'https://finance.pae.baidu.com/selfselect/sug'
  url = f'{base_url}?{urllib.parse.urlencode(params)}'

  # 准备请求头
  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
      'Referer': 'https://finance.baidu.com/',
      'Cookie': 'BAIDUID=DAECC9F862E73705E9CE99DF9314CD17:FG=1',
      'Accept': 'application/json, text/javascript, */*; q=0.01'
  }

  # 创建请求对象
  req = urllib.request.Request(url, headers=headers)

  try:
      # 发送请求
      with urllib.request.urlopen(req, context=ssl_context) as response:
          # 读取响应内容
          content = response.read().decode('utf-8')
          
          # 尝试解析为JSON（如果是JSON格式）
          try:
              json_data = json.loads(content)
              print("请求成功，JSON响应:")
              print(json.dumps(json_data, indent=2, ensure_ascii=False))
          except json.JSONDecodeError:
              print("请求成功，响应内容:")
              print(content)
          
          print(f"\n响应状态码: {response.status}")
          
  except urllib.error.HTTPError as e:
      print(f"HTTP错误: {e.code} - {e.reason}")
      print("错误响应:", e.read().decode('utf-8'))
  except urllib.error.URLError as e:
      print(f"URL错误: {e.reason}")
  except Exception as e:
      print(f"发生异常: {str(e)}")






if __name__ == '__main__':
    bbb()