import os
import shutil
import time
from telegram import Bot
from telegram.error import TelegramError
from playwright.sync_api import sync_playwright

# 📲 Telegram-Bot initialisieren
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TG_LOG_CHAT_ID = os.getenv('TELEGRAM_LOG_CHAT_ID')
TARGET = os.getenv('TARGET_USERNAME')

bot = Bot(token=TG_TOKEN)

def send_log(message):
    try:
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=message)
    except Exception as e:
        print(f"Fehler beim Senden der Lognachricht: {e}")

send_log("🚀 Bot gestartet (Fallback-Modus aktiv)")

# 📥 Fallback über instasupersave.com
def download_stories_via_fallback():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://instasupersave.com/de/instagram-stories/", timeout=60000)

            page.fill("input[name='url']", f"https://instagram.com/{TARGET}")
            page.click("button:has-text('Suchen')")
            page.wait_for_selector("div.story-list-item", timeout=20000)

            story_elements = page.query_selector_all("div.story-list-item")
            if not story_elements:
                send_log("ℹ️ Keine Storys gefunden (Fallback).")
                return

            os.makedirs("downloads", exist_ok=True)

            for i, el in enumerate(story_elements):
                link = el.query_selector("a").get_attribute("href")
                if not link:
                    continue
                page.goto(link)
                download_link = page.query_selector("a[href*='/download']")
                if download_link:
                    url = download_link.get_attribute("href")
                    file_ext = ".mp4" if ".mp4" in url else ".jpg"
                    filename = f"downloads/story_{i}{file_ext}"
                    page.goto(url)
                    with open(filename, "wb") as f:
                        f.write(page.content().encode())
                    with open(filename, "rb") as f:
                        if file_ext == ".mp4":
                            bot.send_video(chat_id=TG_CHAT_ID, video=f)
                        else:
                            bot.send_photo(chat_id=TG_CHAT_ID, photo=f)
                    time.sleep(3)
            send_log(f"✅ Fallback erfolgreich. {len(story_elements)} Storys gesendet.")
            browser.close()
        except Exception as e:
            send_log(f"❌ Fallback fehlgeschlagen: {e}")

# Starte Fallback-Download
download_stories_via_fallback()

# Downloads löschen
if os.path.exists("downloads"):
    shutil.rmtree("downloads")
