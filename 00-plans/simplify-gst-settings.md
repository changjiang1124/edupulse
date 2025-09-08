# 简化 GST 设置

## 目标
简化现有复杂的 GST 设置界面，将澳洲固定的 10% GST 率和 "GST" 标签硬编码，只保留"价格是否含税"开关。符合澳洲客户使用习惯，类似 WooCommerce 的 GST 价格显示机制。

## 实施步骤

### 步骤 1：创建计划文档
*已完成*

### 步骤 2：精简组织设置模板
`/Users/changjiang/Dev/edupulse/templates/core/settings/organisation.html`

在 GST Configuration 卡片中：
│ │ - 保留"Prices Include GST"复选框开关（line 120-127）
│ │ - 移除 GST Rate 输入框及百分比显示（line 130-139）  
│ │ - 移除 GST Label 输入框（line 141-146）
│ │ - 移除"Show GST Breakdown"复选框（line 148-154）
│ │ - 移除 GST Calculator 预览区域（line 156-181）
│ │ - 移除 Configuration Preview 整张卡片（line 197-232）
│ │ - 清理相关 JavaScript 逻辑（line 248-325）

具体修改：
│ │ - GST Configuration 卡片仅包含价格含税开关和简单说明
│ │ - 移除所有预览、计算器和交互式设置
│ │ - 保持简洁的 Bootstrap 风格布局

### 步骤 3：更新视图函数处理
`/Users/changjiang/Dev/edupulse/core/views.py`

在 organisation_settings_view 函数中：
│ │ - 移除 gst_rate、gst_label、show_gst_breakdown 的表单读取（line 1307-1308, 1310）
│ │ - 移除对这些字段的保存操作（line 1318-1320）
│ │ - 保留 prices_include_gst 的处理逻辑
│ │ - 移除 test_gst_calculation 函数（line 1340-1384）

具体修改：
│ │ - 固定 GST 率为 10%，GST 标签为 "GST"
│ │ - 删除测试计算相关的 URL 路由和视图

### 步骤 4：调整 GST 配置获取
`/Users/changjiang/Dev/edupulse/core/models.py`

在 OrganisationSettings.get_gst_config 方法中：
│ │ - 返回固定的 gst_rate = 0.1000 和 gst_label = "GST"
│ │ - 保留 prices_include_gst 从实例读取
│ │ - 简化 gst_rate_percentage 属性返回固定 10

具体修改：
│ │ - 硬编码 GST 配置，避免依赖数据库字段
│ │ - 确保向后兼容现有价格分解逻辑

### 步骤 5：优化百分比显示
`/Users/changjiang/Dev/edupulse/core/templatetags/price_tags.py`

调整 percentage 过滤器：
│ │ - 将输出从 "10.0%" 改为 "10%"（移除小数位）
│ │ - 保持其他 GST 计算函数不变

具体修改：
│ │ - 修改格式化逻辑，使用无小数的整数百分比

### 步骤 6：运行预览测试
│ │ - 启动开发服务器
│ │ - 访问组织设置页面确认 UI 简化效果
│ │ - 测试价格显示功能正常

### 步骤 7：更新项目文档
│ │ - 在 plans.md 标注"GST设置简化"完成状态
│ │ - 在 DEPLOYMENT.md 记录变更说明

## 用户体验改进
经过简化后，用户在组织设置中只需关注"价格是否含税"这一核心开关。澳洲固定的 10% GST 率和标准 "GST" 标签被系统自动处理，消除了不必要的配置复杂性。界面更清晰直观，符合澳洲商业环境的使用习惯。

## 预期效果
1. **简化设置**：组织设置页面大幅精简，减少用户困惑
2. **标准化**：GST 率和标签统一为澳洲标准（10% GST）
3. **向后兼容**：现有价格计算逻辑保持功能完整
4. **用户友好**：类似 WooCommerce 的直观价格显示机制

## 测试要点
│ │ 1. 验证组织设置页面 UI 精简正确
│ │ 2. 确认价格计算逻辑使用固定 10% GST
│ │ 3. 检查课程价格显示格式正确（含/不含 GST）
│ │ 4. 测试价格分解功能正常工作
│ │ 5. 验证现有功能不受影响