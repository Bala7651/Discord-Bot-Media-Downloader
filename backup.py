#!/usr/bin/env python3
"""
Discord 頻道備份工具 — 命令列介面
支援單頻道、多頻道批次、續傳。
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from tqdm import tqdm

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
    setup_logging,
)
import logging

logger = logging.getLogger("discord_backup")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Discord 頻道備份工具 v{TOOL_VERSION}：抓取歷史訊息並下載附件。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "範例：\n"
            "  python backup.py\n"
            "  python backup.py --token TOKEN --channel 111\n"
            "  python backup.py --token TOKEN --channels 111,222,333\n"
            "  python backup.py --token TOKEN --channel 111 --resume backups/channel_111_...\n"
            "  python gui.py          # 圖形介面（含首次教學）\n"
        ),
    )
    parser.add_argument("--token", "-t", help="Discord Bot Token")
    parser.add_argument("--channel", "-c", help="單一 Channel ID")
    parser.add_argument(
        "--channels",
        help="多個 Channel ID（逗號或空白分隔），例如 111,222,333",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="backups",
        help="備份輸出根目錄（預設：backups）",
    )
    parser.add_argument(
        "--resume",
        "-r",
        metavar="DIR",
        help="從既有備份目錄續傳（僅單頻道）",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="啟動圖形介面",
    )
    naming_help = "；".join(f"{k}={v[0]}（{v[1]}）" for k, v in NAMING_SCHEMES.items())
    parser.add_argument(
        "--naming",
        "-n",
        default=DEFAULT_NAMING_SCHEME,
        choices=list(NAMING_SCHEMES.keys()),
        help=f"附件命名方式（預設 {DEFAULT_NAMING_SCHEME}）。{naming_help}",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="關閉詳細日誌（不逐張/逐日輸出）",
    )
    parser.add_argument(
        "--sort-media",
        action="store_true",
        help="依類型分資料夾：media/images、gifs、videos、audio、files",
    )
    parser.add_argument(
        "--delay-download",
        type=float,
        default=0.0,
        metavar="SEC",
        help="每個附件下載後額外等待秒數（0–30，預設 0）",
    )
    parser.add_argument(
        "--delay-message",
        type=float,
        default=0.0,
        metavar="SEC",
        help="每則訊息處理後額外等待秒數（0–30，預設 0）",
    )
    parser.add_argument(
        "--delay-channel",
        type=float,
        default=0.0,
        metavar="SEC",
        help="多頻道時，頻道之間等待秒數（0–60，預設 0）",
    )
    return parser.parse_args(argv)


def resolve_inputs(args: argparse.Namespace) -> tuple[str, list[ChannelJob], Path]:
    token = sanitize_token(args.token or "")
    if not token:
        token = sanitize_token(getpass.getpass("請輸入 Discord Bot Token（輸入不會顯示）: "))
    if not token:
        print("錯誤：Token 不可為空。", file=sys.stderr)
        sys.exit(2)

    output_root = Path(args.output).expanduser().resolve()
    jobs: list[ChannelJob] = []

    if args.resume:
        resume_dir = Path(args.resume).expanduser().resolve()
        if not resume_dir.is_dir():
            print(f"錯誤：續傳目錄不存在：{resume_dir}", file=sys.stderr)
            sys.exit(2)
        # 從目錄名或 messages.json 推 channel id
        channel_id: Optional[int] = None
        if args.channel:
            channel_id = int(args.channel.strip())
        else:
            name = resume_dir.name
            # channel_123_timestamp
            parts = name.split("_")
            if len(parts) >= 2 and parts[0] == "channel" and parts[1].isdigit():
                channel_id = int(parts[1])
            else:
                meta_path = resume_dir / "messages.json"
                if meta_path.exists():
                    import json

                    with meta_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    cid = (data.get("meta") or {}).get("channel_id")
                    if cid:
                        channel_id = int(cid)
        if channel_id is None:
            print("錯誤：續傳時請用 --channel 指定 Channel ID，或使用標準輸出目錄名。", file=sys.stderr)
            sys.exit(2)
        jobs = [ChannelJob(channel_id=channel_id, out_dir=resume_dir, resume=True)]
        return token, jobs, output_root

    ids: list[int] = []
    if args.channels:
        ids.extend(parse_channel_ids(args.channels))
    if args.channel:
        ids.extend(parse_channel_ids(args.channel))

    if not ids:
        raw = input("請輸入 Channel ID（多個請用逗號分隔）: ").strip()
        try:
            ids = parse_channel_ids(raw)
        except ValueError as exc:
            print(f"錯誤：{exc}", file=sys.stderr)
            sys.exit(2)

    # 去重保序
    seen: set[int] = set()
    unique: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            unique.append(i)

    # 資料夾名稱在連線後以頻道／討論串名稱建立（不用 ID）
    if len(unique) == 1:
        jobs = [
            ChannelJob(
                channel_id=unique[0],
                out_dir=None,
                resume=False,
                output_parent=output_root,
            )
        ]
    else:
        # 多頻道時 run_batch_backup 會再建 batch_*，其下以名稱建子資料夾
        jobs = [
            ChannelJob(channel_id=i, out_dir=None, resume=False, output_parent=None)
            for i in unique
        ]

    return token, jobs, output_root


class CliProgress:
    def __init__(self) -> None:
        self.msg_bar: Optional[tqdm] = None
        self.att_bar: Optional[tqdm] = None
        self._cur_channel: Optional[int] = None

    def close_bars(self) -> None:
        if self.msg_bar is not None:
            self.msg_bar.close()
            self.msg_bar = None
        if self.att_bar is not None:
            self.att_bar.close()
            self.att_bar = None

    def __call__(self, event: ProgressEvent) -> None:
        if event.kind == "channel_start":
            self.close_bars()
            self._cur_channel = event.channel_id
            self.msg_bar = tqdm(desc=f"訊息 [{event.channel_name}]", unit="則", dynamic_ncols=True)
            self.att_bar = tqdm(desc=f"附件 [{event.channel_name}]", unit="檔", dynamic_ncols=True)
            logger.info(event.message)
        elif event.kind == "message":
            if self.msg_bar is not None:
                self.msg_bar.n = event.messages
                self.msg_bar.refresh()
        elif event.kind == "attachment":
            if self.att_bar is not None:
                self.att_bar.n = event.attachments_ok + event.attachments_fail
                self.att_bar.refresh()
        elif event.kind == "channel_done":
            self.close_bars()
            if event.level == "error":
                logger.error(event.message)
            else:
                logger.info(event.message)
        elif event.kind in ("log", "batch_done", "error"):
            if event.level == "error":
                logger.error(event.message)
            elif event.level == "warning":
                logger.warning(event.message)
            else:
                logger.info(event.message)


async def async_main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.gui:
        from gui import main as gui_main

        gui_main()
        return 0

    token, jobs, output_root = resolve_inputs(args)
    setup_logging()
    progress = CliProgress()

    options = BackupOptions(
        naming_scheme=args.naming,
        verbose=not args.quiet,
        sort_media_by_type=bool(args.sort_media),
        delay_download_sec=float(args.delay_download or 0),
        delay_message_sec=float(args.delay_message or 0),
        delay_channel_sec=float(args.delay_channel or 0),
    )
    logger.info(
        "命名方式：%s · 詳細日誌：%s",
        NAMING_SCHEMES.get(options.normalized_scheme(), ("?",))[0],
        "開" if options.verbose else "關",
    )

    try:
        batch = await run_batch_backup(
            token,
            jobs,
            output_root,
            progress=progress,
            options=options,
        )
    except KeyboardInterrupt:
        progress.close_bars()
        logger.warning("使用者中斷。")
        return 1
    finally:
        progress.close_bars()

    if batch.login_error:
        return 1

    print()
    print("=" * 50)
    for r in batch.results:
        status = "OK" if r.success else "FAIL"
        print(
            f"[{status}] {r.channel_name or r.channel_id}: "
            f"訊息 {r.message_count}, 附件 {r.attachment_ok}/{r.attachment_fail} 失敗"
        )
        print(f"       → {r.out_dir}")
        if r.error:
            print(f"       錯誤：{r.error}")
    if batch.batch_dir:
        print(f"批次目錄：{batch.batch_dir}")
    print("=" * 50)

    return batch.exit_code


def main() -> None:
    if sys.platform != "win32":
        print("Please run this tool on Windows.", file=sys.stderr)
        sys.exit(1)
    try:
        code = asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
