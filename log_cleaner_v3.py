#!/usr/bin/env python3
"""
日志清理脚本 v3 - 基于磁盘使用率的智能日志清理工具
支持多目录、安全检查、实时监控
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import re
import shutil

def get_disk_usage(path):
    """获取指定路径所在磁盘的使用率"""
    total, used, free = shutil.disk_usage(path)
    usage_percent = (used / total) * 100
    return usage_percent, total, used, free

def human_readable_size(size_bytes):
    """将字节转换为人类可读的格式"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_names[i]}"

def is_file_in_use(file_path):
    """检查文件是否被进程使用"""
    try:
        subprocess.check_output(['lsof', file_path], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        # lsof不存在，尝试fuser
        try:
            subprocess.check_output(['fuser', file_path], stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

def is_file_recent(file_path, hours=24):
    """检查文件是否在指定小时内修改过"""
    try:
        mtime = Path(file_path).stat().st_mtime
        file_time = datetime.fromtimestamp(mtime)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return file_time > cutoff_time
    except OSError:
        return True  # 保守起见认为是最近的文件

def find_log_files(log_dir):
    """查找所有日志文件"""
    log_patterns = [
        r'.*\.log$',                                    # *.log
        r'.*\.log\.20\d{2}-\d{2}-\d{2}-\d{2}$',        # server.log.2025-12-01-02
        r'.*\.log\.20\d{2}-\d{2}-\d{2}$',              # controller.log.2021-05-16
        r'log\.20\d{2}-\d{2}-\d{2}\.\d+\.log$',        # log.2025-12-24.0.log
        r'trace\.20\d{2}-\d{2}-\d{2}\.\d+\.log$',      # trace.2025-12-03.0.log
        r'\d+\.log$',                                   # 1201838490.log
    ]
    
    log_files = []
    for root, dirs, files in os.walk(log_dir):
        for file in files:
            if any(re.match(pattern, file) for pattern in log_patterns):
                file_path = Path(root) / file
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    log_files.append((mtime, str(file_path)))
    
    # 按修改时间排序，最旧的在前
    log_files.sort()
    return log_files

def main():
    parser = argparse.ArgumentParser(
        description="根据磁盘使用率清理日志文件，当磁盘使用率超过阈值时删除最旧的文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s /var/log 70                    # 单个目录，磁盘使用率到70%%停止
  %(prog)s /var/log:/app/logs 80          # 多个目录，用冒号分隔
  %(prog)s /var/log 70 --dry-run          # 预览模式
  %(prog)s /var/log 70 --auto-confirm     # 自动确认（适合定时任务）

安全特性:
  - 自动跳过最近24小时内修改的文件
  - 检查文件是否被进程使用，避免删除活跃文件
  - 实时监控磁盘使用率，达到阈值立即停止
        """)
    
    parser.add_argument('directories', 
                       help='要清理的日志目录路径，多个目录用冒号分隔')
    parser.add_argument('disk_threshold', type=int, 
                       help='磁盘使用率阈值 (1-99)，当使用率降到此值以下时停止清理')
    parser.add_argument('--dry-run', action='store_true', 
                       help='预览模式，只显示将要删除的文件，不实际删除')
    parser.add_argument('--auto-confirm', action='store_true', 
                       help='自动确认删除，不询问用户（适合定时任务）')
    
    args = parser.parse_args()
    
    # 验证阈值
    if not 1 <= args.disk_threshold <= 99:
        print("错误: 磁盘使用率阈值必须在 1-99 之间")
        sys.exit(1)
    
    # 解析目录路径
    log_dirs = [d.strip() for d in args.directories.split(':') if d.strip()]
    
    # 验证目录存在
    for log_dir in log_dirs:
        if not Path(log_dir).exists():
            print(f"错误: 目录不存在: {log_dir}")
            sys.exit(1)
    
    print(f"开始分析 {len(log_dirs)} 个日志目录:")
    for log_dir in log_dirs:
        print(f"  - {log_dir}")
    print(f"磁盘使用率阈值: {args.disk_threshold}%")
    
    # 检查每个目录的磁盘使用率
    need_cleanup = False
    disk_info = {}
    
    for log_dir in log_dirs:
        usage_percent, total, used, free = get_disk_usage(log_dir)
        disk_info[log_dir] = {
            'usage': usage_percent,
            'total': total,
            'used': used,
            'free': free
        }
        
        print(f"  {log_dir}: 磁盘使用率 {usage_percent:.1f}% "
              f"(总计: {human_readable_size(total)}, "
              f"已用: {human_readable_size(used)}, "
              f"可用: {human_readable_size(free)})")
        
        if usage_percent > args.disk_threshold:
            need_cleanup = True
    
    if not need_cleanup:
        print(f"\n所有目录的磁盘使用率都低于阈值 {args.disk_threshold}%，无需清理")
        return
    
    print("\n发现磁盘使用率超过阈值的目录，开始清理...")
    
    # 收集所有日志文件
    all_log_files = []
    for log_dir in log_dirs:
        log_files = find_log_files(log_dir)
        all_log_files.extend(log_files)
        print(f"  {log_dir}: 找到 {len(log_files)} 个文件")
    
    # 重新按时间排序所有文件，最旧的在前
    all_log_files.sort()
    
    if not all_log_files:
        print("所有目录中均未找到任何日志文件")
        return
    
    print(f"\n总计找到 {len(all_log_files)} 个日志文件")
    print(f"\n开始删除最旧的文件，直到磁盘使用率降到 {args.disk_threshold}% 以下...")
    
    if args.dry_run:
        print("\n[DRY RUN] 预览将要删除的文件:")
    
    # 从最旧的文件开始删除
    deleted_count = 0
    deleted_size = 0
    failed_files = []
    skipped_files = []
    
    for mtime, filepath in all_log_files:
        # 安全检查1: 检查文件是否在最近24小时内修改
        if is_file_recent(filepath, 24):
            skipped_files.append((filepath, "最近24小时内的文件"))
            continue
            
        # 安全检查2: 检查文件是否被进程使用
        if is_file_in_use(filepath):
            skipped_files.append((filepath, "文件正在被进程使用"))
            continue
        
        # 检查当前磁盘使用率
        current_usage = None
        for log_dir in log_dirs:
            if filepath.startswith(log_dir):
                usage_percent, _, _, _ = get_disk_usage(log_dir)
                if usage_percent <= args.disk_threshold:
                    current_usage = usage_percent
                    break
        
        if current_usage is not None:
            print(f"\n磁盘使用率已降到 {current_usage:.1f}%，达到阈值 {args.disk_threshold}%，停止清理")
            break
        
        # 获取文件信息
        try:
            file_size = Path(filepath).stat().st_size
            file_mtime = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            if args.dry_run:
                print(f"  {filepath} (修改时间: {file_mtime}, 大小: {human_readable_size(file_size)})")
            else:
                print(f"删除: {filepath} (大小: {human_readable_size(file_size)})")
            
            deleted_size += file_size
            deleted_count += 1
            
            # 实际删除文件
            if not args.dry_run:
                try:
                    Path(filepath).unlink()
                except FileNotFoundError:
                    print(f"文件不存在: {filepath}")
                except OSError as e:
                    print(f"删除失败: {filepath} ({e})")
                    failed_files.append(filepath)
                    
        except OSError as e:
            print(f"获取文件信息失败: {filepath} ({e})")
    
    print("\n清理完成!")
    if args.dry_run:
        print(f"[DRY RUN] 预计删除 {deleted_count} 个文件")
        print(f"[DRY RUN] 预计释放 {human_readable_size(deleted_size)} 的磁盘空间")
    else:
        print(f"成功删除了 {deleted_count} 个文件")
        print(f"释放了 {human_readable_size(deleted_size)} 的磁盘空间")
        
        if failed_files:
            print(f"删除失败的文件数: {len(failed_files)}")
    
    # 显示跳过的文件
    if skipped_files:
        print(f"\n跳过的文件 ({len(skipped_files)} 个):")
        for filepath, reason in skipped_files:
            print(f"  {Path(filepath).name} - {reason}")
    
    # 显示最终磁盘使用率
    print("\n最终磁盘使用率:")
    for log_dir in log_dirs:
        usage_percent, total, used, free = get_disk_usage(log_dir)
        print(f"  {log_dir}: {usage_percent:.1f}%")
    
    print("日志清理脚本执行完毕")

if __name__ == "__main__":
    main()
