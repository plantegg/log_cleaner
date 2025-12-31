#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志清理脚本
根据文件修改时间清理指定目录下的日志文件，保留指定百分比的最新文件
"""

import os
import sys
import glob
import argparse
from datetime import datetime
import re

def human_readable_size(size_bytes):
    """将字节转换为人类可读的格式"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return "{:.1f}{}".format(size_bytes, size_names[i])

def find_log_files(log_dir):
    """查找所有日志文件"""
    all_files = set()
    
    # 使用os.walk递归遍历目录
    for root, dirs, files in os.walk(log_dir):
        for file in files:
            if (file.endswith('.log') or 
                re.match(r'log\.20\d{2}-\d{2}-\d{2}\.\d+\.log$', file) or
                re.match(r'trace\.20\d{2}-\d{2}-\d{2}\.\d+\.log$', file) or
                re.match(r'\d+\.log$', file)):
                file_path = os.path.join(root, file)
                all_files.add(file_path)
    
    # 过滤出真正的日志文件（排除目录等）
    log_files = []
    for file_path in all_files:
        if os.path.isfile(file_path):
            # 获取文件修改时间
            mtime = os.path.getmtime(file_path)
            log_files.append((mtime, file_path))
    
    # 按修改时间排序，最新的在前
    log_files.sort(reverse=True)
    return log_files

def main():
    parser = argparse.ArgumentParser(
        description="根据修改时间清理日志文件，保留指定百分比的最新文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s /path/to/logs 70                           # 单个目录
  %(prog)s /path/to/logs:/path2/logs:/path3/logs 70   # 多个目录，用冒号分隔
  %(prog)s ./app/logs 80                              # 保留最新的80%%的文件
        """
    )
    
    parser.add_argument("log_dirs", help="日志文件目录路径，多个目录用冒号(:)分隔")
    parser.add_argument("keep_percent", type=int, 
                       help="要保留的文件百分比 (1-99)")
    parser.add_argument("--dry-run", action="store_true",
                       help="仅显示将要删除的文件，不实际删除")
    parser.add_argument("--auto-confirm", action="store_true",
                       help="自动确认删除，不询问用户")
    
    args = parser.parse_args()
    
    # 解析多个目录
    log_dirs = [d.strip() for d in args.log_dirs.split(':') if d.strip()]
    
    # 验证参数
    for log_dir in log_dirs:
        if not os.path.isdir(log_dir):
            print("错误: 目录 '{}' 不存在".format(log_dir))
            sys.exit(1)
    
    if not (1 <= args.keep_percent <= 99):
        print("错误: 保留百分比必须是1-99之间的整数")
        sys.exit(1)
    
    print("开始分析 {} 个日志目录:".format(len(log_dirs)))
    for log_dir in log_dirs:
        print("  - {}".format(log_dir))
    print("保留最新的 {}% 文件".format(args.keep_percent))
    
    # 查找所有目录中的日志文件
    all_log_files = []
    for log_dir in log_dirs:
        log_files = find_log_files(log_dir)
        all_log_files.extend(log_files)
        print("  {}: 找到 {} 个文件".format(log_dir, len(log_files)))
    
    # 重新按时间排序所有文件
    all_log_files.sort(reverse=True)
    log_files = all_log_files
    
    if not log_files:
        print("所有目录中均未找到任何日志文件")
        sys.exit(0)
    
    total_files = len(log_files)
    keep_count = int(total_files * args.keep_percent / 100)
    delete_count = total_files - keep_count
    
    print("\n总计找到 {} 个日志文件".format(total_files))
    print("将保留最新的 {} 个文件".format(keep_count))
    print("将删除最旧的 {} 个文件".format(delete_count))
    
    if delete_count == 0:
        print("无需删除任何文件")
        sys.exit(0)
    
    # 获取要删除的文件列表（最旧的文件）
    files_to_delete = log_files[-delete_count:]
    
    print("\n即将删除的文件（最旧的 {} 个）:".format(delete_count))
    total_size = 0
    for mtime, filepath in files_to_delete:
        try:
            file_size = os.path.getsize(filepath)
            total_size += file_size
            mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            print("  {}".format(filepath))
            print("    修改时间: {}, 大小: {}".format(mod_time, human_readable_size(file_size)))
        except OSError as e:
            print("  {} (无法获取文件信息: {})".format(filepath, e))
    
    print("\n总计将释放约 {} 的磁盘空间".format(human_readable_size(total_size)))
    
    if args.dry_run:
        print("\n[DRY RUN] 仅预览，未实际删除任何文件")
        sys.exit(0)
    
    # 确认删除
    if not args.auto_confirm:
        try:
            confirm = input("\n确认删除这些文件吗? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("取消删除操作")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n\n操作被用户取消")
            sys.exit(0)
    
    # 执行删除
    print("\n开始删除文件...")
    deleted_count = 0
    deleted_size = 0
    failed_files = []
    
    for mtime, filepath in files_to_delete:
        try:
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                os.remove(filepath)
                print("已删除: {}".format(filepath))
                deleted_count += 1
                deleted_size += file_size
            else:
                print("文件不存在: {}".format(filepath))
        except OSError as e:
            print("删除失败: {} ({})".format(filepath, e))
            failed_files.append(filepath)
    
    print("\n清理完成!")
    print("成功删除了 {} 个文件".format(deleted_count))
    print("释放了 {} 的磁盘空间".format(human_readable_size(deleted_size)))
    
    if failed_files:
        print("删除失败的文件数: {}".format(len(failed_files)))
    
    # 清理空的日期目录
    if not args.auto_confirm:
        try:
            clean_empty = input("\n是否清理所有目录中的空日期目录? (y/N): ").strip().lower()
            if clean_empty in ['y', 'yes']:
                for log_dir in log_dirs:
                    print("\n清理目录: {}".format(log_dir))
                    clean_empty_date_dirs(log_dir)
        except KeyboardInterrupt:
            print("\n跳过清理空目录")
    
    print("日志清理脚本执行完毕")

def clean_empty_date_dirs(log_dir):
    """清理空的日期目录"""
    date_pattern = re.compile(r'20\d{2}-\d{2}-\d{2}$')
    cleaned_count = 0
    
    for root, dirs, files in os.walk(log_dir, topdown=False):
        for dir_name in dirs:
            if date_pattern.match(dir_name):
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):  # 目录为空
                        os.rmdir(dir_path)
                        print("已删除空目录: {}".format(dir_path))
                        cleaned_count += 1
                except OSError:
                    pass  # 忽略删除失败的情况
    
    if cleaned_count > 0:
        print("清理了 {} 个空的日期目录".format(cleaned_count))
    else:
        print("未找到需要清理的空目录")

if __name__ == "__main__":
    main()
