"""本機偏好設定（教學完成狀態、輸出目錄等）。不儲存 Token。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_DIR = Path.home() / ".discord_channel_backup"
SETTINGS_PATH = APP_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "tutorial_completed": False,
    "output_dir": "",
    "window_geometry": "",
    "remember_channel_ids": True,
    "last_channel_ids": "",
    "naming_scheme": "full",
    "verbose_log": True,
    "sort_media_by_type": False,
    "delay_download_sec": 0.0,
    "delay_message_sec": 0.0,
    "delay_channel_sec": 0.0,
    "language": "zh-TW",
    "last_bot_id": "",
}


def load_settings() -> dict[str, Any]:
    data = dict(DEFAULTS)
    if not SETTINGS_PATH.exists():
        return data
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            data.update({k: raw[k] for k in DEFAULTS if k in raw})
    except (json.JSONDecodeError, OSError):
        pass
    return data


def save_settings(data: dict[str, Any]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULTS)
    merged.update(data)
    # 絕不寫入 token
    merged.pop("token", None)
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")


def update_settings(**kwargs: Any) -> dict[str, Any]:
    data = load_settings()
    data.update(kwargs)
    save_settings(data)
    return data
