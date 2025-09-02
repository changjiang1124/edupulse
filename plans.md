# EduPulse 項目實施計劃

## 項目概述

EduPulse 是一個基於 Django 的藝術學校管理系統，用於替代 Perth Art School 當前的 WordPress + WooCommerce 系統，主要處理課程管理和學生註冊功能。

## 技術架構

### 後端技術棧
- **框架**: Django 5.2.5
- **資料庫**: SQLite (開發環境)
- **認證**: 自定義 Staff 用戶模型
- **郵件服務**: Amazon SES
- **簡訊服務**: Twilio
- **環境變量**: python-dotenv

### 前端技術棧  
- **CSS 框架**: Bootstrap 5
- **JavaScript**: jQuery 3.6+
- **樣式**: 現代化簡約設計，統一色彩方案
- **代碼組織**: 分離的 CSS/JS 文件，避免內聯代碼

### 部署環境
- **域名**: https://edupulse.perthartschool.com.au/
- **支付**: 銀行轉帳/線下支付 (避免支付網關費用)

## MVP 階段實施計劃

### 第一階段：項目基礎搭建 ✅ 已完成

#### 1.1 環境設置
- [x] 創建 Django 項目和核心應用
- [x] 配置 settings.py 
- [x] 設置靜態文件處理
- [x] 配置 URL 路由

#### 1.2 前端框架配置  
- [x] 集成 Bootstrap 5
- [x] 實現現代化簡約設計主題
- [x] 配置 jQuery 庫
- [x] 創建基礎模板結構 (base.html)
- [x] 實現響應式導航欄

### 第二階段：資料庫設計與模型 ✅ 已完成

#### 2.1 核心資料模型
- [x] **設施模型**: Facility  
- [x] **教室模型**: Classroom
- [x] **員工模型**: Staff (擴展 AbstractUser)
- [x] **學生模型**: Student (包含監護人信息)

#### 2.2 課程管理模型
- [x] **課程模型**: Course (包含 description, short_description)
- [x] **班級模型**: Class (1:n 關係與 Course)
- [x] **註冊模型**: Enrollment
- [x] **考勤模型**: Attendance
- [x] **打卡模型**: ClockInOut

#### 2.3 通信模型
- [x] **郵件記錄模型**: EmailLog
- [x] **簡訊記錄模型**: SMSLog

### 第三階段：課程管理系統 ✅ 已完成

#### 3.1 課程與班級關係
- [x] 實現 Course 與 Class 的 1:n 關係
- [x] Course 模型包含 description 和 short_description 字段
- [x] 班級可根據課程排程自動生成 (支持重複模式)

#### 3.2 課程管理界面
- [x] 課程列表頁面 (core/courses/list.html)
- [x] 課程添加/編輯表單 (core/courses/form.html) 
- [x] 課程詳情頁面 (core/courses/detail.html)
- [x] 所有課程相關 URL 和視圖已配置

#### 3.3 導航和用戶界面
- [x] 修復導航選單中的課程鏈接
- [x] 實現現代化簡約設計
- [x] 移除多餘圖標，保持界面簡潔
- [x] 統一顏色方案和現代化樣式

### 第四階段：用戶管理與權限 ✅ 已完成

#### 4.1 員工管理系統
- [x] 員工信息管理界面
- [x] 角色權限控制 (管理員/教師)  
- [x] 員工狀態管理
- [x] 員工表單 Bootstrap 樣式優化

#### 4.2 學生管理系統
- [x] 學生信息 CRUD 操作
- [x] 監護人信息管理
- [x] 學生狀態管理
- [x] 學生表單 Bootstrap 樣式優化
- [x] 學生列表頁面，支持搜索功能
- [x] 學生詳情頁面，顯示註冊和出勤記錄

#### 4.3 設施與教室管理
- [x] 設施（Facility）管理系統
- [x] 教室（Classroom）管理系統，1:n 關係與設施
- [x] 教室 CRUD 操作和導航菜單整合
- [x] 教室狀態管理和篩選功能
- [x] **修復**: 教室創建表單 is_active 字段顯示問題

#### 4.4 儀表板功能
- [x] 管理員儀表板視圖
- [x] 統計資料顯示
- [x] 近期課程和註冊信息

#### 4.5 表單系統優化 ✅ 已完成
- [x] **Django 表單類創建**: 所有模型的自定義表單類，包含 Bootstrap CSS 類
- [x] **Bootstrap 樣式集成**: 完整的 Bootstrap 5 樣式支持和對齊
- [x] **表單驗證增強**: 改進的錯誤顯示和驗證反饋
- [x] **一致的表單佈局**: 統一的表單設計和用戶體驗
- [x] **響應式設計**: 所有表單在移動設備上正確顯示
- [x] **CSS 增強**: 完善的表單樣式，包括焦點狀態、驗證狀態等
- [x] **所有模組表單模板**: 課程、學生、員工、設施、教室表單模板已完成

#### 4.6 富文本編輯器系統 ✅ 已完成
- [x] **TinyMCE 集成**: 替換 CKEditor，使用自托管方案避免 API 金鑰需求
- [x] **圖片上傳功能**: 安全的圖片上傳，支持課程描述圖片插入
- [x] **WordPress 兼容**: 簡化工具欄，確保與 WordPress/WooCommerce 同步兼容
- [x] **安全驗證**: 文件類型和大小限制，UUID 命名防止衝突
- [x] **檔案組織**: 按日期組織的目錄結構 (YYYY/MM)

### 第五階段：註冊與考勤系統 ✅ 已完成

#### 5.1 註冊系統
- [x] **完整的 CRUD 系統**: 註冊的創建、讀取、更新、刪除功能
- [x] **內部管理界面**: 工作人員使用的註冊管理系統
- [x] **公開註冊表單**: 無需認證的學生/監護人註冊頁面
- [x] **智能學生管理**: 自動創建或更新現有學生資料
- [x] **註冊狀態管理**: pending/confirmed/cancelled 狀態流程
- [x] **註冊來源跟蹤**: website/form/staff 來源記錄
- [x] **表單資料保存**: 原始註冊表單資料的 JSON 儲存
- [x] **重複註冊檢測**: 防止同一學生重複註冊相同課程
- [x] **成功頁面引導**: 註冊成功後的後續步驟說明

#### 5.2 註冊表單功能
- [x] **學生資訊收集**: 姓名、聯絡方式、出生日期、地址
- [x] **監護人資訊**: 針對未成年學生的監護人資料（動態驗證）
- [x] **緊急聯絡人**: 緊急情況聯絡資訊
- [x] **醫療資訊**: 醫療條件和特殊需求記錄
- [x] **課程選擇**: 動態課程列表，顯示價格資訊
- [x] **表單驗證**: 前端和後端雙重驗證
- [x] **響應式設計**: 移動設備友好的表單界面

#### 5.3 註冊管理功能
- [x] **篩選功能**: 按學生、課程、狀態篩選註冊記錄
- [x] **快速操作**: 確認註冊、編輯、刪除等快速操作
- [x] **詳細視圖**: 完整的註冊資訊顯示，包含學生和課程詳情
- [x] **相關資料**: 顯示學生的其他註冊記錄
- [x] **緊急聯絡資訊**: 側邊欄顯示監護人和緊急聯絡人資訊
- [x] **原始資料追蹤**: 表單提交的原始資料查看功能

#### 5.4 URL 配置和路由
- [x] **公開註冊路由**: `/enroll/` 無需認證即可訪問
- [x] **管理功能路由**: `/enrollment/` 需要認證的管理功能
- [x] **命名空間管理**: 避免 URL 命名衝突的 namespace 配置
- [x] **導航菜單整合**: 在主導航中添加註冊管理鏈接

#### 5.5 考勤管理 📋 部分完成
- [x] **考勤模型**: Attendance 模型和資料庫結構
- [x] **考勤錄入頁面**: AttendanceMarkView 基礎頁面
- [ ] 教師考勤錄入界面完善
- [ ] 學生出勤狀態記錄
- [ ] 考勤報表生成
- [ ] 缺勤自動通知

#### 5.6 打卡系統 📋 待開始
- [ ] GPS 位置驗證
- [ ] 上下班打卡記錄
- [ ] 工時統計和導出功能

### 第六階段：通知系統 📧 部分完成

#### 6.1 郵件服務 ✅ 已完成
- [x] **Google Workspace SMTP 集成**: 支援 SMTP + App Password 方式發送郵件
- [x] **動態郵件後端**: 資料庫驅動的郵件配置，支援即時配置變更
- [x] **管理員郵件設定界面**: 完整的前端配置界面，包含 Google Workspace 預設功能
- [x] **連接測試功能**: AJAX 即時連接測試，驗證 SMTP 配置有效性
- [x] **測試郵件發送**: 支援發送測試郵件到指定收件人
- [x] **郵件統計面板**: 顯示發送成功、失敗和最近 7 天統計資料
- [x] **郵件日誌記錄**: 完整的 EmailLog 模型，記錄發送狀態和內容
- [x] **權限控制**: 僅管理員可存取郵件設定功能
- [x] **單例模式配置**: 確保只有一個作用中的郵件配置

#### 6.2 簡訊服務 ✅ 已完成
- [x] **SMS 配置模型 (SMSSettings)**: 支援 Twilio 和自定義 SMS 網關配置
- [x] **動態 SMS 後端**: 資料庫配置優先，環境變量降級機制
- [x] **SMS 表單和視圖**: 完整的前端配置界面，包含 Twilio 預設功能
- [x] **連接測試功能**: AJAX 即時連接測試，驗證 Twilio 配置有效性
- [x] **測試簡訊發送**: 支援發送測試簡訊到指定手機號碼
- [x] **SMS 統計面板**: 顯示發送成功、失敗和最近 7 天統計資料
- [x] **SMS 日誌記錄**: 完整的 SMSLog 模型，記錄發送狀態、內容和 Message SID
- [x] **權限控制**: 僅管理員可存取 SMS 設定功能
- [x] **單例模式配置**: 確保只有一個作用中的 SMS 配置
- [x] **E.164 格式驗證**: 確保手機號碼格式正確
- [x] **URL 路由配置**: SMS 設定、測試和日誌相關的 URL
- [x] **管理界面集成**: 完整的 Django Admin 配置

### 第七階段：WooCommerce 集成 ✅ 已完成

#### 7.1 API 集成 ✅ 已完成
- [x] **WooCommerce API 客户端**: 完整的 WooCommerceAPI 類，支援產品 CRUD 操作
- [x] **外部產品同步**: 課程自動同步為 WooCommerce External Product 類型
- [x] **自動重定向**: External Product 的「Enrol Now」按鈕重定向到 EduPulse 註冊表單
- [x] **同步服務**: WooCommerceSyncService 處理課程創建、更新和刪除同步
- [x] **錯誤處理和重試**: 完整的異常處理和日誌記錄機制
- [x] **分類支持**: 課程分類自動創建和映射到 WooCommerce 分類系統

#### 7.2 數據同步機制 ✅ 已完成
- [x] **Django 信號集成**: post_save 和 post_delete 信號自動同步課程變更
- [x] **雙向數據一致性**: Course.external_id 字段追蹤 WooCommerce Product ID
- [x] **發布狀態同步**: 只有 published 狀態課程同步到 WooCommerce
- [x] **價格和描述同步**: 課程價格、描述、短描述自動同步
- [x] **註冊 URL 生成**: 自動生成指向 EduPulse 的註冊鏈接

#### 7.3 管理功能 ✅ 已完成
- [x] **Django Admin 集成**: Course Admin 添加 WooCommerce 同步狀態顯示
- [x] **批量同步操作**: Admin actions 支援批量同步和移除操作
- [x] **管理命令**: test_woocommerce 命令支援連接測試、單個/批量同步
- [x] **同步狀態追蹤**: Admin 界面顯示 WooCommerce 產品 ID 和同步狀態
- [x] **手動操作**: 支援手動同步特定課程和批量操作

#### 7.4 測試和驗證 ✅ 已完成
- [x] **API 連接測試**: 成功連接到 WooCommerce API (版本 10.0.2)
- [x] **課程同步測試**: 成功創建測試課程並同步到 WooCommerce
- [x] **編輯同步測試**: 課程編輯自動更新 WooCommerce 產品信息
- [x] **批量同步測試**: 成功同步 16 個已發布課程到 WooCommerce
- [x] **產品列表驗證**: 確認所有課程在 WooCommerce 中正確顯示

#### 7.5 技術實施詳情
```python
# 核心組件
WooCommerceAPI: REST API 客户端，支援產品 CRUD
WooCommerceSyncService: 課程同步業務邏輯
academics.signals: Django 信號自動同步
test_woocommerce: 管理命令工具

# 配置要求
WC_CONSUMER_KEY: WooCommerce API 消費者金鑰
WC_CONSUMER_SECRET: WooCommerce API 消費者密鑰
WC_BASE_URL: WooCommerce API 基礎 URL
```

### 第八階段：系統重構 ✅ 已完成

#### 8.1 應用模組化
- [x] **重構為模組化架構**: 將單一 core 應用拆分為專業化應用
- [x] **accounts 應用**: Staff 模型和用戶認證管理
- [x] **students 應用**: Student 模型和學生管理功能
- [x] **academics 應用**: Course 和 Class 模型，課程管理功能  
- [x] **facilities 應用**: Facility 和 Classroom 模型，設施管理功能
- [x] **enrollment 應用**: Enrollment 和 Attendance 模型，註冊和考勤功能

#### 8.2 資料庫遷移和重構
- [x] **模型遷移**: 所有模型成功遷移到對應應用
- [x] **自定義用戶模型**: 將 AUTH_USER_MODEL 更新為 accounts.Staff
- [x] **外鍵關係**: 跨應用模型關係正確配置
- [x] **資料庫重建**: 解決遷移歷史衝突，重新建立乾淨的資料庫結構

#### 8.3 代碼組織優化
- [x] **views 拆分**: 將 views 按功能分配到各個應用
- [x] **forms 拆分**: 創建各應用專屬的 forms.py 文件
- [x] **admin 配置**: 各應用獨立的 admin.py 配置
- [x] **URL 路由**: 模組化 URL 配置，namespace 管理
- [x] **templates 重組**: 按應用組織模板文件結構

#### 8.4 測試與驗證
- [x] **模型創建測試**: 所有模型可正常創建和關聯
- [x] **URL 路由測試**: 所有路由響應正確的 HTTP 狀態碼
- [x] **管理命令測試**: Django 管理命令正常執行
- [x] **外鍵關係測試**: 跨應用模型關係正常工作
- [x] **服務器運行測試**: 開發服務器正常啟動和響應

### 第九階段：系統優化與部署 🚀 待開始

#### 9.1 測試與優化
- [ ] 系統測試
- [ ] 性能優化
- [ ] 安全檢查

#### 9.2 生產部署
- [ ] 服務器環境配置
- [ ] SSL 證書配置
- [ ] 數據備份策略

## 當前進度總結 📊

### ✅ 已完成的功能
1. **基础架构**: Django 项目设置、数据库模型设计
2. **用户界面**: 现代化简约设计、统一色彩方案
3. **课程管理**: 完整的课程 CRUD 操作，支持 TinyMCE 富文本编辑
4. **用户管理**: 员工和学生管理系统，包含详细信息页面
5. **设施管理**: 设施与教室管理，1:n 关系实现
6. **数据模型**: 完整的学校管理系统数据结构
7. **表单系统**: Bootstrap 5 集成、一致的表单样式
8. **富文本编辑器**: TinyMCE 自托管方案，支持图片上传
9. **问题修复**: 教室创建表单状态字段显示问题已解决
10. **模組化重構**: 成功將單一核心應用重構為5個專業化應用
11. **資料庫遷移**: 完成 AUTH_USER_MODEL 變更和跨應用模型遷移
12. **功能驗證**: 所有模型、關係和基礎功能測試通過
13. **註冊系統**: 完整的註冊 CRUD 系統，包含公開註冊表單和內部管理界面
14. **預選課程註冊**: 課程詳情頁面註冊按鈕，支持預選課程的註冊 URL，提升用戶體驗
15. **Google Workspace 郵件系統**: 完整的 SMTP 郵件配置管理，包含前端設定界面、連接測試和郵件統計功能
16. **Twilio SMS 簡訊系統**: 完整的 SMS 配置管理系統，支援 Twilio 和自定義 SMS 網關，包含前端設定界面、連接測試、測試簡訊發送和統計功能

### 🔄 下一步重点任务
1. **考勤功能完善**: 完善教師考勤錄入界面和報表功能
2. **郵件模板系統**: 建立自動化郵件模板（歡迎郵件、註冊確認、課程提醒等）
3. **SMS 模板系統**: 建立自動化簡訊模板，整合到註冊流程和課程通知中
4. **WooCommerce 同步**: 建立與現有網站的數據同步
5. **系統測試**: 全面的功能測試和性能優化

### 📋 技术债务和改进计划
1. ~~需要创建更多模板文件 (学生、员工管理页面)~~ ✅ 已完成
2. ~~添加表单验证和错误处理~~ ✅ 已完成
3. ~~实现统一的 Bootstrap 表单样式~~ ✅ 已完成
4. ~~Course 描述字段添加富文本编辑器支持~~ ✅ 已完成
5. 实现数据分页和搜索功能
6. 添加单元测试
7. 创建缺失的列表和详情页面模板
8. 考虑升级到 CKEditor 5 以解决安全问题

## 開發標準

### 代碼質量
- 遵循 Django 最佳實踐
- 澳洲英語界面，中文註釋
- 模組化和可維護性
- 避免內聯 CSS/JS

### 設計原則
- 現代化簡約設計
- 統一色彩方案 (主色: #2563eb)
- 最少化圖標使用
- 專業的藝術學校管理系統外觀

### 📝 專案文檔更新 ✅ 已完成

#### CLAUDE.md 記憶更新 (2025-08-31)
- [x] **當前實現狀態總結**: 完整記錄項目架構、應用結構和實現功能
- [x] **模型和功能清單**: 詳細列出已完成的核心模型和功能特性  
- [x] **技術棧記錄**: 更新完整的技術選型，包含 TinyMCE 等新增元件
- [x] **URL 命名空間**: 記錄各應用的 URL 結構和命名規範
- [x] **模板組織問題**: 標識當前模板結構需要重組的問題
- [x] **架構文檔**: 完善模組化架構和自定義用戶模型的說明

---

*最後更新時間: 2025-09-01*

## 🚀 SMS 系統實施詳細文檔 (2025-09-01)

### 系統架構
SMS 系統按照現有郵件系統的架構模式實施，確保代碼一致性和可維護性：

#### 核心組件
1. **SMSSettings 模型**: 單例模式配置管理，支援 Twilio 和自定義 SMS 網關
2. **DynamicSMSBackend**: 動態後端，支援分層配置（資料庫 → 環境變量 → 默認配置）
3. **SMSLog 模型**: 完整的 SMS 發送記錄，包含狀態、錯誤信息和 Message SID
4. **管理界面**: 前端配置界面、連接測試和統計功能

#### 配置優先級
```
1. 資料庫配置 (SMSSettings.get_active_config())
2. 環境變量 (.env 文件)
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN  
   - TWILIO_FROM_NUMBER
3. Django 設定預設值
```

### 主要功能特性

#### 配置管理
- **多後端支援**: Twilio (完整實施) + 自定義 SMS 網關 (預留接口)
- **單例模式**: 確保只有一個活躍配置
- **前端界面**: Bootstrap 風格的配置表單，支援 JavaScript 動態表單切換
- **驗證機制**: E.164 格式手機號碼驗證，Twilio SID 格式驗證

#### 測試功能
- **連接測試**: AJAX 即時測試 Twilio 帳戶狀態
- **測試簡訊**: 支援向指定手機號碼發送測試簡訊
- **狀態回饋**: 即時顯示測試結果和錯誤信息

#### 日誌系統
- **完整記錄**: 收件人、內容、狀態、錯誤信息、Message SID
- **分類管理**: 按狀態、簡訊類型、收件人類型篩選
- **統計面板**: 發送成功/失敗統計，最近 7 天活動統計
- **詳細查看**: 模態框顯示完整簡訊內容和發送詳情

### 技術實施

#### 資料庫模型
```python
# core/models.py
class SMSSettings(models.Model):
    sms_backend_type = 'twilio' | 'custom_sms'
    account_sid, auth_token, from_number  # Twilio 配置
    api_url, api_key                      # 自定義網關配置
    sender_name, is_active               # 發送人信息和狀態
    test_status, test_message            # 連接測試結果

class SMSLog(models.Model):
    recipient_phone, recipient_type, content
    sms_type, status, error_message
    message_sid, backend_type, sent_at   # 新增字段
```

#### 後端架構
```python
# core/sms_backends.py
class DynamicSMSBackend:
    def __init__(self):
        self._initialize_config()  # 分層配置加載
        
    def send_messages(self, sms_messages):
        # 批量發送簡訊，支援自動日誌記錄
        
    def _log_sms(self, message, status, message_sid=None, error_message=None):
        # 統一日誌記錄接口
```

#### 視圖和表單
```python
# core/views.py
@login_required
def sms_settings_view(request):     # SMS 配置管理
def test_sms_connection(request):   # AJAX 連接測試  
def send_test_sms(request):         # AJAX 測試簡訊發送
def sms_logs_view(request):         # SMS 日誌查看

# core/forms.py
class SMSSettingsForm(forms.ModelForm):  # 配置表單，支援動態驗證
class TestSMSForm(forms.Form):           # 測試簡訊表單
```

#### URL 路由
```python
# core/urls.py
path('settings/sms/', views.sms_settings_view, name='sms_settings'),
path('settings/sms/test-connection/', views.test_sms_connection, name='test_sms_connection'),
path('settings/sms/send-test/', views.send_test_sms, name='send_test_sms'),
path('settings/sms/logs/', views.sms_logs_view, name='sms_logs'),
```

### 前端實施

#### 模板結構
```
templates/core/settings/
├── sms.html      # SMS 配置管理頁面
└── sms_logs.html # SMS 日誌查看頁面
```

#### 功能特性
- **響應式設計**: 完全符合現有 Bootstrap 風格
- **AJAX 互動**: 連接測試和測試簡訊發送不需頁面重載
- **動態表單**: JavaScript 根據後端類型動態顯示相關配置字段
- **即時驗證**: 前端 E.164 格式驗證，後端深度驗證
- **統計面板**: 視覺化統計數據展示
- **日誌篩選**: 支援多條件篩選和搜索

### 使用方式

#### 管理員配置
1. 訪問 `/core/settings/sms/` 進行 SMS 配置
2. 選擇 Twilio 後端，輸入 Account SID、Auth Token 和 From Number
3. 點擊「Test Connection」驗證配置
4. 使用「Send Test SMS」功能發送測試簡訊
5. 啟用配置並儲存

#### 程式化發送
```python
from core.sms_backends import send_sms, send_bulk_sms, SMSMessage

# 發送單條簡訊
send_sms('+61400123456', 'Hello from EduPulse!', 'general')

# 批量發送
messages = [
    SMSMessage('+61400123456', 'Welcome to Perth Art School!', 'welcome'),
    SMSMessage('+61400123457', 'Your class starts tomorrow.', 'course_reminder')
]
send_bulk_sms(messages)
```

### 安全考慮
- **權限控制**: 只有管理員 (superuser 或 role='admin') 可存取 SMS 設定
- **敏感信息保護**: Auth Token 以密碼字段形式輸入，不明文顯示
- **輸入驗證**: 多層驗證確保數據完整性和格式正確性
- **錯誤處理**: 完善的錯誤處理機制，避免敏感信息洩露

### 擴展性
- **多後端支援**: 架構設計支援未來添加更多 SMS 服務提供商
- **模板系統**: 預留接口支援簡訊模板功能
- **國際化**: 支援不同國家的手機號碼格式
- **API 集成**: 可輕鬆集成到註冊流程和課程通知系統

---
*版本: v3.5*
*當前階段: 學生頁面通知系統完成，實現完整的單個/批量郵件短信發送功能，包含系統級Reply-to配置、月度配額管理、智能聯繫人選擇邏輯和響應式通知界面*

## 🚀 學生頁面通知系統實施完成記錄 (2025-09-01)

### 系統架構與核心功能

**完整實施的通知系統**按照既定架構成功完成：

#### 1. 系統級配置增強 ✅ 已完成
- **EmailSettings模型擴展**: 添加 `reply_to_email` 字段作為系統級配置
- **動態Reply-to功能**: 郵件後端自動為所有發送的郵件添加reply-to頭部
- **配置優先級**: 配置的reply-to → from_email降級 → 環境變數降級
- **前端界面集成**: 郵件設定頁面添加Reply-to配置欄位

#### 2. 通知配額管理系統 ✅ 已完成
- **NotificationQuota模型**: 月度SMS/郵件配額管理，支援配額檢查和自動消耗
- **智能配額監控**: 配額超限檢查、使用量統計、剩餘配額計算
- **Django Admin配置**: 完整的管理界面，支援彩色使用率顯示和只讀統計欄位
- **即時配額顯示**: 前端JavaScript即時獲取和顯示配額狀況

#### 3. 通知發送系統 ✅ 已完成
- **NotificationForm**: 支援單個/批量、郵件/短信/混合發送的完整表單驗證
- **智能聯繫人選擇**: 基於enrollment form_data自動識別監護人/學生聯繫方式
- **發送視圖**: 完整的AJAX發送邏輯，包含錯誤處理和配額檢查
- **URL路由配置**: `/core/notifications/send/` 和 `/core/notifications/quotas/`

#### 4. 用戶界面設計 ✅ 已完成
- **學生詳情頁通知按鈕**: 在Quick Actions區域添加"Send Notification"按鈕
- **響應式模態框**: Bootstrap 5驅動的通知發送界面
- **配額視覺化**: 進度條顯示郵件/短信使用狀況，顏色警告系統
- **收件人確認**: 顯示實際聯繫人信息供用戶確認
- **即時字符計數**: SMS 160字符限制提醒和超限警告

#### 5. 智能功能特性 ✅ 已完成

##### 聯繫人智能選擇邏輯
- **Enrollment數據優先**: 從最新enrollment的form_data提取contact_info元數據
- **年齡相關處理**: 18歲以下使用監護人聯繫方式，18歲以上使用學生直接聯繫
- **數據降級機制**: enrollment數據 → Student模型數據 → 空值處理
- **聯繫人類型標識**: 自動識別並標記guardian/student聯繫類型

##### 通信功能增強
- **系統級Reply-to**: 所有郵件自動添加配置的reply-to頭部
- **SMS字符優化**: 自動截斷過長短信，保持160字符限制
- **消息格式化**: 郵件和短信不同的格式化模板
- **錯誤處理**: 完整的發送錯誤處理和用戶反饋

#### 6. 前端用戶體驗 ✅ 已完成
- **現代化界面**: Bootstrap 5組件，響應式設計
- **即時反饋**: 配額狀況、字符計數、發送狀態的即時更新
- **用戶友好**: 清晰的步驟指引，智能字段顯示/隱藏
- **錯誤處理**: 完善的前端錯誤提示和處理機制

### 技術實施

#### 後端實施
```python
# 核心模型
NotificationQuota: 月度配額管理，支援配額檢查和統計
EmailSettings: 系統級reply-to配置
DynamicEmailBackend: 自動添加reply-to頭部

# 核心視圖
send_notification_view: AJAX通知發送處理
get_notification_quotas: 配額信息API
_get_student_contact_info: 智能聯繫人選擇邏輯
```

#### 前端實施
```javascript
// 核心功能
openNotificationModal(): 模態框管理和數據加載
loadQuotaInfo(): 配額信息即時更新
getStudentContactDisplay(): 聯繫人信息展示
sendNotification(): AJAX發送處理
```

### 系統整合

#### 與既有系統整合
- **完美整合enrollment系統**: 使用form_data中的contact_info元數據
- **複用通信後端**: 利用既有的Email和SMS配置和發送邏輯
- **統一管理界面**: Django Admin統一配置入口

#### 安全和權限
- **Staff權限檢查**: 只有員工可存取通知功能
- **CSRF保護**: 所有AJAX請求包含CSRF令牌
- **輸入驗證**: 前端和後端雙重驗證

### 使用案例

#### 單個學生通知流程
1. 進入學生詳情頁面
2. 點擊"Send Notification"按鈕
3. 系統自動加載配額信息和聯繫人詳情
4. 選擇通知類型（郵件/短信/混合）
5. 輸入郵件主題和消息內容
6. 系統顯示實際收件人進行確認
7. 發送並獲得即時反饋

#### 批量通知支持
- 架構已預留批量功能接口
- 表單支援多學生ID處理
- 配額系統支援批量配額檢查

### 實施成果

通過本次實施，EduPulse獲得了：

1. **完整的通知系統**: 支援個別和批量發送，郵件和短信通道
2. **智能聯繫人管理**: 基於enrollment數據的年齡相關聯繫人選擇
3. **系統級Reply-to配置**: 統一的郵件回複管理
4. **配額控制系統**: 月度使用限制和成本控制
5. **現代化用戶界面**: 響應式、直觀的通知發送體驗
6. **完整的管理後台**: Django Admin配置界面

這個實施為Perth Art School提供了professional級別的學生通信管理系統，既滿足了immediate需求，也為future擴展奠定了solid foundation。