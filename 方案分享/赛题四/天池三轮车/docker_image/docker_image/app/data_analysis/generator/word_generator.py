import pypandoc
import re


def fix_markdown_table(text):
    # 确保表头分隔符存在
    text = re.sub(r"(\|.*\|)\n([^|:-]+)", r"\1\n|:---|:---:|---:|\n", text)
    # 对齐符号标准化
    text = re.sub(r"(\| *:?-+:? *){2,}", lambda m: "|".join(["---"] * len(m.group().split("|"))), text)
    return text


def format_markdown(output_file):
    try:
        import subprocess
        format_cmd = ["mdformat", output_file]
        subprocess.run(format_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"✅ 已用 mdformat 格式化 Markdown 文件: {output_file}")
    except Exception as e:
        print(f"[提示] mdformat 格式化失败: {e}\n请确保已安装 mdformat (pip install mdformat)")


def word_generator(output_file, docx_output):
    """转换为Word文档"""
    if docx_output is None:
        docx_output = output_file.replace('.md', '.docx')
    try:
        import subprocess
        import os
        pandoc_cmd = [
            "pandoc",
            output_file,
            "-o",
            docx_output,
            "--standalone",
            "--resource-path=.",
            "--extract-media=."
        ]
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True, encoding='utf-8', env=env)
        print(f"\n📄 Word版报告已生成: {docx_output}")
    except subprocess.CalledProcessError as e:
        print(f"[提示] pandoc转换失败。错误信息: {e.stderr}")
        print("[建议] 检查图片路径是否正确，或使用 --extract-media 选项")
    except Exception as e:
        print(f"[提示] 若需生成Word文档，请确保已安装pandoc。当前转换失败: {e}")


def convert_md_to_docx(md_file, docx_file, reference_doc=None):
    extra_args = [
        "--standalone",
        "--wrap=preserve",  # 保留原始换行
        "--columns=500",  # 禁用自动换行
        # "--extensions=hard_line_breaks"  # 启用硬换行扩展
    ]

    if reference_doc:
        extra_args.append(f"--reference-doc={reference_doc}")

    pypandoc.convert_file(
        md_file,
        "docx",
        outputfile=docx_file,
        format="markdown+hard_line_breaks",  # 启用扩展
        extra_args=extra_args
    )

# format_markdown("../../reports/reports.md")
# convert_md_to_docx("../../reports/reports.md", "test.docx")
