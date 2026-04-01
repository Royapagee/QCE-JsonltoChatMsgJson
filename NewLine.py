import os
import json


def process_jsonl_file(input_path, output_path):
    """
    读取JSONL文件，将文本字段中的\\n替换为实际换行符，并输出到指定路径
    
    Args:
        input_path: 输入JSONL文件路径
        output_path: 输出JSONL文件路径
    """
    processed_lines = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用状态机方法提取完整的JSON对象
    i = 0
    n = len(content)
    
    while i < n:
        # 跳过空白字符
        while i < n and content[i] in ' \t\r\n':
            i += 1
        
        if i >= n:
            break
        
        # 尝试找到完整的JSON对象
        if content[i] == '{':
            json_obj, end_pos = extract_json_object(content, i)
            if json_obj:
                try:
                    # 解析JSON
                    data = json.loads(json_obj)
                    
                    # 处理text字段中的\\n
                    if 'text' in data and isinstance(data['text'], str):
                        data['text'] = data['text'].replace('\\n', '\n')
                    
                    # 转回JSON字符串
                    processed_lines.append(json.dumps(data, ensure_ascii=False))
                except json.JSONDecodeError as e:
                    print(f"警告: 无法解析JSON对象: {json_obj[:50]}... 错误: {e}")
                    # 直接替换\\n作为后备方案
                    processed_lines.append(json_obj.replace('\\n', '\n'))
                
                i = end_pos
            else:
                # 无法提取完整JSON，跳过
                i += 1
        else:
            # 不是JSON开始，跳过
            i += 1
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 写入输出文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(processed_lines))
        if processed_lines:
            f.write('\n')  # 文件末尾添加换行
    
    print(f"已处理: {input_path} -> {output_path}")


def extract_json_object(content, start_pos):
    """
    从指定位置提取完整的JSON对象
    
    Args:
        content: 完整内容字符串
        start_pos: JSON对象开始位置（应该是'{'）
    
    Returns:
        (json_obj_str, end_pos) 或 (None, start_pos) 如果无法提取
    """
    if content[start_pos] != '{':
        return None, start_pos
    
    # 使用括号计数和字符串状态跟踪
    brace_count = 0
    in_string = False
    escape_next = False
    i = start_pos
    
    while i < len(content):
        char = content[i]
        
        if escape_next:
            escape_next = False
            i += 1
            continue
        
        if char == '\\' and in_string:
            escape_next = True
            i += 1
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            i += 1
            continue
        
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # 找到完整的JSON对象
                    return content[start_pos:i+1], i + 1
        
        i += 1
    
    # 未找到完整的JSON对象
    return None, start_pos


def process_directory(input_dir, output_subdir='Translate'):
    """
    处理指定目录中的所有JSONL文件（排除子目录）
    
    Args:
        input_dir: 输入目录路径
        output_subdir: 输出子目录名称
    """
    # 构建输出目录路径
    output_dir = os.path.join(input_dir, output_subdir)
    
    # 遍历输入目录
    for filename in os.listdir(input_dir):
        # 跳过子目录
        file_path = os.path.join(input_dir, filename)
        if os.path.isdir(file_path):
            continue
            
        # 只处理.jsonl文件
        if not filename.endswith('.jsonl'):
            continue
        
        # 构建输出文件路径
        output_path = os.path.join(output_dir, filename)
        
        # 处理文件
        process_jsonl_file(file_path, output_path)
    
    print(f"\n所有文件处理完成！输出目录: {output_dir}")


if __name__ == '__main__':
    # 处理 4-Cleansing 目录
    input_directory = '4-Cleansing'
    
    if not os.path.exists(input_directory):
        print(f"错误: 目录 {input_directory} 不存在")
    else:
        process_directory(input_directory)
