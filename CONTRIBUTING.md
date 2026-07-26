# Contributing

## Development setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
python gui.py
# or
python backup.py --help
```

## Before opening a PR

- Do not commit tokens, backups, logs, or `.venv/`
- Keep changes focused; update `README.md` if behavior changes
- Prefer clear commit messages

## Code layout

| File | Role |
|------|------|
| `core.py` | Backup engine (history, downloads, naming, delays) |
| `gui.py` | CustomTkinter UI + tutorial |
| `backup.py` | CLI |
| `bot_store.py` | Encrypted saved-bot list (user home) |
| `settings_store.py` | Non-secret preferences (user home) |
| `i18n.py` | zh-TW / English strings |
