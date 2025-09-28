# import nest_asyncio
# nest_asyncio.apply()
from fastapi import FastAPI, Request
from openai import AsyncOpenAI
from fastapi.responses import JSONResponse
import uvicorn
from sse_starlette.sse import EventSourceResponse
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Document,
    ServiceContext,
    Settings
)

import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from elasticsearch import AsyncElasticsearch
from llama_index.vector_stores.elasticsearch.base import ElasticsearchStore
from llama_index.vector_stores.elasticsearch import AsyncDenseVectorStrategy
# 定义和执行检索器
from llama_index.core.indices.postprocessor import SentenceTransformerRerank
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor import SimilarityPostprocessor
from loguru import logger
from datetime import datetime
import re

from utils import get_toc_info_llm, download_pdf


# 设置日志
current_date = datetime.now().strftime('%Y-%m-%d')
logger_file_path = "rag_{}.log".format(current_date)
logger.add(logger_file_path, rotation="00:00", retention="7 days", compression="zip")

embed_model = HuggingFaceEmbedding(model_name='/workspace/code/bge-large-zh', embed_batch_size=10)

Settings.embed_model = embed_model
Settings.llm = None

dev_es_url = "es-cn-pe33cyg3b000lcjo4.public.elasticsearch.aliyuncs.com"
prod_es_url = "es-cn-7pe9v6vzj0004z5o4.elasticsearch.aliyuncs.com"
# es向量数据库初始化
ES_Client = AsyncElasticsearch(
    hosts=[{'host': 'es-cn-pe33cyg3b000lcjo4.public.elasticsearch.aliyuncs.com', 'port': 9200, 'scheme': 'http'}],
    basic_auth=('elastic', 'KMy3G1LHmeMn3Ev0Zv1t'),
    request_timeout=600
)

app = FastAPI()


@app.route('/embedding', methods=['POST'])
async def embedding(request: Request):
    params = await request.json()
    logger.info("embedding params: {}".format(params))
    content = params
    result = {}
    result["code"] = 200
    result["message"] = "embedding success"
    documents = []
    table_name = str(content["table_name"])
    index_name = "financial_report"

    es = ElasticsearchStore(
            index_name=index_name,
            es_client=ES_Client,
            retrieval_strategy=AsyncDenseVectorStrategy(hybrid=True),
        )
    try:
        for key, value in content.items():
            if key != "table_name" :
                text = "{}:{}".format(key, value)
                document = Document(text=text, metadata={"table_name": table_name})
                documents.append(document)
             
        # 创建ServiceContext
        auto_merging_context = ServiceContext.from_defaults(
            llm=None,
            embed_model=embed_model,
        )

        storage_context = StorageContext.from_defaults(vector_store=es)
        automerging_index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            service_context=auto_merging_context,
            show_progress=True,
            transformations=[SentenceSplitter(chunk_size=2048 , chunk_overlap=256)]
        )
    except Exception as e:
        result["code"] = 500
        result["message"] = f"Error occurred: {e}"
        logger.error(f"Error occurred: {e}")
    finally:
        logger.info("embedding result: {}".format(result))
        return JSONResponse(content=result)

@app.route('/get_toc_info', methods=['POST'])
async def get_toc_info(request: Request):
    data = await request.json()
    logger.info("query params: {}".format(data))
    query = data['query']
    stock_code = data["stock_code"]
    year = data["year"]
    conpany_name = data["company_name"]
    if len(str(stock_code)) == 5 or "HK" in str(stock_code):
        stock_type = "hke"
        table_name = f"{year}_{stock_type}_combined_financial_reports.xlsx"
    else:
        table_name = f"{year}_combined_financial_reports.xlsx"

    index_name = "financial_reporting"
    
    es = ElasticsearchStore(
            index_name=index_name,
            es_client=ES_Client,
            retrieval_strategy=AsyncDenseVectorStrategy(hybrid=True),
        )
    try:
        filters = MetadataFilters(filters=[ExactMatchFilter(key="table_name", value=table_name)])
        automerging_index = VectorStoreIndex.from_vector_store(vector_store=es)
        
        base_retriever = automerging_index.as_retriever(
            # search_type = "similarity_score_threshold",
            # search_kwargs = {
            #     "score_threshold": 0.5
            # },
            filters=filters
        )

        retriever = AutoMergingRetriever(
            base_retriever,
            automerging_index.storage_context,
            verbose=True
        )
        rerank = SentenceTransformerRerank(top_n=7, model="/workspace/code/bge-reranker-base")
        auto_merging_engine = RetrieverQueryEngine.from_args(
            retriever,
            node_postprocessors=[rerank])
        auto_merging_response = auto_merging_engine.query(query)
        logger.info("auto_merging_response: {}".format(auto_merging_response))

        search = auto_merging_response.response.split('table_name: {}\n\n'.format(table_name))[1:]
        logger.info("search: {}, type: {}".format(search, type(search)))
        pdf_links = []
        report_name = search[0].split('https')[0][:-1]
        for item in search:
            match = re.search(r'(https?://[^\s]+?\.PDF)', item, re.IGNORECASE)
            if match:
                pdf_links.append(match.group(1))
        logger.info("report_name: {}".format(report_name))
        logger.info("pdf_links: {}".format(pdf_links))
        pdf_url = pdf_links[0]
        logger.info("pdf_url: {}".format(pdf_url))
        pdf_name = pdf_url.split('/')[-1][:-4]+".pdf"
        pdf_path = "pdf_path"
        abs_path = "pdf_path/{}".format(pdf_name)
        # 判断pdf是否存在，如果不存在则下载
        if not os.path.exists(abs_path):
            logger.info("pdf not exist, start download")
            download_pdf(pdf_url, abs_path)
        else:
            logger.info("pdf exist")
        toc_info = get_toc_info_llm(abs_path)
        result = {"toc_info": toc_info,
                  "report_name": report_name}
        return JSONResponse(result, status_code=200)
    except Exception as e:
        logger.error("error occurred: {}".format(e))
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5001, loop="asyncio")