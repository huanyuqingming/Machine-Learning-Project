def split_file(input_file, output_prefix, num_parts, lines_per_part):
    # 读取所有URL
    with open(input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # 计算每份的大小
    total_lines = len(lines)
    part_size = lines_per_part
    last_part_size = total_lines - part_size * (num_parts - 1)

    # 分割并写入文件
    for i in range(num_parts):
        start_index = i * part_size
        if i == num_parts - 1:
            end_index = start_index + last_part_size
        else:
            end_index = start_index + part_size

        part_lines = lines[start_index:end_index]
        output_file = f"{output_prefix}_part_{i+1}.txt"
        with open(output_file, 'w', encoding='utf-8') as part_file:
            part_file.writelines(part_lines)

# 使用示例
split_file('urls.txt', 'urls', 13, 930)