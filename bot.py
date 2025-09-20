import os
import pandas as pd
from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import PhoneNumberInvalidError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = "checker_session"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-app.onrender.com

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to **Telegram XLSX Number Checker!**\n\n"
        "📥 Send me an `.xlsx` file with numbers (and messages if any).\n\n"
        "I can:\n"
        "📄 Export TXT\n"
        "🔢 Extract numbers/messages\n"
        "✅ Show registered / ❌ non-registered\n"
        "📊 Show merged results ✅❌",
        parse_mode="Markdown"
    )

# === FILE HANDLER ===
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    filepath = f"downloads/{update.message.document.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await file.download_to_drive(filepath)

    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading file: {e}")
        return

    has_message = any("message" in c.lower() for c in df.columns)

    buttons = [
        [InlineKeyboardButton("📄 Export TXT", callback_data=f"txt|{filepath}")],
        [InlineKeyboardButton("💬 Show Numbers in Chat", callback_data=f"chat|{filepath}")],
        [InlineKeyboardButton("🔢 Extract Only Numbers", callback_data=f"onlynum|{filepath}")],
        [InlineKeyboardButton("✅ Registered Only", callback_data=f"reg|{filepath}")],
        [InlineKeyboardButton("❌ Non-Registered Only", callback_data=f"nreg|{filepath}")],
        [InlineKeyboardButton("📊 All Results (✅/❌)", callback_data=f"all|{filepath}")]
    ]
    if has_message:
        buttons.insert(2, [InlineKeyboardButton("💬 Extract Only Messages", callback_data=f"onlymsg|{filepath}")])

    await update.message.reply_text("✨ File received! Choose an option:", 
                                    reply_markup=InlineKeyboardMarkup(buttons))

# === BUTTON HANDLER ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, filepath = query.data.split("|", 1)

    df = pd.read_excel(filepath)
    numbers = df.iloc[:, 0].astype(str).tolist()
    results = []

    if action == "txt":
        outpath = filepath.replace(".xlsx", ".txt")
        df.to_csv(outpath, index=False, header=False, sep="\t")
        await query.message.reply_document(open(outpath, "rb"))

    elif action == "chat":
        preview = "\n".join(numbers[:50])
        await query.message.reply_text(f"📄 First numbers:\n\n{preview}")

    elif action == "onlynum":
        outpath = filepath.replace(".xlsx", "_numbers.txt")
        with open(outpath, "w") as f:
            f.write("\n".join(numbers))
        await query.message.reply_document(open(outpath, "rb"))

    elif action == "onlymsg":
        messages = df.iloc[:, 1].astype(str).tolist()
        outpath = filepath.replace(".xlsx", "_messages.txt")
        with open(outpath, "w") as f:
            f.write("\n".join(messages))
        await query.message.reply_document(open(outpath, "rb"))

    elif action in ["reg", "nreg", "all"]:
        await query.message.reply_text("⏳ Checking Telegram registration...")

        await client.start()
        registered, non_registered = [], []
        try:
            for num in numbers:
                contact = InputPhoneContact(client_id=0, phone=num, first_name="Check", last_name="")
                imported, = await client(ImportContactsRequest([contact]))
                user = imported.users[0] if imported.users else None
                if user:
                    registered.append(f"✅ {num}")
                    await client(DeleteContactsRequest([user.id]))
                else:
                    non_registered.append(f"❌ {num}")
        except PhoneNumberInvalidError:
            non_registered.append("⚠️ Invalid format number")
        finally:
            await client.disconnect()

        if action == "reg":
            msg = "\n".join(registered[:50]) or "⚠️ No registered numbers."
            await query.message.reply_text(f"✅ Registered:\n\n{msg}")
            with open(filepath.replace(".xlsx", "_registered.txt"), "w") as f:
                f.write("\n".join(registered))
            await query.message.reply_document(open(filepath.replace(".xlsx", "_registered.txt"), "rb"))

        elif action == "nreg":
            msg = "\n".join(non_registered[:50]) or "⚠️ No non-registered numbers."
            await query.message.reply_text(f"❌ Non-Registered:\n\n{msg}")
            with open(filepath.replace(".xlsx", "_nonregistered.txt"), "w") as f:
                f.write("\n".join(non_registered))
            await query.message.reply_document(open(filepath.replace(".xlsx", "_nonregistered.txt"), "rb"))

        elif action == "all":
            merged = registered + non_registered
            msg = "\n".join(merged[:50]) or "⚠️ No numbers found."
            await query.message.reply_text(f"📊 All Results:\n\n{msg}")
            with open(filepath.replace(".xlsx", "_checked.txt"), "w") as f:
                f.write("\n".join(merged))
            await query.message.reply_document(open(filepath.replace(".xlsx", "_checked.txt"), "rb"))

# === MAIN ===
def main():
    port = int(os.getenv("PORT", 8080))
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button))

    # Use webhook mode for Render
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
