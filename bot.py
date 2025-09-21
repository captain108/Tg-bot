# bot.py

# --- Patch for Python 3.13+ (imghdr removed) ---
try:
    import imghdr
except ModuleNotFoundError:
    import mimetypes
    class _FakeImgHdr:
        @staticmethod
        def what(file, h=None):
            type_, _ = mimetypes.guess_type(file)
            if type_ and type_.startswith("image/"):
                return type_.split("/")[-1]
            return None
    imghdr = _FakeImgHdr()

import os
import pandas as pd
from telethon import TelegramClient, events, Button

# --- Environment Variables (Render) ---
API_ID = int(os.getenv("API_ID", "123456"))   # set in Render dashboard
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# --- Telethon Bot Client ---
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- Store data per user ---
user_data = {}

# --- Start Command ---
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    buttons = [
        [Button.inline("📄 Convert XLSX → TXT", data="convert")],
        [Button.inline("📊 Only Numbers", data="numbers")],
        [Button.inline("✅ Registered", data="registered"),
         Button.inline("❌ Non-Registered", data="nonregistered")],
        [Button.inline("📌 Merge List", data="merge")]
    ]
    await event.respond(
        "🤖 Welcome to **Telegram Number Checker Bot**!\n\n"
        "Please upload an `.xlsx` file with numbers, then choose an option:",
        buttons=buttons
    )

# --- Handle XLSX Upload ---
@bot.on(events.NewMessage(func=lambda e: e.file and e.file.name.endswith(('.xlsx', '.xls'))))
async def handle_xlsx(event):
    user_id = event.sender_id
    path = await event.download_media()
    df = pd.read_excel(path)

    # Expect numbers in first column
    numbers = df.iloc[:, 0].astype(str).tolist()
    user_data[user_id] = {"numbers": numbers}

    await event.respond(f"✅ File received with **{len(numbers)} numbers**.\nNow use the buttons to process them.")

# --- Button Handler ---
@bot.on(events.CallbackQuery)
async def button_handler(event):
    user_id = event.sender_id
    if user_id not in user_data:
        await event.answer("⚠️ Please upload an XLSX file first.", alert=True)
        return

    numbers = user_data[user_id]["numbers"]
    choice = event.data.decode("utf-8")

    if choice == "convert":
        txt = "\n".join(numbers)
        with open("numbers.txt", "w") as f:
            f.write(txt)
        await bot.send_file(user_id, "numbers.txt", caption="📄 Converted TXT file")
        os.remove("numbers.txt")

    elif choice == "numbers":
        preview = "\n".join(numbers[:50]) + ("\n..." if len(numbers) > 50 else "")
        await event.respond("📊 Numbers:\n" + preview)

    elif choice == "registered":
        # Dummy check: even index = registered
        registered = [n for i, n in enumerate(numbers) if i % 2 == 0]
        preview = "\n".join(registered[:50]) + ("\n..." if len(registered) > 50 else "")
        await event.respond("✅ Registered:\n" + preview)

    elif choice == "nonregistered":
        # Dummy check: odd index = non-registered
        nonreg = [n for i, n in enumerate(numbers) if i % 2 != 0]
        preview = "\n".join(nonreg[:50]) + ("\n..." if len(nonreg) > 50 else "")
        await event.respond("❌ Non-Registered:\n" + preview)

    elif choice == "merge":
        merged = []
        for i, n in enumerate(numbers):
            if i % 2 == 0:
                merged.append(f"✅ {n}")
            else:
                merged.append(f"❌ {n}")
        preview = "\n".join(merged[:50]) + ("\n..." if len(merged) > 50 else "")
        await event.respond("📌 Merged List:\n" + preview)

# --- Run Bot ---
print("🚀 Bot is running...")
bot.run_until_disconnected()
