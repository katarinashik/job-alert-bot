"""
Handles /pause, /resume, /status commands sent to the bot.
State is persisted in bot_state.json (cached by GitHub Actions between runs).
The bot checks for new commands at the START of each run.
"""
import json
import os
import requests

STATE_FILE = os.environ.get("STATE_FILE", "bot_state.json")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"paused": False, "offset": 0}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def process_commands(token: str, chat_id: str) -> bool:
    """
    Fetches new Telegram messages, processes commands.
    Returns True if the bot should run, False if paused.
    """
    state = load_state()

    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": state.get("offset", 0), "timeout": 0},
            timeout=10,
        )
        r.raise_for_status()
        updates = r.json().get("result", [])
    except Exception as e:
        print(f"[commands] failed to fetch updates: {e}")
        return not state.get("paused", False)

    for update in updates:
        state["offset"] = update["update_id"] + 1
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        from_id = str(msg.get("chat", {}).get("id", ""))

        if from_id != str(chat_id):
            continue

        cmd = text.lower()
        if cmd == "/pause":
            state["paused"] = True
            _reply(token, chat_id, "⏸ Bot paused. Send /resume to restart alerts.")
        elif cmd == "/resume":
            state["paused"] = False
            _reply(token, chat_id, "▶️ Bot resumed. Checking for new jobs every 2 hours.")
        elif cmd == "/status":
            status = "⏸ Paused" if state["paused"] else "▶️ Running (every 2 hours)"
            _reply(token, chat_id, f"Status: {status}")

    save_state(state)
    return not state.get("paused", False)


def _reply(token: str, chat_id: str, text: str) -> None:
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception as e:
        print(f"[commands] reply failed: {e}")
