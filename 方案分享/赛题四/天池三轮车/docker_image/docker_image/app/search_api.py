from loguru import logger
import asyncio
from src.tool.web_search import WebSearch


def bing_search(query):
    web_search = WebSearch()
    search_response = asyncio.run(
        web_search.execute(
            query=query, fetch_content=True, num_results=10,
            lang="zh-CN", country="CN"
        )
    )

    results_list = []
    for result in search_response.results:
        if result.raw_content:
            search_content = {"url": result.url,
                      "title": result.title,
                      "description": result.description,
                      "content": result.raw_content}
            results_list.append(search_content)
    logger.info(f"search results: {results_list}")
    results = {"search_response": results_list}
    return results
    
    

if __name__ == '__main__':
    pass
