# 将 registration_status 字段从 Student 移动到 Enrollment

## 问题分析

### 当前状况
- `registration_status` 字段目前在 `Student` 模型中
- 该字段有选项：`new`, `returning`, `transferred`
- 该字段用于确定是否收取注册费（影响 enrollment 定价）

### 为什么需要移动
1. **业务逻辑正确性**：registration_status 应该属于每次 enrollment，而不是 student
   - 同一个学生可能在不同时间有不同的注册状态
   - 例如：学生第一次注册是 "new"，后续注册应该是 "returning"

2. **定价逻辑**：registration_status 直接影响 enrollment 的费用计算
   - 新学生可能需要支付注册费
   - 返回学生可能免注册费
   - 这个逻辑应该在 enrollment 层面处理

3. **数据一致性**：避免学生状态与实际注册情况不符

## 迁移计划

### 阶段 1：准备工作

#### 1.1 数据分析
- [ ] 分析当前数据库中 `registration_status` 的使用情况
- [ ] 检查是否有依赖该字段的代码逻辑
- [ ] 确认 enrollment 表中是否已有类似字段

#### 1.2 备份策略
- [ ] 创建数据备份脚本
- [ ] 记录当前所有学生的 registration_status 值

### 阶段 2：模型修改

#### 2.1 添加新字段到 Enrollment 模型
```python
# enrollment/models.py
class Enrollment(models.Model):
    # ... 现有字段 ...
    
    # 新增字段
    registration_status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New Student'),
            ('returning', 'Returning Student'),
            ('transferred', 'Transferred Student')
        ],
        default='new',
        verbose_name='Registration Status',
        help_text='Student status for this specific enrollment'
    )
```

#### 2.2 创建数据迁移
- [ ] 创建 Django migration 添加新字段
- [ ] 创建数据迁移脚本，将现有 student.registration_status 复制到相关的 enrollments
- [ ] 处理没有 enrollment 的学生（设置默认值）

#### 2.3 更新相关模型
- [ ] 保留 Student 模型中的字段（暂时），标记为 deprecated
- [ ] 更新 Enrollment 模型的 `__str__` 和其他方法

### 阶段 3：代码更新

#### 3.1 表单更新
- [ ] 更新 `PublicEnrollmentForm` - 已经有 `student_status` 字段，需要映射到新的 enrollment.registration_status
- [ ] 更新 `StaffEnrollmentForm` - 添加 registration_status 字段
- [ ] 更新 `StudentForm` - 移除或标记 registration_status 为只读

#### 3.2 视图更新
- [ ] 更新 enrollment 创建逻辑
- [ ] 更新费用计算逻辑，从 enrollment.registration_status 读取
- [ ] 更新学生匹配服务

#### 3.3 模板更新
- [ ] 更新 enrollment 相关模板
- [ ] 更新 student 表单模板
- [ ] 确保所有显示 registration_status 的地方都从正确的模型读取

### 阶段 4：业务逻辑更新

#### 4.1 费用计算服务
```python
# 更新 EnrollmentFeeCalculator
class EnrollmentFeeCalculator:
    @staticmethod
    def calculate_fees(enrollment):
        # 从 enrollment.registration_status 而不是 student.registration_status 读取
        if enrollment.registration_status == 'new':
            # 计算注册费
            pass
```

#### 4.2 学生匹配逻辑
```python
# 更新 StudentMatchingService
class StudentMatchingService:
    @staticmethod
    def create_or_update_student(form_data, enrollment):
        # 不再设置 student.registration_status
        # 而是设置 enrollment.registration_status
        pass
```

### 阶段 5：测试和验证

#### 5.1 单元测试
- [ ] 测试新的 enrollment.registration_status 字段
- [ ] 测试费用计算逻辑
- [ ] 测试表单验证

#### 5.2 集成测试
- [ ] 测试完整的 enrollment 流程
- [ ] 测试学生创建和更新
- [ ] 测试数据迁移的正确性

#### 5.3 数据验证
- [ ] 验证所有现有 enrollment 都有正确的 registration_status
- [ ] 验证费用计算的准确性

### 阶段 6：清理工作

#### 6.1 移除旧字段
- [ ] 从 Student 模型中移除 registration_status 字段
- [ ] 创建 migration 删除数据库列
- [ ] 清理相关的表单字段和模板

#### 6.2 文档更新
- [ ] 更新 API 文档
- [ ] 更新用户手册
- [ ] 更新开发者文档

## 风险评估

### 高风险
- **数据丢失**：迁移过程中可能丢失现有的 registration_status 数据
- **业务中断**：费用计算逻辑错误可能导致错误的收费

### 中风险
- **表单验证**：现有表单可能需要大量修改
- **模板渲染**：显示逻辑可能需要调整

### 低风险
- **性能影响**：新字段对查询性能的影响很小

## 回滚计划

如果迁移出现问题：
1. 恢复数据库备份
2. 回滚代码到迁移前的版本
3. 重新评估迁移策略

## 实施时间表

- **阶段 1-2**：1-2 天（准备和模型修改）
- **阶段 3**：2-3 天（代码更新）
- **阶段 4**：1-2 天（业务逻辑）
- **阶段 5**：2-3 天（测试）
- **阶段 6**：1 天（清理）

**总计**：7-11 天

## 成功标准

1. 所有现有 enrollment 都有正确的 registration_status
2. 费用计算逻辑正确工作
3. 新的 enrollment 创建流程正常
4. 所有测试通过
5. 没有数据丢失
6. 用户界面正常显示和操作

## 实施状态：✅ 已完成

### 实施日期：2025-09-10

### 实际完成的工作：

#### ✅ 阶段 1：数据分析
- 分析了当前数据库中的 registration_status 使用情况
- 发现 2 个逻辑不一致的学生记录（标记为 'new' 但有多次注册）
- 确认了 9 条 enrollment 记录需要迁移

#### ✅ 阶段 2：模型修改
- 在 Enrollment 模型中添加了 registration_status 字段
- 创建了数据迁移脚本，成功迁移了所有现有数据
- 第一次注册保持原状态，后续注册自动设为 'returning'

#### ✅ 阶段 3：代码更新
- 更新了 StaffEnrollmentForm，添加 registration_status 字段
- 更新了 PublicEnrollmentView，正确设置 registration_status
- 更新了相关模板，显示新字段

#### ✅ 阶段 4：业务逻辑更新
- 更新了 EnrollmentFeeCalculator，从 enrollment.registration_status 读取状态
- 保持了向后兼容性，支持旧的 API 调用
- 费用计算逻辑现在基于每次 enrollment 的状态，而不是学生的全局状态

#### ✅ 阶段 5：测试验证
- 创建了全面的测试套件，验证所有功能
- 测试了费用计算逻辑的正确性
- 验证了表单和模板的正常工作
- 确认了向后兼容性

### 迁移结果：
- ✅ 所有 9 条 enrollment 记录成功迁移
- ✅ 费用计算逻辑正确工作
- ✅ 新的 enrollment 创建流程正常
- ✅ 表单和模板正确显示新字段
- ✅ 向后兼容性得到保持

### 业务价值：
1. **逻辑正确性**：registration_status 现在属于每次 enrollment，符合业务逻辑
2. **定价准确性**：费用计算基于具体 enrollment 的状态，避免了定价错误
3. **数据一致性**：解决了学生状态与实际注册情况不符的问题
4. **可扩展性**：为未来的定价策略提供了更灵活的基础

### 注意事项：
- Student 模型中的 registration_status 字段暂时保留，用于向后兼容
- 未来可以考虑移除 Student.registration_status 字段（需要额外的清理工作）
- 所有新的 enrollment 都应该使用 Enrollment.registration_status 字段