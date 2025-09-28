import os
from pathlib import Path

from loguru import logger

from mineru.utils.enum_class import MakeMode
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json


def do_parse(
    output_dir,  # Output directory for storing parsing results
    pdf_file_names: list[str],  # List of PDF file names to be parsed
    pdf_bytes_list: list[bytes],  # List of PDF bytes to be parsed
    p_lang_list: list[str],  # List of languages for each PDF, default is 'ch' (Chinese)
    parse_method="auto",  # The method for parsing PDF, default is 'auto'
    formula_enable=True,  # Enable formula parsing
    table_enable=True,  # Enable table parsing
    f_make_md_mode=MakeMode.MM_MD,  # The mode for making markdown content, default is MM_MD
    start_page_id=0,  # Start page ID for parsing, default is 0
    end_page_id=None,  # End page ID for parsing, default is None (parse all pages until the end of the document)
):


    for idx, pdf_bytes in enumerate(pdf_bytes_list):
        new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
        pdf_bytes_list[idx] = new_pdf_bytes

    infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(pdf_bytes_list, p_lang_list, parse_method=parse_method, formula_enable=formula_enable,table_enable=table_enable)

    for idx, model_list in enumerate(infer_results):
        pdf_file_name = pdf_file_names[idx]
        local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, parse_method)
        image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)

        images_list = all_image_lists[idx]
        pdf_doc = all_pdf_docs[idx]
        _lang = lang_list[idx]
        _ocr_enable = ocr_enabled_list[idx]
        middle_json = pipeline_result_to_middle_json(model_list, images_list, pdf_doc, image_writer, _lang, _ocr_enable, formula_enable)
        pdf_info = middle_json["pdf_info"]
        pdf_bytes = pdf_bytes_list[idx]

        
        image_dir = str(os.path.basename(local_image_dir))
        md_content_str = pipeline_union_make(pdf_info, f_make_md_mode, image_dir)
        md_writer.write_string(f"{pdf_file_name}.md", md_content_str)
        
        logger.info(f"local output dir is {local_md_dir}")

        # \u00字符串解码
        with open(f"{local_md_dir}/{pdf_file_name}.md", "r", encoding="utf-8") as f:
            md_content = f.read()
            # print(md_content)
        return md_content


def parse_doc(
        path_list: list[Path],
        output_dir,
        lang="ch",
        backend="pipeline",
        method="auto",
        server_url=None,
        start_page_id=0,
        end_page_id=None
):
    md_content_str = ""
    try:
        file_name_list = []
        pdf_bytes_list = []
        lang_list = []
        for path in path_list:
            file_name = str(Path(path).stem)
            pdf_bytes = read_fn(path)
            file_name_list.append(file_name)
            pdf_bytes_list.append(pdf_bytes)
            lang_list.append(lang)
        md_content_str = do_parse(output_dir=output_dir,
                                  pdf_file_names=file_name_list, 
                                  pdf_bytes_list=pdf_bytes_list,
                                  p_lang_list=lang_list,
                                  parse_method=method,
                                  start_page_id=start_page_id,
                                  end_page_id=end_page_id
        )
    except Exception as e:
        logger.exception(e)

    return md_content_str



if __name__ == '__main__':
    pass