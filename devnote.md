# EduPulse 开发备注

## 技术架构更新 (2025-08-24)

### 核心技术栈变更：
- **Django 版本**: 升级至 Django 5.x（最新版本）
- **虚拟环境**: 使用 `.venv` 目录
- **环境配置**: 采用 `.env` 文件 + `python-dotenv`
- **邮件服务**: 从 Mailgun 改为 Amazon SES
- **生产部署**: Ubuntu Server + Nginx + Gunicorn

### 架构简化：
- **移除组织模块**: 非多租户架构，直接使用设施-教室管理
- **单一学校结构**: 专为 Perth Art School 定制

### 关键决定：
1. 使用最新 Django 5.x 版本获得最佳性能和安全性
2. Amazon SES 提供更稳定的邮件发送服务
3. 简化数据模型，移除不必要的组织层级

## 项目进度 (2025-08-24)

### 已完成的任务：
1. ✅ 创建项目实施计划文档 (plans.md)
2. ✅ 更新技术架构配置
3. ✅ 初始化 Django 项目结构
4. ✅ 设计和实现数据库模型
5. ✅ 配置前端框架 (Bootstrap + jQuery + 自定义主题)

### 当前状态：
- Django 5.2.5 成功安装和配置
- 数据库迁移完成，包含所有核心模型
- 管理后台界面配置完成
- 基础模板系统和样式配置完成
- 认证系统和权限控制实现
- 核心视图类和URL路由配置

### 数据模型设计：
- **Staff**: 扩展用户模型，支持管理员和教师角色
- **Facility**: 设施管理
- **Classroom**: 教室管理
- **Student**: 学生信息，包含监护人信息
- **Course**: 课程管理，支持单次和重复模式
- **Class**: 班级实例，支持动态调整
- **Enrollment**: 报名管理，支持多种来源
- **Attendance**: 考勤记录
- **ClockInOut**: 员工打卡，支持GPS定位
- **EmailLog/SMSLog**: 通信日志

### 技术特色：
1. **响应式设计**: 使用 Bootstrap 5 + 自定义主题色彩
2. **权限控制**: 基于角色的访问控制
3. **数据完整性**: 完善的外键关系和约束
4. **审计功能**: 创建/更新时间自动记录
5. **国际化**: 中文界面和澳洲时区配置

## 下一步计划：
1. 完成核心模块的前端模板
2. 实现报名流程和在线表单
3. 集成邮件和短信服务
4. WooCommerce API 对接
5. 生产环境部署配置

## 开发命令：
```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动开发服务器
python manage.py runserver

# 创建超级用户
python manage.py createsuperuser

# 数据库迁移
python manage.py makemigrations
python manage.py migrate
```

## 课程排课逻辑调整 (2025-12-04)

- 新建课程时，`repeat_pattern` 仅暴露 `once` 和 `weekly` 两种最常用选项，暂时隐藏 `daily` / `monthly`。
- 在课程编辑页，可以勾选 “Apply Changes to Existing Classes”，
  - 同步教师、时间、时长、教室等变更到选中的未来 Class；
  - 对于 `repeat_pattern == 'weekly'` 且 weekday 发生变化的课程：
    - 自动将选中的、未开始的 Class 日期**向后**移动到最近一次目标 weekday（不会早于原始日期）；
    - 如有 Class 被移动到 `end_date` 之后，会在前端给管理员提示。
- 现有 `repeat_pattern` 为 daily/monthly 的课程仍然保留原有行为，但不鼓励新建。


## 批量通知进度缓存调整 (2025-12-09)

- 为 `BulkNotificationProgress` 配置统一的 Redis 缓存：
  - 新增逻辑：如果没有显式的 `REDIS_CACHE_URL`/`REDIS_URL`，会从 `REDIS_HOST`/`REDIS_PORT`/`REDIS_DB` 自动拼出 `redis://host:port/db`。
  - `CACHES['notifications']` 始终指向 Redis，而不是多进程各自独立的本地内存缓存。
- 目的：确保在 Gunicorn 多 worker 下，Student 列表的批量通知进度轮询始终能读到同一份数据，不再出现前端卡在 “Preparing/Starting...” 但邮件已发送完成的情况。

## Digital Ocean Spaces 配置修复 (2025-12-10)

- 问题: DO Spaces 文件上传和读取失败
- 原因: `.env` 中的 `AWS_S3_ENDPOINT_URL` 配置错误地包含了 bucket 名称
  - 错误格式: `https://edupulse.syd1.digitaloceanspaces.com`
  - 正确格式: `https://syd1.digitaloceanspaces.com`
- 解决方案:
  - 修正 `.env` 文件中的 endpoint URL 配置
  - 在 `settings.py` 中将 `STORAGES['default']` 切换为 `storages.backends.s3boto3.S3Boto3Storage`，确保 `default_storage` 实际写入 DO Spaces（而不是本地 `media/`）
  - 创建 `test_do_spaces.py` 测试脚本，可用于验证 DO Spaces 配置
  - TinyMCE 图片上传使用 `default_storage`，上传的邮件图片将写入 `media/email_images/` 前缀，并通过 `https://syd1.digitaloceanspaces.com/edupulse/media/...` 直接公开访问
- 验证: `core.tests.test_tinymce_upload.TinyMCEUploadTests` 通过，手工 curl 访问 DO URL 返回 200，文件上传和读取功能正常工作


## 开发环境开启 redis 

你需要使用以下命令启动 RQ worker 来处理邮件队列:

```bash
python manage.py rqworker notifications default
```
这个命令会启动一个 Django-RQ worker,监听 `notifications` 和 `default` 两个队列。

**在开发环境中,你可以这样操作:**

1. **在一个终端窗口中启动开发服务器:**
```bash
   source .venv/bin/activate
   python manage.py runserver
```
2. **在另一个终端窗口中启动 RQ worker:**
```bash
   source .venv/bin/activate
   python manage.py rqworker notifications default
```
**注意事项:**
- RQ worker 需要 Redis 服务器正在运行
- 确保你的 `.env` 文件中有正确的 Redis 配置(REDIS_HOST, REDIS_PORT 等)
- worker 会处理异步的邮件发送任务,避免阻塞主进程