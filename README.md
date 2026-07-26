# Discord Bot Media Downloader

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20only-blue.svg)](#platform-support)

Backup **Discord channel / thread history and attachments** with the official **Bot API** (Python + discord.py).

English UI by default · **Traditional Chinese (繁體中文)** available in the app language menu.

> **Bot tokens only.** Do not use user-account tokens (self-bots).

---

## Platform support

| OS | Supported |
|----|-----------|
| **Windows 10 / 11** | Yes |
| **macOS** | **No** — not supported |
| **Linux** | **No** — not supported |

This project is **Windows-only** (GUI launcher `run_gui.bat`, packaging, and tested runtime).  
There is **no macOS app, no Homebrew formula, and no Linux support**.

---

## Quick start (Windows)

1. **Code → Download ZIP** and extract the whole folder  
2. Install [Python 3.10+](https://www.python.org/downloads/) with **Add python.exe to PATH**  
3. Double-click **`run_gui.bat`** (first run installs dependencies)  
4. Paste **Bot Token** + **Channel ID(s)** → **Start backup**  

In-app **Tutorial** covers bot setup and intents.

### CLI (Windows)

```bat
pip install -r requirements.txt
python backup.py --token YOUR_BOT_TOKEN --channel CHANNEL_ID
python backup.py --help
```

---

## Features

| | |
|--|--|
| GUI + progress log | Multi-channel batch |
| Folder named after channel/thread | Optional media folders (`images` / `gifs` / `videos` / …) |
| Naming schemes & rate delays | Checkpoints, retries, rate-limit handling |

**Output example**

```text
ChannelName/
  messages.json
  media/   # or media/images, media/gifs, ...
```

---

## Requirements

- **Windows 10 or 11**
- Python **3.10+**
- Bot with **Message Content Intent**, **View Channel**, **Read Message History**

Saved bots / prefs (if any) live under `%USERPROFILE%\.discord_channel_backup\` — **not** in this repo.

Optional: `pack_release.bat` builds a clean ZIP without `.venv`.

---

## License

MIT — see [LICENSE](LICENSE). See also [SECURITY.md](SECURITY.md).
