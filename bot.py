import os
from telegram import Bot
from telegram.error import TelegramError
from playwright.sync_api import sync_playwright

TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TG_LOG_CHAT_ID = os.getenv('TELEGRAM_LOG_CHAT_ID')
TARGET = os.getenv('TARGET_USERNAME')

bot = Bot(token=TG_TOKEN)

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=text)
    except TelegramError as e:
        print(f"Telegram Error: {e}")

def download_from_instasupersave(username):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto("https://instasupersave.com/de/instagram-stories/", timeout=60000)
            page.fill("input[name='url']", f"https://www.instagram.com/{username}/")
            page.click("button:has-text('Suchen')")

            page.wait_for_selector(".content-box a", timeout=15000)

            story_links = page.locator(".content-box a").element_handles()
            count = 0

            for link in story_links:
                url = link.get_attribute("href")
                if url and ("story" in url or "stories" in url):
                    count += 1
                    bot.send_message(chat_id=TG_CHAT_ID, text=f"📲 Story gefunden:\n{url}")
                    if count >= 3:
                        break

            if count == 0:
                send_telegram_message("ℹ️ Keine Stories gefunden.")
            else:
                send_telegram_message(f"✅ {count} Story-Link(s) gesendet.")

        except Exception as e:
            send_telegram_message(f"❌ Fallback fehlgeschlagen: {e}")
        finally:
            browser.close()

def main():
    send_telegram_message("✅ Fallback-Bot wurde gestartet")
    download_from_instasupersave(TARGET)

if __name__ == "__main__":
    main()
