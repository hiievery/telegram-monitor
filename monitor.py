import os
import json
import requests
from bs4 import BeautifulSoup

STATE_FILE = "state.json"

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

CHANNELS = [
    x.strip().lstrip("@")
    for x in os.getenv("CHANNELS", "").split(",")
    if x.strip()
]

KEYWORDS = [
    x.strip()
    for x in os.getenv("KEYWORDS", "").split(",")
    if x.strip()
]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def read_channel(channel):
    url = f"https://t.me/s/{channel}"

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    messages = []

    for item in soup.select(".tgme_widget_message"):
        post = item.get("data-post", "")

        if "/" not in post:
            continue

        post_id = post.split("/")[-1]

        text_element = item.select_one(
            ".tgme_widget_message_text"
        )

        text = (
            text_element.get_text(" ", strip=True)
            if text_element else ""
        )

        messages.append({
            "id": int(post_id),
            "text": text,
            "link": f"https://t.me/{channel}/{post_id}"
        })

    return messages


def send_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError(
            "BOT_TOKEN dan CHAT_ID belum diatur"
        )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": True
        },
        timeout=20
    )

    response.raise_for_status()

    if not response.json().get("ok"):
        raise RuntimeError("Telegram gagal mengirim pesan")


def match_keywords(text):
    text = text.lower()

    return [
        keyword
        for keyword in KEYWORDS
        if keyword.lower() in text
    ]


def test_mode():
    send_message("✅ Tes berhasil! Bot terhubung.")
    print("Tes berhasil.")


def check_mode():
    for channel in CHANNELS:
        messages = read_channel(channel)

        matches = sum(
            bool(match_keywords(m["text"]))
            for m in messages
        )

        if messages:
            ids = [m["id"] for m in messages]

            print(
                f"[{channel}] {len(messages)} pesan terbaca "
                f"(ID {min(ids)}-{max(ids)}), "
                f"{matches} cocok keyword"
            )
        else:
            print(f"[{channel}] 0 pesan terbaca")


def demo_mode():
    channel = CHANNELS[0] if CHANNELS else "contoh"
    keyword = KEYWORDS[0] if KEYWORDS else "contoh"

    send_message(
        "🧪 CONTOH NOTIFIKASI\n\n"
        f"Channel: {channel}\n"
        f"Keyword: {keyword}\n"
        "Cuplikan: Ini adalah pesan contoh.\n"
        f"Link: https://t.me/{channel}/1"
    )

    print("Demo berhasil.")


def run_mode():
    state = load_state()
    changed = False

    for channel in CHANNELS:
        try:
            messages = read_channel(channel)

            if not messages:
                print(f"[{channel}] Tidak ada pesan.")
                continue

            messages.sort(key=lambda m: m["id"])
            latest_id = max(m["id"] for m in messages)

            if channel not in state:
                state[channel] = latest_id
                changed = True

                print(
                    f"[{channel}] pertama kali: "
                    f"titik awal ID {latest_id} "
                    "(tanpa notifikasi)"
                )

                continue

            last_id = int(state[channel])

            new_messages = [
                m for m in messages
                if m["id"] > last_id
            ]

            sent = 0

            for message in new_messages:
                matched = match_keywords(message["text"])

                if not matched:
                    continue

                notification = (
                    "🔔 KEYWORD DITEMUKAN\n\n"
                    f"Channel: {channel}\n"
                    f"Keyword: {', '.join(matched)}\n\n"
                    f"{message['text'][:1000]}\n\n"
                    f"Link: {message['link']}"
                )

                send_message(notification)
                sent += 1

            state[channel] = latest_id
            changed = True

            print(
                f"[{channel}] {len(new_messages)} pesan baru, "
                f"{sent} notifikasi terkirim"
            )

        except Exception as e:
            print(f"[{channel}] GAGAL: {e}")

    if changed:
        save_state(state)


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError(
            "BOT_TOKEN dan CHAT_ID belum diatur"
        )

    if not CHANNELS:
        raise RuntimeError("CHANNELS belum diatur")

    if not KEYWORDS:
        raise RuntimeError("KEYWORDS belum diatur")

    mode = os.getenv("MODE", "run").lower()

    if mode == "test":
        test_mode()

    elif mode == "check":
        check_mode()

    elif mode == "demo":
        demo_mode()

    elif mode == "run":
        run_mode()

    else:
        raise RuntimeError(f"Mode tidak dikenal: {mode}")


if __name__ == "__main__":
    main()
\
