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