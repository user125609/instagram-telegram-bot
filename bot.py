import os
import instaloader
import shutil
import time
from telegram import Bot
from telegram.error import TelegramError
from playwright.sync_api import sync_playwright

# 🔐 Umgebungsvariablen
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TG_LOG_CHAT_ID = os.getenv('TELEGRAM_LOG_CHAT_ID')
TARGET = os.getenv('TARGET_USERNAME')
FALLBACK_ENABLED = os.getenv('IG_FALLBACK_ENABLED') == "true"

# 📲 Telegram-Bot initialisieren
bot = Bot(token=TG_TOKEN)

def send_log(msg):
    try:
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=msg)
    except:
        pass

send_log("✅ Bot wurde gestartet (Cookie-Login aktiv)")

# 📤 Gesendete ID loggen
def log_sent_id(item_id):
    try:
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=f"ID: {item_id}")
    except:
        pass

# 🔧 Instaloader mit Cookie vorbereiten
loader = instaloader.Instaloader(
    download_videos=True,
    save_metadata=False,
    download_comments=False,
    post_metadata_txt_pattern="",
    dirname_pattern="downloads"
)

try:
    loader.load_session_from_file('user25180_u')
    send_log("✅ Session-Cookie geladen")
except Exception as e:
    send_log(f"❌ Fehler beim Laden der Session: {e}")
    exit(1)

time.sleep(10)

# 🔎 Profil laden
try:
    profile = instaloader.Profile.from_username(loader.context, TARGET)
    print(f"📡 Zielprofil geladen: {profile.username}")
except Exception as e:
    send_log(f"⚠️ Instaloader-Fehler: {e}")
    if FALLBACK_ENABLED:
        send_log("⏬ Wechsle zu instasupersave.com…")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://instasupersave.com/de/instagram-stories/")
                page.fill("input[name='url']", f"https://instagram.com/{TARGET}")
                page.click("button[type='submit']")
                page.wait_for_timeout(5000)
                page.screenshot(path="fallback.png")
                with open("fallback.png", "rb") as img:
                    bot.send_photo(chat_id=TG_CHAT_ID, photo=img, caption="📸 Fallback: Story-Vorschau")
                browser.close()
        except Exception as e:
            send_log(f"❌ Fallback fehlgeschlagen: {e}")
    exit(1)

# 📥 Storys holen
new_content = False
for story in loader.get_stories(userids=[profile.userid]):
    for item in story.get_items():
        item_id = str(item.mediaid)
        try:
            path = loader.download_storyitem(item, TARGET)
            for file in os.listdir(path):
                full_path = os.path.join(path, file)
                with open(full_path, "rb") as f:
                    if file.endswith(".mp4"):
                        bot.send_video(chat_id=TG_CHAT_ID, video=f)
                    elif file.endswith(".jpg"):
                        bot.send_photo(chat_id=TG_CHAT_ID, photo=f)
                    log_sent_id(item_id)
                    new_content = True
                    break
        except Exception as e:
            send_log(f"⚠️ Fehler beim Download oder Senden: {e}")

# 🧹 Downloads löschen
if os.path.exists("downloads"):
    shutil.rmtree("downloads")

if not new_content:
    send_log("ℹ️ Keine neuen Inhalte gefunden.")
