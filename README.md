# Discord Channel Backup（Discord 頻道備份工具）

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Backup Discord channel / thread **history + attachments** with **Python + discord.py**.

GUI (CustomTkinter) · CLI · **繁體中文 / English** · multi-channel batch · media folders · naming schemes · manual rate delays.

> **Bot Token only** (official Bot API). Do **not** use user tokens / self-bots (against Discord ToS).

## 功能一覽

| 功能 | 說明 |
|------|------|
| GUI | `gui.py` / `run_gui.bat`，含進度列與日誌 |
| 雙語 | 繁體中文 / English |
| 首次教學 | 第一次啟動導覽；之後可手動重開 |
| 多頻道批次 | 一次多個 Channel ID，登入一次依序備份 |
| 輸出資料夾 | 以**頻道／討論串名稱**命名（不用 ID） |
| 媒體分類 | 可選 `images` / `gifs` / `videos` / `audio` / `files` |
| 附件命名 | 下拉多種方案（純數字、日期-序號、完整…） |
| 限速延遲 | 可調附件／訊息／頻道間秒數 |
| 已存 Bot | 本機加密（使用者目錄，不進 git） |
| CLI | `backup.py` |
| 容錯 | rate limit、重試、checkpoint、續傳 |

## 環境需求

- Windows / macOS / Linux
- **Python 3.10+**
- 可連線 Discord API 的網路

## 快速開始（GUI，推薦）

### Windows 一鍵

1. 安裝 [Python 3.10+](https://www.python.org/downloads/)，安裝時勾選 **Add python.exe to PATH**
2. 雙擊專案內的 **`run_gui.bat`**
   - 第一次會自動建立虛擬環境並安裝依賴
   - 之後會開啟圖形介面
3. 若是第一次使用，會出現**教學視窗**，照步驟設定 Bot
4. 在主畫面貼上 Token、Channel ID，按 **開始備份**

### 手動啟動 GUI

```bash
cd discord-channel-backup
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
python gui.py
```

## 首次教學會帶你做什麼

1. 認識工具能做什麼  
2. **伺服器已有 Bot 的快速設定**（Token、Intent、權限、Channel ID、開始擷取）  
3. 或從頭：**建立 Bot** → Intent → 邀請 → Channel ID → 開始備份  

本機偏好與（可選）已存 Bot 存在**使用者家目錄**（**不在本 repo 內**）：

```
%USERPROFILE%\.discord_channel_backup\     # Windows
~/.discord_channel_backup/                 # macOS / Linux
  settings.json    # 語言、命名、延遲等（不含 Token）
  bots.enc.json    # 可選：加密後的已存 Bot Token
```

請勿把上述資料夾複製進 GitHub 專案。之後可從主畫面 **「首次教學」** 重新開啟導覽。

## Bot 設定（精簡版）

### 伺服器裡已經有 Bot（快速）

1. 開啟 [Developer Portal](https://discord.com/developers/applications)，進入**該 Bot 所屬的 Application**  
2. **Bot** → **Reset Token / Copy** 複製 **Bot Token**（本工具登入用的是 Token，不是 Application ID / Bot 使用者 ID）  
3. 同頁開啟 **MESSAGE CONTENT INTENT** 並 Save  
4. Discord 伺服器：確認 Bot 角色有「檢視頻道」「讀取訊息歷史」，且能看到目標頻道  
5. 開發者模式 → 右鍵頻道 → **複製頻道 ID**  
6. 本工具貼上 **Token + Channel ID** → 開始備份  

> 若你沒有該 Application 的管理權限，就拿不到 Token，請改用自己新建的 Bot。

### 從頭建立 Bot

1. [Discord Developer Portal](https://discord.com/developers/applications) → New Application → Bot  
2. 複製 **Token**  
3. 開啟 **MESSAGE CONTENT INTENT** 並儲存  
4. OAuth2 → URL Generator：`bot` + `View Channels` + `Read Message History` → 邀請到伺服器  
5. Discord 設定 → 進階 → 開發者模式 → 右鍵頻道 → 複製 ID  

**論壇（Forum）：** 請用**討論串（Thread）ID**，不要用論壇父頻道 ID。

## 圖形介面操作

1. **語言**：頂部 **Developer Portal** 旁的下拉可切換 **繁體中文 / English**（會記住）  
2. **Bot Token**：貼上（可「顯示」／「測試 Token」）  
   - 右側 **已存 Bot** 下拉：載入曾經驗證過的 Bot  
   - **管理**：列表中每筆右側 **✕** 可永久刪除該 Bot 的加密 Token  
   - Token 存在 `%USERPROFILE%\.discord_channel_backup\bots.enc.json`（Windows 優先 DPAPI 加密），**不會**寫進專案目錄或 README  
3. **Channel ID**：單個或多個（每行／逗號）  
4. **輸出目錄**、**附件命名**、**詳細日誌**  
5. **媒體分類存放**（可選）：勾選後每個討論串內  
   `media/images`、`media/gifs`、`media/videos`、`media/audio`、`media/files`  
6. **限速延遲（秒）**（可選）：每個附件後 / 每則訊息後 / 頻道之間  
   - 預設 `0`（不額外等待；discord.py 仍會自動處理 HTTP 429）  
   - 想更保守可設附件 `0.3`–`1.0`  
7. **開始備份** / **取消** / **開啟輸出資料夾**  

CLI 延遲範例：

```bash
python backup.py --token TOKEN --channel ID --delay-download 0.5 --delay-message 0.1
```

多頻道時輸出結構（資料夾以 **頻道／討論串名稱** 命名，不用 ID）：

```
backups/
└── batch_20260725_143052/
    ├── summary.json          # 批次摘要
    ├── batch.log
    ├── 一般討論/
    │   ├── messages.json
    │   ├── media/
    │   └── errors.log
    └── 活動公告/
        ├── messages.json
        └── media/
```

單頻道時：

```
backups/   （或你指定的輸出目錄，例如 Desktop）
└── 我的討論串名稱/
    ├── messages.json
    ├── media/
    └── errors.log
```

若同名資料夾已存在，會自動變成 `名稱_2`、`名稱_3`…

## 命令列用法

```bash
# 互動式
python backup.py

# 單頻道
python backup.py --token YOUR_TOKEN --channel 111

# 多頻道批次
python backup.py --token YOUR_TOKEN --channels 111,222,333

# 指定輸出根目錄
python backup.py --token YOUR_TOKEN --channels 111,222 -o D:\DiscordBackups

# 續傳（單頻道）
python backup.py --token YOUR_TOKEN --channel 111 --resume backups\channel_111_...

# 從 CLI 開 GUI
python backup.py --gui
```

### 參數一覽

| 參數 | 說明 |
|------|------|
| `--token` / `-t` | Bot Token |
| `--channel` / `-c` | 單一 Channel ID |
| `--channels` | 多個 ID（逗號或空白分隔） |
| `--output` / `-o` | 輸出根目錄（預設 `backups`） |
| `--resume` / `-r` | 既有備份目錄，續傳用 |
| `--gui` | 啟動圖形介面 |
| `-h` | 說明 |

## 輸出格式

### 附件命名（可選）

GUI 下拉選單或 CLI `--naming`：

| 方案 key | 範例 |
|----------|------|
| `seq` | `1.png`, `2.jpg` |
| `seq_padded` | `000001.png`, `000002.jpg` |
| `date_seq` | `20260726-1.png`, `20260726-2.jpg`（同日遞增） |
| `date_time_seq` | `20260726_143052-1.png` |
| `seq_original` | `1_photo.png` |
| `full`（預設） | `000001_20260726_143052_photo.png` |

時間皆為訊息建立時間（**UTC**）。同名時自動加 `_2`、`_3` 避免覆蓋。

```bash
python backup.py --token TOKEN --channel 111 --naming date_seq
python backup.py --token TOKEN --channel 111 --naming seq --quiet
```

### `messages.json` 摘要

```json
{
  "meta": {
    "channel_id": "...",
    "channel_name": "...",
    "guild_id": "...",
    "guild_name": "...",
    "exported_at": "ISO8601",
    "message_count": 100,
    "attachment_count": 20,
    "attachment_failed": 0,
    "timezone": "UTC",
    "tool_version": "1.1.0"
  },
  "messages": [ /* 時間由舊到新 */ ]
}
```

每則訊息含：作者、內容、附件（含 `local_path`）、embeds、reactions、回覆 reference、stickers metadata 等。

> 第一版記錄 sticker metadata，不強制下載貼圖資源。

## 專案結構

```
discord-channel-backup/
├── gui.py              # GUI + tutorial + i18n wiring
├── backup.py           # CLI
├── core.py             # Backup engine
├── bot_store.py        # Encrypted saved bots (user home only)
├── settings_store.py   # Non-secret prefs (user home only)
├── i18n.py             # zh-TW / English strings
├── requirements.txt
├── run_gui.bat         # Windows launcher
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
├── README.md
└── .gitignore
```

## 進度與容錯

| 項目 | 行為 |
|------|------|
| Discord API 限流 | discord.py 自動處理 |
| 附件 429 / 5xx | 最多 5 次指數退避 |
| 歷史讀取中斷 | 最多 5 次重試並從 last id 續抓 |
| 批次中某頻道失敗 | 記錄錯誤，繼續下一個頻道 |
| GUI 取消 | 設取消旗標，於檢查點後停止 |
| Checkpoint | 每 50 則寫入 `messages.json` |

## 登入到底需要什麼？（重要）

**是的：正式 Bot 登入只需要正確的 Bot Token。**  
Channel ID 是登入**成功之後**才用來指定要備份哪個頻道。

這與 [discord-downloader-go](https://github.com/get-got/discord-downloader-go) 相同：它也是用 `credentials.token` 連 Discord，並在設定裡綁定 channel；不會用 Channel ID 來「登入」。

| 項目 | 何時用到 | 錯了會怎樣 |
|------|----------|------------|
| **Bot Token** | 登入 Discord API | `LoginFailure` / 401 |
| **Message Content Intent** | 讀訊息文字 | 能登入，但 content 常是空的 |
| **檢視頻道 / 讀取歷史** | 讀指定頻道 | 能登入，但該頻道 403 |
| **Channel ID** | 指定備份目標 | 能登入，但找不到頻道 / 抓錯地方 |

### Token 常見貼錯（會 401）

- 貼成 **Application ID**（一串純數字）
- 貼成 **Client Secret**（OAuth2 頁面，不是 Bot Token）
- 貼成 **Bot 使用者 ID**
- 前面多加了 `Bot `（discord.py 會自動加；本工具會嘗試剝除）
- 外面多了引號、空白、隱藏字元
- 按過 **Reset Token** 後仍用舊的

**正確位置：** Developer Portal → 你的 App → 左側 **Bot** → **Reset Token** / **Copy**  
標準 Bot Token 通常是**三段**、中間兩個 **`.`**。

主畫面有 **「測試 Token」** 按鈕：只驗證 Token，不必先填 Channel ID。

## 常見問題

### 訊息 content 幾乎都是空的

請確認 Developer Portal 已開啟 **Message Content Intent** 並儲存，然後重新執行備份。

### 登入失敗 / 401

1. 用主畫面 **測試 Token** 看詳細診斷  
2. Developer Portal → **Bot** → **Reset Token** 後立刻重貼  
3. 確認不是 ID / Client Secret  
4. 確認網路可連 `discord.com`

### 403 / 找不到頻道

- Bot 是否已加入該伺服器？  
- 頻道權限是否對 Bot 隱藏？  
- 論壇請用 Thread ID  

### 部分附件失敗

可能 CDN 暫時錯誤或檔案已失效。失敗會寫在 JSON 的 `download_error` 與 `errors.log`。可用 CLI `--resume` 對該目錄再試。

### 教學一直跳出來 / 想重看

- 完成或跳過後不會再自動跳出  
- 設定檔：`%USERPROFILE%\.discord_channel_backup\settings.json` 中 `tutorial_completed`  
- 主畫面右上角 **首次教學** 可隨時重看  

### GUI 打不開

```bash
pip install -r requirements.txt
python gui.py
```

確認已安裝 `customtkinter`，且系統有可用的 Python 3.10+（不是 Windows Store 空殼轉址）。

## 安全提醒

- **Bot Token 等同密碼**，勿提交 Git、勿公開貼出  
- Token **不會**寫入 repo；若使用「已存 Bot」，只存在使用者目錄的加密檔  
- 備份可能含個資，請妥善保管輸出目錄  
- 詳見 [SECURITY.md](SECURITY.md)

## 上傳到 GitHub 前檢查

- [ ] 專案內無 `.env`、log、backups、`.venv`  
- [ ] 未把 `%USERPROFILE%\.discord_channel_backup\` 拷進 repo  
- [ ] `git status` 只看到原始碼與文件  
- [ ] 若 Token 曾外洩：到 Developer Portal **Reset Token**

```bash
cd discord-channel-backup
git init
git add .
git status   # 再確認一次沒有機密
git commit -m "Initial commit: Discord channel backup tool"
# 建立空 repo 後：
# git remote add origin https://github.com/YOU/REPO.git
# git push -u origin main
```

## 授權與免責

MIT — 見 [LICENSE](LICENSE)。

本工具以現況提供，作者不對備份完整性、資料遺失或帳號處置負責。使用前請自行確認符合 Discord 服務條款與當地法規。
