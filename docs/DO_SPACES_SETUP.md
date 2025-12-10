# Digital Ocean Spaces 配置指南

## 配置要求

在 `.env` 文件中需要配置以下环境变量：

```bash
# AWS/DO Spaces Settings
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_STORAGE_BUCKET_NAME=your_bucket_name
# 注意: Endpoint 不应包含 bucket 名称
AWS_S3_ENDPOINT_URL=https://region.digitaloceanspaces.com
AWS_S3_REGION_NAME=region  # 例如: syd1, sgp1, nyc3

USE_DO_SPACES=True
```

## 常见错误

### Endpoint URL 配置错误

**错误示例:**
```bash
AWS_S3_ENDPOINT_URL=https://mybucket.syd1.digitaloceanspaces.com  # ❌ 错误
```

**正确示例:**
```bash
AWS_S3_ENDPOINT_URL=https://syd1.digitaloceanspaces.com  # ✅ 正确
```

Endpoint URL 应该只包含区域信息，不应包含 bucket 名称。

## 测试配置

运行测试脚本验证配置是否正确：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行测试脚本
python test_do_spaces.py
```

测试脚本会执行以下操作：
1. 测试连接到 DO Spaces
2. 测试访问指定的 bucket
3. 上传测试文件
4. 下载测试文件
5. 删除测试文件（清理）

如果所有测试通过，你会看到：
```
============================================================
✅ Test suite completed successfully!
============================================================
```

## 在 Django 中使用

项目已配置 `django-storages` 来处理文件上传。当 `USE_DO_SPACES=True` 时，所有通过 Django 的 `FileField` 和 `ImageField` 上传的文件会自动存储到 DO Spaces。

### 上传文件示例

```python
from django.core.files.uploadedfile import SimpleUploadedFile
from students.models import Student

# 上传学生照片
student = Student.objects.get(pk=1)
with open('photo.jpg', 'rb') as f:
    student.photo.save('student_photo.jpg', f, save=True)

# 文件会自动上传到 DO Spaces，可以通过 URL 访问
photo_url = student.photo.url
print(photo_url)  # https://syd1.digitaloceanspaces.com/edupulse/media/students/photos/student_photo.jpg
```

### 获取文件 URL

```python
# 公开访问的文件 URL
student = Student.objects.get(pk=1)
if student.photo:
    public_url = student.photo.url
    print(public_url)
```

## 开发环境 vs 生产环境

- **开发环境**: 设置 `USE_DO_SPACES=False` 使用本地文件存储（`media/` 目录）
- **生产环境**: 设置 `USE_DO_SPACES=True` 使用 DO Spaces 云存储

这样可以在开发时避免不必要的云存储费用，同时在生产环境享受云存储的优势。

## 常见 DO Spaces 区域

- `syd1` - Sydney, Australia
- `sgp1` - Singapore
- `nyc3` - New York, USA
- `sfo3` - San Francisco, USA
- `ams3` - Amsterdam, Netherlands
- `fra1` - Frankfurt, Germany

选择离你的用户最近的区域以获得最佳性能。

## 安全建议

1. **不要将 `.env` 文件提交到版本控制系统**
2. 定期轮换 Access Key 和 Secret Key
3. 只给必要的权限（读写权限，而非完全管理权限）
4. 为不同环境使用不同的 bucket（开发、测试、生产）
5. 启用 bucket 的访问日志以监控使用情况
