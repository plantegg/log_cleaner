# 日志清理脚本使用说明

## 概述

基于对你的服务器日志目录结构分析，我创建了两个版本的日志清理脚本：
- `log_cleaner.sh` - Bash版本
- `log_cleaner.py` - Python版本（推荐）

## 支持的日志文件类型

脚本会自动识别以下类型的日志文件：

1. **通用日志文件**: `*.log`
2. **按日期命名的日志**: `log.2025-12-24.0.log`, `log.2025-12-25.1.log`
3. **trace日志**: `trace.2025-12-03.0.log`, `trace.2025-12-11.0.log`
4. **数字ID日志**: `1201838490.log`, `1201838524.log`
5. **日期目录下的日志**: `2025-12-27/1201838490.log`

## 使用方法

### Python版本（推荐）

```bash
# 单个目录：保留70%的最新文件，删除30%的最旧文件
./log_cleaner.py /path/to/logs 70

# 多个目录：用冒号分隔多个目录路径
./log_cleaner.py /path/to/logs:/path2/logs:/path3/logs 70

# 预览模式：只显示将要删除的文件，不实际删除
./log_cleaner.py /path/to/logs:/path2/logs 70 --dry-run

# 自动确认模式：不询问用户确认，直接删除
./log_cleaner.py /path/to/logs:/path2/logs:/path3/logs 70 --auto-confirm

# 查看帮助
./log_cleaner.py --help
```

### Bash版本

```bash
# 单个目录
./log_cleaner.sh /path/to/logs 70

# 多个目录
./log_cleaner.sh /path/to/logs:/path2/logs:/path3/logs 70
```

## 参数说明

- **目录路径**: 要清理的日志目录路径
  - 单个目录：`/path/to/logs`
  - 多个目录：`/path/to/logs:/path2/logs:/path3/logs` （用冒号分隔）
- **保留百分比**: 要保留的文件百分比（1-99）
  - 70 表示保留最新的70%文件，删除最旧的30%
  - 90 表示保留最新的90%文件，删除最旧的10%

## 工作原理

1. **目录解析**: 解析冒号分隔的多个目录路径
2. **文件发现**: 递归扫描所有指定目录，找到所有匹配的日志文件
3. **全局排序**: 将所有目录中的文件按最后修改时间统一排序（最新的在前）
4. **计算删除数量**: 根据保留百分比计算要删除的文件数量
5. **用户确认**: 显示将要删除的文件列表，等待用户确认
6. **执行删除**: 删除最旧的文件
7. **清理空目录**: 可选择清理所有目录中的空日期目录

## 安全特性

- **预览模式**: 使用 `--dry-run` 可以预览将要删除的文件
- **用户确认**: 默认会显示删除列表并要求用户确认
- **详细信息**: 显示每个文件的修改时间和大小
- **错误处理**: 妥善处理文件不存在或权限不足的情况

## 使用示例

### 示例1：清理多个应用日志目录，保留最新80%

```bash
./log_cleaner.py /app/logs:/app2/logs:/app3/logs 80
```

输出示例：
```
开始分析 3 个日志目录:
  - /app/logs
  - /app2/logs  
  - /app3/logs
保留最新的 80% 文件
  /app/logs: 找到 500 个文件
  /app2/logs: 找到 300 个文件
  /app3/logs: 找到 200 个文件

总计找到 1000 个日志文件
将保留最新的 800 个文件
将删除最旧的 200 个文件

即将删除的文件（最旧的 200 个）:
  /app/logs/2025-12-01/1201234567.log
    修改时间: 2025-12-01 10:30:15, 大小: 2.3MB
  ...

总计将释放约 450.2MB 的磁盘空间

确认删除这些文件吗? (y/N):
```

### 示例2：预览多目录清理

```bash
./log_cleaner.py /var/log/app1:/var/log/app2:/home/user/logs 70 --dry-run
```

这会显示将要删除的文件，但不实际删除。

### 示例3：自动化脚本中使用多目录

```bash
./log_cleaner.py /app/logs:/nginx/logs:/system/logs 80 --auto-confirm
```

适合在定时任务中使用，不需要人工确认。

## 定时清理

可以将脚本加入crontab实现定时清理：

```bash
# 编辑crontab
crontab -e

# 每天凌晨2点清理多个目录的日志，保留最新70%
0 2 * * * /path/to/log_cleaner.py /app/logs:/nginx/logs:/system/logs 70 --auto-confirm >> /var/log/log_cleaner.log 2>&1
```

## 注意事项

1. **备份重要日志**: 清理前请确保重要日志已备份
2. **测试环境**: 建议先在测试环境验证脚本行为
3. **权限检查**: 确保脚本有删除目标文件的权限
4. **磁盘空间**: 清理过程中可能需要额外的临时空间
5. **并发访问**: 避免在应用正在写入日志时进行清理

## 故障排除

### 权限不足
```bash
chmod +x log_cleaner.py
sudo ./log_cleaner.py /var/log/app 70
```

### Python版本要求
脚本需要Python 3.6+，检查版本：
```bash
python3 --version
```

### 查看详细错误
使用Python版本可以看到更详细的错误信息。
