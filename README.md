# Discord Bot Media Downloader

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Backup **Discord channel / thread history and attachments** using the official **Bot API** (Python + [discord.py](https://github.com/Rapptz/discord.py)).

- Desktop **GUI** (`run_gui.bat` on Windows) or **CLI**
- Full history (oldest → newest), images / GIFs / videos / files
- Optional media subfolders, naming schemes, and rate-limit delays
- **UI language:** English by default · **Traditional Chinese (繁體中文)** available in the app language menu

> **Bot tokens only.** Do not use user-account tokens (self-bots) — against Discord ToS.

---

## Quick start (Windows)

1. **Code → Download ZIP** (or clone this repo) and extract the whole folder  
2. Install [Python 3.10+](https://www.python.org/downloads/) with **Add python.exe to PATH**  
3. Double-click **`run_gui.bat`**  
   - First run creates `.venv` and installs dependencies (1–3 min)  
4. In the app: paste **Bot Token** + **Channel ID(s)** → **Start backup**  
5. Optional: switch language to **繁體中文** via the top-bar dropdown (next to Developer Portal)

In-app **Tutorial** covers Bot setup, Message Content Intent, permissions, and Channel IDs — you do not need a long guide in this README.

More detail for non-developers: [使用說明_下載後請看.md](./使用說明_下載後請看.md) (Traditional Chinese).

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python gui.py
```

### CLI

```bash
pip install -r requirements.txt
python backup.py --token YOUR_BOT_TOKEN --channel CHANNEL_ID
python backup.py --help
```

---

## Features

| Feature | Description |
|--------|-------------|
| GUI | Progress, log, saved bots, delays, naming |
| Languages | **English (default)**, Traditional Chinese |
| Multi-channel | Batch several channel/thread IDs |
| Output folder | Named after **channel/thread title** (not the snowflake ID) |
| Media sort | Optional: `media/images`, `gifs`, `videos`, `audio`, `files` |
| Naming schemes | Numbers, date-seq, full timestamp+name, etc. |
| Delays | Optional sleep after file / message / between channels |
| Resilience | Auto rate-limit handling, retries, checkpoints |

### Output layout (example)

```text
YourChannelName/
  messages.json
  media/                 # or media/images, media/gifs, ...
  errors.log
```

---

## Requirements

- Python **3.10+**
- A Discord **bot** with:
  - **Message Content Intent** enabled
  - **View Channel** + **Read Message History** on target channels
- Network access to Discord

---

## Project layout

```text
run_gui.bat / pack_release.bat
gui.py · backup.py · core.py · i18n.py · bot_store.py · settings_store.py
requirements.txt · LICENSE · SECURITY.md · CONTRIBUTING.md
```

Local prefs / optional encrypted saved bots live under the **user home directory**  
(`~/.discord_channel_backup/`), **not** in this repo. Never commit tokens.

Pack a clean ZIP for friends (no `.venv`):

```bat
pack_release.bat
```

---

## Security

See [SECURITY.md](SECURITY.md). Reset any bot token that may have leaked.

---

## License

MIT — see [LICENSE](LICENSE).

Provided as-is; you are responsible for complying with Discord’s Terms of Service and applicable law.
