import os
import glob
import json

def split_jsonl_files(input_dir, output_dir, lines_per_file=1000):
    """
    读取输入目录中的所有jsonl文件，按指定行数切分，保存到输出目录
    
    Args:
        input_dir: 输入目录路径
        output_dir: 输出目录路径
        lines_per_file: 每个切分文件的行数
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有jsonl文件
    jsonl_pattern = os.path.join(input_dir, "*.jsonl")
    jsonl_files = glob.glob(jsonl_pattern)
    
    if not jsonl_files:
        print(f"在 {input_dir} 目录中未找到任何 .jsonl 文件")
        return
    
    print(f"找到 {len(jsonl_files)} 个 jsonl 文件")
    
    for file_path in jsonl_files:
        file_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(file_name)[0]
        
        print(f"\n正在处理文件: {file_name}")
        
        # 读取并切分文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                file_count = 1
                
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:  # 跳过空行
                        lines.append(line)
                        
                        # 达到指定行数时写入文件
                        if len(lines) >= lines_per_file:
                            output_filename = f"{name_without_ext}_part{file_count:04d}.jsonl"
                            output_path = os.path.join(output_dir, output_filename)
                            
                            with open(output_path, 'w', encoding='utf-8') as out_f:
                                out_f.write('\n'.join(lines) + '\n')
                            
                            print(f"  已保存: {output_filename} ({len(lines)} 行)")
                            
                            lines = []
                            file_count += 1
                
                # 写入剩余的行（如果有）
                if lines:
                    output_filename = f"{name_without_ext}_part{file_count:04d}.jsonl"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    with open(output_path, 'w', encoding='utf-8') as out_f:
                        out_f.write('\n'.join(lines) + '\n')
                    
                    print(f"  已保存: {output_filename} ({len(lines)} 行)")
                    file_count += 1
                
                print(f"  共切分为 {file_count - 1} 个文件")
                
        except Exception as e:
            print(f"  处理文件 {file_name} 时出错: {str(e)}")
    
    print(f"\n所有文件处理完成！切分结果保存在: {output_dir}")

if __name__ == "__main__":
    # 配置
    INPUT_DIRECTORY = "2-Extracted"      # 输入目录
    OUTPUT_DIRECTORY = "3-Divided"       # 输出目录
    LINES_PER_SPLIT = 1000               # 每个文件的行数
    
    # 执行切分
    split_jsonl_files(INPUT_DIRECTORY, OUTPUT_DIRECTORY, LINES_PER_SPLIT)
