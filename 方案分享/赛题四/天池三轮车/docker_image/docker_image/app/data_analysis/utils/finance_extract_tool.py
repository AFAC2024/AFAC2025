import datetime

import requests
import json


def extract_markdown(stock_code, company_name, year, query):
    get_toc_info_url = "http://localhost:5001/get_toc_info"
    get_md_content_url = "http://localhost:5000/parse_pdf"
    params = json.dumps({
        "stock_code": stock_code,
        "company_name": company_name,
        "year": year,
        "query": query
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", get_toc_info_url, headers=headers, data=params)
    response_json = response.json()
    toc_info = response_json["toc_info"]
    report_name = response_json["report_name"]

    get_md_content_params = json.dumps({
        "toc_info": toc_info,
        "timeout": 300
    })
    response = requests.request("POST", get_md_content_url, headers=headers, data=get_md_content_params)
    print(response.text)
    try:
        md_content = response.json()
        md_content["report_name"] = report_name
        return md_content
    except Exception as e:
        return ""


# print(extract_markdown("00020", "商汤科技", "2025", "商汤科技2025年度报告"))