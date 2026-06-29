# 職場短影音「半自動內容工廠」

本機網頁 App：選主題（或全自動出題）→ 自動產腳本 → 你拿角色圖＋口播語音去 Kling 做對口型 avatar 影片 → 回傳 → App 自動上字幕、轉 9:16、疊開場問題字卡 → 成果畫廊看片下載 → 手動發 IG。

腳本／字幕／合成全程 $0（Groq 免費腳本 + edge-tts 免費語音 + 本機 Whisper/FFmpeg）；avatar 那步用 Kling（先手動，免費版可能有浮水印）。每個環節都是可抽換 provider，日後要升級全自動只改設定。

> avatar 工具選擇：原本規劃 HeyGen，因免費版浮水印＋下載受限已棄用，改用 **Kling 對口型**（支援中文、可鎖定同一張臉、能做走動運鏡）。

## 安裝（Windows / PowerShell）

> ⚠️ 兩個關鍵前置：
> 1. **要用 Python 3.12，不要用最新的 3.13/3.14**：faster-whisper 的依賴（onnxruntime / av）在太新的 Python 可能沒有對應套件。
> 2. **ffmpeg 要能用字幕功能**：本工具需要 `subtitles` 與 `drawtext` filter，才能燒字幕與疊開場字卡。

```powershell
# 1. 安裝系統工具
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg -e

# 安裝完請關掉 PowerShell 重開，讓 PATH 生效
```

重開 PowerShell 後驗證：

```powershell
py -3.12 --version
ffmpeg -version
ffmpeg -hide_banner -filters | Select-String "subtitles|drawtext"
```

如果最後一行看不到 `subtitles` 和 `drawtext`，請改裝 FFmpeg full build，並確認 `ffmpeg.exe` 所在的 `bin` 資料夾已加入 PATH。

建立 Python 環境：

```powershell
# 從 repo 根目錄進入真正的 App 資料夾
cd .\career-reels-factory

py -3.12 -m venv .venv

# 如果啟用 venv 被 PowerShell 執行政策擋住，先跑這行，只影響目前視窗
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

也可以直接用專案附的安裝腳本：

```powershell
cd .\career-reels-factory
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_windows.ps1
```

設定金鑰：

```powershell
Copy-Item .env.example .env
notepad .env
```

在 `.env` 裡填入：

```dotenv
GROQ_API_KEY=你的 Groq key
SCRIPT_PROVIDER=auto
```

Windows 通常會自動偵測微軟正黑體；如果字卡或字幕中文字型不正常，可在 `.env` 加上：

```dotenv
CJK_FONT=C:/Windows/Fonts/msjh.ttc
CJK_FONT_NAME=Microsoft JhengHei
```

## 啟動（Windows / PowerShell）

```powershell
cd .\career-reels-factory
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

或直接執行：

```powershell
.\run_windows.ps1
```

開瀏覽器：

```text
http://localhost:8000
```

> 第一次合成影片時，faster-whisper 會自動下載語音模型（約數百 MB），需要網路、會等一下；之後就快。

## 安裝（macOS）

> ⚠️ 兩個關鍵前置跟一般直覺不同，照下面做：
> 1. **要用 Python 3.12，不要用最新的 3.13/3.14**：faster-whisper 的依賴（onnxruntime / av）在太新的 Python 還沒有預編套件，會裝不起來。
> 2. **ffmpeg 要用「含字幕功能」的版本**：homebrew 預設的 `brew install ffmpeg` 沒有燒字幕（libass）與字卡（libfreetype）功能，本工具兩者都要。用下面的 homebrew-ffmpeg tap。

```bash
# 1. 系統工具
#   含字幕功能的 ffmpeg（會從原始碼編譯，約 10-15 分鐘，跑一次就好）
brew install homebrew-ffmpeg/ffmpeg/ffmpeg
#   Python 3.12
brew install python@3.12

# 驗證 ffmpeg 真的有字幕功能（要看到 subtitles 和 drawtext）
ffmpeg -hide_banner -filters | grep -E "subtitles|drawtext"

# 2. Python 環境（用 3.12 建 venv）
cd career-reels-factory
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 設定金鑰
cp .env.example .env
# 編輯 .env，填入免費的 GROQ_API_KEY（到 https://console.groq.com 申請）
# 或填 ANTHROPIC_API_KEY 改用 Claude（繁中更好）
```

## 啟動（macOS）

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
# 開瀏覽器 http://localhost:8000
```

> 第一次合成影片時，faster-whisper 會自動下載語音模型（約數百 MB），需要網路、會等一下；之後就快。

## 使用流程

0. （一次性）用 ChatGPT 生一張固定「角色圖」= 虛擬前輩的臉，之後每支都用同一張
1. 在網頁選「內容線」「主題」（皆可留空 → AI 自動出題）「調整方向」→ 按產生腳本
2. 任務卡出現腳本，按 **📋 複製口播逐字稿（貼 Kling）**；另有 **📋 複製完整腳本**
3. 到 Kling 用「角色圖＋口播語音（逐字稿或 edge-tts 語音檔）」做對口型影片、下載 mp4
4. 回到網頁，在該任務卡上傳 mp4
5. App 自動上字幕＋疊開場問題字卡＋轉直式，完成後在卡片預覽、下載
6. 手動上傳到 IG Reels

## 調整

- `config.json`：人設語氣（`persona.style`）、內容線、字幕樣式、輸出解析度、Whisper 模型大小
- 換腳本 LLM：`.env` 的 `SCRIPT_PROVIDER`（auto / groq / claude）

## 之後升級（架構已預留）

- avatar 全自動：新增 `app/providers/avatar/kling.py`（串 Kling API，約 $0.07–0.14/秒、lipsync ~$0.084/支；官方預付包 $9.80 起，或 fal.ai／kie.ai 等三方），讓步驟 3 也自動
- 口播語音整進工具（產腳本時順便用 edge-tts 吐 mp3）；之後可換 ElevenLabs、自動排程發文（IG Graph API）

## 專案結構

```
app/
  main.py            FastAPI：UI + API
  pipeline.py        流程編排 + job 狀態機
  jobs.py            job 持久化
  providers/script/  腳本 provider（claude / groq，可抽換）
  providers/prompts.py  人設 + 格式模板
  media/captions.py  faster-whisper 轉字幕
  media/compose.py   FFmpeg 合成
static/              前端（表單 + 成果畫廊）
data/                jobs / incoming / output（自動建立）
```
