import os
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from playwright.async_api import async_playwright

TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TG_LOG_CHAT_ID = os.getenv('TELEGRAM_LOG_CHAT_ID')
TARGET = os.getenv('TARGET_USERNAME')

bot = Bot(token=TG_TOKEN)

async def send_telegram_message(text):
    try:
        await bot.send_message(chat_id=TG_LOG_CHAT_ID, text=text)
    except TelegramError as e:
        print(f"Telegram Error: {e}")

async def download_from_instasupersave(username):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("https://instasupersave.com/de/instagram-stories/", timeout=60000)
            await page.fill("input[name='url']", f"https://www.instagram.com/{username}/")
            await page.click("button:has-text('Suchen')")

            await page.wait_for_selector(".content-box a", timeout=15000)

            story_links = await page.locator(".content-box a").element_handles()
            count = 0

            for link in story_links:
                url = await link.get_attribute("href")
                if url and ("story" in url or "stories" in url):
                    count += 1
                    await bot.send_message(chat_id=TG_CHAT_ID, text=f"📲 Story gefunden:\n{url}")
                    if count >= 3:
                        break

            if count == 0:
                await send_telegram_message("ℹ️ Keine Stories gefunden.")
            else:
                await send_telegram_message(f"✅ {count} Story-Link(s) gesendet.")

        except Exception as e:
            await send_telegram_message(f"❌ Fallback fehlgeschlagen: {e}")
        finally:
            await browser.close()

async def main():
    await send_telegram_message("✅ Fallback-Bot wurde gestartet")
    await download_from_instasupersave(TARGET)

if __name__ == "__main__":
    asyncio.run(main())
