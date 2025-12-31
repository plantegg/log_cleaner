#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志清理脚本
根据磁盘使用率清理指定目录下的日志文件，当磁盘使用率超过阈值时删除最旧的文件
"""

import os
import sys
import glob
import argparse
from datetime import datetime, timedelta
import re
import shutil
import subprocess

def is_file_in_use(file_path):
    """检查文件是否被进程使用"""
    try:
        # 使用lsof检查文件是否被打开
        result = subprocess.check_output(['lsof', file_path], stderr=subprocess.DEVNULL)
        return True  # 如果lsof有输出，说明文件被使用
    except subprocess.CalledProcessError:
        return False  # lsof返回非0状态码，说明文件未被使用
    except OSError:
        # lsof命令不存在，使用fuser作为备选
        try:
            result = subprocess.check_output(['fuser', file_path], stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, OSError):
            return False  # 都失败了，假设文件未被使用

def is_file_recent(file_path, hours=24):
    """检查文件是否在指定小时内修改过"""
    try:
        mtime = os.path.getmtime(file_path)
        file_time = datetime.fromtimestamp(mtime)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return file_time > cutoff_time
    except OSError:
        return True  # 如果无法获取时间，保守起见认为是最近的文件

def get_disk_usage(path):
    """获取指定路径所在磁盘的使用率"""
    try:
        # 先尝试 Python 3.3+ 的方法
        if hasattr(shutil, 'disk_usage'):
            total, used, free = shutil.disk_usage(path)
            usage_percent = (used / total) * 100
            return usage_percent, total, used, free
    except:
        pass
    
    # Python 2 或 shutil.disk_usage 失败时的 fallback
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - (st.f_bfree * st.f_frsize)
        # 强制浮点数除法，兼容Python 2
        usage_percent = (float(used) / float(total)) * 100
        return usage_percent, total, used, free
    except Exception as e:
        return None, 0, 0, 0

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
                re.match(r'.*\.log\.20\d{2}-\d{2}-\d{2}-\d{2}$', file) or  # server.log.2025-12-01-02
                re.match(r'.*\.log\.20\d{2}-\d{2}-\d{2}$', file) or        # controller.log.2021-05-16
                re.match(r'log\.20\d{2}-\d{2}-\d{2}\.\d+\.log$', file) or  # log.2025-12-24.0.log
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
    
    # 按修改时间排序，最旧的在前
    log_files.sort()
    return log_files

def main():
    parser = argparse.ArgumentParser(
        description="根据磁盘使用率清理日志文件，当磁盘使用率超过阈值时删除最旧的文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s /path/to/logs 70                           # 单个目录，磁盘使用率到70%%停止
  %(prog)s /path/to/logs:/path2/logs:/path3/logs 80   # 多个目录，磁盘使用率到80%%停止
        """
    )
    
    parser.add_argument("log_dirs", help="日志文件目录路径，多个目录用冒号(:)分隔")
    parser.add_argument("disk_threshold", type=int, 
                       help="磁盘使用率阈值 (1-99)，达到此使用率时停止清理")
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
    
    if not (1 <= args.disk_threshold <= 99):
        print("错误: 磁盘使用率阈值必须是1-99之间的整数")
        sys.exit(1)
    
    print("开始分析 {} 个日志目录:".format(len(log_dirs)))
    for log_dir in log_dirs:
        print("  - {}".format(log_dir))
    print("磁盘使用率阈值: {}%".format(args.disk_threshold))
    
    # 检查每个目录的磁盘使用率
    need_cleanup = False
    disk_info = {}
    
    for log_dir in log_dirs:
        usage_percent, total, used, free = get_disk_usage(log_dir)
        if usage_percent is None:
            print("警告: 无法获取目录 {} 的磁盘使用率".format(log_dir))
            continue
            
        disk_info[log_dir] = {
            'usage': usage_percent,
            'total': total,
            'used': used,
            'free': free
        }
        
        print("  {}: 磁盘使用率 {:.1f}% (总计: {}, 已用: {}, 可用: {})".format(
            log_dir, usage_percent, 
            human_readable_size(total),
            human_readable_size(used),
            human_readable_size(free)
        ))
        
        if usage_percent > args.disk_threshold:
            need_cleanup = True
    
    if not need_cleanup:
        print("\n所有目录的磁盘使用率都低于阈值 {}%，无需清理".format(args.disk_threshold))
        sys.exit(0)
    
    print("\n发现磁盘使用率超过阈值的目录，开始清理...")
    
    # 查找所有目录中的日志文件
    all_log_files = []
    for log_dir in log_dirs:
        log_files = find_log_files(log_dir)
        all_log_files.extend(log_files)
        print("  {}: 找到 {} 个文件".format(log_dir, len(log_files)))
    
    # 重新按时间排序所有文件，最旧的在前
    all_log_files.sort()
    log_files = all_log_files
    
    if not log_files:
        print("所有目录中均未找到任何日志文件")
        sys.exit(0)
    
    total_files = len(log_files)
    print("\n总计找到 {} 个日志文件".format(total_files))
    
    # 逐个删除最旧的文件，直到磁盘使用率降到阈值以下
    deleted_count = 0
    deleted_size = 0
    failed_files = []
    
    print("\n开始删除最旧的文件，直到磁盘使用率降到 {}% 以下...".format(args.disk_threshold))
    
    if args.dry_run:
        print("\n[DRY RUN] 预览将要删除的文件:")
    
    # 从最旧的文件开始删除
    skipped_files = []
    for mtime, filepath in reversed(log_files):
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
                if usage_percent is not None and usage_percent <= args.disk_threshold:
                    current_usage = usage_percent
                    break
        
        if current_usage is not None and current_usage <= args.disk_threshold:
            print("\n磁盘使用率已降到 {:.1f}%，达到阈值 {}%，停止清理".format(
                current_usage, args.disk_threshold))
            break
        
        try:
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                if args.dry_run:
                    print("  {} (修改时间: {}, 大小: {})".format(
                        filepath, mod_time, human_readable_size(file_size)))
                    deleted_count += 1
                    deleted_size += file_size
                else:
                    # 确认删除
                    if not args.auto_confirm and deleted_count == 0:
                        try:
                            confirm = input("\n开始删除文件，确认继续? (y/N): ").strip().lower()
                            if confirm not in ['y', 'yes']:
                                print("取消删除操作")
                                sys.exit(0)
                        except KeyboardInterrupt:
                            print("\n\n操作被用户取消")
                            sys.exit(0)
                    
                    os.remove(filepath)
                    print("已删除: {} (大小: {})".format(filepath, human_readable_size(file_size)))
                    deleted_count += 1
                    deleted_size += file_size
            else:
                if not args.dry_run:
                    print("文件不存在: {}".format(filepath))
        except OSError as e:
            print("删除失败: {} ({})".format(filepath, e))
            failed_files.append(filepath)
    
    print("\n清理完成!")
    if args.dry_run:
        print("[DRY RUN] 预计删除 {} 个文件".format(deleted_count))
        print("[DRY RUN] 预计释放 {} 的磁盘空间".format(human_readable_size(deleted_size)))
    else:
        print("成功删除了 {} 个文件".format(deleted_count))
        print("释放了 {} 的磁盘空间".format(human_readable_size(deleted_size)))
        
        if failed_files:
            print("删除失败的文件数: {}".format(len(failed_files)))
    
    # 显示跳过的文件
    if skipped_files:
        print("\n跳过的文件 ({} 个):".format(len(skipped_files)))
        for filepath, reason in skipped_files:
            print("  {} - {}".format(os.path.basename(filepath), reason))
    
    # 显示最终磁盘使用率
    print("\n最终磁盘使用率:")
    for log_dir in log_dirs:
        usage_percent, total, used, free = get_disk_usage(log_dir)
        if usage_percent is not None:
            print("  {}: {:.1f}%".format(log_dir, usage_percent))
    
    # 清理空的日期目录
    if not args.dry_run and not args.auto_confirm:
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
