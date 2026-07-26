#!/usr/bin/env python3
"""
Discord 頻道備份工具 — 圖形介面
雙語（繁中 / English）、已存 Bot、首次教學、多頻道批次。
"""

from __future__ import annotations

import asyncio
import queue
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import customtkinter as ctk
except ImportError:
    print(
        "缺少 customtkinter。請執行：\n  pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

from tkinter import filedialog, font as tkfont, messagebox

import bot_store
import i18n
from core import (
    DEFAULT_NAMING_SCHEME,
    NAMING_SCHEMES,
    TOOL_VERSION,
    BackupOptions,
    ChannelJob,
    ProgressEvent,
    parse_channel_ids,
    run_batch_backup,
    sanitize_token,
    verify_bot_token,
)
from i18n import LANG_EN, LANG_ZH, get_lang, naming_option_label, set_lang, t, tutorial_steps
from settings_store import load_settings, update_settings

# ---------------------------------------------------------------------------
# 統一字型
# ---------------------------------------------------------------------------


def _pick_ui_font_family() -> str:
    candidates = (
        "Microsoft JhengHei UI",
        "Microsoft JhengHei",
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "Segoe UI",
        "Arial",
    )
    try:
        available = {name.lower() for name in tkfont.families()}
    except Exception:  # noqa: BLE001
        available = set()
    for name in candidates:
        if not available or name.lower() in available:
            return name
    return "TkDefaultFont"


def _pick_mono_font_family(ui_family: str) -> str:
    candidates = ("Cascadia Mono", "Consolas", "Courier New")
    try:
        available = {name.lower() for name in tkfont.families()}
    except Exception:  # noqa: BLE001
        available = set()
    for name in candidates:
        if not available or name.lower() in available:
            return name
    return ui_family


class AppFonts:
    _instance: Optional["AppFonts"] = None

    def __init__(self) -> None:
        self.family = _pick_ui_font_family()
        self.mono_family = _pick_mono_font_family(self.family)
        self.body = ctk.CTkFont(family=self.family, size=13)
        self.small = ctk.CTkFont(family=self.family, size=12)
        self.label = ctk.CTkFont(family=self.family, size=13, weight="bold")
        self.title = ctk.CTkFont(family=self.family, size=18, weight="bold")
        self.heading = ctk.CTkFont(family=self.family, size=14, weight="bold")
        self.button = ctk.CTkFont(family=self.family, size=13)
        self.button_primary = ctk.CTkFont(family=self.family, size=14, weight="bold")
        self.mono = ctk.CTkFont(family=self.mono_family, size=12)
        self.entry = ctk.CTkFont(family=self.family, size=13)

    @classmethod
    def get(cls) -> "AppFonts":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> "AppFonts":
        cls._instance = cls()
        return cls._instance

    def apply_tk_defaults(self, root: ctk.CTk) -> None:
        try:
            for name, size, weight in (
                ("TkDefaultFont", 13, "normal"),
                ("TkTextFont", 13, "normal"),
                ("TkFixedFont", 12, "normal"),
                ("TkMenuFont", 13, "normal"),
                ("TkHeadingFont", 14, "bold"),
            ):
                try:
                    f = tkfont.nametofont(name)
                    family = self.mono_family if name == "TkFixedFont" else self.family
                    f.configure(family=family, size=size, weight=weight)
                except Exception:  # noqa: BLE001
                    continue
            root.option_add("*Font", (self.family, 13))
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# 教學
# ---------------------------------------------------------------------------


class TutorialWindow(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, on_finish: Optional[Callable[[], None]] = None):
        super().__init__(master)
        self.on_finish = on_finish
        self.step = 0
        self.steps = tutorial_steps()
        self.fonts = AppFonts.get()
        self.title(t("tutorial_title"))
        self.geometry("700x560")
        self.minsize(560, 480)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self, text="", font=self.fonts.title, wraplength=640, justify="left"
        )
        self.title_label.grid(row=0, column=0, padx=24, pady=(24, 8), sticky="w")

        self.body = ctk.CTkTextbox(self, wrap="word", font=self.fonts.body)
        self.body.grid(row=1, column=0, padx=24, pady=8, sticky="nsew")
        self.body.configure(state="disabled")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=24, pady=(8, 8), sticky="ew")
        btn_row.grid_columnconfigure(1, weight=1)

        self.link_btn = ctk.CTkButton(
            btn_row, text=t("open_link"), width=160, font=self.fonts.button, command=self._open_link
        )
        self.link_btn.grid(row=0, column=0, sticky="w")
        self.progress_label = ctk.CTkLabel(btn_row, text="", font=self.fonts.small)
        self.progress_label.grid(row=0, column=1, padx=12)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=3, column=0, padx=24, pady=(8, 24), sticky="ew")
        nav.grid_columnconfigure(1, weight=1)

        self.skip_btn = ctk.CTkButton(
            nav,
            text=t("tutorial_skip"),
            font=self.fonts.button,
            fg_color="transparent",
            border_width=1,
            command=self._finish,
        )
        self.skip_btn.grid(row=0, column=0, sticky="w")
        self.prev_btn = ctk.CTkButton(
            nav, text=t("tutorial_prev"), width=100, font=self.fonts.button, command=self._prev
        )
        self.prev_btn.grid(row=0, column=2, padx=(0, 8))
        self.next_btn = ctk.CTkButton(
            nav, text=t("tutorial_next"), width=140, font=self.fonts.button_primary, command=self._next
        )
        self.next_btn.grid(row=0, column=3, sticky="e")

        self.protocol("WM_DELETE_WINDOW", self._finish)
        self._render()
        self.after(100, self._center)

    def _center(self) -> None:
        self.update_idletasks()
        try:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            w, h = self.winfo_width(), self.winfo_height()
            self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
        except Exception:  # noqa: BLE001
            pass

    def _render(self) -> None:
        step = self.steps[self.step]
        self.title_label.configure(text=step["title"])
        self.body.configure(state="normal")
        self.body.delete("1.0", "end")
        self.body.insert("1.0", step["body"])
        self.body.configure(state="disabled")
        if step.get("link"):
            self.link_btn.configure(state="normal", text=step.get("link_label") or t("open_link"))
        else:
            self.link_btn.configure(state="disabled", text=t("tutorial_no_link"))
        self.progress_label.configure(text=f"{self.step + 1} / {len(self.steps)}")
        self.prev_btn.configure(state="normal" if self.step > 0 else "disabled")
        if self.step >= len(self.steps) - 1:
            self.next_btn.configure(text=t("tutorial_finish"))
        else:
            self.next_btn.configure(text=t("tutorial_next"))

    def _open_link(self) -> None:
        link = self.steps[self.step].get("link")
        if link:
            webbrowser.open(link)

    def _prev(self) -> None:
        if self.step > 0:
            self.step -= 1
            self._render()

    def _next(self) -> None:
        if self.step < len(self.steps) - 1:
            self.step += 1
            self._render()
        else:
            self._finish()

    def _finish(self) -> None:
        update_settings(tutorial_completed=True)
        self.grab_release()
        self.destroy()
        if self.on_finish:
            self.on_finish()


# ---------------------------------------------------------------------------
# 已存 Bot 管理（含 ✕ 刪除）
# ---------------------------------------------------------------------------


class ManageBotsWindow(ctk.CTkToplevel):
    def __init__(self, master: "BackupApp"):
        super().__init__(master)
        self.master_app = master
        self.fonts = AppFonts.get()
        self.title(t("manage_bots_title"))
        self.geometry("640x420")
        self.minsize(480, 320)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=t("manage_bots_hint"), font=self.fonts.small, wraplength=600).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            self, text=t("close"), font=self.fonts.button, command=self._close, width=100
        ).grid(row=2, column=0, pady=(8, 16))

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._rebuild()

    def _close(self) -> None:
        self.grab_release()
        self.destroy()
        self.master_app._refresh_bot_menu()

    def _rebuild(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        bots = bot_store.list_bots()
        if not bots:
            ctk.CTkLabel(self.list_frame, text=t("empty_list"), font=self.fonts.body).grid(
                row=0, column=0, sticky="w", padx=8, pady=12
            )
            return
        for i, bot in enumerate(bots):
            row = ctk.CTkFrame(self.list_frame)
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=4)
            row.grid_columnconfigure(0, weight=1)
            name = bot.get("name") or t("bot_unknown")
            guilds = bot_store.guilds_label(bot, empty=t("bot_no_guild"))
            ctk.CTkLabel(
                row,
                text=f"{name}\n{guilds}",
                font=self.fonts.body,
                justify="left",
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=10, pady=8)
            bid = bot.get("id") or ""
            ctk.CTkButton(
                row,
                text="✕",
                width=36,
                height=28,
                fg_color="#8B0000",
                hover_color="#A52A2A",
                font=self.fonts.button,
                command=lambda b=bid, n=name: self._delete(b, n),
            ).grid(row=0, column=1, padx=10, pady=8)

    def _delete(self, bot_id: str, name: str) -> None:
        if not messagebox.askyesno(t("delete_bot_title"), t("delete_bot_confirm", name=name), parent=self):
            return
        ok = bot_store.delete_bot(bot_id)
        if ok:
            if self.master_app._current_bot_id == bot_id:
                self.master_app._current_bot_id = None
                self.master_app.token_var.set("")
            messagebox.showinfo(t("delete_bot_title"), t("delete_bot_done", name=name), parent=self)
            self._rebuild()
            self.master_app._refresh_bot_menu()
            self.master_app._append_log(t("delete_bot_done", name=name))


# ---------------------------------------------------------------------------
# 主視窗
# ---------------------------------------------------------------------------


class BackupApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.settings = load_settings()
        lang = self.settings.get("language") or LANG_EN
        set_lang(lang)

        self.fonts = AppFonts.reset()
        self.fonts.apply_tk_defaults(self)

        self._event_queue: queue.Queue = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._cancel_flag = threading.Event()
        self._loop_cancel: Optional[asyncio.Event] = None
        self._worker_loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._current_bot_id: Optional[str] = self.settings.get("last_bot_id") or None
        self._bot_menu_map: dict[str, str] = {}  # display label → bot id
        self._session_guilds: dict[str, str] = {}  # guild_id → name during backup
        self._naming_keys = list(NAMING_SCHEMES.keys())

        self.title(f"{t('app_title')} v{TOOL_VERSION}")
        self.geometry(self.settings.get("window_geometry") or "920x760")
        self.minsize(740, 600)

        self._build_menu()
        self._build_ui()
        self._apply_language_texts()
        self._refresh_bot_menu(select_id=self._current_bot_id)
        if self._current_bot_id:
            self._load_bot(self._current_bot_id, quiet=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queue)
        self.after(200, self._maybe_show_tutorial)

    # --- build ---

    def _build_menu(self) -> None:
        f = self.fonts
        self.top_bar = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        self.lbl_bar_title = ctk.CTkLabel(self.top_bar, text=t("bar_title"), font=f.heading)
        self.lbl_bar_title.pack(side="left", padx=16)

        self.btn_tutorial = ctk.CTkButton(
            self.top_bar, text=t("tutorial"), width=90, height=28, font=f.button, command=self._show_tutorial
        )
        self.btn_tutorial.pack(side="right", padx=(4, 12), pady=6)

        self.btn_readme = ctk.CTkButton(
            self.top_bar,
            text=t("readme"),
            width=80,
            height=28,
            font=f.button,
            fg_color="transparent",
            border_width=1,
            command=self._open_readme,
        )
        self.btn_readme.pack(side="right", padx=4, pady=6)

        # 語言下拉：放在 Developer Portal 右邊（pack side=right 先 pack 的在更右邊）
        # 順序：最右 tutorial，再左 readme，再左 language，再左 portal
        lang_values = [t("lang_zh"), t("lang_en")]
        current = t("lang_zh") if get_lang() == LANG_ZH else t("lang_en")
        self.lang_var = ctk.StringVar(value=current)
        self.lang_menu = ctk.CTkOptionMenu(
            self.top_bar,
            values=lang_values,
            variable=self.lang_var,
            width=120,
            height=28,
            font=f.button,
            dropdown_font=f.small,
            command=self._on_language_change,
        )
        self.lang_menu.pack(side="right", padx=4, pady=6)

        self.btn_portal = ctk.CTkButton(
            self.top_bar,
            text=t("dev_portal"),
            width=140,
            height=28,
            font=f.button,
            fg_color="transparent",
            border_width=1,
            command=lambda: webbrowser.open("https://discord.com/developers/applications"),
        )
        self.btn_portal.pack(side="right", padx=4, pady=6)

    def _build_ui(self) -> None:
        f = self.fonts
        self.root = ctk.CTkFrame(self, fg_color="transparent")
        self.root.pack(fill="both", expand=True, padx=16, pady=12)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(6, weight=1)

        # Token header row: label + saved bots dropdown + manage
        head = ctk.CTkFrame(self.root, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew")
        head.grid_columnconfigure(1, weight=1)

        self.lbl_token = ctk.CTkLabel(head, text=t("bot_token"), anchor="w", font=f.label)
        self.lbl_token.grid(row=0, column=0, sticky="w")

        self.bot_select_var = ctk.StringVar(value=t("saved_bots_none"))
        self.bot_menu = ctk.CTkOptionMenu(
            head,
            values=[t("saved_bots_none")],
            variable=self.bot_select_var,
            width=280,
            font=f.small,
            dropdown_font=f.small,
            command=self._on_bot_selected,
        )
        self.bot_menu.grid(row=0, column=2, sticky="e", padx=(8, 4))

        self.btn_manage_bots = ctk.CTkButton(
            head,
            text=t("manage_bots"),
            width=70,
            height=28,
            font=f.button,
            fg_color="transparent",
            border_width=1,
            command=self._open_manage_bots,
        )
        self.btn_manage_bots.grid(row=0, column=3, sticky="e")

        token_row = ctk.CTkFrame(self.root, fg_color="transparent")
        token_row.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        token_row.grid_columnconfigure(0, weight=1)

        self.token_var = ctk.StringVar()
        self.token_entry = ctk.CTkEntry(
            token_row,
            textvariable=self.token_var,
            show="•",
            font=f.entry,
            placeholder_text=t("token_placeholder"),
        )
        self.token_entry.grid(row=0, column=0, sticky="ew")

        self.show_token_var = ctk.BooleanVar(value=False)
        self.chk_show = ctk.CTkCheckBox(
            token_row,
            text=t("show_token"),
            variable=self.show_token_var,
            width=70,
            font=f.body,
            command=self._toggle_token_visibility,
        )
        self.chk_show.grid(row=0, column=1, padx=(8, 0))

        self.btn_test = ctk.CTkButton(
            token_row, text=t("test_token"), width=110, font=f.button, command=self._test_token
        )
        self.btn_test.grid(row=0, column=2, padx=(8, 0))

        self.lbl_channels = ctk.CTkLabel(
            self.root, text=t("channel_ids"), anchor="w", font=f.label
        )
        self.lbl_channels.grid(row=2, column=0, sticky="w")
        self.channels_box = ctk.CTkTextbox(self.root, height=100, font=f.mono)
        self.channels_box.grid(row=3, column=0, sticky="ew", pady=(4, 12))
        if self.settings.get("last_channel_ids"):
            self.channels_box.insert("1.0", self.settings["last_channel_ids"])

        out_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        out_frame.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        out_frame.grid_columnconfigure(1, weight=1)

        self.lbl_output = ctk.CTkLabel(out_frame, text=t("output_dir"), font=f.label)
        self.lbl_output.grid(row=0, column=0, sticky="w", padx=(0, 8))
        default_out = self.settings.get("output_dir") or str(
            (Path(__file__).resolve().parent / "backups")
        )
        self.output_var = ctk.StringVar(value=default_out)
        self.output_entry = ctk.CTkEntry(out_frame, textvariable=self.output_var, font=f.entry)
        self.output_entry.grid(row=0, column=1, sticky="ew")
        self.btn_browse = ctk.CTkButton(
            out_frame, text=t("browse"), width=80, font=f.button, command=self._browse_output
        )
        self.btn_browse.grid(row=0, column=2, padx=(8, 0))

        opt_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        opt_frame.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        opt_frame.grid_columnconfigure(1, weight=1)

        self.lbl_naming = ctk.CTkLabel(opt_frame, text=t("naming"), font=f.label)
        self.lbl_naming.grid(row=0, column=0, sticky="w", padx=(0, 8))

        saved_scheme = self.settings.get("naming_scheme") or DEFAULT_NAMING_SCHEME
        if saved_scheme not in self._naming_keys:
            saved_scheme = DEFAULT_NAMING_SCHEME
        self.naming_var = ctk.StringVar(value=naming_option_label(saved_scheme))
        self.naming_menu = ctk.CTkOptionMenu(
            opt_frame,
            values=[naming_option_label(k) for k in self._naming_keys],
            variable=self.naming_var,
            font=f.body,
            dropdown_font=f.small,
            width=420,
        )
        self.naming_menu.grid(row=0, column=1, sticky="ew")

        self.verbose_var = ctk.BooleanVar(value=bool(self.settings.get("verbose_log", True)))
        self.chk_verbose = ctk.CTkCheckBox(
            opt_frame, text=t("verbose_log"), variable=self.verbose_var, font=f.body
        )
        self.chk_verbose.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.sort_media_var = ctk.BooleanVar(
            value=bool(self.settings.get("sort_media_by_type", False))
        )
        self.chk_sort_media = ctk.CTkCheckBox(
            opt_frame, text=t("sort_media"), variable=self.sort_media_var, font=f.body
        )
        self.chk_sort_media.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # Rate-limit delays (seconds)
        self.lbl_delay_section = ctk.CTkLabel(
            opt_frame, text=t("delay_section"), font=f.label, anchor="w"
        )
        self.lbl_delay_section.grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 4))

        delay_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        delay_row.grid(row=4, column=0, columnspan=2, sticky="ew")

        def _delay_var(key: str, default: float = 0.0) -> ctk.StringVar:
            try:
                v = float(self.settings.get(key, default))
            except (TypeError, ValueError):
                v = default
            return ctk.StringVar(value=str(v))

        self.delay_download_var = _delay_var("delay_download_sec", 0.0)
        self.delay_message_var = _delay_var("delay_message_sec", 0.0)
        self.delay_channel_var = _delay_var("delay_channel_sec", 0.0)

        self.lbl_delay_dl = ctk.CTkLabel(delay_row, text=t("delay_download"), font=f.small)
        self.lbl_delay_dl.grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.entry_delay_dl = ctk.CTkEntry(
            delay_row, textvariable=self.delay_download_var, width=64, font=f.entry
        )
        self.entry_delay_dl.grid(row=0, column=1, sticky="w", padx=(0, 12))

        self.lbl_delay_msg = ctk.CTkLabel(delay_row, text=t("delay_message"), font=f.small)
        self.lbl_delay_msg.grid(row=0, column=2, sticky="w", padx=(0, 4))
        self.entry_delay_msg = ctk.CTkEntry(
            delay_row, textvariable=self.delay_message_var, width=64, font=f.entry
        )
        self.entry_delay_msg.grid(row=0, column=3, sticky="w", padx=(0, 12))

        self.lbl_delay_ch = ctk.CTkLabel(delay_row, text=t("delay_channel"), font=f.small)
        self.lbl_delay_ch.grid(row=0, column=4, sticky="w", padx=(0, 4))
        self.entry_delay_ch = ctk.CTkEntry(
            delay_row, textvariable=self.delay_channel_var, width=64, font=f.entry
        )
        self.entry_delay_ch.grid(row=0, column=5, sticky="w")

        self.lbl_delay_hint = ctk.CTkLabel(
            opt_frame,
            text=t("delay_hint"),
            font=f.small,
            text_color=("gray40", "gray70"),
            anchor="w",
            wraplength=640,
        )
        self.lbl_delay_hint.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        mid = ctk.CTkFrame(self.root)
        mid.grid(row=6, column=0, sticky="nsew", pady=(0, 12))
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_rowconfigure(3, weight=1)

        self.status_label = ctk.CTkLabel(
            mid, text=t("status_ready"), anchor="w", font=f.body
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        self.channel_progress = ctk.CTkProgressBar(mid)
        self.channel_progress.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        self.channel_progress.set(0)

        self.stats_label = ctk.CTkLabel(mid, text=t("stats_zero"), anchor="w", font=f.small)
        self.stats_label.grid(row=2, column=0, sticky="ew", padx=12, pady=4)

        self.log_box = ctk.CTkTextbox(mid, wrap="word", font=f.body)
        self.log_box.grid(row=3, column=0, sticky="nsew", padx=12, pady=(4, 12))
        self.log_box.configure(state="disabled")

        actions = ctk.CTkFrame(self.root, fg_color="transparent")
        actions.grid(row=7, column=0, sticky="ew")
        actions.grid_columnconfigure(0, weight=1)

        self.start_btn = ctk.CTkButton(
            actions,
            text=t("start_backup"),
            height=40,
            font=f.button_primary,
            command=self._start_backup,
        )
        self.start_btn.grid(row=0, column=1, padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            actions,
            text=t("cancel"),
            height=40,
            width=100,
            font=f.button,
            fg_color="#8B0000",
            hover_color="#A52A2A",
            state="disabled",
            command=self._cancel_backup,
        )
        self.cancel_btn.grid(row=0, column=2, padx=(0, 8))

        self.open_out_btn = ctk.CTkButton(
            actions,
            text=t("open_output"),
            height=40,
            width=160,
            font=f.button,
            fg_color="transparent",
            border_width=1,
            command=self._open_output_folder,
        )
        self.open_out_btn.grid(row=0, column=3)

        self.lbl_autosave = ctk.CTkLabel(
            self.root, text=t("auto_save_hint"), font=f.small, text_color=("gray40", "gray70")
        )
        self.lbl_autosave.grid(row=8, column=0, sticky="w", pady=(4, 0))

    # --- language ---

    def _on_language_change(self, choice: str) -> None:
        new_lang = LANG_EN if str(choice).strip() == "English" else LANG_ZH
        set_lang(new_lang)
        update_settings(language=new_lang)
        self._apply_language_texts()
        self._refresh_bot_menu(select_id=self._current_bot_id)

    def _apply_language_texts(self) -> None:
        self.title(f"{t('app_title')} v{TOOL_VERSION}")
        self.lbl_bar_title.configure(text=t("bar_title"))
        self.btn_tutorial.configure(text=t("tutorial"))
        self.btn_readme.configure(text=t("readme"))
        self.btn_portal.configure(text=t("dev_portal"))
        # 語言選單本身
        self.lang_menu.configure(values=[t("lang_zh"), t("lang_en")])
        self.lang_var.set(t("lang_zh") if get_lang() == LANG_ZH else t("lang_en"))

        self.lbl_token.configure(text=t("bot_token"))
        self.btn_manage_bots.configure(text=t("manage_bots"))
        self.token_entry.configure(placeholder_text=t("token_placeholder"))
        self.chk_show.configure(text=t("show_token"))
        self.btn_test.configure(text=t("test_token"))
        self.lbl_channels.configure(text=t("channel_ids"))
        self.lbl_output.configure(text=t("output_dir"))
        self.btn_browse.configure(text=t("browse"))
        self.lbl_naming.configure(text=t("naming"))
        # naming options
        scheme = self._selected_naming_scheme()
        self.naming_menu.configure(values=[naming_option_label(k) for k in self._naming_keys])
        self.naming_var.set(naming_option_label(scheme))
        self.chk_verbose.configure(text=t("verbose_log"))
        self.chk_sort_media.configure(text=t("sort_media"))
        self.lbl_delay_section.configure(text=t("delay_section"))
        self.lbl_delay_dl.configure(text=t("delay_download"))
        self.lbl_delay_msg.configure(text=t("delay_message"))
        self.lbl_delay_ch.configure(text=t("delay_channel"))
        self.lbl_delay_hint.configure(text=t("delay_hint"))
        if not self._running:
            self.status_label.configure(text=t("status_ready"))
        self.stats_label.configure(text=t("stats_zero") if not self._running else self.stats_label.cget("text"))
        self.start_btn.configure(text=t("start_backup"))
        self.cancel_btn.configure(text=t("cancel"))
        self.open_out_btn.configure(text=t("open_output"))
        self.lbl_autosave.configure(text=t("auto_save_hint"))

    # --- bots ---

    def _refresh_bot_menu(self, select_id: Optional[str] = None) -> None:
        bots = bot_store.list_bots()
        self._bot_menu_map.clear()
        if not bots:
            values = [t("saved_bots_none")]
            self.bot_menu.configure(values=values)
            self.bot_select_var.set(values[0])
            return
        values = [t("saved_bots_pick")]
        self._bot_menu_map[t("saved_bots_pick")] = ""
        selected_label = values[0]
        for b in bots:
            name = b.get("name") or t("bot_unknown")
            guilds = bot_store.guilds_label(b, empty=t("bot_no_guild"))
            label = f"{name}  ·  {guilds}"
            # 避免重複 label
            base = label
            n = 2
            while label in self._bot_menu_map:
                label = f"{base} ({n})"
                n += 1
            self._bot_menu_map[label] = b.get("id") or ""
            values.append(label)
            if select_id and b.get("id") == select_id:
                selected_label = label
        self.bot_menu.configure(values=values)
        self.bot_select_var.set(selected_label)

    def _on_bot_selected(self, choice: str) -> None:
        bot_id = self._bot_menu_map.get(choice) or ""
        if not bot_id:
            return
        self._load_bot(bot_id)

    def _load_bot(self, bot_id: str, quiet: bool = False) -> None:
        token = bot_store.get_bot_token(bot_id)
        bot = bot_store.get_bot(bot_id)
        if not token or not bot:
            if not quiet:
                messagebox.showerror(t("error"), t("token_fail_status"))
            return
        self._current_bot_id = bot_id
        self.token_var.set(token)
        channels = bot.get("channel_ids") or ""
        if channels:
            self.channels_box.delete("1.0", "end")
            self.channels_box.insert("1.0", channels)
        update_settings(last_bot_id=bot_id)
        if not quiet:
            self._append_log(t("bot_loaded", name=bot.get("name") or t("bot_unknown")))
            self.status_label.configure(text=t("bot_loaded", name=bot.get("name") or t("bot_unknown")))

    def _open_manage_bots(self) -> None:
        ManageBotsWindow(self)

    def _save_current_bot(
        self,
        token: str,
        name: str,
        bot_user_id: str = "",
        guilds: Optional[list[dict[str, str]]] = None,
    ) -> None:
        channels = self.channels_box.get("1.0", "end").strip()
        saved = bot_store.upsert_bot(
            token=token,
            name=name,
            bot_user_id=bot_user_id,
            guilds=guilds,
            channel_ids=channels,
            bot_id=self._current_bot_id,
        )
        self._current_bot_id = saved.get("id")
        update_settings(last_bot_id=self._current_bot_id or "")
        self._refresh_bot_menu(select_id=self._current_bot_id)
        self._append_log(t("save_bot_ok", name=saved.get("name") or name))

    # --- helpers ---

    def _toggle_token_visibility(self) -> None:
        self.token_entry.configure(show="" if self.show_token_var.get() else "•")

    def _test_token(self) -> None:
        raw = self.token_var.get()
        token = sanitize_token(raw)
        if not token:
            messagebox.showwarning(t("missing_token"), t("paste_token"))
            return
        if token != raw.strip():
            self.token_var.set(token)

        self._append_log(t("verifying_token"))
        self.status_label.configure(text=t("verifying_token"))

        def worker() -> None:
            try:
                ok, msg, data = asyncio.run(verify_bot_token(token))
                self._event_queue.put(("token_test", ok, msg, data, token))
            except Exception as exc:  # noqa: BLE001
                self._event_queue.put(("token_test", False, str(exc), None, token))

        threading.Thread(target=worker, daemon=True).start()

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.home()))
        if path:
            self.output_var.set(path)

    def _open_output_folder(self) -> None:
        path = Path(self.output_var.get()).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(t("error"), t("open_folder_fail", e=exc))

    def _open_readme(self) -> None:
        readme = Path(__file__).resolve().parent / "README.md"
        if readme.exists():
            try:
                import os

                os.startfile(readme)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                webbrowser.open(readme.as_uri())
        else:
            messagebox.showinfo(t("info"), t("readme_missing"))

    def _append_log(self, text: str, level: str = "info") -> None:
        if get_lang() == LANG_EN:
            prefix = {"warning": "[WARN] ", "error": "[ERROR] "}.get(level, "")
        else:
            prefix = {"warning": "[警告] ", "error": "[錯誤] "}.get(level, "")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", prefix + text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_widget_state(self, widget: Any, state: str) -> None:
        try:
            widget.configure(state=state)
        except Exception:  # noqa: BLE001
            pass

    def _set_running(self, running: bool) -> None:
        """鎖定 / 解鎖備份期間不應變更的控制項。"""
        self._running = running
        # 主按鈕
        self._set_widget_state(self.start_btn, "disabled" if running else "normal")
        self._set_widget_state(self.cancel_btn, "normal" if running else "disabled")
        # 輸入與選項（含附件命名，避免備份中途改方案）
        locked = "disabled" if running else "normal"
        for w in (
            self.token_entry,
            self.channels_box,
            self.output_entry,
            self.naming_menu,
            self.bot_menu,
            self.lang_menu,
            self.chk_show,
            self.chk_verbose,
            self.chk_sort_media,
            self.entry_delay_dl,
            self.entry_delay_msg,
            self.entry_delay_ch,
            self.btn_test,
            self.btn_browse,
            self.btn_manage_bots,
            self.btn_tutorial,
        ):
            self._set_widget_state(w, locked)

    def _maybe_show_tutorial(self) -> None:
        if not self.settings.get("tutorial_completed"):
            self._show_tutorial()

    def _show_tutorial(self) -> None:
        TutorialWindow(self)

    def _selected_naming_scheme(self) -> str:
        label = self.naming_var.get()
        for key in self._naming_keys:
            if label == naming_option_label(key):
                return key
            # 寬鬆比對
            zh = i18n.NAMING_LABELS[key][LANG_ZH][0]
            en = i18n.NAMING_LABELS[key][LANG_EN][0]
            if label.startswith(zh) or label.startswith(en):
                return key
        return DEFAULT_NAMING_SCHEME

    @staticmethod
    def _parse_delay(raw: str, max_v: float = 30.0) -> float:
        try:
            v = float(str(raw).strip().replace(",", "."))
        except (TypeError, ValueError):
            return 0.0
        if v != v:  # NaN
            return 0.0
        return max(0.0, min(max_v, v))

    # --- backup ---

    def _start_backup(self) -> None:
        # 立刻上鎖，避免連點 race（必須在任何 await/執行緒前）
        if self._running:
            return
        self._running = True
        self._set_running(True)

        try:
            token = sanitize_token(self.token_var.get())
            if not token:
                messagebox.showwarning(t("missing_token"), t("paste_token"))
                self._set_running(False)
                return
            self.token_var.set(token)

            channels_text = self.channels_box.get("1.0", "end").strip()
            try:
                channel_ids = parse_channel_ids(channels_text)
            except ValueError as exc:
                messagebox.showwarning(t("invalid_channel"), str(exc))
                self._set_running(False)
                return

            output_root = Path(self.output_var.get().strip() or "backups").expanduser()
            try:
                output_root.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror(t("output_error"), str(exc))
                self._set_running(False)
                return

            naming_scheme = self._selected_naming_scheme()
            verbose = bool(self.verbose_var.get())
            sort_media = bool(self.sort_media_var.get())
            delay_dl = self._parse_delay(self.delay_download_var.get())
            delay_msg = self._parse_delay(self.delay_message_var.get())
            delay_ch = self._parse_delay(self.delay_channel_var.get(), max_v=60.0)
            # 寫回正規化後的數字
            self.delay_download_var.set(str(delay_dl))
            self.delay_message_var.set(str(delay_msg))
            self.delay_channel_var.set(str(delay_ch))
            update_settings(
                output_dir=str(output_root),
                last_channel_ids=channels_text if self.settings.get("remember_channel_ids", True) else "",
                naming_scheme=naming_scheme,
                verbose_log=verbose,
                sort_media_by_type=sort_media,
                delay_download_sec=delay_dl,
                delay_message_sec=delay_msg,
                delay_channel_sec=delay_ch,
            )

            jobs = [ChannelJob(channel_id=cid) for cid in channel_ids]
            options = BackupOptions(
                naming_scheme=naming_scheme,
                verbose=verbose,
                sort_media_by_type=sort_media,
                delay_download_sec=delay_dl,
                delay_message_sec=delay_msg,
                delay_channel_sec=delay_ch,
            )
            self._session_guilds.clear()

            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.configure(state="disabled")
            self.channel_progress.set(0)
            self.stats_label.configure(text=t("stats_zero"))
            self.status_label.configure(text=t("preparing", n=len(jobs)))
            scheme_label = naming_option_label(naming_scheme)
            self._append_log(t("batch_start", n=len(jobs), path=str(output_root)))
            self._append_log(
                t(
                    "naming_scheme_log",
                    label=scheme_label,
                    scheme=naming_scheme,
                    verbose=t("on") if verbose else t("off"),
                )
            )
            self._append_log(
                t("sort_media_on_log", state=t("on") if sort_media else t("off"))
            )
            self._append_log(
                t("delay_log", dl=f"{delay_dl:g}", msg=f"{delay_msg:g}", ch=f"{delay_ch:g}")
            )
            self._append_log(
                "Connecting to Discord…" if get_lang() == LANG_EN else "正在連線 Discord…"
            )
            self._cancel_flag.clear()
            self._loop_cancel = None
            self._worker_loop = None

            def worker() -> None:
                try:
                    loop = asyncio.SelectorEventLoop()  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._worker_loop = loop
                cancel_event = asyncio.Event()
                self._loop_cancel = cancel_event

                def on_progress(event: ProgressEvent) -> None:
                    try:
                        self._event_queue.put(event)
                    except Exception:  # noqa: BLE001
                        pass
                    if self._cancel_flag.is_set() and not cancel_event.is_set():
                        try:
                            loop.call_soon_threadsafe(cancel_event.set)
                        except Exception:  # noqa: BLE001
                            pass

                try:
                    self._event_queue.put(
                        ProgressEvent(
                            kind="log",
                            message=(
                                "Backup worker started…"
                                if get_lang() == LANG_EN
                                else "備份工作執行緒已啟動…"
                            ),
                        )
                    )
                    batch = loop.run_until_complete(
                        run_batch_backup(
                            token,
                            jobs,
                            output_root,
                            progress=on_progress,
                            cancel_event=cancel_event,
                            options=options,
                        )
                    )
                    self._event_queue.put(("done", batch, token))
                except Exception as exc:  # noqa: BLE001
                    self._event_queue.put(("fail", f"{exc}\n{traceback.format_exc()}"))
                finally:
                    self._loop_cancel = None
                    self._worker_loop = None
                    try:
                        # 取消殘留 tasks
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        if pending:
                            loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )
                    except Exception:  # noqa: BLE001
                        pass
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:  # noqa: BLE001
                        pass
                    try:
                        loop.close()
                    except Exception:  # noqa: BLE001
                        pass

            self._worker = threading.Thread(target=worker, name="backup-worker", daemon=True)
            self._worker.start()
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"{exc}\n{traceback.format_exc()}", "error")
            self._set_running(False)
            messagebox.showerror(t("backup_fail"), str(exc))

    def _cancel_backup(self) -> None:
        if not self._running:
            return
        self._cancel_flag.set()
        # 立刻通知 asyncio 端
        loop = self._worker_loop
        ev = self._loop_cancel
        if loop is not None and ev is not None:
            try:
                loop.call_soon_threadsafe(ev.set)
            except Exception:  # noqa: BLE001
                pass
        self._append_log(t("cancel_log"), "warning")
        self.status_label.configure(text=t("cancelling"))
        # 取消時保持 start 鎖定，直到 worker 回報 done/fail
        self._set_widget_state(self.cancel_btn, "disabled")

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._event_queue.get_nowait()
                if isinstance(item, ProgressEvent):
                    self._handle_progress(item)
                elif isinstance(item, tuple):
                    kind = item[0]
                    if kind == "done":
                        self._on_batch_done(item[1], item[2] if len(item) > 2 else "")
                    elif kind == "fail":
                        self._append_log(str(item[1]), "error")
                        self.status_label.configure(text=t("backup_fail"))
                        self._set_running(False)
                        messagebox.showerror(t("backup_fail"), t("backup_fail_body"))
                    elif kind == "token_test":
                        ok, msg, data, token = item[1], item[2], item[3], item[4]
                        level = "info" if ok else "error"
                        self._append_log(msg, level)
                        self.status_label.configure(
                            text=t("token_ok_status") if ok else t("token_fail_status")
                        )
                        if ok:
                            name = (data or {}).get("username") or t("bot_unknown")
                            bot_id = str((data or {}).get("id") or "")
                            self._save_current_bot(token, name=name, bot_user_id=bot_id)
                            messagebox.showinfo(t("token_test"), msg)
                        else:
                            messagebox.showerror(t("token_test_fail"), msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle_progress(self, event: ProgressEvent) -> None:
        if event.message and event.kind in (
            "log",
            "error",
            "channel_start",
            "channel_done",
            "batch_done",
        ):
            self._append_log(event.message, event.level)

        if event.kind == "channel_start":
            if event.guild_id and event.guild_name:
                self._session_guilds[str(event.guild_id)] = event.guild_name
            if event.channel_total:
                frac = (event.channel_index - 1) / max(event.channel_total, 1)
                self.channel_progress.set(frac)
                self.status_label.configure(
                    text=t(
                        "backing_up",
                        i=event.channel_index,
                        t=event.channel_total,
                        name=event.channel_name or event.channel_id,
                    )
                )

        if event.kind in ("message", "attachment", "channel_done"):
            self.stats_label.configure(
                text=t(
                    "stats_fmt",
                    m=event.messages,
                    ok=event.attachments_ok,
                    fail=event.attachments_fail,
                )
            )

        if event.kind == "channel_done" and event.channel_total:
            self.channel_progress.set(event.channel_index / max(event.channel_total, 1))

        if event.kind == "batch_done":
            self.channel_progress.set(1)

    def _on_batch_done(self, batch: Any, token: str) -> None:
        self._set_running(False)
        if batch.login_error:
            self.status_label.configure(text=t("login_fail"))
            self._append_log(batch.login_error, "error")
            short = batch.login_error if len(batch.login_error) < 900 else (
                batch.login_error[:900] + "\n\n…"
            )
            messagebox.showerror(t("login_fail"), short)
            return

        # 登入成功：更新已存 bot（含伺服器）
        if token:
            guilds = [{"id": gid, "name": name} for gid, name in self._session_guilds.items()]
            # 名稱：若有 current bot 用既有名，否則 Bot
            name = t("bot_unknown")
            if self._current_bot_id:
                b = bot_store.get_bot(self._current_bot_id)
                if b and b.get("name"):
                    name = b["name"]
            self._save_current_bot(token, name=name, guilds=guilds)

        ok = sum(1 for r in batch.results if r.success)
        total = len(batch.results)
        self.status_label.configure(text=t("done_status", ok=ok, total=total))
        lines = [t("success_line", ok=ok, total=total)]
        for r in batch.results:
            mark = "✓" if r.success else "✗"
            lines.append(
                f"{mark} {r.channel_name or r.channel_id}: "
                f"msg {r.message_count}, att {r.attachment_ok} (fail {r.attachment_fail})\n"
                f"    {r.out_dir}"
            )
        if batch.batch_dir:
            lines.append("\n" + t("batch_dir", p=batch.batch_dir))

        if ok == total:
            messagebox.showinfo(t("backup_done"), "\n".join(lines))
        else:
            messagebox.showwarning(t("backup_partial"), "\n".join(lines))

    def _on_close(self) -> None:
        try:
            update_settings(window_geometry=self.geometry(), language=get_lang())
        except Exception:  # noqa: BLE001
            pass
        if self._running:
            if not messagebox.askyesno(t("quit_title"), t("quit_confirm")):
                return
            self._cancel_flag.set()
        self.destroy()


def _require_windows() -> None:
    if sys.platform == "win32":
        return
    msg = "Please run this app on Windows."
    print(msg, file=sys.stderr)
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb

        _r = _tk.Tk()
        _r.withdraw()
        _mb.showerror("Discord Bot Media Downloader", msg)
        _r.destroy()
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(1)


def main() -> None:
    _require_windows()
    try:
        app = BackupApp()
        app.mainloop()
    except Exception:
        import traceback as tb

        tb.print_exc()
        log_path = Path(__file__).resolve().parent / "gui_crash.log"
        try:
            with log_path.open("w", encoding="utf-8") as f:
                f.write(tb.format_exc())
            print(f"\n{log_path}", file=sys.stderr)
        except OSError:
            pass
        try:
            input(t("crash_enter") if "t" in dir() else "\nPress Enter…")
        except EOFError:
            pass
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
