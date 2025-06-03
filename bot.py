import os
import instaloader
from telegram import Bot
from telegram.error import TelegramError
import shutil
import asyncio
from playwright.async_api import async_playwright

# 🔐 Umgebungsvariablen
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TG_LOG_CHAT_ID = os.getenv('TELEGRAM_LOG_CHAT_ID')
TARGET = os.getenv('TARGET_USERNAME')
COOKIE_USER = 'user25180_u'

# 📲 Telegram-Bot initialisieren
bot = Bot(token=TG_TOKEN)
bot.send_message(chat_id=TG_LOG_CHAT_ID, text="✅ Bot wurde erfolgreich gestartet (Cookie-Login aktiv)")

# 📥 Bereits gesendete IDs aus Telegram laden
def load_sent_ids():
    try:
        updates = bot.get_updates(limit=500)
        ids = set()
        for update in updates:
            if update.message and update.message.chat.id == int(TG_LOG_CHAT_ID):
                for line in update.message.text.strip().splitlines():
                    if line.startswith("ID:"):
                        ids.add(line.replace("ID:", "").strip())
        return ids
    except TelegramError as e:
        print(f"⚠️ Fehler beim Lesen der Log-IDs: {e}")
        return set()

def log_sent_id(item_id):
    try:
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=f"ID: {item_id}")
    except TelegramError as e:
        print(f"⚠️ Fehler beim Loggen in Telegram: {e}")

# 📦 Instaloader Setup
loader = instaloader.Instaloader(
    download_videos=True,
    save_metadata=False,
    download_comments=False,
    post_metadata_txt_pattern="",
    dirname_pattern="downloads"
)

# 🧩 Cookie laden
try:
    loader.load_session_from_file(COOKIE_USER)
    print("✅ Session-Cookie geladen und Login aktiv")
except Exception as e:
    print(f"❌ Fehler beim Laden der Session: {e}")
    exit(1)

# 🕵️‍♂️ Profil laden mit Error-Handling
try:
    print("⏳ Warte 10 Sekunden vor dem Laden des Profils…")
    import time; time.sleep(10)
    profile = instaloader.Profile.from_username(loader.context, TARGET)
    print(f"📡 Zielprofil geladen: {profile.username}")
except Exception as e:
    print(f"⚠️ Instaloader-Fehler: {e}")
    print("⏬ Wechsle zu instasupersave.com…")
    asyncio.run(async_fallback_instasupersave(TARGET))
    exit(1)

# 📑 Gesendete Stories erkennen
sent_items = load_sent_ids()
new_content_found = False

for story in loader.get_stories(userids=[profile.userid]):
    for item in story.get_items():
        item_id = str(item.mediaid)
        if item_id in sent_items:
            continue

        try:
            path = loader.download_storyitem(item, TARGET)
        except Exception as e:
            print(f"⚠️ Fehler beim Herunterladen von Story {item_id}: {e}")
            continue

        if not os.path.exists(path):
            continue

        sent = False
        for file in os.listdir(path):
            full_path = os.path.join(path, file)
            try:
                with open(full_path, "rb") as f:
                    if file.endswith(".mp4"):
                        bot.send_video(chat_id=TG_CHAT_ID, video=f)
                        sent = True
                    elif file.endswith(".jpg"):
                        bot.send_photo(chat_id=TG_CHAT_ID, photo=f)
                        sent = True
                if sent:
                    log_sent_id(item_id)
                    new_content_found = True
                    break
            except Exception as e:
                print(f"⚠️ Fehler beim Senden: {e}")

# 🧹 Aufräumen
if os.path.exists("downloads"):
    shutil.rmtree("downloads")

if not new_content_found:
    print("ℹ️ Keine neuen Storys gefunden.")

# 🪂 Fallback-Funktion via Playwright
async def async_fallback_instasupersave(target_username):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("https://instasupersave.com/de/instagram-stories/", timeout=60000)
            await page.wait_for_selector("input[name='url']", timeout=20000)
            await page.fill("input[name='url']", f"https://www.instagram.com/{target_username}/")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(8000)

            # Hier kann optional ein Screenshot gemacht werden oder Log-Nachricht
            await page.screenshot(path="fallback_result.png")

            await browser.close()
            bot.send_message(chat_id=TG_LOG_CHAT_ID, text="✅ Fallback (instasupersave) wurde gestartet. Screenshot gespeichert.")
    except Exception as e:
        print(f"❌ Fallback fehlgeschlagen: {e}")
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=f"❌ Fallback fehlgeschlagen: {e}")
