#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQ消息导出处理器
从chunk.jsonl中提取发送人昵称和纯文本内容
"""

import json
import sys
import os
from pathlib import Path


def extract_sender_name(sender_data: dict) -> str:
    """
    从sender对象中提取发送者昵称
    优先级: groupCard > name > nickname > remark > uid > "未知用户"
    """
    if not isinstance(sender_data, dict):
        return "未知用户"
    
    # 优先使用群名片(groupCard)，其次是name
    name = sender_data.get("groupCard") or sender_data.get("name") or sender_data.get("nickname") or sender_data.get("remark")
    
    if name and name.strip():
        return name.strip()
    
    # 如果都没有，使用uid作为后备
    uid = sender_data.get("uid") or sender_data.get("uin")
    if uid and str(uid).strip():
        return f"用户_{uid}"
    
    return "未知用户"


def extract_text_content(content_data: dict) -> str:
    """
    从content对象中提取纯文本内容
    """
    if not isinstance(content_data, dict):
        return ""
    
    # 直接获取text字段
    text = content_data.get("text", "")
    
    # 如果text为空，尝试从elements中提取
    if not text or not text.strip():
        elements = content_data.get("elements", [])
        if isinstance(elements, list):
            text_parts = []
            for elem in elements:
                if isinstance(elem, dict):
                    elem_type = elem.get("type", "")
                    elem_data = elem.get("data", {})
                    if isinstance(elem_data, dict):
                        if elem_type == "text":
                            text_parts.append(elem_data.get("text", ""))
                        elif elem_type == "at":
                            # @某人，使用name
                            at_name = elem_data.get("name", "")
                            if at_name:
                                text_parts.append(f"@{at_name}")
                        elif elem_type == "face":
                            # 表情
                            face_name = elem_data.get("name", "")
                            if face_name:
                                text_parts.append(f"[{face_name}]")
                        elif elem_type == "image":
                            # 图片
                            text_parts.append("[图片]")
                        elif elem_type == "video":
                            # 视频
                            text_parts.append("[视频]")
                        elif elem_type == "reply":
                            # 回复消息标记
                            text_parts.append("[回复消息]")
            text = "".join(text_parts)
    
    return text.strip()


def process_message(message: dict) -> dict | None:
    """
    处理单条消息，提取name和text
    返回None表示跳过此消息（如系统消息）
    """
    if not isinstance(message, dict):
        return None
    
    # 检查是否为系统消息
    msg_type = message.get("type", "")
    is_system = message.get("system", False)
    
    # 跳过纯系统消息（如撤回提示等）
    if is_system or msg_type == "system":
        return None
    
    # 提取发送者名称
    sender = message.get("sender", {})
    name = extract_sender_name(sender)
    
    # 提取文本内容
    content = message.get("content", {})
    text = extract_text_content(content)
    
    # 如果文本为空，根据类型给出提示
    if not text:
        if msg_type == "image":
            text = "[图片]"
        elif msg_type == "video":
            text = "[视频]"
        elif msg_type == "json":
            text = "[JSON消息]"
        elif msg_type == "type_17":
            text = "[表情]"
        else:
            text = f"[{msg_type}]" if msg_type else "[空消息]"
    
    return {
        "name": name,
        "text": text
    }


def process_file(input_path: str, output_path: str) -> dict:
    """
    处理JSONL文件
    """
    stats = {
        "total_lines": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0
    }
    
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    if not input_file.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        
        for line_num, line in enumerate(fin, 1):
            stats["total_lines"] += 1
            line = line.strip()
            
            # 跳过空行
            if not line:
                stats["skipped"] += 1
                continue
            
            try:
                # 解析JSON
                message = json.loads(line)
                
                # 处理消息
                result = process_message(message)
                
                if result is None:
                    stats["skipped"] += 1
                    continue
                
                # 写入输出
                fout.write(json.dumps(result, ensure_ascii=False) + '\n')
                stats["success"] += 1
                
                # 每1000行显示进度
                if line_num % 1000 == 0:
                    print(f"已处理 {line_num} 行...", end='\r')
                    
            except json.JSONDecodeError as e:
                stats["failed"] += 1
                print(f"\n第 {line_num} 行 JSON解析失败: {e}")
                # 写入错误日志
                with open(output_file.with_suffix('.errors.log'), 'a', encoding='utf-8') as ferr:
                    ferr.write(f"Line {line_num}: {line[:200]}\nError: {e}\n\n")
                    
            except Exception as e:
                stats["failed"] += 1
                print(f"\n第 {line_num} 行 处理异常: {e}")
    
    print()  # 换行
    return stats


def get_output_path(input_file: Path, input_base: Path, output_base: Path) -> Path:
    """
    根据输入文件路径生成对应的输出文件路径
    保持相对目录结构，文件名添加 _processed 后缀
    """
    # 获取相对路径
    relative_path = input_file.relative_to(input_base)
    # 添加 _processed 后缀
    output_name = input_file.stem + "_processed" + input_file.suffix
    # 组合输出路径
    return output_base / relative_path.parent / output_name


def process_directory(input_dir: Path, output_dir: Path) -> dict:
    """
    批量处理目录下的所有 JSONL 文件
    """
    # 查找所有 .jsonl 文件
    jsonl_files = list(input_dir.rglob("*.jsonl"))
    
    if not jsonl_files:
        print(f"在 {input_dir} 目录下未找到 .jsonl 文件")
        return {"total_files": 0, "processed_files": 0, "failed_files": 0}
    
    print(f"找到 {len(jsonl_files)} 个 JSONL 文件")
    print("-" * 50)
    
    total_stats = {
        "total_files": len(jsonl_files),
        "processed_files": 0,
        "failed_files": 0,
        "total_lines": 0,
        "total_success": 0,
        "total_skipped": 0,
        "total_failed": 0
    }
    
    for i, input_file in enumerate(jsonl_files, 1):
        output_file = get_output_path(input_file, input_dir, output_dir)
        
        print(f"\n[{i}/{len(jsonl_files)}] 处理: {input_file}")
        print(f"       输出: {output_file}")
        
        try:
            stats = process_file(str(input_file), str(output_file))
            total_stats["processed_files"] += 1
            total_stats["total_lines"] += stats["total_lines"]
            total_stats["total_success"] += stats["success"]
            total_stats["total_skipped"] += stats["skipped"]
            total_stats["total_failed"] += stats["failed"]
            
            print(f"       完成: {stats['success']} 条消息, 跳过: {stats['skipped']}, 失败: {stats['failed']}")
            
        except Exception as e:
            total_stats["failed_files"] += 1
            print(f"       错误: {e}")
    
    return total_stats


def process_single_file(input_path: str, output_path: str = None) -> dict:
    """
    处理单个文件（保持向后兼容）
    """
    input_file = Path(input_path)
    
    if output_path is None:
        # 自动生成输出文件名
        output_path = str(input_file.with_stem(input_file.stem + "_processed"))
    
    print(f"输入文件: {input_path}")
    print(f"输出文件: {output_path}")
    print("开始处理...")
    print("-" * 50)
    
    stats = process_file(input_path, output_path)
    
    print("-" * 50)
    print("处理完成!")
    print(f"总行数: {stats['total_lines']}")
    print(f"成功提取: {stats['success']}")
    print(f"跳过(系统消息/空行): {stats['skipped']}")
    print(f"失败: {stats['failed']}")
    
    return stats


def main():
    # 默认目录
    default_input_dir = Path("1-Original")
    default_output_dir = Path("2-Extracted")
    
    # 支持命令行参数
    if len(sys.argv) >= 2:
        input_arg = Path(sys.argv[1])
        
        # 如果参数是文件，按单文件模式处理（向后兼容）
        if input_arg.is_file():
            output_arg = sys.argv[2] if len(sys.argv) >= 3 else None
            try:
                process_single_file(str(input_arg), output_arg)
                return
            except FileNotFoundError as e:
                print(f"错误: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"处理过程中发生错误: {e}")
                sys.exit(1)
        
        # 如果参数是目录，作为输入目录
        default_input_dir = input_arg
    
    # 确定输入输出目录
    input_dir = default_input_dir
    output_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else default_output_dir
    
    # 确保输入目录存在
    if not input_dir.exists():
        print(f"输入目录不存在: {input_dir}")
        print(f"请创建 {input_dir} 目录并将 .jsonl 文件放入其中")
        sys.exit(1)
    
    if not input_dir.is_dir():
        print(f"输入路径不是目录: {input_dir}")
        sys.exit(1)
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"输入目录: {input_dir.absolute()}")
    print(f"输出目录: {output_dir.absolute()}")
    print("=" * 50)
    
    try:
        stats = process_directory(input_dir, output_dir)
        
        if stats["total_files"] == 0:
            sys.exit(0)
        
        print("\n" + "=" * 50)
        print("批量处理完成!")
        print(f"总文件数: {stats['total_files']}")
        print(f"成功处理: {stats['processed_files']}")
        print(f"处理失败: {stats['failed_files']}")
        print("-" * 50)
        print(f"总行数: {stats['total_lines']}")
        print(f"成功提取: {stats['total_success']}")
        print(f"跳过(系统消息/空行): {stats['total_skipped']}")
        print(f"解析失败: {stats['total_failed']}")
        
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
