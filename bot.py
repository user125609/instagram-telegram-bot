import os
import instaloader
import shutil
from telegram import Bot
from telegram.error import TelegramError
from playwright.sync_api import sync_playwright

TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TG_LOG_CHAT_ID = os.getenv('TELEGRAM_LOG_CHAT_ID')
TARGET = os.getenv('TARGET_USERNAME')
SESSION_USER = "user25180_u"

bot = Bot(token=TG_TOKEN)
bot.send_message(chat_id=TG_LOG_CHAT_ID, text="✅ Bot gestartet (mit Cookie & Fallback aktiviert)")

def send_fallback_message(reason):
    bot.send_message(chat_id=TG_LOG_CHAT_ID, text=f"⚠️ Instaloader-Fehler: {reason}\n⏬ Wechsle zu instasupersave.com…")

def send_instasupersave_story(username):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://instasupersave.com/de/instagram-stories/")
            page.fill("input[name='url']", username)
            page.click("button[type='submit']")
            page.wait_for_timeout(8000)
            stories = page.query_selector_all(".download-button")
            if not stories:
                bot.send_message(chat_id=TG_LOG_CHAT_ID, text="ℹ️ Kein Story-Content über instasupersave gefunden.")
            else:
                for s in stories:
                    href = s.get_attribute("href")
                    if href.endswith(".mp4"):
                        bot.send_video(chat_id=TG_CHAT_ID, video=href)
                    else:
                        bot.send_photo(chat_id=TG_CHAT_ID, photo=href)
            browser.close()
    except Exception as e:
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=f"❌ Fallback fehlgeschlagen: {e}")

loader = instaloader.Instaloader(dirname_pattern="downloads", download_comments=False,
                                  save_metadata=False, download_videos=True, post_metadata_txt_pattern="")

try:
    loader.load_session_from_file(SESSION_USER)
    print("✅ Session-Cookie geladen")
except Exception as e:
    send_fallback_message(f"Cookie konnte nicht geladen werden: {e}")
    send_instasupersave_story(TARGET)
    exit()

try:
    profile = instaloader.Profile.from_username(loader.context, TARGET)
except Exception as e:
    send_fallback_message(f"Profilfehler: {e}")
    send_instasupersave_story(TARGET)
    exit()

new_content_found = False
for story in loader.get_stories(userids=[profile.userid]):
    for item in story.get_items():
        item_id = str(item.mediaid)
        try:
            path = loader.download_storyitem(item, TARGET)
        except Exception as e:
            send_fallback_message(f"Story konnte nicht geladen werden: {e}")
            send_instasupersave_story(TARGET)
            continue

        if not os.path.exists(path):
            continue

        for file in os.listdir(path):
            full_path = os.path.join(path, file)
            with open(full_path, "rb") as f:
                try:
                    if file.endswith(".mp4"):
                        bot.send_video(chat_id=TG_CHAT_ID, video=f)
                    elif file.endswith(".jpg"):
                        bot.send_photo(chat_id=TG_CHAT_ID, photo=f)
                    new_content_found = True
                except Exception as e:
                    print(f"❌ Senden fehlgeschlagen: {e}")

if os.path.exists("downloads"):
    shutil.rmtree("downloads")

if not new_content_found:
    bot.send_message(chat_id=TG_LOG_CHAT_ID, text="ℹ️ Keine neuen Storys mit Instaloader gefunden.")
