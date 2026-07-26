#!/usr/bin/env python3
"""Discord 頻道備份核心引擎：單頻道 / 多頻道批次、進度回呼、續傳。"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import aiohttp
import discord

TOOL_VERSION = "1.3.0"
MAX_DOWNLOAD_RETRIES = 5
HISTORY_RETRY_LIMIT = 5
CHECKPOINT_EVERY = 50
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
# Discord bot token 大致為三段 base64（以 . 分隔）；僅作格式提示，非嚴格校驗
TOKEN_SHAPE = re.compile(r"^[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{4,}\.[A-Za-z0-9_\-]{20,}$")

logger = logging.getLogger("discord_backup")

# 附件命名方案：key → (顯示名稱, 說明)
NAMING_SCHEMES: dict[str, tuple[str, str]] = {
    "seq": ("純數字", "1.png, 2.jpg, 3.webp …"),
    "seq_padded": ("補零數字", "000001.png, 000002.jpg …"),
    "date_seq": ("日期-序號", "20260726-1.png, 20260726-2.jpg …（同日遞增）"),
    "date_time_seq": ("日期時間-序號", "20260726_143052-1.png …"),
    "seq_original": ("序號_原始檔名", "1_photo.png, 2_video.mp4 …"),
    "full": ("完整（預設）", "000001_20260726_143052_photo.png"),
}
DEFAULT_NAMING_SCHEME = "full"


# ---------------------------------------------------------------------------
# Token 清理 / 診斷（LoginFailure 幾乎都是貼錯內容，不是少設定）
# ---------------------------------------------------------------------------


def sanitize_token(raw: str) -> str:
    """
    清理使用者貼上的 Token：
    - 去空白、引號、零寬字元
    - 去掉多餘的「Bot 」前綴（discord.py 會自己加，重複會 401）
    """
    if raw is None:
        return ""
    token = str(raw)
    # 常見複製髒字元
    for ch in ("\ufeff", "\u200b", "\u200c", "\u200d", "\u2060", "\xa0"):
        token = token.replace(ch, "")
    token = token.strip()
    # 整段被包在引號裡
    if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
        token = token[1:-1].strip()
    # 多行貼上時只取第一行有效內容
    if "\n" in token or "\r" in token:
        for line in re.split(r"[\r\n]+", token):
            line = line.strip()
            if line and not line.lower().startswith("bot token"):
                token = line
                break
    # discord.py Client 會自動加 "Bot "；若使用者已含此前綴會變成 "Bot Bot xxx"
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    return token


def describe_token(token: str) -> str:
    """產生不含機密的 Token 診斷摘要（可寫入 log）。"""
    if not token:
        return "空字串"
    parts = token.split(".")
    shape_ok = bool(TOKEN_SHAPE.match(token))
    preview = f"{token[:6]}…{token[-4:]}" if len(token) >= 16 else f"(過短，長度 {len(token)})"
    return (
        f"長度={len(token)}，段數={len(parts)}，"
        f"格式看起來{'像' if shape_ok else '不像'}標準 Bot Token，預覽={preview}"
    )


def diagnose_token_issues(token: str) -> list[str]:
    """回傳可能問題列表（人話）。"""
    tips: list[str] = []
    if not token:
        tips.append("Token 為空。")
        return tips
    lower = token.lower()
    if lower.startswith("bot "):
        tips.append("仍含「Bot 」前綴（應已自動剝除；若仍失敗請重貼純 Token）。")
    if " " in token or "\t" in token:
        tips.append("Token 內含空白，可能貼到多餘文字。")
    if token.isdigit() and len(token) >= 17:
        tips.append("這看起來像「數字 ID」（Application ID / 使用者 ID / 頻道 ID），不是 Bot Token。")
    if len(token) < 50:
        tips.append("Token 過短，可能只貼了 Application ID 或截斷了。")
    if len(token) > 120:
        tips.append("Token 過長，可能多貼了別的文字。")
    if not TOKEN_SHAPE.match(token):
        tips.append(
            "格式不像標準 Bot Token（通常是三段、中間用「.」分隔）。"
            "請到 Developer Portal → 你的 App → Bot → Reset Token / Copy。"
        )
    # Client Secret 通常較短且無兩點三段結構
    if token.count(".") != 2:
        tips.append("Bot Token 幾乎一定有兩個「.」分成三段；若沒有，多半貼錯欄位（例如 Client Secret）。")
    return tips


async def verify_bot_token(token: str) -> tuple[bool, str, Optional[dict[str, Any]]]:
    """
    用 REST /users/@me 驗證 Token（不需 WebSocket）。
    回傳 (ok, message, user_json_or_none)。
    """
    token = sanitize_token(token)
    if not token:
        return False, "Token 為空。", None

    issues = diagnose_token_issues(token)
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": f"DiscordChannelBackup/{TOOL_VERSION}",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
                body_text = await resp.text()
                if resp.status == 200:
                    try:
                        data = json.loads(body_text)
                    except json.JSONDecodeError:
                        return True, "Token 有效（無法解析使用者資料）。", None
                    name = data.get("username") or "?"
                    bid = data.get("id") or "?"
                    is_bot = data.get("bot", False)
                    if not is_bot:
                        return (
                            False,
                            "此 Token 登入成功但不是 Bot 帳號。本工具只支援正式 Bot Token，"
                            "不支援使用者帳號（self-bot）。",
                            data,
                        )
                    return True, f"Token 有效。Bot：{name}（ID {bid}）", data
                if resp.status == 401:
                    detail = (
                        "Discord 回傳 401：Token 被拒絕。\n"
                        f"診斷：{describe_token(token)}\n"
                    )
                    if issues:
                        detail += "可能原因：\n- " + "\n- ".join(issues) + "\n"
                    detail += (
                        "請確認：\n"
                        "1. Developer Portal → 正確的 Application → 左側「Bot」\n"
                        "2. 按 Reset Token 後立刻 Copy（只顯示一次）\n"
                        "3. 貼上時不要加引號、不要加「Bot 」前綴\n"
                        "4. 不要貼 Application ID / Client Secret / OAuth Client ID\n"
                        "5. 若剛 Reset，舊 Token 會立刻失效，需用新的"
                    )
                    return False, detail, None
                if resp.status == 403:
                    return False, f"Discord 回傳 403：{body_text[:300]}", None
                if resp.status == 429:
                    return False, "被 Discord 限流（429），請稍後再試。", None
                return False, f"Discord 回傳 HTTP {resp.status}：{body_text[:300]}", None
    except aiohttp.ClientError as exc:
        return False, f"網路錯誤，無法連到 Discord API：{exc}", None
    except asyncio.TimeoutError:
        return False, "連線 Discord API 逾時，請檢查網路 / 代理 / 防火牆。", None


# ---------------------------------------------------------------------------
# Progress / job types
# ---------------------------------------------------------------------------


@dataclass
class ProgressEvent:
    kind: str  # log | channel_start | channel_done | message | attachment | batch_done | error
    message: str = ""
    level: str = "info"  # info | warning | error
    channel_id: Optional[int] = None
    channel_name: str = ""
    guild_id: str = ""
    guild_name: str = ""
    channel_index: int = 0
    channel_total: int = 0
    messages: int = 0
    attachments_ok: int = 0
    attachments_fail: int = 0
    out_dir: Optional[str] = None


ProgressCallback = Callable[[ProgressEvent], None]


@dataclass
class BackupOptions:
    """備份行為選項（命名、日誌詳細度、限速等）。"""

    naming_scheme: str = DEFAULT_NAMING_SCHEME
    verbose: bool = True  # 詳細記錄掃描日期、每檔下載過程
    log_every_message: bool = False  # True 時每則訊息都寫 log（極吵）
    # 依類型分資料夾：media/images、media/gifs、media/videos、media/audio、media/files
    sort_media_by_type: bool = False
    # 手動限速（秒）。官方 Bot API 主要靠 rate limit；額外延遲可更保守
    delay_download_sec: float = 0.0  # 每個附件下載完成後
    delay_message_sec: float = 0.0  # 每則訊息處理完後
    delay_channel_sec: float = 0.0  # 多頻道時，頻道與頻道之間

    def normalized_scheme(self) -> str:
        key = (self.naming_scheme or DEFAULT_NAMING_SCHEME).strip().lower()
        return key if key in NAMING_SCHEMES else DEFAULT_NAMING_SCHEME

    def clamp_delays(self) -> "BackupOptions":
        """把延遲限制在合理範圍，避免誤填。"""
        self.delay_download_sec = _clamp_delay(self.delay_download_sec)
        self.delay_message_sec = _clamp_delay(self.delay_message_sec)
        self.delay_channel_sec = _clamp_delay(self.delay_channel_sec, max_v=60.0)
        return self


def _clamp_delay(value: Any, min_v: float = 0.0, max_v: float = 30.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return max(min_v, min(max_v, v))


async def polite_delay(seconds: float, cancel_event: Optional[asyncio.Event] = None) -> bool:
    """
    可中斷的 sleep。回傳 False 表示已被取消。
    """
    sec = _clamp_delay(seconds)
    if sec <= 0:
        return True
    # 分段 sleep，方便 cancel
    end = asyncio.get_event_loop().time() + sec
    while True:
        if cancel_event is not None and cancel_event.is_set():
            return False
        now = asyncio.get_event_loop().time()
        remaining = end - now
        if remaining <= 0:
            return True
        await asyncio.sleep(min(0.2, remaining))


@dataclass
class ChannelJob:
    channel_id: int
    out_dir: Optional[Path] = None  # 指定則寫入/續傳到此目錄（續傳用）
    resume: bool = False
    # 新建備份時 out_dir 可為 None：取得頻道名稱後在 output_parent 下建立資料夾
    output_parent: Optional[Path] = None


@dataclass
class ChannelResult:
    channel_id: int
    success: bool
    out_dir: Path
    channel_name: str = ""
    message_count: int = 0
    attachment_ok: int = 0
    attachment_fail: int = 0
    error: Optional[str] = None


@dataclass
class BatchResult:
    results: list[ChannelResult] = field(default_factory=list)
    batch_dir: Optional[Path] = None
    login_error: Optional[str] = None

    @property
    def all_ok(self) -> bool:
        return self.login_error is None and all(r.success for r in self.results)

    @property
    def exit_code(self) -> int:
        if self.login_error:
            return 1
        if not self.results:
            return 1
        if any(not r.success for r in self.results):
            return 1
        return 0


def emit(
    cb: Optional[ProgressCallback],
    kind: str,
    message: str = "",
    level: str = "info",
    **kwargs: Any,
) -> None:
    if cb is None:
        return
    try:
        cb(ProgressEvent(kind=kind, message=message, level=level, **kwargs))
    except Exception:  # noqa: BLE001 — UI callback must not kill backup
        logger.exception("progress callback failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def setup_logging(log_file: Optional[Path] = None, *, also_console: bool = True) -> None:
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    if also_console:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)


def parse_channel_ids(text: str) -> list[int]:
    """從多行 / 逗號 / 空白分隔文字解析 Channel ID 列表（去重、保序）。"""
    raw = re.split(r"[\s,;，；]+", text.strip())
    ids: list[int] = []
    seen: set[int] = set()
    for part in raw:
        part = part.strip()
        if not part:
            continue
        if not part.isdigit():
            raise ValueError(f"無效的 Channel ID：{part!r}（必須是純數字）")
        cid = int(part)
        if cid not in seen:
            seen.add(cid)
            ids.append(cid)
    if not ids:
        raise ValueError("請至少提供一個 Channel ID")
    return ids


def sanitize_filename(name: str, max_len: int = 120) -> str:
    name = name.strip().replace("\n", " ").replace("\r", "")
    name = INVALID_FILENAME_CHARS.sub("_", name)
    name = name.strip(" .")
    if not name:
        name = "file"
    if len(name) > max_len:
        stem = Path(name).stem[: max_len - 20]
        suffix = Path(name).suffix[:20]
        name = f"{stem}{suffix}" if suffix else stem
    return name


def guess_extension(content_type: Optional[str], filename: str) -> str:
    if Path(filename).suffix:
        return Path(filename).suffix
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    return ".bin"


def ensure_extension(original: str, content_type: Optional[str]) -> tuple[str, str]:
    """回傳 (safe_stem_or_name, extension 含點)。"""
    safe = sanitize_filename(original or "file")
    ext = Path(safe).suffix
    if not ext:
        ext = guess_extension(content_type, safe)
        if not ext.startswith("."):
            ext = f".{ext}"
        stem = safe
    else:
        stem = Path(safe).stem
    if not stem:
        stem = "file"
    return stem, ext


def format_bytes(n: Optional[int]) -> str:
    if n is None or n < 0:
        return "?"
    units = ["B", "KB", "MB", "GB"]
    size = float(n)
    for u in units:
        if size < 1024 or u == units[-1]:
            if u == "B":
                return f"{int(size)} {u}"
            return f"{size:.1f} {u}"
        size /= 1024
    return f"{n} B"


IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
    ".avif",
    ".jfif",
}
GIF_EXTS = {".gif", ".apng"}
VIDEO_EXTS = {
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
    ".avi",
    ".wmv",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".flv",
    ".3gp",
}
AUDIO_EXTS = {
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",
    ".aac",
    ".wma",
    ".opus",
    ".aiff",
}

# 子資料夾名（路徑用英文，穩定跨語系）
MEDIA_CATEGORY_FOLDERS = {
    "images": "images",
    "gifs": "gifs",
    "videos": "videos",
    "audio": "audio",
    "files": "files",
}

MEDIA_CATEGORY_LABELS_ZH = {
    "images": "圖片",
    "gifs": "GIF 動圖",
    "videos": "影片",
    "audio": "音訊",
    "files": "其他檔案",
}


def is_image_attachment(filename: str, content_type: Optional[str]) -> bool:
    """靜態圖或 GIF 皆視為 image（統計用）。"""
    cat = classify_media(filename, content_type)
    return cat in ("images", "gifs")


def classify_media(filename: str, content_type: Optional[str]) -> str:
    """
    回傳媒體分類 key：images | gifs | videos | audio | files
    GIF 獨立一類（動圖資料夾）。
    """
    ext = Path(filename or "").suffix.lower()
    ct = (content_type or "").lower().split(";")[0].strip()

    if ext in GIF_EXTS or ct == "image/gif" or ct == "image/apng":
        return "gifs"
    if ct.startswith("image/") or ext in IMAGE_EXTS:
        return "images"
    if ct.startswith("video/") or ext in VIDEO_EXTS:
        return "videos"
    if ct.startswith("audio/") or ext in AUDIO_EXTS:
        return "audio"
    return "files"


def media_subfolder(category: str) -> str:
    return MEDIA_CATEGORY_FOLDERS.get(category, "files")


def resolve_attachment_paths(
    media_root: Path,
    filename: str,
    *,
    sort_by_type: bool,
    category: str,
) -> tuple[Path, str, Path]:
    """
    回傳 (實際儲存目錄, 相對路徑 local_path, 完整檔案路徑)。
    sort_by_type=False → media/xxx
    sort_by_type=True  → media/images/xxx 等
    """
    if sort_by_type:
        sub = media_subfolder(category)
        target_dir = media_root / sub
        relative = f"media/{sub}/{filename}"
    else:
        target_dir = media_root
        relative = f"media/{filename}"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir, relative, target_dir / filename


class AttachmentNameBuilder:
    """依使用者選擇的方案產生檔名，並避免同名覆蓋。"""

    def __init__(self, scheme: str = DEFAULT_NAMING_SCHEME, start_seq: int = 1):
        self.scheme = scheme if scheme in NAMING_SCHEMES else DEFAULT_NAMING_SCHEME
        self.global_seq = max(1, start_seq)
        self.day_seq: dict[str, int] = {}  # YYYYMMDD → next index

    def next_name(
        self,
        created_at: datetime,
        original: str,
        content_type: Optional[str],
        media_dir: Path,
    ) -> tuple[str, int]:
        """回傳 (檔名, 使用的全域序號)。"""
        seq = self.global_seq
        self.global_seq += 1
        dt = created_at.astimezone(timezone.utc)
        day = dt.strftime("%Y%m%d")
        time_s = dt.strftime("%H%M%S")
        stem, ext = ensure_extension(original, content_type)
        safe_original = sanitize_filename(f"{stem}{ext}")

        day_i = self.day_seq.get(day, 1)
        self.day_seq[day] = day_i + 1

        if self.scheme == "seq":
            base = f"{seq}{ext}"
        elif self.scheme == "seq_padded":
            base = f"{seq:06d}{ext}"
        elif self.scheme == "date_seq":
            base = f"{day}-{day_i}{ext}"
        elif self.scheme == "date_time_seq":
            base = f"{day}_{time_s}-{day_i}{ext}"
        elif self.scheme == "seq_original":
            base = f"{seq}_{safe_original}"
        else:  # full
            base = f"{seq:06d}_{day}_{time_s}_{safe_original}"

        return self._unique(media_dir, base), seq

    @staticmethod
    def _unique(media_dir: Path, filename: str) -> str:
        dest = media_dir / filename
        if not dest.exists():
            return filename
        stem = Path(filename).stem
        ext = Path(filename).suffix
        n = 2
        while True:
            candidate = f"{stem}_{n}{ext}"
            if not (media_dir / candidate).exists():
                return candidate
            n += 1


async def download_attachment(
    session: aiohttp.ClientSession,
    url: str,
    dest: Path,
    *,
    max_retries: int = MAX_DOWNLOAD_RETRIES,
    expected_size: Optional[int] = None,
    on_progress: Optional[Callable[[int, Optional[int]], None]] = None,
) -> tuple[bool, Optional[str], int]:
    """
    下載附件。
    回傳 (成功, 錯誤訊息, 實際寫入位元組數)。
    on_progress(downloaded_bytes, total_or_None)
    """
    if dest.exists() and dest.stat().st_size > 0:
        size = dest.stat().st_size
        if on_progress:
            on_progress(size, size)
        return True, None, size

    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Optional[str] = None

    for attempt in range(max_retries):
        try:
            timeout = aiohttp.ClientTimeout(total=600)
            async with session.get(url, timeout=timeout) as resp:
                if resp.status == 429:
                    retry_after = float(resp.headers.get("Retry-After", 2 ** attempt))
                    last_error = f"HTTP 429，等待 {retry_after}s"
                    logger.warning("下載限流 %s：%s", dest.name, last_error)
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status >= 500:
                    last_error = f"HTTP {resp.status}"
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status != 200:
                    last_error = f"HTTP {resp.status}"
                    return False, last_error, 0

                total = resp.content_length or expected_size
                tmp = dest.with_suffix(dest.suffix + ".part")
                written = 0
                last_report = 0
                with tmp.open("wb") as f:
                    async for chunk in resp.content.iter_chunked(64 * 1024):
                        f.write(chunk)
                        written += len(chunk)
                        # 約每 512KB 回報一次，避免洗版
                        if on_progress and (written - last_report >= 512 * 1024 or (total and written >= total)):
                            on_progress(written, total)
                            last_report = written
                tmp.replace(dest)
                if on_progress:
                    on_progress(written, total or written)
                return True, None, written
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
            last_error = str(exc)
            logger.warning(
                "下載失敗 (%s/%s) %s：%s",
                attempt + 1,
                max_retries,
                dest.name,
                last_error,
            )
            await asyncio.sleep(2 ** attempt)

    return False, last_error or "unknown error", 0


def serialize_embed(embed: discord.Embed) -> dict[str, Any]:
    data: dict[str, Any] = {
        "title": embed.title,
        "description": embed.description,
        "url": embed.url,
        "type": str(embed.type) if embed.type else None,
    }
    if embed.image and embed.image.url:
        data["image"] = embed.image.url
    if embed.thumbnail and embed.thumbnail.url:
        data["thumbnail"] = embed.thumbnail.url
    if embed.video and embed.video.url:
        data["video"] = embed.video.url
    if embed.author and embed.author.name:
        data["author"] = embed.author.name
    if embed.footer and embed.footer.text:
        data["footer"] = embed.footer.text
    return data


def serialize_message(message: discord.Message, attachment_records: list[dict[str, Any]]) -> dict[str, Any]:
    author = message.author
    display_name = getattr(author, "display_name", None) or author.name

    reactions = []
    for reaction in message.reactions:
        emoji = reaction.emoji
        if isinstance(emoji, str):
            emoji_str = emoji
        else:
            emoji_str = f"{emoji.name}:{emoji.id}" if getattr(emoji, "id", None) else str(emoji)
        reactions.append({"emoji": emoji_str, "count": reaction.count})

    stickers = []
    for sticker in message.stickers:
        stickers.append(
            {
                "id": str(sticker.id),
                "name": sticker.name,
                "format": str(getattr(sticker, "format", "")),
                "url": getattr(sticker, "url", None),
            }
        )

    reference = None
    if message.reference and message.reference.message_id:
        reference = {
            "message_id": str(message.reference.message_id),
            "channel_id": str(message.reference.channel_id) if message.reference.channel_id else None,
            "guild_id": str(message.reference.guild_id) if message.reference.guild_id else None,
        }

    return {
        "id": str(message.id),
        "created_at": message.created_at.astimezone(timezone.utc).isoformat(),
        "edited_at": message.edited_at.astimezone(timezone.utc).isoformat() if message.edited_at else None,
        "author": {
            "id": str(author.id),
            "name": author.name,
            "display_name": display_name,
            "bot": bool(author.bot),
        },
        "content": message.content or "",
        "type": str(message.type),
        "attachments": attachment_records,
        "embeds": [serialize_embed(e) for e in message.embeds],
        "reactions": reactions,
        "mentions": [str(u.id) for u in message.mentions],
        "reference": reference,
        "pinned": message.pinned,
        "tts": message.tts,
        "stickers": stickers,
    }


def load_existing_messages(out_dir: Path) -> tuple[list[dict[str, Any]], Optional[int], int]:
    path = out_dir / "messages.json"
    if not path.exists():
        return [], None, 1

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("無法讀取既有 messages.json，將重新開始：%s", exc)
        return [], None, 1

    messages = data.get("messages") or []
    last_id: Optional[int] = None
    max_seq = 0
    att_count = 0
    for msg in messages:
        try:
            last_id = int(msg["id"])
        except (KeyError, TypeError, ValueError):
            pass
        for att in msg.get("attachments") or []:
            if att.get("local_path") or att.get("saved_as"):
                att_count += 1
            local = att.get("local_path") or att.get("saved_as") or ""
            base = Path(str(local)).name
            # 000001_... 或 1_name 或 1.png 或 20260726-3.png
            m = re.match(r"^(\d+)(?:[_\-.]|$)", base)
            if m:
                max_seq = max(max_seq, int(m.group(1)))
            m2 = re.search(r"-(\d+)\.[^.]+$", base)
            if m2:
                max_seq = max(max_seq, int(m2.group(1)))

    next_seq = max(max_seq, att_count) + 1
    return messages, last_id, next_seq


def write_messages_json(out_dir: Path, meta: dict[str, Any], messages: list[dict[str, Any]]) -> None:
    payload = {"meta": meta, "messages": messages}
    path = out_dir / "messages.json"
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def folder_name_from_channel(channel_name: str) -> str:
    """把 Discord 頻道／討論串名稱轉成安全的資料夾名（不含 ID）。"""
    base = sanitize_filename((channel_name or "").strip() or "unnamed-channel", max_len=80)
    if not base or base in {".", ".."}:
        base = "unnamed-channel"
    return base


def unique_channel_out_dir(output_root: Path, channel_name: str) -> Path:
    """
    以頻道名稱在 output_root 下建立唯一資料夾路徑。
    例：一般討論 → Desktop/一般討論
    若已存在 → Desktop/一般討論_2
    """
    output_root.mkdir(parents=True, exist_ok=True)
    base = folder_name_from_channel(channel_name)
    candidate = output_root / base
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        alt = output_root / f"{base}_{n}"
        if not alt.exists():
            return alt
        n += 1


# ---------------------------------------------------------------------------
# Single-channel backup (uses an already-ready client)
# ---------------------------------------------------------------------------


async def backup_one_channel(
    client: discord.Client,
    job: ChannelJob,
    *,
    session: aiohttp.ClientSession,
    progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[asyncio.Event] = None,
    channel_index: int = 1,
    channel_total: int = 1,
    log_to_file: bool = True,
    options: Optional[BackupOptions] = None,
) -> ChannelResult:
    opts = (options or BackupOptions()).clamp_delays()
    scheme = opts.normalized_scheme()
    verbose = opts.verbose
    sort_media = bool(opts.sort_media_by_type)
    delay_dl = opts.delay_download_sec
    delay_msg = opts.delay_message_sec

    # 暫定路徑（取得名稱後可能改為以討論串／頻道名命名）
    out_dir: Path = job.out_dir or (job.output_parent or Path("backups")) / f"_pending_{job.channel_id}"

    def _cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    def _prog(kind: str, message: str = "", level: str = "info", **kw: Any) -> None:
        emit(
            progress,
            kind,
            message,
            level=level,
            channel_id=job.channel_id,
            channel_index=channel_index,
            channel_total=channel_total,
            out_dir=str(out_dir),
            **kw,
        )

    if _cancelled():
        return ChannelResult(
            channel_id=job.channel_id,
            success=False,
            out_dir=out_dir,
            error="已取消",
        )

    scheme_label, scheme_desc = NAMING_SCHEMES.get(scheme, NAMING_SCHEMES[DEFAULT_NAMING_SCHEME])
    _prog("log", f"開始備份頻道 ID {job.channel_id}…")
    _prog("log", f"附件命名：{scheme_label} — {scheme_desc}")
    _prog(
        "log",
        "命名規則套用於所有附件類型（圖片/GIF/影片/音訊/其他）；"
        "媒體分類只改變子資料夾，不改變檔名規則。",
    )

    try:
        channel = await client.fetch_channel(job.channel_id)
    except discord.NotFound:
        err = f"找不到頻道 ID {job.channel_id}"
        _prog("error", err, level="error")
        return ChannelResult(job.channel_id, False, out_dir, error=err)
    except discord.Forbidden:
        err = f"無權限存取頻道 {job.channel_id}（需檢視頻道 + 讀取訊息歷史）"
        _prog("error", err, level="error")
        return ChannelResult(job.channel_id, False, out_dir, error=err)
    except discord.HTTPException as exc:
        err = f"取得頻道失敗：{exc}"
        _prog("error", err, level="error")
        return ChannelResult(job.channel_id, False, out_dir, error=err)

    if isinstance(channel, discord.ForumChannel):
        err = f"此 ID 是論壇頻道「{channel.name}」，請改用討論串（Thread）ID"
        _prog("error", err, level="error")
        return ChannelResult(job.channel_id, False, out_dir, channel_name=channel.name, error=err)

    if not hasattr(channel, "history"):
        err = f"頻道類型不支援讀取歷史：{type(channel).__name__}"
        _prog("error", err, level="error")
        return ChannelResult(job.channel_id, False, out_dir, error=err)

    channel_name = getattr(channel, "name", None) or ""
    if not channel_name:
        # DM 等可能無 name
        channel_name = f"channel-{str(job.channel_id)[-6:]}"
    guild = getattr(channel, "guild", None)
    guild_id = str(guild.id) if guild else None
    guild_name = guild.name if guild else None

    # 新建備份：用討論串／頻道名稱當資料夾名（不用 ID）
    if not job.resume and job.out_dir is None:
        parent = job.output_parent or Path("backups")
        out_dir = unique_channel_out_dir(parent, channel_name)
    elif job.out_dir is not None:
        out_dir = job.out_dir
    else:
        parent = job.output_parent or Path("backups")
        out_dir = unique_channel_out_dir(parent, channel_name)

    media_dir = out_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    if sort_media:
        for sub in MEDIA_CATEGORY_FOLDERS.values():
            (media_dir / sub).mkdir(parents=True, exist_ok=True)
    if log_to_file:
        setup_logging(out_dir / "errors.log", also_console=False)

    _prog(
        "channel_start",
        f"[{channel_index}/{channel_total}] {channel_name} → {out_dir.name}",
        channel_name=channel_name,
        guild_id=guild_id or "",
        guild_name=guild_name or "",
    )
    _prog("log", f"輸出資料夾：{out_dir}")
    if sort_media:
        _prog(
            "log",
            "媒體分類：開啟 → media/images、media/gifs、media/videos、media/audio、media/files",
        )
    else:
        _prog("log", "媒體分類：關閉 → 全部放在 media/")
    if delay_dl > 0 or delay_msg > 0:
        _prog(
            "log",
            f"限速延遲：附件後 {delay_dl:g}s、訊息後 {delay_msg:g}s"
            "（官方 Bot 仍會自動處理 429 rate limit）",
        )
    _prog("log", f"開始由舊到新掃描「{channel_name}」歷史訊息…")

    messages: list[dict[str, Any]] = []
    last_message_id: Optional[int] = None
    att_seq = 1
    attachment_ok = 0
    attachment_fail = 0
    empty_content_count = 0
    fatal = False
    error_msg: Optional[str] = None
    images_found = 0
    files_found = 0
    current_day: Optional[str] = None
    day_msg_count = 0
    day_att_count = 0

    if job.resume:
        messages, last_message_id, att_seq = load_existing_messages(out_dir)
        _prog(
            "log",
            f"續傳：已有 {len(messages)} 則訊息，附件序號從 {att_seq} 開始",
            channel_name=channel_name,
            messages=len(messages),
        )

    name_builder = AttachmentNameBuilder(scheme=scheme, start_seq=att_seq)

    meta: dict[str, Any] = {
        "channel_id": str(job.channel_id),
        "channel_name": channel_name,
        "guild_id": guild_id,
        "guild_name": guild_name,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "message_count": len(messages),
        "attachment_count": 0,
        "attachment_failed": 0,
        "timezone": "UTC",
        "tool_version": TOOL_VERSION,
        "naming_scheme": scheme,
        "sort_media_by_type": sort_media,
        "delay_download_sec": delay_dl,
        "delay_message_sec": delay_msg,
    }

    history_kwargs: dict[str, Any] = {"limit": None, "oldest_first": True}
    if last_message_id is not None:
        history_kwargs["after"] = discord.Object(id=last_message_id)

    for history_attempt in range(HISTORY_RETRY_LIMIT):
        if _cancelled():
            fatal = True
            error_msg = "已取消"
            break
        try:
            async for message in channel.history(**history_kwargs):  # type: ignore[attr-defined]
                if _cancelled():
                    fatal = True
                    error_msg = "已取消"
                    break

                msg_day = message.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
                msg_day_compact = message.created_at.astimezone(timezone.utc).strftime("%Y%m%d")
                if current_day != msg_day:
                    if current_day is not None and verbose:
                        _prog(
                            "log",
                            f"── 日期 {current_day} 小計：訊息 {day_msg_count} 則，附件 {day_att_count} 個 ──",
                            channel_name=channel_name,
                        )
                    current_day = msg_day
                    day_msg_count = 0
                    day_att_count = 0
                    if verbose:
                        _prog(
                            "log",
                            f"📅 掃描到日期 {msg_day}（UTC）的訊息…",
                            channel_name=channel_name,
                        )

                day_msg_count += 1
                n_att = len(message.attachments)
                author = getattr(message.author, "display_name", None) or getattr(
                    message.author, "name", "?"
                )
                msg_time = message.created_at.astimezone(timezone.utc).strftime("%H:%M:%S")

                if n_att > 0:
                    img_n = sum(
                        1
                        for a in message.attachments
                        if is_image_attachment(a.filename, a.content_type)
                    )
                    if verbose:
                        kind_hint = (
                            f"含 {img_n} 張圖片" + (f"、{n_att - img_n} 個其他檔" if n_att > img_n else "")
                            if img_n
                            else f"含 {n_att} 個附件"
                        )
                        _prog(
                            "log",
                            f"🔎 找到 {msg_day} {msg_time} UTC · {author} · {kind_hint} · msg={message.id}",
                            channel_name=channel_name,
                        )
                elif opts.log_every_message and verbose:
                    preview = (message.content or "")[:40].replace("\n", " ")
                    _prog(
                        "log",
                        f"… {msg_day} {msg_time} {author}: {preview or '(無文字/無附件)'}",
                        channel_name=channel_name,
                    )

                attachment_records: list[dict[str, Any]] = []
                for att_i, attachment in enumerate(message.attachments, start=1):
                    if _cancelled():
                        fatal = True
                        error_msg = "已取消"
                        break

                    category = classify_media(attachment.filename, attachment.content_type)
                    is_img = category in ("images", "gifs")
                    if is_img:
                        images_found += 1
                    else:
                        files_found += 1

                    # ----------------------------------------------------------
                    # 命名與分類彼此獨立：
                    # 1) 一律用下拉選單的 naming scheme 產生檔名（name_builder）
                    # 2) 分類只決定放哪個子資料夾（images/gifs/videos/…）
                    #    關閉分類時全部放 media/，檔名規則不變
                    # ----------------------------------------------------------
                    target_dir_for_name = (
                        media_dir / media_subfolder(category) if sort_media else media_dir
                    )
                    target_dir_for_name.mkdir(parents=True, exist_ok=True)

                    # 步驟 1：依使用者選擇的 scheme 命名（所有類型共用同一套序號）
                    filename, used_seq = name_builder.next_name(
                        message.created_at,
                        attachment.filename,
                        attachment.content_type,
                        target_dir_for_name,
                    )
                    att_seq = name_builder.global_seq
                    # 步驟 2：只決定路徑（media/ 或 media/<category>/），不改檔名
                    _tdir, relative, dest = resolve_attachment_paths(
                        media_dir,
                        filename,
                        sort_by_type=sort_media,
                        category=category,
                    )
                    size_txt = format_bytes(attachment.size)
                    type_label = MEDIA_CATEGORY_LABELS_ZH.get(category, "檔案")

                    if verbose:
                        _prog(
                            "log",
                            f"⬇ 開始下載{type_label} [{att_i}/{n_att}] "
                            f"#{used_seq} 「{attachment.filename}」({size_txt}) "
                            f"→ {relative}",
                            channel_name=channel_name,
                            messages=len(messages),
                            attachments_ok=attachment_ok,
                            attachments_fail=attachment_fail,
                        )

                    def _dl_progress(done: int, total: Optional[int], _fn: str = filename) -> None:
                        if not verbose or not total or total <= 0:
                            return
                        pct = min(100, int(done * 100 / total))
                        # 僅在 25/50/75/100 節點記錄，避免洗版
                        if pct not in (25, 50, 75, 100) and done < total:
                            return
                        _prog(
                            "log",
                            f"   … {_fn} 進度 {format_bytes(done)} / {format_bytes(total)} ({pct}%)",
                            channel_name=channel_name,
                        )

                    already = dest.exists() and dest.stat().st_size > 0
                    ok, err, written = await download_attachment(
                        session,
                        attachment.url,
                        dest,
                        expected_size=attachment.size,
                        on_progress=_dl_progress if verbose else None,
                    )
                    # 附件後延遲（略過已存在檔案時也延遲，避免連發請求）
                    if not await polite_delay(delay_dl, cancel_event):
                        fatal = True
                        error_msg = "已取消"
                        break
                    day_att_count += 1
                    if ok:
                        attachment_ok += 1
                        if verbose:
                            action = "略過（已存在）" if already else "完成"
                            _prog(
                                "log",
                                f"✓ {action} {type_label} → {relative} "
                                f"({format_bytes(written or attachment.size)}) "
                                f"[{msg_day_compact}]",
                                channel_name=channel_name,
                                messages=len(messages),
                                attachments_ok=attachment_ok,
                                attachments_fail=attachment_fail,
                            )
                        attachment_records.append(
                            {
                                "id": str(attachment.id),
                                "filename": attachment.filename,
                                "url": attachment.url,
                                "size": attachment.size,
                                "content_type": attachment.content_type,
                                "media_category": category,
                                "local_path": relative,
                                "saved_as": filename,
                                "download_error": None,
                            }
                        )
                    else:
                        attachment_fail += 1
                        logger.error(
                            "附件下載失敗 message=%s file=%s：%s",
                            message.id,
                            attachment.filename,
                            err,
                        )
                        _prog(
                            "log",
                            f"✗ 下載失敗 「{attachment.filename}」：{err}",
                            level="warning",
                            channel_name=channel_name,
                            messages=len(messages),
                            attachments_ok=attachment_ok,
                            attachments_fail=attachment_fail,
                        )
                        attachment_records.append(
                            {
                                "id": str(attachment.id),
                                "filename": attachment.filename,
                                "url": attachment.url,
                                "size": attachment.size,
                                "content_type": attachment.content_type,
                                "media_category": category,
                                "local_path": None,
                                "saved_as": None,
                                "download_error": err,
                            }
                        )
                    _prog(
                        "attachment",
                        f"附件 {'OK' if ok else 'FAIL'}: {attachment.filename} → {filename if ok else '?'}",
                        level="info" if ok else "warning",
                        channel_name=channel_name,
                        messages=len(messages),
                        attachments_ok=attachment_ok,
                        attachments_fail=attachment_fail,
                    )

                if fatal:
                    break

                record = serialize_message(message, attachment_records)
                if (
                    not (record.get("content") or "").strip()
                    and not attachment_records
                    and not record.get("embeds")
                    and message.type == discord.MessageType.default
                    and not message.embeds
                    and not message.stickers
                ):
                    empty_content_count += 1

                messages.append(record)
                last_message_id = message.id
                history_kwargs["after"] = discord.Object(id=last_message_id)

                _prog(
                    "message",
                    f"訊息 {len(messages)}"
                    + (f" · {msg_day} · 附件 {n_att}" if n_att else f" · {msg_day}"),
                    channel_name=channel_name,
                    messages=len(messages),
                    attachments_ok=attachment_ok,
                    attachments_fail=attachment_fail,
                )

                if not await polite_delay(delay_msg, cancel_event):
                    fatal = True
                    error_msg = "已取消"
                    break

                if len(messages) % CHECKPOINT_EVERY == 0:
                    meta["message_count"] = len(messages)
                    meta["attachment_count"] = attachment_ok
                    meta["attachment_failed"] = attachment_fail
                    meta["exported_at"] = datetime.now(timezone.utc).isoformat()
                    write_messages_json(out_dir, meta, messages)
                    if verbose:
                        _prog(
                            "log",
                            f"💾 檢查點：已處理 {len(messages)} 則訊息，"
                            f"附件成功 {attachment_ok} / 失敗 {attachment_fail} "
                            f"（圖片約 {images_found}、其他檔 {files_found}）",
                            channel_name=channel_name,
                        )

            break  # history finished or cancelled
        except (discord.HTTPException, discord.GatewayNotFound, aiohttp.ClientError, OSError) as exc:
            logger.warning(
                "讀取歷史中斷（%s/%s）：%s",
                history_attempt + 1,
                HISTORY_RETRY_LIMIT,
                exc,
            )
            _prog(
                "log",
                f"讀取中斷，重試中… ({history_attempt + 1}/{HISTORY_RETRY_LIMIT})：{exc}",
                level="warning",
                channel_name=channel_name,
            )
            if history_attempt + 1 >= HISTORY_RETRY_LIMIT:
                fatal = True
                error_msg = f"讀取歷史重試次數用盡：{exc}"
                break
            await asyncio.sleep(2 ** history_attempt)
            if last_message_id is not None:
                history_kwargs["after"] = discord.Object(id=last_message_id)

    if current_day is not None and verbose:
        _prog(
            "log",
            f"── 日期 {current_day} 小計：訊息 {day_msg_count} 則，附件 {day_att_count} 個 ──",
            channel_name=channel_name,
        )

    meta["message_count"] = len(messages)
    meta["attachment_count"] = attachment_ok
    meta["attachment_failed"] = attachment_fail
    meta["exported_at"] = datetime.now(timezone.utc).isoformat()
    meta["images_found"] = images_found
    meta["other_files_found"] = files_found
    write_messages_json(out_dir, meta, messages)

    if empty_content_count > 0 and empty_content_count >= max(5, len(messages) // 10 or 1):
        warn = (
            f"偵測到大量空 content（約 {empty_content_count} 則）。"
            "請確認已開啟 Message Content Intent。"
        )
        _prog("log", warn, level="warning", channel_name=channel_name)

    success = not fatal
    if success and error_msg is None:
        summary = (
            f"完成「{channel_name}」：訊息 {len(messages)}，"
            f"附件成功 {attachment_ok} / 失敗 {attachment_fail}"
            f"（圖片 {images_found}、其他 {files_found}），命名={scheme_label}"
        )
        _prog(
            "channel_done",
            summary,
            channel_name=channel_name,
            messages=len(messages),
            attachments_ok=attachment_ok,
            attachments_fail=attachment_fail,
        )
    else:
        _prog(
            "channel_done",
            error_msg or "失敗",
            level="error",
            channel_name=channel_name,
            messages=len(messages),
            attachments_ok=attachment_ok,
            attachments_fail=attachment_fail,
        )

    return ChannelResult(
        channel_id=job.channel_id,
        success=success,
        out_dir=out_dir,
        channel_name=channel_name,
        message_count=len(messages),
        attachment_ok=attachment_ok,
        attachment_fail=attachment_fail,
        error=error_msg,
    )


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------


class _BatchClient(discord.Client):
    def __init__(self, **kwargs: Any):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents, **kwargs)
        self.ready_event = asyncio.Event()

    async def on_ready(self) -> None:
        if not self.ready_event.is_set():
            self.ready_event.set()


async def run_batch_backup(
    token: str,
    jobs: list[ChannelJob],
    output_root: Path,
    *,
    progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[asyncio.Event] = None,
    batch_stamp: Optional[str] = None,
    options: Optional[BackupOptions] = None,
) -> BatchResult:
    """
    登入一次 Bot，依序備份多個頻道。

    每個 job 若未指定 out_dir，會建立在 output_root 下。
    多頻道時另建 batch_*/ 目錄並寫入 summary.json。
    """
    opts = (options or BackupOptions()).clamp_delays()
    if not jobs:
        return BatchResult(login_error="沒有要備份的頻道")

    stamp = batch_stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    multi = len(jobs) > 1
    batch_dir: Optional[Path] = None

    if multi:
        batch_dir = output_root / f"batch_{stamp}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(batch_dir / "batch.log", also_console=True)
        base_for_channels = batch_dir
    else:
        output_root.mkdir(parents=True, exist_ok=True)
        setup_logging(also_console=True)
        base_for_channels = output_root

    # 準備 job：新建時不先用 ID 建資料夾，等抓到頻道名稱再用名稱建
    prepared: list[ChannelJob] = []
    for job in jobs:
        if job.out_dir is not None:
            # 續傳 / 明確指定路徑
            job.out_dir.mkdir(parents=True, exist_ok=True)
            (job.out_dir / "media").mkdir(parents=True, exist_ok=True)
            prepared.append(job)
        else:
            parent = job.output_parent or base_for_channels
            parent.mkdir(parents=True, exist_ok=True)
            prepared.append(
                ChannelJob(
                    channel_id=job.channel_id,
                    out_dir=None,
                    resume=False,
                    output_parent=parent,
                )
            )

    emit(progress, "log", f"準備備份 {len(prepared)} 個頻道…")
    emit(progress, "log", f"輸出根目錄：{output_root}")

    # --- Token 清理與預檢（避免無意義的 WebSocket 嘗試）---
    token = sanitize_token(token)
    emit(progress, "log", f"Token 檢查：{describe_token(token)}")
    try:
        ok, verify_msg, user_data = await verify_bot_token(token)
    except Exception as exc:  # noqa: BLE001
        msg = f"Token 預檢例外：{exc}"
        batch = BatchResult(batch_dir=batch_dir, login_error=msg)
        emit(progress, "error", msg, level="error")
        return batch
    if not ok:
        batch = BatchResult(batch_dir=batch_dir, login_error=verify_msg)
        emit(progress, "error", verify_msg, level="error")
        return batch
    emit(progress, "log", verify_msg)
    emit(progress, "log", "正在建立 Discord Gateway 連線…")

    client = _BatchClient()
    batch = BatchResult(batch_dir=batch_dir)
    connect_task: Optional[asyncio.Task[Any]] = None

    try:
        await client.login(token)
        emit(progress, "log", "HTTP 登入成功，等待 Gateway ready…")
        connect_task = asyncio.create_task(client.connect(reconnect=True))
        try:
            await asyncio.wait_for(client.ready_event.wait(), timeout=90)
        except asyncio.TimeoutError:
            batch.login_error = (
                "Token 有效，但 Gateway 連線逾時未能就緒。\n"
                "請檢查網路、防火牆、代理，或稍後再試。\n"
                "（這通常不是 Channel ID 問題；Channel ID 在登入後才會用到。）"
            )
            emit(progress, "error", batch.login_error, level="error")
            return batch

        emit(
            progress,
            "log",
            f"已登入：{client.user}（{getattr(client.user, 'id', '?')}）",
        )
        # Intent 提示（不影響登入，但影響訊息 content）
        if not client.intents.message_content:
            emit(
                progress,
                "log",
                "警告：未啟用 message_content intent（程式內建應已開啟）。",
                level="warning",
            )
        else:
            emit(
                progress,
                "log",
                "提示：若訊息文字全空，請到 Developer Portal → Bot → "
                "開啟 MESSAGE CONTENT INTENT 並儲存。",
            )

        timeout = aiohttp.ClientTimeout(total=None)
        connector = aiohttp.TCPConnector(limit=4)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            for idx, job in enumerate(prepared, start=1):
                if cancel_event is not None and cancel_event.is_set():
                    emit(progress, "log", "批次已取消", level="warning")
                    for remaining in prepared[idx - 1 :]:
                        batch.results.append(
                            ChannelResult(
                                channel_id=remaining.channel_id,
                                success=False,
                                out_dir=remaining.out_dir or base_for_channels,
                                error="已取消",
                            )
                        )
                    break

                result = await backup_one_channel(
                    client,
                    job,
                    session=session,
                    progress=progress,
                    cancel_event=cancel_event,
                    channel_index=idx,
                    channel_total=len(prepared),
                    log_to_file=True,
                    options=opts,
                )
                batch.results.append(result)

                # 多頻道之間可選延遲
                if idx < len(prepared) and opts.delay_channel_sec > 0:
                    emit(
                        progress,
                        "log",
                        f"頻道間延遲 {opts.delay_channel_sec:g}s…",
                    )
                    if not await polite_delay(opts.delay_channel_sec, cancel_event):
                        emit(progress, "log", "批次已取消", level="warning")
                        for remaining in prepared[idx:]:
                            batch.results.append(
                                ChannelResult(
                                    channel_id=remaining.channel_id,
                                    success=False,
                                    out_dir=remaining.out_dir or base_for_channels,
                                    error="已取消",
                                )
                            )
                        break

    except discord.LoginFailure as exc:
        issues = diagnose_token_issues(token)
        batch.login_error = (
            "登入失敗：Discord 拒絕此 Token（LoginFailure）。\n"
            f"診斷：{describe_token(token)}\n"
            + (("可能原因：\n- " + "\n- ".join(issues) + "\n") if issues else "")
            + "請到 Developer Portal → Bot → Reset Token 後重新複製「純 Token」。\n"
            f"原始錯誤：{exc}"
        )
        emit(progress, "error", batch.login_error, level="error")
        return batch
    except Exception as exc:  # noqa: BLE001
        batch.login_error = f"未預期錯誤：{exc}"
        logger.exception("batch backup failed")
        emit(progress, "error", batch.login_error, level="error")
        return batch
    finally:
        try:
            if not client.is_closed():
                await client.close()
        except Exception:  # noqa: BLE001
            pass
        # ensure connect task ends
        try:
            if connect_task is not None and not connect_task.done():
                connect_task.cancel()
                try:
                    await connect_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

    # summary
    if batch_dir is not None:
        summary = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": TOOL_VERSION,
            "channel_count": len(batch.results),
            "channels": [
                {
                    "channel_id": str(r.channel_id),
                    "channel_name": r.channel_name,
                    "success": r.success,
                    "message_count": r.message_count,
                    "attachment_ok": r.attachment_ok,
                    "attachment_fail": r.attachment_fail,
                    "out_dir": str(r.out_dir),
                    "error": r.error,
                }
                for r in batch.results
            ],
        }
        summary_path = batch_dir / "summary.json"
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            f.write("\n")
        emit(progress, "log", f"批次摘要：{summary_path}")

    ok_n = sum(1 for r in batch.results if r.success)
    emit(
        progress,
        "batch_done",
        f"批次結束：成功 {ok_n}/{len(batch.results)}",
        level="info" if batch.all_ok else "warning",
    )
    return batch
