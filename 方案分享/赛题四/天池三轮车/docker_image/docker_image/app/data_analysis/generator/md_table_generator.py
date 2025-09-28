def generate_markdown_table(headers, rows, align=None):
    """
    生成 Markdown 格式表格
    :param headers: 表头列表，例如 ["Name", "Age", "City"]
    :param rows: 二维数据列表，例如 [["Alice", 30, "New York"], ...]
    :param align: 对齐方式列表（可选），例如 ["left", "center", "right"]
    :return: Markdown 表格字符串
    """
    # 生成表头
    header_line = "| " + " | ".join(headers) + " |"

    # 生成分隔线
    if align:
        separators = []
        for a in align:
            if a == "left":
                separators.append(":---")
            elif a == "center":
                separators.append(":---:")
            elif a == "right":
                separators.append("---:")
            else:
                separators.append("---")
        separator_line = "| " + " | ".join(separators) + " |"
    else:
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"

    # 生成数据行
    data_lines = []
    for row in rows:
        data_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

    # 组合所有部分
    return "\n".join([header_line, separator_line] + data_lines)


if __name__ == "__main__":
    headers = ["Name", "Age", "City"]
    data = [
        ["Alice", 30, "New York"],
        ["Bob", 25, "Los Angeles"],
        ["Charlie", 35, "Chicago"]
    ]
    alignment = ["left", "center", "right"]

    md_table = generate_markdown_table(headers, data, alignment)
    print(md_table)