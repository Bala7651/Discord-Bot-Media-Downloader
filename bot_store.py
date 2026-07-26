"""Saved bot list with encrypted tokens (local user data only)."""

from __future__ import annotations

import base64
import json
import os
import secrets
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from settings_store import APP_DIR

BOTS_PATH = APP_DIR / "bots.enc.json"
KEY_PATH = APP_DIR / ".store_key"
LEGACY_PLAIN_PATH = APP_DIR / "bots.json"  # 若誤建明文，刪除時一併清


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Crypto
# ---------------------------------------------------------------------------


def _dpapi_protect(data: bytes) -> Optional[bytes]:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
        blob_out = DATA_BLOB()
        if not crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            "discord_channel_backup",
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            return None
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            kernel32.LocalFree(blob_out.pbData)
    except Exception:  # noqa: BLE001
        return None


def _dpapi_unprotect(data: bytes) -> Optional[bytes]:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
        blob_out = DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            return None
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            kernel32.LocalFree(blob_out.pbData)
    except Exception:  # noqa: BLE001
        return None


def _load_or_create_fernet_key() -> bytes:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    key = base64.urlsafe_b64encode(secrets.token_bytes(32))
    KEY_PATH.write_bytes(key)
    try:
        if sys.platform != "win32":
            os.chmod(KEY_PATH, 0o600)
    except OSError:
        pass
    return key


def _fernet_encrypt(plain: bytes) -> bytes:
    try:
        from cryptography.fernet import Fernet

        f = Fernet(_load_or_create_fernet_key())
        return f.encrypt(plain)
    except ImportError:
        # 無 cryptography 時：僅做混淆（仍寫入本機私有目錄）
        return base64.urlsafe_b64encode(plain)


def _fernet_decrypt(blob: bytes) -> bytes:
    try:
        from cryptography.fernet import Fernet

        f = Fernet(_load_or_create_fernet_key())
        return f.decrypt(blob)
    except ImportError:
        return base64.urlsafe_b64decode(blob)
    except Exception:  # noqa: BLE001
        return base64.urlsafe_b64decode(blob)


def encrypt_token(token: str) -> dict[str, str]:
    raw = token.encode("utf-8")
    protected = _dpapi_protect(raw)
    if protected is not None:
        return {
            "method": "dpapi",
            "data": base64.b64encode(protected).decode("ascii"),
        }
    return {
        "method": "fernet",
        "data": base64.b64encode(_fernet_encrypt(raw)).decode("ascii"),
    }


def decrypt_token(blob: dict[str, Any]) -> str:
    method = (blob or {}).get("method") or "fernet"
    data_b64 = (blob or {}).get("data") or ""
    raw = base64.b64decode(data_b64.encode("ascii"))
    if method == "dpapi":
        plain = _dpapi_unprotect(raw)
        if plain is None:
            raise ValueError("DPAPI decrypt failed")
        return plain.decode("utf-8")
    return _fernet_decrypt(raw).decode("utf-8")


def secure_delete_file(path: Path) -> None:
    """覆寫後刪除，降低殘留風險。"""
    try:
        if not path.exists():
            return
        size = path.stat().st_size
        with path.open("r+b") as f:
            f.write(os.urandom(max(size, 64)))
            f.flush()
            os.fsync(f.fileno())
        path.unlink(missing_ok=True)
    except OSError:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Store CRUD
# ---------------------------------------------------------------------------


def _empty_store() -> dict[str, Any]:
    return {"version": 1, "bots": []}


def load_store() -> dict[str, Any]:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not BOTS_PATH.exists():
        return _empty_store()
    try:
        with BOTS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_store()
        data.setdefault("version", 1)
        data.setdefault("bots", [])
        return data
    except (json.JSONDecodeError, OSError):
        return _empty_store()


def save_store(data: dict[str, Any]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    # 絕不寫明文 token 欄位
    clean = deepcopy(data)
    for bot in clean.get("bots") or []:
        bot.pop("token", None)
        bot.pop("token_plain", None)
    tmp = BOTS_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(BOTS_PATH)
    # 清理可能存在的明文殘留
    if LEGACY_PLAIN_PATH.exists():
        secure_delete_file(LEGACY_PLAIN_PATH)


def list_bots() -> list[dict[str, Any]]:
    bots = load_store().get("bots") or []
    # 回傳不含解密 token 的安全複本
    out = []
    for b in bots:
        out.append(
            {
                "id": b.get("id"),
                "name": b.get("name") or "Bot",
                "bot_user_id": b.get("bot_user_id") or "",
                "guilds": list(b.get("guilds") or []),
                "channel_ids": b.get("channel_ids") or "",
                "last_used": b.get("last_used") or "",
                "has_token": bool(b.get("token_blob")),
            }
        )
    # 最近使用在前
    out.sort(key=lambda x: x.get("last_used") or "", reverse=True)
    return out


def get_bot_token(bot_id: str) -> Optional[str]:
    for b in load_store().get("bots") or []:
        if b.get("id") == bot_id and b.get("token_blob"):
            try:
                return decrypt_token(b["token_blob"])
            except Exception:  # noqa: BLE001
                return None
    return None


def get_bot(bot_id: str) -> Optional[dict[str, Any]]:
    for b in list_bots():
        if b.get("id") == bot_id:
            return b
    return None


def upsert_bot(
    *,
    token: str,
    name: str,
    bot_user_id: str = "",
    guilds: Optional[list[dict[str, str]]] = None,
    channel_ids: str = "",
    bot_id: Optional[str] = None,
) -> dict[str, Any]:
    """新增或更新 Bot（以 bot_user_id 或 token 比對既有項目）。"""
    store = load_store()
    bots: list[dict[str, Any]] = list(store.get("bots") or [])
    guilds = guilds or []

    target: Optional[dict[str, Any]] = None
    if bot_id:
        for b in bots:
            if b.get("id") == bot_id:
                target = b
                break
    if target is None and bot_user_id:
        for b in bots:
            if b.get("bot_user_id") and b.get("bot_user_id") == bot_user_id:
                target = b
                break
    if target is None:
        # 比對 token（解密）
        for b in bots:
            blob = b.get("token_blob")
            if not blob:
                continue
            try:
                if decrypt_token(blob) == token:
                    target = b
                    break
            except Exception:  # noqa: BLE001
                continue

    if target is None:
        target = {"id": str(uuid.uuid4())}
        bots.append(target)

    target["name"] = name or target.get("name") or "Bot"
    if bot_user_id:
        target["bot_user_id"] = bot_user_id
    target["token_blob"] = encrypt_token(token)
    target["last_used"] = _utcnow()
    if channel_ids is not None and channel_ids != "":
        target["channel_ids"] = channel_ids
    if guilds:
        # 合併伺服器名稱
        by_id = {g.get("id"): g for g in (target.get("guilds") or []) if g.get("id")}
        for g in guilds:
            if g.get("id"):
                by_id[g["id"]] = {"id": g["id"], "name": g.get("name") or g["id"]}
        target["guilds"] = list(by_id.values())

    store["bots"] = bots
    save_store(store)
    return {
        "id": target["id"],
        "name": target.get("name"),
        "bot_user_id": target.get("bot_user_id") or "",
        "guilds": list(target.get("guilds") or []),
        "channel_ids": target.get("channel_ids") or "",
        "last_used": target.get("last_used") or "",
        "has_token": True,
    }


def delete_bot(bot_id: str) -> bool:
    """永久刪除指定 Bot 的加密 Token 與紀錄。"""
    store = load_store()
    bots = list(store.get("bots") or [])
    new_bots = []
    found = False
    for b in bots:
        if b.get("id") == bot_id:
            found = True
            # 覆寫記憶體中的敏感欄位
            if isinstance(b.get("token_blob"), dict):
                b["token_blob"]["data"] = "0" * 64
            b.clear()
            continue
        new_bots.append(b)
    if not found:
        return False
    store["bots"] = new_bots
    if not new_bots:
        # 清單空了：直接安全刪除整個檔案與可能明文
        secure_delete_file(BOTS_PATH)
        secure_delete_file(LEGACY_PLAIN_PATH)
        # 保留 key 供之後再用；若要更狠可一併刪 key
        return True
    save_store(store)
    secure_delete_file(LEGACY_PLAIN_PATH)
    return True


def guilds_label(bot: dict[str, Any], empty: str = "") -> str:
    guilds = bot.get("guilds") or []
    names = [g.get("name") or g.get("id") for g in guilds if g]
    names = [n for n in names if n]
    if not names:
        return empty
    if len(names) <= 2:
        return " · ".join(names)
    return f"{names[0]} · {names[1]} +{len(names) - 2}"
