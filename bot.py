import os
import instaloader
from telegram import Bot
from telegram.error import TelegramError
import shutil

# 🔐 Umgebungsvariablen laden
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TG_LOG_CHAT_ID = os.getenv('TELEGRAM_LOG_CHAT_ID')
TARGET = os.getenv('TARGET_USERNAME')

# 📲 Telegram-Bot initialisieren
bot = Bot(token=TG_TOKEN)

# ✅ Testnachricht nach Bot-Start
try:
    bot.send_message(chat_id=TG_LOG_CHAT_ID, text="✅ Bot wurde erfolgreich gestartet (Cookie-Login aktiv)")
except TelegramError as e:
    print(f"⚠️ Fehler beim Senden der Startnachricht: {e}")

# 📥 Bereits gesendete IDs aus Telegram-Log abrufen
def load_sent_ids():
    print("📥 Lade gesendete IDs aus Telegram-Log…")
    try:
        updates = bot.get_updates(limit=500)
        ids = {
            line.replace("ID:", "").strip()
            for update in updates
            if update.message and update.message.chat.id == int(TG_LOG_CHAT_ID)
            for line in update.message.text.strip().splitlines()
            if line.startswith("ID:")
        }
        print(f"✅ {len(ids)} gesendete IDs erkannt.")
        return ids
    except TelegramError as e:
        print(f"⚠️ Fehler beim Lesen der Log-IDs: {e}")
        return set()

# 📤 Neue ID in Telegram loggen
def log_sent_id(item_id):
    try:
        bot.send_message(chat_id=TG_LOG_CHAT_ID, text=f"ID: {item_id}")
    except TelegramError as e:
        print(f"⚠️ Fehler beim Loggen der ID: {e}")

# 🔧 Instaloader mit Cookie konfigurieren
loader = instaloader.Instaloader(
    download_videos=True,
    save_metadata=False,
    download_comments=False,
    post_metadata_txt_pattern="",
    dirname_pattern="downloads"
)

# 📎 Session-Datei laden (Cookie-Login)
try:
    loader.load_session_from_file('user25180_u')
    print("✅ Session-Cookie geladen und Login aktiv")
except Exception as e:
    print(f"❌ Fehler beim Laden der Session: {e}")
    exit(1)

# 🔎 Zielprofil laden
try:
    profile = instaloader.Profile.from_username(loader.context, TARGET)
    print(f"📡 Zielprofil geladen: {profile.username}")
except Exception as e:
    print(f"❌ Fehler beim Laden des Zielprofils: {e}")
    exit(1)

# 📑 Bereits gesendete Story-IDs laden
sent_items = load_sent_ids()
new_content_found = False

# 📥 Stories laden und filtern
for story in loader.get_stories(userids=[profile.userid]):
    for item in story.get_items():
        item_id = str(item.mediaid)
        if item_id in sent_items:
            print(f"⏭️ Bereits gesendet: {item_id}")
            continue

        print(f"📥 Lade neue Story-ID: {item_id}")
        try:
            path = loader.download_storyitem(item, TARGET)
        except Exception as e:
            print(f"⚠️ Fehler beim Herunterladen: {e}")
            continue

        if not os.path.exists(path):
            print("⚠️ Kein gültiger Pfad – übersprungen.")
            continue

        # 📤 Telegram-Versand
        sent = False
        for file in os.listdir(path):
            full_path = os.path.join(path, file)
            try:
                with open(full_path, "rb") as f:
                    if file.endswith(".mp4"):
                        print(f"📤 Sende Video: {file}")
                        bot.send_video(chat_id=TG_CHAT_ID, video=f)
                        sent = True
                    elif file.endswith(".jpg"):
                        print(f"📤 Sende Bild: {file}")
                        bot.send_photo(chat_id=TG_CHAT_ID, photo=f)
                        sent = True
                if sent:
                    log_sent_id(item_id)
                    new_content_found = True
                    break  # nur eine Datei pro Story senden
            except Exception as e:
                print(f"⚠️ Fehler beim Senden: {e}")

# 🧹 Downloads löschen
if os.path.exists("downloads"):
    shutil.rmtree("downloads")
    print("🧼 Downloads gelöscht")

# ℹ️ Statusmeldung
if not new_content_found:
    print("ℹ️ Keine neuen Storys gefunden.")
