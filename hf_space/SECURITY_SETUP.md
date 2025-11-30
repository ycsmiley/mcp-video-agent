# 🔒 安全設定指南

## 架構：HF Space + Modal Backend

```
┌─────────────────┐          ┌─────────────────┐
│   HF Space      │  ────→   │     Modal       │
│   (前端+認證)    │          │   (後端處理)     │
│                 │          │   - Gemini API  │
│   🔒 認證       │          │   - ElevenLabs  │
│   ⏱️ 速率限制   │          │   - Volume      │
└─────────────────┘          └─────────────────┘
```

---

## 🚀 步驟 1: 部署 Modal Backend

```bash
cd /Users/jimmmmmmmmmmyc./Desktop/mcp-video-agent/backend
modal deploy modal_app.py
```

確認部署成功後，你會看到：
```
✓ Created _internal_analyze_video
✓ Created _internal_speak_text
✓ App deployed!
```

---

## 🔐 步驟 2: 設定 Modal Token

### 2.1 生成 Modal Token

```bash
modal token new
```

這會生成兩個值：
- `MODAL_TOKEN_ID` (例如: `ak-xxx`)
- `MODAL_TOKEN_SECRET` (例如: `as-xxx`)

### 2.2 在 HF Space 設定 Secrets

前往: https://huggingface.co/spaces/MCP-1st-Birthday/Video-Agent-MCP/settings

在 **Repository secrets** 新增：

```
Name: MODAL_TOKEN_ID
Value: [你的 Modal Token ID]

Name: MODAL_TOKEN_SECRET
Value: [你的 Modal Token Secret]
```

---

## 🔒 步驟 3: 設定認證機制

### 3.1 設定 Gradio 登入密碼

在 HF Space Secrets 新增：

```
Name: GRADIO_PASSWORD
Value: [設定一個強密碼，例如: MySecurePass123!]
```

**注意**: 
- 如果不設定此密碼，任何人都可以使用你的 Space
- 用戶名固定為 `admin`（可在代碼中修改）

### 3.2 (選用) 自訂用戶名

```
Name: GRADIO_USERNAME
Value: [自訂用戶名，預設是 admin]
```

---

## ⏱️ 步驟 4: 設定速率限制

### 4.1 限制每小時請求數

在 HF Space Secrets 新增：

```
Name: MAX_REQUESTS_PER_HOUR
Value: 10
```

**建議值**:
- 個人使用: `10-20`
- 小團隊: `50-100`
- 公開展示: `5-10`

### 4.2 原理

- 每個用戶（根據登入帳號）有獨立的請求配額
- 計算過去 1 小時內的請求數
- 超過限制會顯示友善錯誤訊息
- 自動清理過期記錄

---

## 🛡️ 步驟 5: 其他安全措施

### 5.1 設為 Private Space（最強保護）

1. 前往 Space Settings
2. 將 **Visibility** 改為 **Private**
3. 只有你和授權的協作者可以訪問

### 5.2 監控用量

**Gemini API 用量**:
- 前往: https://console.cloud.google.com/
- 查看 API 使用量和成本

**Modal 用量**:
```bash
modal app logs mcp-video-agent
```

**ElevenLabs 用量**:
- 前往: https://elevenlabs.io/app/usage

### 5.3 設定成本警報

**Google Cloud**:
1. 前往 Billing → Budgets & alerts
2. 設定每日/每月預算
3. 超過 80% 會收到 email 警報

**Modal**:
1. 前往 Modal Dashboard
2. Settings → Billing
3. 設定用量警報

---

## 📝 步驟 6: 更新 HF Space 代碼

### 6.1 重新命名檔案

```bash
cd /Users/jimmmmmmmmmmyc./Desktop/mcp-video-agent/hf_space
mv app.py app_standalone.py
mv app_with_modal.py app.py
```

### 6.2 更新 requirements.txt

確保包含 Modal:

```
gradio>=6.0.1
modal>=0.60.0
```

### 6.3 推送更新

```bash
git add app.py requirements.txt
git commit -m "Switch to Modal backend with security"
git push hf main --force
```

---

## ✅ 步驟 7: 驗證設定

### 7.1 測試認證

1. 訪問你的 Space URL
2. 應該會看到登入畫面
3. 使用設定的用戶名/密碼登入

### 7.2 測試速率限制

1. 連續提交多個請求
2. 超過限制後應該看到：
   ```
   ⚠️ Rate limit exceeded. You have 0 requests remaining this hour.
   ```

### 7.3 測試 Modal 連接

1. 上傳影片
2. 提問
3. 應該看到：
   ```
   📤 Uploading video...
   🤔 Analyzing video with Gemini...
   🗣️ Generating audio response...
   ```

---

## 🔧 完整 Secrets 清單

在 HF Space Settings → Repository secrets 應該有：

### 必填（Modal Backend）:
```
MODAL_TOKEN_ID          # Modal 認證 ID
MODAL_TOKEN_SECRET      # Modal 認證 Secret
```

### 必填（安全）:
```
GRADIO_PASSWORD         # Gradio 登入密碼
```

### 選填（自訂）:
```
GRADIO_USERNAME         # Gradio 用戶名（預設: admin）
MAX_REQUESTS_PER_HOUR   # 每小時請求限制（預設: 10）
```

**注意**: Modal backend 的 API keys (GOOGLE_API_KEY, ELEVENLABS_API_KEY) 
應該設定在 **Modal Secrets** 而不是 HF Space Secrets。

---

## 🆘 故障排除

### "Failed to connect to Modal backend"

**檢查**:
1. Modal app 是否已部署？執行 `modal app list`
2. MODAL_TOKEN_ID 和 MODAL_TOKEN_SECRET 是否正確？
3. Modal token 是否過期？重新生成

**解決**:
```bash
modal token new  # 生成新 token
# 更新 HF Space Secrets
```

### "Authentication failed"

**檢查**:
1. GRADIO_PASSWORD 是否已設定？
2. 用戶名是否正確？（預設: admin）

### "Rate limit exceeded" 太頻繁

**解決**:
增加 MAX_REQUESTS_PER_HOUR 的值

---

## 💰 成本估算

### 有速率限制時（10 req/hr/user）:

**單一用戶**:
- 每天: 最多 240 requests
- 每月: 最多 ~7,200 requests
- 估計成本: **$5-15/月**

**多用戶（10 用戶）**:
- 每月: 最多 ~72,000 requests
- 估計成本: **$50-150/月**

### 建議:

1. **開始時**: 設定 `MAX_REQUESTS_PER_HOUR=10`
2. **監控一週**: 查看實際用量
3. **調整**: 根據需求增加或減少
4. **設定警報**: 避免意外超支

---

## 🎯 最佳實踐

### 安全性:
- ✅ 啟用 Gradio 認證
- ✅ 設定速率限制
- ✅ 定期監控用量
- ✅ 使用 Private Space（重要項目）
- ✅ 定期更換密碼

### 成本控制:
- ✅ 設定每小時/每日限制
- ✅ 在 Google Cloud 設定預算警報
- ✅ 使用 Gemini Context Caching（減少 90% 成本）
- ✅ 監控異常用量

### 用戶體驗:
- ✅ 清楚顯示剩餘請求數
- ✅ 友善的錯誤訊息
- ✅ 提供使用指南

---

**設定完成後，你的 Space 將會安全且成本可控！** 🎉

