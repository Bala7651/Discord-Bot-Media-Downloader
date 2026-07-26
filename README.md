# Discord Bot Media Downloader

So me myself when I search for any online discord downloader I dont see any which is 2026 made. So I just asked my almost expired Grok to build one simple one so I can download lots of my archives incase.
anything below is made by AI so if there is any mistake Im sorry.if there is any feature or any changes in the future you can ask me too, but my subscription is going out soon so...
---------------------------------------------------------------------------------------------------------------------------
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-blue.svg)](#quick-start)

Backup **Discord channel / thread history and attachments** using the official **Bot API** (Python + discord.py).

English UI by default · **Traditional Chinese (繁體中文)** available in the app language menu.

> **Bot tokens only.** Do not use user-account tokens (self-bots).

Built and tested on **Windows 10 / 11**. Launch with `run_gui.bat`.

---

## Quick start

1. **Code → Download ZIP** and extract the whole folder  
2. Install [Python 3.10+](https://www.python.org/downloads/) and enable **Add python.exe to PATH**  
3. Double-click **`run_gui.bat`** (first run installs dependencies)  
4. Paste **Bot Token** + **Channel ID(s)** → **Start backup**  

The in-app **Tutorial** covers bot setup and intents.

### CLI

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

- Windows 10 or 11  
- Python **3.10+**  
- A Discord bot with **Message Content Intent**, **View Channel**, and **Read Message History**

Local prefs / optional saved bots are stored under  
`%USERPROFILE%\.discord_channel_backup\` (not in this repository).

Optional: run `pack_release.bat` to build a clean ZIP without `.venv`.

---

## License

MIT — see [LICENSE](LICENSE). See also [SECURITY.md](SECURITY.md).
