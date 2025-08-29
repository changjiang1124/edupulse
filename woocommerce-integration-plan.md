# WooCommerce 集成方案文档

## 项目概述

为 Perth Art School 实现 WordPress/WooCommerce 网站与 EduPulse 系统的无缝集成。客户可在熟悉的 WordPress 网站浏览课程信息，通过简化的产品展示页面直接跳转到 EduPulse 进行课程注册，避免标准电商流程和支付网关费用。

## 核心方案：简化产品展示 + 外部链接

### 设计理念
- WooCommerce 产品仅作为课程信息展示
- 移除标准购物流程（购物车、结账等）
- 直接链接到 EduPulse 注册表单
- 银行转账付款流程完全在 EduPulse 处理
- 保持客户现有网站用户体验

## 实施阶段计划

### 第一阶段：WooCommerce 配置修改

#### 1.1 产品类型配置
```php
// 产品配置选项
- 使用 "External/Affiliate Product" 产品类型
- 或创建自定义产品类型，完全移除购买功能
- 隐藏价格显示（价格在 EduPulse 表单中处理）
```

#### 1.2 移除标准电商功能
**需禁用的功能：**
- 购物车页面 (`/cart/`)
- 结账页面 (`/checkout/`)
- 我的账户订单历史
- 库存管理
- 运送设置
- 支付网关

**保留的功能：**
- 产品目录和搜索
- 产品分类和筛选
- 基本产品信息展示
- SEO 和分析功能

#### 1.3 自定义按钮实现
```php
// functions.php 或自定义插件代码示例
// 移除默认购物车按钮
remove_action('woocommerce_after_shop_loop_item', 'woocommerce_template_loop_add_to_cart');
remove_action('woocommerce_single_product_summary', 'woocommerce_template_single_add_to_cart');

// 添加自定义注册按钮
add_action('woocommerce_single_product_summary', 'custom_enrol_button', 30);
function custom_enrol_button() {
    global $product;
    $course_id = get_post_meta($product->get_id(), 'edupulse_course_id', true);
    $enrol_url = 'https://edupulse.perthartschool.com.au/enrol/' . $course_id;
    echo '<a href="' . $enrol_url . '" class="btn btn-primary btn-large">立即报名</a>';
}

// 隐藏价格显示
add_filter('woocommerce_get_price_html', '__return_empty_string');
```

### 第二阶段：EduPulse 同步 API 开发

#### 2.1 需要同步的课程数据
```python
# Django 模型字段映射到 WooCommerce
sync_fields = {
    'name': 'product_title',           # 产品标题
    'short_description': 'excerpt',    # 产品简短描述  
    'description': 'content',          # 产品完整描述
    'featured_image': 'featured_media', # 课程图片
    'category': 'product_cat',         # 课程分类
    'status': 'status',                # 发布状态 (draft/publish)
    'schedule_info': 'meta_schedule',  # 上课时间信息（自定义字段）
}
```

#### 2.2 WordPress REST API 集成
```python
# EduPulse Django 设置
# settings.py
WORDPRESS_API_BASE = 'https://perthartschool.com.au/wp-json/wc/v3/'
WORDPRESS_API_KEY = 'your_consumer_key'
WORDPRESS_API_SECRET = 'your_consumer_secret'

# sync_service.py
import requests
from django.conf import settings

class WooCommerceSync:
    def __init__(self):
        self.api_base = settings.WORDPRESS_API_BASE
        self.auth = (settings.WORDPRESS_API_KEY, settings.WORDPRESS_API_SECRET)
    
    def sync_course_to_woocommerce(self, course):
        """同步单个课程到 WooCommerce"""
        product_data = {
            'name': course.name,
            'description': course.description,
            'short_description': course.short_description,
            'type': 'external',
            'external_url': f'https://edupulse.perthartschool.com.au/enrol/{course.id}',
            'button_text': '立即报名',
            'status': 'publish' if course.is_active else 'draft',
            'meta_data': [
                {'key': 'edupulse_course_id', 'value': str(course.id)},
                {'key': 'schedule_info', 'value': course.schedule_display}
            ]
        }
        
        response = requests.post(
            f'{self.api_base}products',
            json=product_data,
            auth=self.auth
        )
        return response.json()
```

#### 2.3 定时同步任务
```python
# tasks.py (使用 Django Celery)
from celery import shared_task
from .models import Course
from .services import WooCommerceSync

@shared_task
def sync_all_courses():
    """定时同步所有课程到 WooCommerce"""
    sync_service = WooCommerceSync()
    courses = Course.objects.filter(is_active=True)
    
    for course in courses:
        try:
            sync_service.sync_course_to_woocommerce(course)
        except Exception as e:
            # 记录错误日志
            pass

# 在 Django signals 中触发即时同步
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Course)
def sync_course_on_save(sender, instance, **kwargs):
    """课程保存时立即同步到 WooCommerce"""
    if instance.is_active:
        sync_service = WooCommerceSync()
        sync_service.sync_course_to_woocommerce(instance)
```

### 第三阶段：用户流程整合

#### 3.1 注册流程设计
```
用户流程：
WordPress 网站浏览课程 
    ↓ (点击"立即报名"按钮)
重定向到 EduPulse 注册表单
    ↓ (URL: /enrol/<course_id>/)
自动预填课程信息
    ↓ (用户填写个人信息)
提交表单
    ↓
显示银行转账付款指示页面
    ↓ (管理员确认付款)
更新注册状态 → 发送确认邮件
```

#### 3.2 EduPulse URL 配置
```python
# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # API 端点
    path('api/sync/courses/', views.SyncCoursesAPIView.as_view(), name='sync_courses'),
    
    # 注册表单页面
    path('enrol/<int:course_id>/', views.EnrolmentFormView.as_view(), name='course_enrol'),
    path('enrol/success/<int:enrollment_id>/', views.EnrolmentSuccessView.as_view(), name='enrol_success'),
    
    # 付款指示页面
    path('payment-instructions/<int:enrollment_id>/', views.PaymentInstructionsView.as_view(), name='payment_instructions'),
]
```

#### 3.3 注册表单预填功能
```python
# views.py
class EnrolmentFormView(CreateView):
    model = Enrollment
    template_name = 'core/enrollment/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        course = Course.objects.get(id=course_id)
        
        context['course'] = course
        context['form'].initial['course'] = course
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # 重定向到付款指示页面
        return redirect('payment_instructions', enrollment_id=self.object.id)
```

## 技术优势分析

### ✅ 这种方案的优势

1. **简化流程**: 去除不必要的购物车/结账步骤
2. **成本效益**: 避免支付网关费用（通常 2.9% + $0.30 每笔交易）
3. **数据控制**: 所有注册和付款数据在 EduPulse 统一管理
4. **用户体验**: 从浏览到注册的无缝流程
5. **维护性**: WooCommerce 仅作展示，复杂业务逻辑在 EduPulse
6. **SEO 保持**: 保留现有 WordPress 网站的搜索引擎优化
7. **品牌一致性**: 客户继续在熟悉的网站环境中浏览

### 🔄 替代方案比较

**方案 A: 完全移除 WooCommerce**
- ✅ 更简洁的技术架构
- ❌ 失去现有产品管理功能
- ❌ 需要重建整个课程展示系统

**方案 B: 保留完整 WooCommerce 但自定义结账**
- ❌ 仍需支付网关集成
- ❌ 增加系统复杂性
- ❌ 数据分散在两个系统中

**推荐方案: 简化 WooCommerce + EduPulse**
- ✅ 平衡现有投资和新系统优势
- ✅ 最小化客户学习成本
- ✅ 保持 SEO 和现有流量

## 实施时间线

- **阶段一**: 2-3 天（WooCommerce 配置）
- **阶段二**: 5-7 天（API 开发和同步机制）  
- **阶段三**: 3-5 天（用户流程测试和优化）
- **总计**: 约 2 周开发时间

## 风险评估和缓解

### 潜在风险
1. **API 同步失败**: 网络问题或 API 限制
2. **数据不一致**: 同步延迟导致信息不匹配
3. **用户跳转丢失**: 重定向过程中的技术问题

### 缓解策略
1. **错误重试机制**: 自动重试失败的同步请求
2. **状态监控**: 实时监控同步状态和数据一致性
3. **降级处理**: 同步失败时的备用方案
4. **全面测试**: 用户流程的端到端测试

---

*文档创建时间: 2025-08-29*  
*版本: v1.0*  
*状态: 待实施*