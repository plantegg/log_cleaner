# 日志清理脚本

基于磁盘使用率的智能日志清理工具，支持多目录、安全检查、实时监控。

## 快速使用

```bash
# 单个目录，磁盘使用率到70%停止清理
./log_cleaner_v3.py /path/to/logs 70

# 多个目录，用冒号分隔
./log_cleaner_v3.py /path1:/path2:/path3 80

# 预览模式（推荐先试用）
./log_cleaner_v3.py /path1:/path2 70 --dry-run

# 自动确认（适合定时任务）
./log_cleaner_v3.py /path1:/path2 70 --auto-confirm
```

## 工作原理

1. **检查磁盘使用率**: 检查所有指定目录的磁盘使用率
2. **判断是否需要清理**: 如果使用率超过阈值才开始清理
3. **安全检查**: 
   - 跳过最近24小时内修改的文件
   - 跳过正在被进程使用的文件（使用lsof/fuser检查）
4. **按时间删除**: 从最旧的文件开始删除
5. **实时监控**: 删除过程中实时检查磁盘使用率
6. **达到阈值停止**: 磁盘使用率降到阈值以下时停止

## 参数说明

- **目录路径**: 单个目录或用冒号分隔的多个目录
- **磁盘使用率阈值**: 1-99之间的整数
  - 70 = 磁盘使用率降到70%时停止清理
  - 80 = 磁盘使用率降到80%时停止清理

## 版本说明

- `log_cleaner_v3.py` - **最新版本**（Python 3专用，推荐使用）
- `log_cleaner_v2.py` - Python 2/3兼容版本
- `log_cleaner.sh` - Bash版本

## 支持的日志文件

- `*.log` - 通用日志文件
- `log.2025-12-24.0.log` - 按日期命名的日志
- `trace.2025-12-03.0.log` - trace日志
- `1201838490.log` - 数字ID日志
- `server.log.2025-12-01-02` - 服务器日志（带时间后缀）
- `controller.log.2021-05-16` - 控制器日志
- `2025-12-27/1201838490.log` - 日期目录下的日志

## 定时清理

```bash
# 每天凌晨2点清理，磁盘使用率到70%停止
0 2 * * * /path/to/log_cleaner_v3.py /app/logs:/nginx/logs 70 --auto-confirm
```

## 安全特性

- **24小时保护**: 自动跳过最近24小时内修改的文件
- **进程检查**: 使用lsof/fuser检查文件是否被进程使用，避免删除正在使用的文件
- **预览模式**: --dry-run避免误删
- **详细报告**: 显示删除和跳过的文件信息
- **实时监控**: 删除过程中实时检查磁盘使用率

## 系统要求

- Python 3.6+
- Linux/Unix系统
- lsof或fuser命令（用于检查文件使用情况）

## 使用示例

### 基本使用
```bash
# 清理单个目录
./log_cleaner_v3.py /var/log 80

# 清理多个目录
./log_cleaner_v3.py /var/log:/app/logs:/nginx/logs 75
```

### 安全预览
```bash
# 先预览要删除的文件
./log_cleaner_v3.py /var/log 70 --dry-run

# 确认无误后实际执行
./log_cleaner_v3.py /var/log 70
```

### 定时任务
```bash
# 添加到crontab
crontab -e

# 每天凌晨2点自动清理
0 2 * * * /usr/local/bin/log_cleaner_v3.py /var/log:/app/logs 70 --auto-confirm >> /var/log/log_cleaner.log 2>&1
```

## 输出示例

```
开始分析 2 个日志目录:
  - /var/log
  - /app/logs
磁盘使用率阈值: 70%
  /var/log: 磁盘使用率 85.2% (总计: 100.0GB, 已用: 85.2GB, 可用: 14.8GB)
  /app/logs: 磁盘使用率 85.2% (总计: 100.0GB, 已用: 85.2GB, 可用: 14.8GB)

发现磁盘使用率超过阈值的目录，开始清理...
  /var/log: 找到 1247 个文件
  /app/logs: 找到 523 个文件

总计找到 1770 个日志文件

开始删除最旧的文件，直到磁盘使用率降到 70% 以下...

删除: /var/log/old.log.2021-01-15 (大小: 15.2MB)
删除: /app/logs/trace.2021-02-10.0.log (大小: 8.7MB)

磁盘使用率已降到 69.8%，达到阈值 70%，停止清理

清理完成!
成功删除了 156 个文件
释放了 2.3GB 的磁盘空间

跳过的文件 (12 个):
  current.log - 最近24小时内的文件
  active.log - 文件正在被进程使用

最终磁盘使用率:
  /var/log: 69.8%
  /app/logs: 69.8%
日志清理脚本执行完毕
```
