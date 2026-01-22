# 限制教师（staff/teacher）访问范围的最小更改方案

## 目标
- 在不大改现有架构的前提下，让“teacher/staff”角色仅能：
  1) 查看个人资料；2) 修改密码；3) 查看“自己”的即将上课（含学生列表）；4) 标记考勤；5) 打卡（Clock In/Out）。
- 管控 UI 导航与服务端权限，避免老师通过直链访问管理功能。

## 实施步骤

### 步骤 1：精简顶部导航，新增必要入口
涉及文件：/Users/changjiang/Dev/edupulse/templates/base.html
任务分解：
- 将“Students / Courses / Enrollments”等仅管理员使用的菜单加上 `{% if user.role == 'admin' %}` 限制（当前 Staff/Facilities 已做）。
- 修复用户下拉菜单中的“Profile”链接（当前 href="#"），指向新加的“我的资料”路由。
- 在用户下拉菜单中新增“Change Password”链接，指向密码修改页面。
- 为教师新增入口：
  - “Clock In/Out” → clock
  - “My Attendance History” → core:teacher_attendance_history
具体修改：
- 替换“Profile”链接为 `{% url 'accounts:profile' %}`。
- 使用 `{% if user.role == 'admin' %}` 包裹“Students / Courses / Enrollments”等菜单。
- 在用户下拉菜单追加“Change Password”“Clock In/Out”“My Attendance History”。

### 步骤 2：复用现有员工详情模板作为“我的资料”页面（隐藏管理操作）
涉及文件：
- /Users/changjiang/Dev/edupulse/accounts/views.py
- /Users/changjiang/Dev/edupulse/accounts/urls.py
- /Users/changjiang/Dev/edupulse/templates/core/staff/detail.html
任务分解：
- 新增 ProfileView（LoginRequiredMixin）：获取 `request.user` 并渲染员工详情模板。
- accounts/urls.py 新增 `path('profile/', views.ProfileView.as_view(), name='profile')`。
- 调整 `core/staff/detail.html`：
  - 将“Edit Staff”“Back to Staff”“Quick Actions”等仅管理员可见内容包裹 `{% if user.role == 'admin' %}`。
  - 避免老师看到“编辑他人/列表”等管理按钮；保留信息展示和“查看与自己相关课程班级”的只读视图。
具体修改：
- 在 accounts/views.py 中添加 ProfileView（仅渲染、无更新逻辑）。
- 在 staff/detail.html 中用条件判断隐藏管理按钮区块。

### 步骤 3：接入 Django 内置密码修改页
涉及文件：
- /Users/changjiang/Dev/edupulse/edupulse/urls.py
- /Users/changjiang/Dev/edupulse/templates/auth/password_change.html（新建）
- /Users/changjiang/Dev/edupulse/templates/auth/password_change_done.html（新建）
任务分解：
- 在全局 URL 添加 `PasswordChangeView` 与 `PasswordChangeDoneView`，模板使用 `auth/password_change.html` 和 `auth/password_change_done.html`。
- 模板继承 base.html，表单使用 Bootstrap 样式，保持 UI 一致。
具体修改：
- edupulse/urls.py 增加：
  - path('auth/password_change/', auth_views.PasswordChangeView.as_view(template_name='auth/password_change.html', success_url=reverse_lazy('password_change_done')), name='password_change')
  - path('auth/password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='auth/password_change_done.html'), name='password_change_done')
- 新建两个模板，包含基本表单与成功提示。

### 步骤 4：教师可见“我的班级”与“即将上课”——在现有视图里加教师过滤
涉及文件：/Users/changjiang/Dev/edupulse/academics/views.py
任务分解：
- ClassListView.get_queryset：若 `user.role == 'teacher'`，仅返回 `course__teacher == request.user` 的班级；保留现有“upcoming/past”筛选。
- ClassDetailView：限制教师仅能访问“自己授课”的班级详情（含学生名单显示）。建议通过重写 get_queryset 在教师角色时 `.filter(course__teacher=request.user)`。
具体修改：
- 在两个视图中加入教师分支逻辑，不影响管理员行为。

### 步骤 5：仪表盘“即将上课”仅显示本教师的课程
涉及文件：/Users/changjiang/Dev/edupulse/core/views.py
任务分解：
- DashboardView.get_context_data：检测教师角色时，将 `upcoming_classes` 改为 `Class.objects.filter(course__teacher=request.user, date__gte=today, is_active=True)`。
- 管理员保持原逻辑。
具体修改：
- 在生成 context 处增加条件分支。

### 步骤 6：考勤标记权限（保留现有页面，强化服务端约束）
涉及文件：/Users/changjiang/Dev/edupulse/enrollment/views.py
任务分解：
- AttendanceMarkView（GET/POST）：
  - 读取 `class_id` 对应的班级；
  - 若用户为管理员 → 允许；
  - 若用户为教师 → 仅当 `class.course.teacher == request.user` 才允许，否则返回 403 或友好错误页。
- AttendanceListView：更安全起见，限制为管理员（使用 AdminRequiredMixin）；教师无需该列表页即可完成工作流。
具体修改：
- 在 AttendanceMarkView 中加入教师归属校验。
- 将 AttendanceListView 的 LoginRequiredMixin 替换/叠加为 AdminRequiredMixin（可从 accounts.views 复用 mixin）。

### 步骤 7：导航与页面入口联通性核查
涉及文件：
- /Users/changjiang/Dev/edupulse/templates/core/classes/list.html
- /Users/changjiang/Dev/edupulse/templates/core/classes/detail.html
- /Users/changjiang/Dev/edupulse/templates/core/attendance/mark.html
任务分解：
- 确保“Mark Attendance”按钮仅显示在教师有权限的班级详情/列表中（如果模板已有按钮，保持不动；依赖第 6 步的服务端校验兜底）。
- 从 Dashboard 的“即将上课”卡片可以进入班级详情或直接进入标记页。
具体修改：
- 如模板存在明显对全体用户展示的“管理型”按钮，可用 `{% if user.role == 'admin' %}` 包裹，保持最小侵入修改。

## 用户体验改进
- 老师登录后，导航只保留与自己工作流直接相关的功能，界面更清爽、避免误点进入管理页。
- “Profile/Change Password/Clock In/Out/Attendance History”集中在用户下拉，符合老师日常使用习惯。
- Dashboard 与“Classes”列表对老师呈现“自己的课”，减少无关信息干扰。
- 标记考勤沿用现有实现，仅新增权限校验，学习成本低。

## 预期效果
1. 权限收敛：老师无法访问学生、课程、设施、员工等管理模块。
2. 流程顺畅：老师从导航或仪表盘直接进入“我的课”和“标记考勤”。
3. 一致性：保留管理员现有工作流不变。
4. 安全性：服务端权限校验补齐，杜绝直链绕过。

## 测试要点
1. 以 teacher 账号登录：
   - 顶部导航仅显示 Dashboard（和与老师相关的入口），无 Students/Courses/Enrollments/Staff/Facilities 等。
   - 用户下拉包含 Profile、Change Password、Clock In/Out、My Attendance History。
   - Dashboard 的“Upcoming Classes”仅显示该教师班级。
   - 访问 /academics/classes/：仅显示自己的班级；进入详情页可见学生名单；可见“Mark Attendance”按钮。
   - 访问 /enrollment/attendance/mark/<class_id>/：仅当该 class 属于该教师时可访问并提交；否则 403。
2. 以 admin 账号登录：
   - 管理菜单与数据范围不变；可访问 AttendanceListView 等。
3. 直链测试：
   - 老师尝试访问 /students/、/academics/courses/、/enrollment/enrollments/ 等应被拒绝或重定向。
   - 老师尝试访问其他老师的 class 详情或 attendance mark，返回 403。
4. 密码修改：
   - 老师可顺利修改密码并看到成功页；下次登录生效。
5. 回归：
   - 现有功能（邮箱/SMS 设置、工时导出等）管理员端均不受影响。
