# Security

## Secrets

- **Never commit** Discord Bot Tokens, Client Secrets, or personal Channel IDs.
- Tokens belong only on your machine. This app may store encrypted tokens under:

  - Windows: `%USERPROFILE%\.discord_channel_backup\`

  That directory is **outside** this repository and must not be copied into a public repo.

- Prefer **Reset Token** in the Discord Developer Portal if a token may have leaked.

## Platform

Designed for **Windows**. Local data path examples below assume Windows.

## What this tool does

Uses the official Discord **Bot API** only. Do not use user-account tokens (self-bots); that violates Discord’s Terms of Service and risks account termination.

## Reporting issues

If you find a security issue in this project, open a private report or an issue without pasting secrets.
