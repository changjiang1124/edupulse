# EduPulse User Guide / EduPulse 用户使用指南

*Scrolldown for English version / 向下滚动查看英文版*

---

# EduPulse 用户使用指南 (Chinese Version)

欢迎使用 EduPulse 教学管理系统。本系统的设计出发点，是让像您这样的校长和管理者，尽量少花时间在「抄表格、对数字、盯流程」上，把精力放回到教学质量和学校发展上。

下面的内容会用**真实的管理场景**来介绍系统功能，重点说明：
- 过去需要人工处理、容易出错的地方，现在如何交给系统自动完成；
- 当报名越来越多、课程越来越复杂时，系统如何帮您「不乱」；
- 您作为管理者，可以通过哪些页面快速看到学校现状，做出决策。

## 1. 系统概览与登录

EduPulse 是一个集成的管理平台。
*   **登录页面**: `/accounts/login/` (通常为系统首页)
*   **控制台 (Dashboard)**: `/core/dashboard/`
    *   **功能**: 登录后看到的第一个页面，显示当前学期信息、本周课程概览和最近的报名情况。
    *   **价值（校长视角）**: 不用翻 Excel、问前台，打开这个页面就能知道：
        - 这个学期目前有哪些课程、哪些课报得好、哪些课可能要合班或取消；
        - 近期有没有很多新的报名，是否有大量「待确认」需要处理；
        - 未来几天有哪些关键课程或老师需要特别关注。

## 2. 课程与班级管理 (Academics)

这是教务管理的核心，用于设置学校开设的课程。

### 课程管理 (Courses)
*   **位置**: `/academics/courses/`
*   **功能**:
    *   创建和编辑课程信息（名称、描述、价格、学期、时间安排）。
    *   设置重复模式（如每周一次，共10周）。
    *   系统会自动根据课程设置生成具体的“班级 (Class)”实例。
*   **价值（解决什么问题）**:
    *   以前：先在 Excel 里排课，再让前台同事把课程一条条搬到官网，容易抄错、版本不一致；
    *   现在：只在 EduPulse 里设置一次，系统自动生成整学期的班级，并把课程信息同步到官网，
      您再也不用担心「官网写的是旧价格或旧时间」。

### 班级管理 (Classes)
*   **位置**: `/academics/classes/`
*   **功能**:
    *   管理课程的每一次具体上课时间（Session）。
    *   支持对单次课程进行调整，例如：临时更换老师、更换教室或更改时间。
*   **价值**: 灵活应对突发情况（如老师请假），而不影响整个课程的设置。

### 官网课程自动同步（WordPress / WooCommerce）
*   **触发方式**: 当你在 `/academics/courses/` 中新增、修改、发布或下架课程时，系统会自动把对应信息更新到现有官网。
*   **在校长眼中的效果**:
    *   官网课程页总是跟后台一致：课程名字、介绍、价格、上课时间地点，改一次就全站更新；
    *   官网上的按钮统一是 **“Enrol Now”**，家长点进去会回到 EduPulse 的线上报名表，方便集中管理；
    *   不再招生或已经结束的课程，会自动从官网下架，避免家长误报、事后再解释和退款。
*   **为您解决的痛点**:
    *   不用再「双重维护」：既改后台又改 WordPress，前台同事也不用担心抄错信息；
    *   避免官网信息过期，减少家长投诉和沟通成本；
    *   报名入口统一到 EduPulse，后续统计和对账更简单。

## 3. 学生与报名管理

### 学生管理 (Students)
*   **位置**: `/students/`
*   **功能**:
    *   录入和查看学生详细档案。
    *   管理监护人联系方式。
    *   查看学生的过往报名记录。
*   **价值（校长/前台视角）**:
    *   所有学生资料放在一个地方，不用再在 Excel、纸卡片和邮箱里到处找；
    *   临时有安全事件或紧急情况时，可以立刻查到家长的最新联系方式；
    *   方便后续做续班统计、老生回流、推荐奖励等运营工作。

### 报名管理 (Enrollment)
*   **位置**: `/enrollment/enrollments/`
*   **功能**:
    *   处理新的报名请求（来自前台或在线表单）。
    *   查看报名状态（待确认、已确认、已取消）。
    *   **内部报名**: `/enrollment/enrollments/staff/create/` (工作人员帮学生报名)
    *   **公开报名表**: `/enroll/` (供家长/学生使用的公共链接)
    *   在从“待确认”改为“已确认”前，系统会自动检查是否需要应用或取消**早鸟价 (Early Bird Price)**，避免因为时间点不同导致收费错误。
    *   报名一旦确认，系统会为该课程已经生成的所有班级自动创建学生考勤记录，老师在点名时可以直接使用，无需逐条添加。
*   **价值**:
    *   集中管理所有报名渠道，清晰追踪每个报名的付款和确认状态。
    *   自动处理早鸟价与常规价格的切换，减少人工核算错误。
    *   自动生成考勤记录，让老师专注上课而不是维护名单。

## 4. 考勤系统 (Attendance)

### 学生考勤
*   **位置**: `/enrollment/attendance/` 或 `/enrollment/attendance/mark/<class_id>/`
*   **功能**:
    *   老师为班级学生标记出勤状态（出席、缺席、迟到）。
*   **价值（实际场景）**:
    *   老师不用再带一叠纸点名册，手机或电脑上几下就完成点名；
    *   不会出现纸被弄丢、字看不清，事后需要回忆某个学生是否来过的问题；
    *   将来可以在此基础上做「缺席自动提醒家长」等功能，减少老师逐个打电话的时间。

## 5. 员工与工时管理 (Staff & Timesheets)

### 员工打卡 (Clock In/Out)
*   **位置**: `/clock/` 或 `/core/attendance/teacher/qr/` (扫码打卡)
*   **功能**:
    *   员工/老师到校后扫码或点击按钮进行上班打卡，离校时下班打卡。
    *   系统记录打卡时间和位置，并可通过老师手机的 GPS 验证其是否在指定校区内。
    *   对老师而言，系统会根据其所在校区和当天日期，自动列出相关课程，方便在打卡时一并选择所上的班级。
    *   管理员可以在 `/core/qr-codes/` 为每个 Facility 批量生成和下载用于打印的 QR 码（对应不同日期和场地），方便贴在教室门口或前台。
*   **价值**:
    *   自动记录工作时间，替代人工签到，并通过定位降低“代打卡”的风险。
    *   通过 QR 码和自动课程匹配，让老师用手机即可完成考勤相关操作。

### 工时表 (Timesheets)
*   **位置**: `/core/timesheet/`
*   **功能**:
    *   查看员工的打卡记录。
    *   导出月度工时报表 (`/core/timesheet/export/`)。
*   **价值**: 月末一键导出工时统计，极大简化工资结算流程。

## 6. 设施与设置

### 设施管理 (Facilities)
*   **位置**: `/facilities/`
*   **功能**: 管理学校的校区、教室及其容量。

### 通信设置
*   **位置**: `/core/settings/email/` 和 `/core/settings/sms/`
*   **功能**:
    *   设置学校统一使用的邮件和短信通道，让系统可以自动发出确认信、提醒短信等；
    *   查看最近有哪些邮件/短信成功发出、哪些失败，方便和家长对话时「心里有数」；
    *   系统会根据预设的每月上限控制发送量，避免意外超出短信或邮件套餐。

## 7. 学生标签、等级与批量通知

### 学生标签与等级
*   **位置**: 学生列表 `/students/`
*   **功能**:
    *   使用彩色 **标签 (Student Tags)** 为学生打标，例如：“高潜力”、“需要跟进”、“奖学金”等，便于快速筛选。
    *   使用 **学生等级 (Student Levels)** 标注学生当前水平（如 Beginner / Intermediate / Advanced），并可在列表中按等级筛选。

### 批量通知 (Bulk Notifications)
*   **位置**: 学生列表页面中的“批量通知”入口（后台对应路径如 `/students/bulk-notification/` 等）。
*   **功能**:
    *   选择“所有在读学生”“按标签”“最近报名”“仅待确认报名”等条件，批量发送 Email / SMS 通知。
    *   系统会根据已配置的每月配额检查是否足够，避免意外超量发送。
*   **价值**:
    *   方便对特定群体（例如“本学期所有 Beginner 班学生”“所有 Pending 报名的学生”）进行有针对性的沟通。
    *   管理层可以快速发出停课通知、节日问候、促销信息等。

---

## 总结：从校长角度，这个系统帮你做到的事

1.  **少担心官网和后台不一致**：
    * 课程、价格、时间在一个地方维护，官网自动更新，不再被家长提醒「网站上写的是另一套」。
2.  **少花时间盯流程**：
    * 报名–确认–生成考勤–后续上课，这一整条链路尽量自动化完成，减少「漏登记」「忘记改状态」。
3.  **更快看清学校运营情况**：
    * 打开 Dashboard 就能看到学生、课程、报名和老师工时的核心数据，方便决定要不要加班、加开或合并班级。
4.  **沟通更有秩序**：
    * 批量邮件、批量短信、缺勤记录都在系统内，有据可查，和家长、老师沟通时更有底气。
5.  **方便未来扩展**：
    * 学生标签、等级、批量通知等功能，为将来做分层教学、营销活动打好基础，而不用再换一套系统。

---
---

# EduPulse User Guide (English Version)

Welcome to the EduPulse School Management System.
If you are a school owner or principal, you can think of EduPulse as a way to move
repetitive admin work (spreadsheets, manual website updates, checking who has paid)
into one place, so you and your team can focus more on teaching and growing the school.

This document gives a non-technical overview of what you can do with the system and
what real-life problems it is designed to solve.

## 1. System Overview & Login

EduPulse is an integrated management platform.
*   **Login Page**: `/accounts/login/` (Usually the system home page)
*   **Dashboard**: `/core/dashboard/`
    *   **Function**: The first page seen after login, displaying current term information and a weekly course overview.
    *   **Value**: Gives you an immediate grasp of the school's current operational status and upcoming courses.

## 2. Academics Management (Courses & Classes)

This is the core of academic management, used for setting up courses offered by the school.

### Course Management
*   **Location**: `/academics/courses/`
*   **Function**:
    *   Create and edit course information (name, description, price, term, schedule).
    *   Set recurrence patterns (e.g., once a week for 10 weeks).
    *   The system automatically generates specific "Class" instances based on course settings.
*   **Value (for school leaders)**:
    * Previously: your team had to plan courses in a spreadsheet and then re-enter
      everything into the website, risking mistakes and outdated information;
    * Now: you set up the course once in EduPulse, the timetable is generated for the
      whole term and the public website is updated automatically, so parents always see
      the latest details.

### Class Management
*   **Location**: `/academics/classes/`
*   **Function**:
    *   Manage specific sessions of a course.
    *   Support adjustments for individual sessions, such as: temporary teacher changes, room changes, or time changes.
*   **Value**: Flexibly handle unexpected situations (like a teacher calling in sick) without affecting the entire course setting.

### Website (WordPress / WooCommerce) Synchronisation
*   **How it works**: Whenever you create, edit or publish/unpublish a course in `/academics/courses/`, EduPulse synchronises it with your WordPress + WooCommerce website.
*   **Function**:
    *   Creates/updates a WooCommerce product for each course, including name, rich description, pricing (including early-bird price, registration fee and GST label), schedule and location details.
    *   Sets the product button label to **“Enrol Now”**, which redirects to the EduPulse public enrolment page `/enroll/?course=<course_id>` so that all enrolments are still handled inside EduPulse.
    *   When a course is no longer open for enrolment, the related WooCommerce product is moved back to draft status so it is not publicly advertised.
*   **Value**:
    *   Ensures your public WordPress site always shows **up-to-date course information** without manual updates in WordPress.
    *   Keeps all enrolments flowing through EduPulse, making reporting and teaching operations simpler.

## 3. Student & Enrollment Management

### Student Management
*   **Location**: `/students/`
*   **Function**:
    *   Record and view detailed student profiles.
    *   Manage guardian contact information.
    *   View student's past enrollment records.
*   **Value**: Keeps all student information in one place, so your team can quickly
    find contact details in an emergency and understand each student's history with
    the school (past courses, attendance, communication).

### Enrollment Management
*   **Location**: `/enrollment/enrollments/`
*   **Function**:
    *   Process new enrollment requests (from reception or online forms).
    *   View enrollment status (Pending, Confirmed, Cancelled).
    *   **Internal Enrollment**: `/enrollment/enrollments/staff/create/` (Staff enrolling students)
    *   **Public Enrollment Form**: `/enroll/` (Public link for parents/students)
    *   Before changing an enrollment from "pending" to "confirmed", the system automatically checks whether **early-bird pricing** should still apply and prompts for adjustment if needed.
    *   Once an enrollment is confirmed, attendance records are automatically created for all existing classes of that course, so teachers can mark attendance straight away without setting up each record manually.
*   **Value**:
    *   Centralizes all enrollment channels and gives a clear view of payment and confirmation status for each student.
    *   Reduces pricing mistakes around early-bird cut-off dates.
    *   Saves time by auto-generating attendance records when a student is confirmed.

## 4. Attendance System

### Student Attendance
*   **Location**: `/enrollment/attendance/` or `/enrollment/attendance/mark/<class_id>/`
*   **Function**:
    *   Teachers mark attendance status (Present, Absent, Late) for class students.
*   **Value**: Replaces paper rolls with reliable digital records so you do not lose
    information, and opens the door to features like automatic absence notifications
    for parents in the future.

## 5. Staff & Timesheet Management

### Staff Clock In/Out
*   **Location**: `/clock/` or `/core/attendance/teacher/qr/` (QR Code Clock-in)
*   **Function**:
    *   Staff/Teachers clock in upon arrival and clock out when leaving by scanning a QR code or clicking a button.
    *   The system records clock-in time and location, and can verify that the teacher is physically at a valid facility using GPS.
    *   For teachers, the system lists today's classes at the scanned facility so they can associate their clock-in/out with specific classes.
    *   Administrators can generate printable QR codes for each facility and date range via `/core/qr-codes/` and `/core/qr-codes/facility/<facility_id>/`.
*   **Value**:
    *   Automatically records working hours while reducing the risk of "buddy punching".
    *   Makes it easy for teachers to clock in with their phone and link attendance to the right classes.

### Timesheets
*   **Location**: `/core/timesheet/`
*   **Function**:
    *   View staff clock-in records.
    *   Export monthly timesheet reports (`/core/timesheet/export/`).
*   **Value**: One-click export of monthly work hour statistics, greatly simplifying payroll processing.

## 6. Facilities & Settings

### Facility Management
*   **Location**: `/facilities/`
*   **Function**: Manage school campuses, classrooms, and their capacities.

### Communication Settings
*   **Location**: `/core/settings/email/` and `/core/settings/sms/`
*   **Function**:
    *   Configure email and SMS channels so enrolment confirmations and reminders are sent
      automatically instead of manually by staff;
    *   Review logs of emails and SMS sent by the system, to troubleshoot any issues;
    *   Keep usage within monthly limits so you do not overspend on messaging.

## 7. Student Tags, Levels & Bulk Notifications

### Student Tags & Levels
*   **Location**: Student list `/students/`
*   **Function**:
    *   Use coloured **Student Tags** to label students (e.g. "High potential", "Needs follow-up", "Scholarship"), making it easy to filter.
    *   Use **Student Levels** to reflect current skill level (e.g. Beginner / Intermediate / Advanced) and filter the list accordingly.

### Bulk Notifications
*   **Location**: Bulk notification entry on the student list page (backend endpoints such as `/students/bulk-notification/`).
*   **Function**:
    *   Send bulk Email/SMS to groups such as "all active students", "students with selected tags", "pending enrollments" or "recent enrollments".
    *   Respect monthly email/SMS quotas and warn when a planned send would exceed limits.
*   **Value**:
    *   Enables targeted communication to specific segments (e.g. "all Beginner students this term", "all students with pending enrolments").
    *   Helps management quickly send closure notices, holiday greetings or promotional messages.

---

## Summary: Value for School Leaders

1.  **Less double-handling**:
    * Courses, prices and schedules are maintained in one place and pushed to the
      website, reducing mistakes and staff time.
2.  **Clearer picture of your school**:
    * Dashboards, enrolment lists and attendance records give you a live view of how
      classes are filling, which teachers are teaching, and where issues may appear.
3.  **More consistent communication**:
    * Bulk email/SMS and attendance records help your team communicate with families
      in a timely and consistent way.
4.  **A solid base for future growth**:
    * Tags, levels and reporting prepare your school for more advanced marketing,
      differentiated teaching and data-driven decisions without changing systems.
