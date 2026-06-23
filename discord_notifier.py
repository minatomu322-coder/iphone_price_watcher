from __future__ import annotations

import os

import requests


DISCORD_LIMIT = 1900


def send_discord_notification(webhook_url: str | None, username: str, content: str) -> None:
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL is not set. Skipping Discord notification.")
        print(content)
        return

    for chunk in split_message(content):
        payload = {
            "username": username,
            "content": chunk,
        }
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()


def split_message(content: str) -> list[str]:
    if len(content) <= DISCORD_LIMIT:
        return [content]

    chunks: list[str] = []
    current = ""
    for line in content.splitlines():
        if len(current) + len(line) + 1 > DISCORD_LIMIT:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


def get_webhook_url() -> str | None:
    return os.environ.get("DISCORD_WEBHOOK_URL")
