#!/bin/bash

# 日志清理脚本
# 用法: ./log_cleaner.sh <目录路径> <保留百分比>
# 例如: ./log_cleaner.sh /path/to/logs 70

set -euo pipefail

# 检查参数
if [ $# -ne 2 ]; then
    echo "用法: $0 <目录路径> <保留百分比>"
    echo "例如: $0 /path/to/logs 70"
    echo "多目录: $0 /path1:/path2:/path3 70"
    exit 1
fi

LOG_DIRS="$1"
KEEP_PERCENT="$2"

# 将冒号分隔的目录转换为数组
IFS=':' read -ra DIR_ARRAY <<< "$LOG_DIRS"

# 验证所有目录存在
for LOG_DIR in "${DIR_ARRAY[@]}"; do
    if [ ! -d "$LOG_DIR" ]; then
        echo "错误: 目录 '$LOG_DIR' 不存在"
        exit 1
    fi
done

# 验证百分比参数
if ! [[ "$KEEP_PERCENT" =~ ^[0-9]+$ ]] || [ "$KEEP_PERCENT" -lt 1 ] || [ "$KEEP_PERCENT" -gt 99 ]; then
    echo "错误: 保留百分比必须是1-99之间的整数"
    exit 1
fi

echo "开始清理 ${#DIR_ARRAY[@]} 个日志目录:"
for LOG_DIR in "${DIR_ARRAY[@]}"; do
    echo "  - $LOG_DIR"
done
echo "保留最新的 $KEEP_PERCENT% 文件"

# 创建临时文件存储文件列表
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# 查找所有目录中的日志文件，按修改时间排序（最新的在前）
for LOG_DIR in "${DIR_ARRAY[@]}"; do
    find "$LOG_DIR" -type f \( \
        -name "*.log" -o \
        -name "log.20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].*.log" -o \
        -name "trace.20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].*.log" -o \
        -name "[0-9]*.log" \
    \) -printf "%T@ %p\n" 2>/dev/null || true
done | sort -nr > "$TEMP_FILE"

# 统计总文件数
TOTAL_FILES=$(wc -l < "$TEMP_FILE")

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo "未找到任何日志文件"
    exit 0
fi

# 计算要保留的文件数量
KEEP_COUNT=$(( TOTAL_FILES * KEEP_PERCENT / 100 ))
DELETE_COUNT=$(( TOTAL_FILES - KEEP_COUNT ))

echo "找到 $TOTAL_FILES 个日志文件"
echo "将保留最新的 $KEEP_COUNT 个文件"
echo "将删除最旧的 $DELETE_COUNT 个文件"

if [ "$DELETE_COUNT" -eq 0 ]; then
    echo "无需删除任何文件"
    exit 0
fi

# 确认删除
echo ""
echo "即将删除的文件（最旧的 $DELETE_COUNT 个）:"
tail -n "$DELETE_COUNT" "$TEMP_FILE" | while read -r timestamp filepath; do
    # 获取文件修改时间
    mod_time=$(date -d "@${timestamp}" '+%Y-%m-%d %H:%M:%S')
    file_size=$(du -h "$filepath" 2>/dev/null | cut -f1 || echo "N/A")
    echo "  $filepath (修改时间: $mod_time, 大小: $file_size)"
done

echo ""
read -p "确认删除这些文件吗? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消删除操作"
    exit 0
fi

# 执行删除
echo "开始删除文件..."
deleted_count=0
deleted_size=0

tail -n "$DELETE_COUNT" "$TEMP_FILE" | while read -r timestamp filepath; do
    if [ -f "$filepath" ]; then
        # 获取文件大小（字节）
        file_size=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null || echo 0)
        
        if rm "$filepath" 2>/dev/null; then
            echo "已删除: $filepath"
            deleted_count=$((deleted_count + 1))
            deleted_size=$((deleted_size + file_size))
        else
            echo "删除失败: $filepath"
        fi
    else
        echo "文件不存在: $filepath"
    fi
done

# 转换字节为人类可读格式
if command -v numfmt >/dev/null 2>&1; then
    readable_size=$(echo "$deleted_size" | numfmt --to=iec-i --suffix=B)
else
    readable_size="${deleted_size} bytes"
fi

echo ""
echo "清理完成!"
echo "删除了 $deleted_count 个文件"
echo "释放了约 $readable_size 的磁盘空间"

# 清理空目录（可选）
echo ""
read -p "是否清理所有目录中的空日期目录? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "清理空目录..."
    for LOG_DIR in "${DIR_ARRAY[@]}"; do
        echo "清理目录: $LOG_DIR"
        find "$LOG_DIR" -type d -empty -name "20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]" -delete 2>/dev/null || true
    done
    echo "空目录清理完成"
fi

echo "日志清理脚本执行完毕"
