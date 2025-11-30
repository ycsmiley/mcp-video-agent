# 變更日誌 (ChangeLog)

## [2024-11-30 16:00] - 優化 Gemini 回應長度與新增並發控制

### 修改 (Modified)
- **`backend/modal_app.py`**:
  - 縮短 Gemini 回應長度：從 300-400 words 改為 150-200 words
  - 新增 `max_containers=5` 限制並發容器數量（成本控制）
  - 修正 `_internal_speak_text` 函數，新增 `audio_filename` 參數

- **`hf_space/app_standalone.py`**:
  - 同步更新 Gemini 回應長度限制

### 技術說明

**Gemini Prompt 調整**:
```python
# 之前
f"{query}\n\nPlease provide a detailed but focused response within 300-400 words..."

# 現在
f"{query}\n\nPlease provide a concise response within 150-200 words. Be direct and informative..."
```

**Modal 並發控制**:
```python
@app.function(
    ...
    max_containers=5  # 限制最多 5 個並發容器
)
```

**為什麼需要這些改變**:
1. 較短的回應 = 更快的 TTS 生成 = 更好的用戶體驗
2. 並發限制 = 成本可控 = 避免意外超支
3. Modal 內建 queue 機制會自動處理超過限制的請求

---

## [2024-11-30 15:00] - 新增 Modal Backend 整合與完整安全機制

### 新增 (Added)
- **`hf_space/app_with_modal.py`** (~350 行): Modal Backend 整合版本
  - 連動 Modal Functions (`_internal_analyze_video`, `_internal_speak_text`)
  - 整合 Modal Volume 進行影片持久化儲存
  - 使用 Modal Token 認證
  
- **安全機制**:
  - **Gradio 認證**: 使用 `auth` 參數要求登入
    - 可透過 `GRADIO_USERNAME` 和 `GRADIO_PASSWORD` 環境變數設定
    - 預設用戶名: `admin`
  
  - **速率限制 (Rate Limiting)**:
    - 基於記憶體的請求計數器
    - 可透過 `MAX_REQUESTS_PER_HOUR` 環境變數設定（預設: 10）
    - 每個用戶獨立計算配額
    - 自動清理過期記錄
    - 顯示剩餘請求數
  
  - **檔案大小限制**: 100MB 上限
  
  - **友善的錯誤訊息**: 
    - 超出速率限制時顯示剩餘配額
    - 連接 Modal 失敗時的清楚提示

- **`hf_space/SECURITY_SETUP.md`** (~300 行): 完整安全設定指南
  - Modal Backend 部署步驟
  - Modal Token 生成與設定
  - Gradio 認證設定
  - 速率限制配置
  - 成本估算與監控
  - 完整的故障排除指南
  - 最佳實踐建議

- **`hf_space/switch_to_modal.sh`**: 快速切換腳本
  - 自動備份獨立版本為 `app_standalone.py`
  - 啟用 Modal 整合版本
  - 顯示後續步驟提示

### 修改 (Modified)
- **`hf_space/requirements.txt`**: 更新依賴
  - 移除 `google-genai` 和 `elevenlabs`（由 Modal backend 處理）
  - 新增 `modal>=0.60.0`
  - 保留 `gradio>=6.0.1`

### 技術細節 (Technical Details)

#### 架構變更
**之前（獨立版本）**:
```
HF Space: Gradio + Gemini API + ElevenLabs API
```

**現在（Modal 整合版本）**:
```
HF Space (前端 + 認證 + 速率限制)
    ↓
Modal Backend (Gemini + ElevenLabs + Volume)
```

#### 安全機制原理

**1. Gradio 認證**:
```python
def authenticate(username, password):
    return username == GRADIO_USERNAME and password == GRADIO_PASSWORD

demo.launch(auth=authenticate)
```

**2. 速率限制**:
```python
class RateLimiter:
    def __init__(self, max_requests_per_hour=10):
        self.max_requests = max_requests_per_hour
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id):
        # 清理過期請求（超過 1 小時）
        # 檢查是否超過限制
        # 記錄新請求
```

**3. 用戶識別**:
- 使用 Gradio 的 `request.username`
- 每個登入用戶有獨立配額

#### 必要的環境變數 / Secrets

**HF Space Secrets**:
- `MODAL_TOKEN_ID` - Modal 認證 ID（必填）
- `MODAL_TOKEN_SECRET` - Modal 認證 Secret（必填）
- `GRADIO_PASSWORD` - Gradio 登入密碼（必填，用於安全）
- `GRADIO_USERNAME` - Gradio 用戶名（選填，預設: admin）
- `MAX_REQUESTS_PER_HOUR` - 每小時請求限制（選填，預設: 10）

**Modal Secrets** (在 Modal 設定，不是 HF Space):
- `GOOGLE_API_KEY` - Gemini API Key
- `ELEVENLABS_API_KEY` - ElevenLabs API Key

#### 成本控制

**有速率限制時** (MAX_REQUESTS_PER_HOUR=10):
- 單一用戶: 每天最多 240 requests
- 估計成本: **$5-15/月** ✅ 可控

**無限制時**:
- 風險: 成本可能爆炸 ❌ 不建議

### 部署流程 (Deployment)

1. 部署 Modal backend: `modal deploy backend/modal_app.py`
2. 生成 Modal token: `modal token new`
3. 切換版本: `cd hf_space && ./switch_to_modal.sh`
4. 設定 HF Space Secrets
5. 推送: `git push hf main --force`

### 使用場景 (Use Cases)

**獨立版本** (`app_standalone.py`):
- ✅ 快速 Demo
- ✅ 個人使用
- ✅ 不需持久化儲存

**Modal 整合版本** (`app_with_modal.py`):
- ✅ 正式環境
- ✅ 需要持久化儲存
- ✅ 多用戶使用（有認證）
- ✅ 成本控制重要
- ✅ 團隊協作

---

## [2024-11-30 23:50] - 針對已存在的 HF Space 優化部署流程

### 修改 (Modified)
- **`hf_space/deploy.sh`**: 適配已存在的 Space
  - 接受完整 Space 路徑作為參數（例如：`MCP-1st-Birthday/Video-Agent-MCP`）
  - 移除自動創建 Space 的邏輯（因為 Space 已存在）
  - 優化 remote URL 處理
  - 自動計算正確的 MCP Server URL
  - 新增 Access Token 使用提示

### 新增 (Added)
- **`hf_space/PUSH_TO_HF.md`**: 針對用戶特定 Space 的推送指南
  - 包含用戶的實際 Space 名稱（`MCP-1st-Birthday/Video-Agent-MCP`）
  - 兩種推送方式（自動化腳本 vs 手動命令）
  - Access Token 取得與使用說明
  - 推送後設定指南
  - MCP Server URL 配置
  - 完整的故障排除指南
  - 推送前後檢查清單

### 使用說明 (Usage)

#### 使用自動化腳本（推薦）:
```bash
cd hf_space
./deploy.sh MCP-1st-Birthday/Video-Agent-MCP
```

#### 或使用手動命令:
```bash
cd hf_space
git init
git remote add hf https://huggingface.co/spaces/MCP-1st-Birthday/Video-Agent-MCP
git add .
git commit -m "Deploy MCP Video Agent"
git push hf main --force
```

### 重要提醒
- 推送時使用 **HF Access Token** 作為密碼（不是帳號密碼）
- 使用 `--force` 推送來覆蓋 Space 的預設初始文件
- 推送後必須在 Space Settings → Secrets 設定 `GOOGLE_API_KEY`

---

## [2024-11-30 23:45] - HF Space 完整部署套件準備完成

### 新增 (Added)

#### 核心程式碼
- **`hf_space/app.py`** (13KB, ~350 行): 創建獨立的 HF Space 部署版本
  - 整合前端 Gradio 界面與後端 Gemini API 邏輯
  - 實作彈性 API Key 載入機制（優先從環境變數讀取）
  - 使用 Gemini 2.5 Flash 的隱式快取（Implicit Caching）
  - 智能檔案快取系統（避免重複上傳相同影片）
  - 完整的錯誤處理與進度提示
  - 語音優先的使用者體驗（Audio-first UX）
  - Base64 編碼音檔嵌入（確保音檔可在聊天記錄中播放）
  
- **`hf_space/requirements.txt`** (53B): HF Space 所需的 Python 套件清單
  - `gradio>=6.0.1`
  - `google-genai>=1.0.0`
  - `elevenlabs>=1.0.0`

- **`hf_space/.gitignore`**: HF Space 專用的 .gitignore
  - 忽略暫存的音檔與影片檔
  - 忽略 Python 編譯檔
  - 忽略環境變數檔

#### 說明文件 (Documentation)
- **`hf_space/README.md`** (2.8KB): HF Space 的公開說明文件 (Card)
  - 功能介紹與特色
  - 使用方式說明
  - MCP Server 整合教學
  - 技術架構圖
  - API Key 設定指南
  - 快取機制詳解
  - 技術堆疊說明

- **`hf_space/QUICKSTART.md`** (4.1KB): 5 分鐘快速上手指南
  - 3 步驟快速部署
  - API Key 取得方式 (Google AI Studio, ElevenLabs)
  - Claude Desktop 整合教學
  - 使用範例
  - 常見問題快速解答
  - 成本估算 (輕量/中度/重度使用)

- **`hf_space/DEPLOYMENT.md`** (3.3KB): 詳細的部署指南
  - 逐步部署流程 (Step-by-Step)
  - 檔案上傳方式
  - Secrets 設定詳解
  - MCP Server 完整設定 (macOS/Linux/Windows)
  - 詳細故障排除指南
  - 成本與效能監控說明
  - API 使用率限制說明

- **`hf_space/CHECKLIST.md`** (3.5KB): 完整的部署檢查清單
  - 部署前環境檢查
  - 部署步驟清單 (可勾選)
  - 功能測試項目 (Web 界面 + MCP Server)
  - 故障排除檢查點
  - 效能檢查指標
  - 部署完成確認表單

- **`hf_space/INDEX.md`** (6KB): 文件導航與索引
  - 快速導航表格 (目標 → 文件 → 預計時間)
  - 所有文件的詳細說明
  - 學習路徑規劃 (快速上手/深入了解/本地開發)
  - 相關連結整理
  - 文件統計資訊

#### 工具腳本 (Scripts)
- **`hf_space/deploy.sh`** (2.5KB, 可執行): 自動化部署腳本
  - 一鍵部署到 Hugging Face Space
  - 自動檢查 HF 登入狀態
  - 自動建立 Space (如果不存在)
  - 自動初始化 Git 儲存庫
  - 自動新增 HF Remote
  - 智能錯誤處理與提示
  - 部署完成後顯示後續步驟

- **`hf_space/test_local.sh`** (2.1KB, 可執行): 本地測試腳本
  - 檢查 API Keys 是否設定
  - 自動建立/啟用虛擬環境
  - 自動安裝依賴套件
  - 啟動 Gradio 本地伺服器
  - 友善的錯誤提示與指引

#### 總計
- **9 個檔案**, **~32KB**
- **說明文件**: 5 份完整指南 (從快速上手到深度解析)
- **工具腳本**: 2 個自動化腳本 (部署 + 測試)
- **核心代碼**: 1 個完整的 Gradio + Gemini 整合應用

### 修改 (Modified)
- **`README.md`**: 更新專案主說明文件
  - 更新架構說明（新增 HF Space 獨立部署選項）
  - 新增兩種部署方式的比較
  - 新增效能與成本分析
  - 新增 MCP Server 整合說明
  - 更新專案結構說明

- **`backend/modal_app.py`**: 確保使用 Gemini 2.5 Flash
  - 修正模型名稱為 `gemini-2.5-flash`
  - 確保 Context Caching 使用正確的模型版本
  - 優化快取效能（最低 1024 tokens 才會觸發顯式快取）

### 技術細節 (Technical Details)

#### Gemini 2.5 Flash 快取策略
- **隱式快取 (Implicit Caching)**: 
  - 使用 `google-genai>=1.0.0` SDK
  - 上傳檔案到 Gemini Files API 後，自動快取 1 小時
  - 後續查詢會自動使用快取，無需手動管理
  - 成本降低 90%，速度提升 2-3 倍

- **顯式快取 (Explicit Caching)** (Modal backend):
  - 使用 `client.caches.create()` 手動建立快取
  - 可自訂 TTL (Time-to-Live)
  - 適合需要精細控制的場景
  - 最低要求 1024 tokens 才會生效

#### 部署架構差異

**HF Space 獨立部署** (推薦用於 Demo):
- ✅ 部署簡單（5 分鐘完成）
- ✅ 免費額度可用
- ✅ 自動擴展
- ⚠️ 影片暫存（重啟後消失）
- ⚠️ 適合輕量使用

**Modal + HF Frontend** (推薦用於正式環境):
- ✅ 持久化儲存（Modal Volume）
- ✅ 高度可擴展
- ✅ 按用量付費
- ⚠️ 需要 Modal 帳號
- ⚠️ 設定較複雜

### 使用說明 (Usage)

#### 快速部署到 HF Space:
```bash
cd hf_space
./deploy.sh YOUR_HF_USERNAME
```

#### 設定 API Keys (在 HF Space Settings → Secrets):
- `GOOGLE_API_KEY`: 從 [Google AI Studio](https://aistudio.google.com/apikey) 取得
- `ELEVENLABS_API_KEY`: 從 [ElevenLabs](https://elevenlabs.io) 取得（選用）

#### 作為 MCP Server 使用:
在 Claude Desktop 設定檔中新增:
```json
{
  "mcpServers": {
    "video-agent": {
      "url": "https://YOUR_USERNAME-mcp-video-agent.hf.space/sse"
    }
  }
}
```

### 已知限制 (Known Limitations)
1. HF Space 版本的影片檔案不會持久化保存
2. 免費版 ElevenLabs 有 10 RPM 速率限制
3. Gemini 2.5 Flash 免費版有 10 RPM 速率限制
4. 影片大小限制為 100MB

### 下一步計畫 (Next Steps)
- [ ] 新增影片字幕提取功能
- [ ] 支援多語言界面
- [ ] 新增影片摘要功能
- [ ] 整合更多 TTS 提供商
- [ ] 新增影片片段搜尋功能

---

## [2024-11-30 22:30] - Gemini 2.5 Flash Context Caching 實作

### 修改 (Modified)
- **`backend/modal_app.py`**: 整合 Gemini 原生 Context Caching
  - 移除 LlamaIndex 依賴
  - 實作 `_internal_create_cache` 函數（建立快取）
  - 實作 `_internal_view_cache` 函數（查看快取狀態）
  - 實作 `_internal_delete_cache` 函數（刪除快取）
  - 修改 `_internal_analyze_video` 使用 cached_content
  - 使用 `gemini-2.5-flash` 模型
  - 最佳化 Token 用量（最低 1024 tokens 才快取）

### 技術說明
- Gemini 2.5 Flash 支援最低 1024 tokens 的顯式快取
- 快取可大幅降低成本（約 90%）並提升速度（2-3 倍）
- 快取有效期（TTL）預設 1 小時，可自訂

---

## [2024-11-30 20:15] - 語音輸出完整性修正

### 修改 (Modified)
- **`backend/modal_app.py`**: 調整 Gemini 回應長度與 TTS 限制
  - Gemini prompt 要求 300-400 字的詳細回應
  - TTS `max_chars` 提升至 2500 字元
  - 確保完整文字都能轉換為語音

---

## [2024-11-30 19:45] - 文字溢位與音檔下載問題修正

### 修改 (Modified)
- **`frontend/app.py`**: 修正文字顯示與音檔處理
  - 將 `<pre>` 改為 `<div>` 並套用 CSS 自動換行
  - 新增 `time.sleep(3)` 等待 TTS 檔案生成
  - 實作重試機制（最多 3 次）確保音檔完整下載
  - 確保音檔大小至少 1KB 才視為有效

---

## [2024-11-30 18:30] - RAG 輸出優化（移除時間戳記）

### 修改 (Modified)
- **`backend/modal_app.py`**: 調整 RAG 模式的 Gemini prompt
  - 明確指示 Gemini 不要提及時間戳記（除非使用者明確詢問）
  - 改善自然語言回應品質

---

*所有時間戳記使用本地系統時間（macOS darwin 24.3.0, US Pacific Time）*

