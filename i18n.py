"""UI 字串：繁體中文 (zh-TW) / English (en)。"""

from __future__ import annotations

from typing import Any

LANG_ZH = "zh-TW"
LANG_EN = "en"
SUPPORTED_LANGS = (LANG_ZH, LANG_EN)

# key → { lang: text }
STRINGS: dict[str, dict[str, str]] = {
    "app_title": {
        LANG_ZH: "Discord 頻道備份工具",
        LANG_EN: "Discord Channel Backup",
    },
    "bar_title": {
        LANG_ZH: "Discord 頻道備份",
        LANG_EN: "Discord Channel Backup",
    },
    "tutorial": {LANG_ZH: "首次教學", LANG_EN: "Tutorial"},
    "readme": {LANG_ZH: "README", LANG_EN: "README"},
    "dev_portal": {LANG_ZH: "Developer Portal", LANG_EN: "Developer Portal"},
    "language": {LANG_ZH: "語言", LANG_EN: "Language"},
    "lang_zh": {LANG_ZH: "繁體中文", LANG_EN: "繁體中文"},
    "lang_en": {LANG_ZH: "English", LANG_EN: "English"},
    "bot_token": {LANG_ZH: "Bot Token", LANG_EN: "Bot Token"},
    "saved_bots": {LANG_ZH: "已存 Bot", LANG_EN: "Saved bots"},
    "saved_bots_none": {LANG_ZH: "（尚無已存 Bot）", LANG_EN: "(No saved bots)"},
    "saved_bots_pick": {LANG_ZH: "選擇已存 Bot…", LANG_EN: "Select a saved bot…"},
    "manage_bots": {LANG_ZH: "管理", LANG_EN: "Manage"},
    "show_token": {LANG_ZH: "顯示", LANG_EN: "Show"},
    "test_token": {LANG_ZH: "測試 Token", LANG_EN: "Test Token"},
    "token_placeholder": {
        LANG_ZH: "貼上 Bot Token（Developer Portal → Bot → Copy，不要貼 ID/Secret）",
        LANG_EN: "Paste Bot Token (Developer Portal → Bot → Copy; not ID/Secret)",
    },
    "channel_ids": {
        LANG_ZH: "Channel ID（可多個：每行一個，或逗號分隔）",
        LANG_EN: "Channel IDs (one per line, or comma-separated)",
    },
    "output_dir": {LANG_ZH: "輸出目錄", LANG_EN: "Output folder"},
    "browse": {LANG_ZH: "瀏覽…", LANG_EN: "Browse…"},
    "naming": {LANG_ZH: "附件命名", LANG_EN: "Attachment naming"},
    "verbose_log": {
        LANG_ZH: "詳細日誌（依日期掃描、每張圖下載過程）",
        LANG_EN: "Verbose log (scan by date, per-file download progress)",
    },
    "sort_media": {
        LANG_ZH: "媒體分類存放（圖片/GIF/影片…；檔名仍遵守上方命名方式）",
        LANG_EN: "Sort media into folders (names still follow naming scheme above)",
    },
    "sort_media_on_log": {
        LANG_ZH: "媒體分類：{state}",
        LANG_EN: "Media sort: {state}",
    },
    "delay_section": {
        LANG_ZH: "限速延遲（秒）— 可手動調慢，較不易觸發限流",
        LANG_EN: "Rate-limit delays (seconds) — slow down to be gentler on Discord",
    },
    "delay_download": {
        LANG_ZH: "每個附件後",
        LANG_EN: "After each file",
    },
    "delay_message": {
        LANG_ZH: "每則訊息後",
        LANG_EN: "After each message",
    },
    "delay_channel": {
        LANG_ZH: "頻道之間",
        LANG_EN: "Between channels",
    },
    "delay_hint": {
        LANG_ZH: "建議：附件 0.2–1.0，訊息 0–0.2。0 = 不額外等待（仍會自動處理 429）。",
        LANG_EN: "Suggested: files 0.2–1.0, messages 0–0.2. 0 = no extra wait (429 still handled).",
    },
    "delay_log": {
        LANG_ZH: "限速：附件 {dl}s · 訊息 {msg}s · 頻道間 {ch}s",
        LANG_EN: "Delays: file {dl}s · message {msg}s · between channels {ch}s",
    },
    "status_ready": {
        LANG_ZH: "就緒。請填寫 Token 與 Channel ID 後開始備份。",
        LANG_EN: "Ready. Enter Token and Channel ID(s), then start backup.",
    },
    "stats_zero": {
        LANG_ZH: "訊息：0　附件成功：0　失敗：0",
        LANG_EN: "Messages: 0  Attachments OK: 0  Failed: 0",
    },
    "stats_fmt": {
        LANG_ZH: "訊息：{m}　附件成功：{ok}　失敗：{fail}",
        LANG_EN: "Messages: {m}  Attachments OK: {ok}  Failed: {fail}",
    },
    "start_backup": {LANG_ZH: "開始備份", LANG_EN: "Start backup"},
    "cancel": {LANG_ZH: "取消", LANG_EN: "Cancel"},
    "open_output": {LANG_ZH: "開啟輸出資料夾", LANG_EN: "Open output folder"},
    "missing_token": {LANG_ZH: "缺少 Token", LANG_EN: "Missing Token"},
    "paste_token": {
        LANG_ZH: "請先貼上 Bot Token。",
        LANG_EN: "Please paste a Bot Token first.",
    },
    "invalid_channel": {LANG_ZH: "Channel ID 無效", LANG_EN: "Invalid Channel ID"},
    "output_error": {LANG_ZH: "輸出目錄錯誤", LANG_EN: "Output folder error"},
    "verifying_token": {
        LANG_ZH: "正在向 Discord API 驗證 Token…",
        LANG_EN: "Verifying Token with Discord API…",
    },
    "token_ok_status": {
        LANG_ZH: "Token 有效，可以開始備份。",
        LANG_EN: "Token is valid. You can start backup.",
    },
    "token_fail_status": {LANG_ZH: "Token 驗證失敗", LANG_EN: "Token verification failed"},
    "token_test": {LANG_ZH: "Token 測試", LANG_EN: "Token test"},
    "token_test_fail": {LANG_ZH: "Token 測試失敗", LANG_EN: "Token test failed"},
    "login_fail": {LANG_ZH: "登入失敗", LANG_EN: "Login failed"},
    "backup_fail": {LANG_ZH: "備份失敗", LANG_EN: "Backup failed"},
    "backup_fail_body": {
        LANG_ZH: "發生錯誤，詳見日誌。",
        LANG_EN: "An error occurred. See the log for details.",
    },
    "backup_done": {LANG_ZH: "備份完成", LANG_EN: "Backup complete"},
    "backup_partial": {
        LANG_ZH: "備份結束（部分失敗）",
        LANG_EN: "Backup finished (partial failures)",
    },
    "preparing": {
        LANG_ZH: "準備備份 {n} 個頻道…",
        LANG_EN: "Preparing backup of {n} channel(s)…",
    },
    "backing_up": {
        LANG_ZH: "備份中 [{i}/{t}] {name}",
        LANG_EN: "Backing up [{i}/{t}] {name}",
    },
    "done_status": {
        LANG_ZH: "完成：成功 {ok}/{total}",
        LANG_EN: "Done: {ok}/{total} succeeded",
    },
    "cancelling": {LANG_ZH: "取消中…", LANG_EN: "Cancelling…"},
    "cancel_log": {
        LANG_ZH: "正在取消…（會在目前檢查點後停止）",
        LANG_EN: "Cancelling… (stops after the current checkpoint)",
    },
    "quit_title": {LANG_ZH: "結束", LANG_EN: "Quit"},
    "quit_confirm": {
        LANG_ZH: "備份仍在進行，確定要關閉？",
        LANG_EN: "Backup is still running. Quit anyway?",
    },
    "error": {LANG_ZH: "錯誤", LANG_EN: "Error"},
    "open_folder_fail": {
        LANG_ZH: "無法開啟資料夾：{e}",
        LANG_EN: "Cannot open folder: {e}",
    },
    "readme_missing": {LANG_ZH: "找不到 README.md", LANG_EN: "README.md not found"},
    "info": {LANG_ZH: "說明", LANG_EN: "Info"},
    "save_bot_ok": {
        LANG_ZH: "已儲存 Bot「{name}」到本機清單。",
        LANG_EN: "Saved bot “{name}” to the local list.",
    },
    "bot_loaded": {
        LANG_ZH: "已載入 Bot「{name}」",
        LANG_EN: "Loaded bot “{name}”",
    },
    "delete_bot_title": {LANG_ZH: "刪除已存 Bot", LANG_EN: "Delete saved bot"},
    "delete_bot_confirm": {
        LANG_ZH: "確定刪除「{name}」？\nToken 會從本機加密儲存中永久清除。",
        LANG_EN: "Delete “{name}”?\nThe token will be permanently removed from local encrypted storage.",
    },
    "delete_bot_done": {
        LANG_ZH: "已刪除「{name}」，Token 已清除。",
        LANG_EN: "Deleted “{name}”. Token purged.",
    },
    "manage_bots_title": {LANG_ZH: "已存 Bot 管理", LANG_EN: "Manage saved bots"},
    "manage_bots_hint": {
        LANG_ZH: "點右側 ✕ 可永久刪除該 Bot 的 Token 與紀錄。",
        LANG_EN: "Click ✕ on the right to permanently delete that bot’s token and record.",
    },
    "bot_col_name": {LANG_ZH: "Bot 名稱", LANG_EN: "Bot name"},
    "bot_col_server": {LANG_ZH: "伺服器 / 備註", LANG_EN: "Servers / notes"},
    "bot_unknown": {LANG_ZH: "未命名 Bot", LANG_EN: "Unnamed bot"},
    "bot_no_guild": {LANG_ZH: "（尚無伺服器資訊）", LANG_EN: "(No server info yet)"},
    "close": {LANG_ZH: "關閉", LANG_EN: "Close"},
    "empty_list": {LANG_ZH: "目前沒有已存的 Bot。", LANG_EN: "No bots saved yet."},
    "auto_save_hint": {
        LANG_ZH: "測試 Token 成功或備份登入成功時，會自動記住此 Bot。",
        LANG_EN: "Bots are saved automatically after a successful token test or login.",
    },
    "naming_scheme_log": {
        LANG_ZH: "命名方式：{label}（{scheme}）· 詳細日誌：{verbose}",
        LANG_EN: "Naming: {label} ({scheme}) · Verbose: {verbose}",
    },
    "on": {LANG_ZH: "開", LANG_EN: "On"},
    "off": {LANG_ZH: "關", LANG_EN: "Off"},
    "batch_start": {
        LANG_ZH: "開始批次：{n} 個頻道 → {path}",
        LANG_EN: "Batch start: {n} channel(s) → {path}",
    },
    "success_line": {
        LANG_ZH: "成功 {ok}/{total} 個頻道",
        LANG_EN: "{ok}/{total} channel(s) succeeded",
    },
    "batch_dir": {LANG_ZH: "批次目錄：{p}", LANG_EN: "Batch folder: {p}"},
    "tutorial_title": {LANG_ZH: "首次使用教學", LANG_EN: "Getting started"},
    "tutorial_skip": {LANG_ZH: "跳過教學", LANG_EN: "Skip tutorial"},
    "tutorial_prev": {LANG_ZH: "上一步", LANG_EN: "Back"},
    "tutorial_next": {LANG_ZH: "下一步", LANG_EN: "Next"},
    "tutorial_finish": {LANG_ZH: "完成，開始使用", LANG_EN: "Done, start using"},
    "tutorial_no_link": {
        LANG_ZH: "（本頁無外部連結）",
        LANG_EN: "(No external link on this page)",
    },
    "open_link": {LANG_ZH: "開啟連結", LANG_EN: "Open link"},
    "crash_enter": {
        LANG_ZH: "\n發生錯誤。按 Enter 關閉視窗…",
        LANG_EN: "\nAn error occurred. Press Enter to close…",
    },
}

# 教學步驟：每步 title/body 雙語
TUTORIAL: list[dict[str, Any]] = [
    {
        "title": {
            LANG_ZH: "歡迎使用 Discord 頻道備份工具",
            LANG_EN: "Welcome to Discord Channel Backup",
        },
        "body": {
            LANG_ZH: (
                "這個工具可以幫你把 Discord 頻道的歷史訊息與附件完整備份到電腦。\n\n"
                "支援：\n"
                "• 單頻道或一次多個頻道批次備份\n"
                "• 自動下載圖片、影片、檔案\n"
                "• 輸出 messages.json + media/ 資料夾\n\n"
                "請選擇你的情況：\n"
                "• 伺服器「已經有 Bot」→ 下一頁有【快速設定】\n"
                "• 還沒有 Bot → 再往後是【從頭建立】完整步驟\n\n"
                "注意：必須使用「Bot Token」，不能用個人帳號 Token。"
            ),
            LANG_EN: (
                "Back up full Discord channel history and attachments to your PC.\n\n"
                "Features:\n"
                "• Single or multi-channel batch backup\n"
                "• Download images, videos, and files\n"
                "• Output messages.json + media/\n\n"
                "Choose your path:\n"
                "• Bot already on the server → quick setup on the next page\n"
                "• No bot yet → full create-bot steps after that\n\n"
                "You must use a Bot Token (not a user account token)."
            ),
        },
        "link": None,
        "link_label": {LANG_ZH: None, LANG_EN: None},
    },
    {
        "title": {
            LANG_ZH: "【已有 Bot】快速設定與開始擷取",
            LANG_EN: "[Existing bot] Quick setup",
        },
        "body": {
            LANG_ZH: (
                "伺服器裡已經有一個 Bot 時，照這 5 步即可開始備份：\n\n"
                "① Developer Portal → 該 Bot 所屬 Application\n"
                "② Bot → Reset/Copy Token（不要用 ID / Client Secret）\n"
                "③ 開啟 MESSAGE CONTENT INTENT 並儲存\n"
                "④ 伺服器權限：檢視頻道 + 讀取訊息歷史\n"
                "⑤ 複製 Channel ID → 主畫面貼 Token + ID → 開始備份\n\n"
                "可用「測試 Token」先確認有效；成功後會自動存到「已存 Bot」。"
            ),
            LANG_EN: (
                "If a bot is already on your server:\n\n"
                "1) Developer Portal → that bot’s Application\n"
                "2) Bot → Reset/Copy Token (not ID / Client Secret)\n"
                "3) Enable MESSAGE CONTENT INTENT and save\n"
                "4) Permissions: View Channel + Read Message History\n"
                "5) Copy Channel ID(s) → paste Token + IDs → Start backup\n\n"
                "Use “Test Token” first; on success the bot is saved to “Saved bots”."
            ),
        },
        "link": "https://discord.com/developers/applications",
        "link_label": {
            LANG_ZH: "開啟 Developer Portal",
            LANG_EN: "Open Developer Portal",
        },
    },
    {
        "title": {
            LANG_ZH: "【新建 Bot】建立與 Intent",
            LANG_EN: "[New bot] Create & intents",
        },
        "body": {
            LANG_ZH: (
                "1. New Application → Bot → 複製 Token\n"
                "2. 開啟 MESSAGE CONTENT INTENT\n"
                "3. OAuth2 URL Generator：bot + View Channels + Read Message History\n"
                "4. 邀請到伺服器\n"
                "5. 開發者模式 → 複製 Channel ID → 開始備份"
            ),
            LANG_EN: (
                "1. New Application → Bot → copy Token\n"
                "2. Enable MESSAGE CONTENT INTENT\n"
                "3. OAuth2 URL Generator: bot + View Channels + Read Message History\n"
                "4. Invite to the server\n"
                "5. Developer Mode → copy Channel ID → start backup"
            ),
        },
        "link": "https://discord.com/developers/applications",
        "link_label": {
            LANG_ZH: "開啟 Developer Portal",
            LANG_EN: "Open Developer Portal",
        },
    },
    {
        "title": {
            LANG_ZH: "開始備份",
            LANG_EN: "Start backup",
        },
        "body": {
            LANG_ZH: (
                "主畫面：Token、Channel ID、輸出目錄、命名方式 → 開始備份。\n"
                "可從右上角切換 繁中 / English。\n"
                "已存 Bot 可從 Token 旁下拉選取；管理視窗可 ✕ 刪除並清除 Token。"
            ),
            LANG_EN: (
                "Main window: Token, Channel IDs, output folder, naming → Start backup.\n"
                "Switch 繁中 / English from the top bar.\n"
                "Use the Saved bots menu next to Token; Manage allows ✕ delete (token purged)."
            ),
        },
        "link": None,
        "link_label": {LANG_ZH: None, LANG_EN: None},
    },
]

# 命名方案顯示名（雙語）
NAMING_LABELS: dict[str, dict[str, tuple[str, str]]] = {
    "seq": {
        LANG_ZH: ("純數字", "1.png, 2.jpg, 3.webp …"),
        LANG_EN: ("Numbers only", "1.png, 2.jpg, 3.webp …"),
    },
    "seq_padded": {
        LANG_ZH: ("補零數字", "000001.png, 000002.jpg …"),
        LANG_EN: ("Zero-padded numbers", "000001.png, 000002.jpg …"),
    },
    "date_seq": {
        LANG_ZH: ("日期-序號", "20260726-1.png, 20260726-2.jpg …（同日遞增）"),
        LANG_EN: ("Date-seq", "20260726-1.png, 20260726-2.jpg … (per day)"),
    },
    "date_time_seq": {
        LANG_ZH: ("日期時間-序號", "20260726_143052-1.png …"),
        LANG_EN: ("Date-time-seq", "20260726_143052-1.png …"),
    },
    "seq_original": {
        LANG_ZH: ("序號_原始檔名", "1_photo.png, 2_video.mp4 …"),
        LANG_EN: ("Seq_original", "1_photo.png, 2_video.mp4 …"),
    },
    "full": {
        LANG_ZH: ("完整（預設）", "000001_20260726_143052_photo.png"),
        LANG_EN: ("Full (default)", "000001_20260726_143052_photo.png"),
    },
}

_current_lang = LANG_ZH


def get_lang() -> str:
    return _current_lang


def set_lang(lang: str) -> str:
    global _current_lang
    if lang not in SUPPORTED_LANGS:
        lang = LANG_ZH
    _current_lang = lang
    return _current_lang


def t(msg_id: str, **kwargs: Any) -> str:
    """取翻譯字串。msg_id 為字串鍵；kwargs 供 .format 使用（勿使用參數名 msg_id）。"""
    entry = STRINGS.get(msg_id) or {}
    text = entry.get(_current_lang) or entry.get(LANG_ZH) or msg_id
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def naming_option_label(scheme_key: str) -> str:
    block = NAMING_LABELS.get(scheme_key) or NAMING_LABELS["full"]
    title, desc = block.get(_current_lang) or block[LANG_ZH]
    return f"{title}（{desc}）" if _current_lang == LANG_ZH else f"{title} ({desc})"


def tutorial_steps() -> list[dict[str, Any]]:
    """依目前語言展開教學步驟。"""
    out = []
    for step in TUTORIAL:
        title = step["title"].get(_current_lang) or step["title"][LANG_ZH]
        body = step["body"].get(_current_lang) or step["body"][LANG_ZH]
        ll = step.get("link_label") or {}
        link_label = ll.get(_current_lang) if isinstance(ll, dict) else None
        if isinstance(ll, dict) and not link_label:
            link_label = ll.get(LANG_ZH)
        out.append(
            {
                "title": title,
                "body": body,
                "link": step.get("link"),
                "link_label": link_label,
            }
        )
    return out
