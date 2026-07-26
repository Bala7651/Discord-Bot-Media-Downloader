# Discord Bot Media Downloader

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Backup **Discord channel / thread history and attachments** with the official **Bot API** (Python + discord.py).

English UI by default · **Traditional Chinese (繁體中文)** available in the app language menu.

> **Bot tokens only.** Do not use user-account tokens (self-bots).

---

## Quick start (Windows)

1. **Code → Download ZIP** and extract the whole folder  
2. Install [Python 3.10+](https://www.python.org/downloads/) with **Add python.exe to PATH**  
3. Double-click **`run_gui.bat`** (first run installs dependencies)  
4. Paste **Bot Token** + **Channel ID(s)** → **Start backup**  

In-app **Tutorial** covers bot setup and intents.

### CLI

```bash
pip install -r requirements.txt
python backup.py --token YOUR_BOT_TOKEN --channel CHANNEL_ID
python backup.py --help
```

### macOS / Linux

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python gui.py
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

- Python **3.10+**
- Bot with **Message Content Intent**, **View Channel**, **Read Message History**

Saved bots / prefs (if any) live under `~/.discord_channel_backup/` — **not** in this repo.

Optional: `pack_release.bat` builds a clean ZIP without `.venv`.

---

## License

MIT — see [LICENSE](LICENSE). See also [SECURITY.md](SECURITY.md).
