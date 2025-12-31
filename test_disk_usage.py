#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

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
        print("Error: %s" % str(e))
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
    return "%.1f%s" % (size_bytes, size_names[i])

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: %s <path>" % sys.argv[0])
        sys.exit(1)
    
    path = sys.argv[1]
    usage_percent, total, used, free = get_disk_usage(path)
    
    if usage_percent is not None:
        print("Path: %s" % path)
        print("Usage: %.1f%%" % usage_percent)
        print("Total: %s" % human_readable_size(total))
        print("Used: %s" % human_readable_size(used))
        print("Free: %s" % human_readable_size(free))
    else:
        print("Failed to get disk usage for: %s" % path)
