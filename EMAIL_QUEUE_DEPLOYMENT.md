# 邮件队列系统部署指南

## 概述

本文档描述了 EduPulse 邮件队列系统的部署配置，包括当前的批量邮件优化方案以及未来的异步队列系统升级路径。

## 第一阶段：批量邮件优化（当前实现）

### 功能特性

- **分批发送**：默认每批 20 封邮件，批次间间隔 0.5 秒
- **连接复用**：使用 SMTP 连接池，减少连接开销
- **错误处理**：增强的错误处理和重试逻辑
- **配额管理**：与现有配额系统集成
- **日志记录**：详细的发送日志和统计

### 配置要求

#### 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 邮件超时设置（秒）
EMAIL_TIMEOUT=60

# 批量邮件设置
BULK_EMAIL_BATCH_SIZE=20
BULK_EMAIL_BATCH_DELAY=0.5

# 现有SMTP配置保持不变
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### Django 设置

新增的 `settings.py` 配置已自动包含：

```python
# Email performance and reliability settings
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '60'))
BULK_EMAIL_BATCH_SIZE = int(os.getenv('BULK_EMAIL_BATCH_SIZE', '20'))
BULK_EMAIL_BATCH_DELAY = float(os.getenv('BULK_EMAIL_BATCH_DELAY', '0.5'))
```

### 部署步骤

#### 开发环境（macOS）

1. **无需额外安装**：当前优化使用现有 Django 组件
2. **配置环境变量**：更新 `.env` 文件
3. **重启开发服务器**：`python manage.py runserver`

#### 生产环境（Ubuntu 24.04）

1. **更新环境变量**：
   ```bash
   sudo nano /etc/environment
   # 或在应用的 .env 文件中添加配置
   ```

2. **重启 Gunicorn**：
   ```bash
   sudo systemctl reload gunicorn
   ```

3. **验证配置**：
   ```bash
   sudo journalctl -u gunicorn -f
   ```

## 第二阶段：异步队列系统（未来升级）

### Redis + django-rq 方案

当批量邮件数量超过 100 封时，建议升级到异步队列系统。

#### 开发环境配置（macOS）

##### 1. 安装 Redis

```bash
# 使用 Homebrew 安装
brew install redis

# 启动 Redis 服务
brew services start redis

# 验证安装
redis-cli ping
# 应返回: PONG
```

##### 2. 安装 Python 依赖

```bash
# 在项目根目录执行
pip install django-rq redis

# 更新 requirements.txt
echo "django-rq==2.10.2" >> requirements.txt
echo "redis==5.0.1" >> requirements.txt
```

##### 3. Django 配置

在 `settings.py` 中添加：

```python
# Redis 和 RQ 配置
import os

INSTALLED_APPS += [
    'django_rq',
]

# Redis 配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# Django-RQ 配置
RQ_QUEUES = {
    'default': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': REDIS_DB,
        'DEFAULT_TIMEOUT': 360,
    },
    'email': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': REDIS_DB,
        'DEFAULT_TIMEOUT': 600,  # 10分钟超时
    }
}
```

##### 4. URL 配置

在主 `urls.py` 中添加：

```python
urlpatterns = [
    # 其他 URL 配置...
    path('django-rq/', include('django_rq.urls')),
]
```

##### 5. 启动队列工作进程

```bash
# 在项目根目录，新终端窗口执行
python manage.py rqworker email

# 或启动默认队列
python manage.py rqworker default
```

#### 生产环境配置（Ubuntu 24.04）

##### 1. 安装 Redis

```bash
# 更新包管理器
sudo apt update

# 安装 Redis
sudo apt install redis-server -y

# 配置 Redis
sudo nano /etc/redis/redis.conf
# 确保以下设置：
# bind 127.0.0.1
# port 6379
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# 启动并启用 Redis 服务
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 验证安装
redis-cli ping
```

##### 2. 安装 Python 依赖

```bash
# 在项目目录执行
source venv/bin/activate  # 激活虚拟环境
pip install django-rq redis
```

##### 3. 配置环境变量

```bash
# 在 .env 文件中添加
echo "REDIS_HOST=localhost" >> .env
echo "REDIS_PORT=6379" >> .env
echo "REDIS_DB=0" >> .env
```

##### 4. 创建系统服务

创建 RQ Worker 服务：

```bash
sudo nano /etc/systemd/system/edupulse-rqworker.service
```

服务文件内容：

```ini
[Unit]
Description=EduPulse RQ Worker
After=network.target redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/edupulse
Environment=DJANGO_SETTINGS_MODULE=edupulse.settings
ExecStart=/path/to/edupulse/venv/bin/python manage.py rqworker email
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start edupulse-rqworker
sudo systemctl enable edupulse-rqworker
```

##### 5. 配置 Nginx（可选监控）

为 Django-RQ 管理界面配置反向代理：

```nginx
location /django-rq/ {
    proxy_pass http://127.0.0.1:8000/django-rq/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Celery 方案（大规模部署）

当需要处理 200+ 封邮件或需要更高级功能时使用。

#### 开发环境配置（macOS）

##### 1. 安装依赖

```bash
# 安装 Celery 和消息代理
brew install redis
pip install celery[redis] django-celery-beat django-celery-results

# 或使用 RabbitMQ
# brew install rabbitmq
# pip install celery[librabbitmq]
```

##### 2. Django 配置

```python
# settings.py
import os

INSTALLED_APPS += [
    'django_celery_beat',
    'django_celery_results',
]

# Celery 配置
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Australia/Perth'

# 邮件队列配置
CELERY_TASK_ROUTES = {
    'core.tasks.send_bulk_emails': {'queue': 'email'},
    'core.tasks.send_single_email': {'queue': 'email'},
}

CELERY_TASK_ANNOTATIONS = {
    'core.tasks.send_bulk_emails': {'rate_limit': '10/m'},
}
```

##### 3. 创建 Celery 应用

创建 `edupulse/celery.py`：

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')

app = Celery('edupulse')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

在 `edupulse/__init__.py` 中：

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

##### 4. 启动 Celery

```bash
# 启动 worker
celery -A edupulse worker -l info

# 启动 beat (定时任务)
celery -A edupulse beat -l info

# 启动 flower (监控界面)
celery -A edupulse flower
```

#### 生产环境配置（Ubuntu 24.04）

##### 1. 系统依赖安装

```bash
# 安装 Redis（如上）或 RabbitMQ
sudo apt install rabbitmq-server -y
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Python 依赖
pip install celery[redis] django-celery-beat django-celery-results
```

##### 2. 创建系统服务

Celery Worker 服务：

```bash
sudo nano /etc/systemd/system/edupulse-celery.service
```

```ini
[Unit]
Description=EduPulse Celery Worker
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
EnvironmentFile=/path/to/edupulse/.env
WorkingDirectory=/path/to/edupulse
ExecStart=/path/to/edupulse/venv/bin/celery -A edupulse worker -l info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Celery Beat 服务：

```bash
sudo nano /etc/systemd/system/edupulse-celerybeat.service
```

```ini
[Unit]
Description=EduPulse Celery Beat
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
EnvironmentFile=/path/to/edupulse/.env
WorkingDirectory=/path/to/edupulse
ExecStart=/path/to/edupulse/venv/bin/celery -A edupulse beat -l info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start edupulse-celery
sudo systemctl start edupulse-celerybeat
sudo systemctl enable edupulse-celery
sudo systemctl enable edupulse-celerybeat
```

## 监控和维护

### 日志监控

```bash
# 查看邮件发送日志
sudo journalctl -u gunicorn -f | grep -i "batch email"

# 查看 RQ Worker 日志
sudo journalctl -u edupulse-rqworker -f

# 查看 Celery 日志
sudo journalctl -u edupulse-celery -f
```

### 性能监控

#### Django-RQ 监控

访问 `https://edupulse.perthartschool.com.au/django-rq/` 查看：
- 队列状态
- 任务执行情况
- 失败任务重试

#### Celery 监控

```bash
# 安装 Flower
pip install flower

# 启动监控界面
celery -A edupulse flower --port=5555
```

### 故障排除

#### 常见问题

1. **Redis 连接失败**
   ```bash
   # 检查 Redis 状态
   sudo systemctl status redis-server
   redis-cli ping
   ```

2. **邮件发送超时**
   - 检查 SMTP 服务器配置
   - 调整 EMAIL_TIMEOUT 设置
   - 检查网络连接

3. **队列积压**
   - 增加 Worker 进程数量
   - 调整批次大小
   - 检查 SMTP 服务器限制

#### 日志分析

```bash
# 统计邮件发送成功率
grep "batch email" /var/log/gunicorn/access.log | grep -c "sent"
grep "batch email" /var/log/gunicorn/error.log | grep -c "failed"

# 查看队列任务状态
redis-cli -c
> LLEN rq:queue:email
> LRANGE rq:queue:email 0 -1
```

## 升级路径建议

### 当前 → django-rq （推荐）

**触发条件**：单次批量邮件 > 50 封

**升级步骤**：
1. 安装 Redis 和 django-rq
2. 创建异步任务函数
3. 更新批量发送视图
4. 配置系统服务
5. 测试验证

### django-rq → Celery

**触发条件**：
- 单次批量邮件 > 200 封
- 需要复杂的任务调度
- 需要分布式处理

**升级步骤**：
1. 安装 Celery 和相关组件
2. 配置消息代理
3. 迁移任务定义
4. 配置系统服务
5. 性能调优

## 安全考虑

### 邮件安全

1. **使用应用密码**：Gmail 等服务使用应用专用密码
2. **TLS 加密**：确保 EMAIL_USE_TLS = True
3. **敏感信息保护**：邮件模板中避免包含敏感数据

### 队列安全

1. **Redis 访问控制**：
   ```bash
   # 在 redis.conf 中设置密码
   requirepass your-strong-password
   ```

2. **网络隔离**：Redis 仅监听本地接口

3. **定期清理**：设置任务结果过期时间

## 备份和恢复

### Redis 数据备份

```bash
# 创建备份脚本
#!/bin/bash
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/redis/dump-$(date +%Y%m%d).rdb
```

### 队列任务恢复

队列任务失败后的恢复步骤：

1. 检查失败任务日志
2. 修复问题（SMTP 配置、网络等）
3. 重新启动 Worker 服务
4. 手动重试失败任务（如需要）

## 性能调优

### 批量邮件优化

```python
# 调整批次大小和延迟
BULK_EMAIL_BATCH_SIZE = 50  # 增加批次大小
BULK_EMAIL_BATCH_DELAY = 0.1  # 减少延迟

# SMTP 连接池配置
EMAIL_TIMEOUT = 30  # 减少超时时间
EMAIL_USE_LOCALTIME = True
```

### Redis 优化

```bash
# redis.conf 优化设置
maxmemory 512mb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
```

### 系统资源

```bash
# 监控内存使用
free -h
htop

# 监控磁盘空间
df -h
du -h /var/log/
```

---

**更新日期**：2025-09-18
**版本**：1.0
**维护者**：EduPulse 开发团队