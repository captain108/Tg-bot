import json
import os
import asyncio
import openpyxl
from datetime import datetime, timedelta
from telethon import TelegramClient, functions, types
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ====== CONFIGURATION =======
API_ID = 'YOUR_TELEGRAM_API_ID'
API_HASH = 'YOUR_TELEGRAM_API_HASH'
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
PHONE_NUMBER = 'YOUR_PHONE_NUMBER'

client = TelegramClient('session_name', API_ID, API_HASH)

CONFIG_FILE = 'config.json'

# Helper to load config
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"tick_style": "✅", "last_summary": {"total_checked":0, "registered_count":0, "non_registered_count":0}, "non_registered_numbers":[]}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# Helper to save config
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    summary = config['last_summary']
    tick = config['tick_style']

    keyboard = [
        [InlineKeyboardButton("📥 Upload Number List", callback_data='upload')],
        [InlineKeyboardButton("📄 Get Non-Registered TXT", callback_data='get_txt')],
        [InlineKeyboardButton(f"⚙️ Toggle {tick} / ✔️ Style", callback_data='toggle_style')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "🤖 Welcome to Telegram Number Checker Bot!\n\n"
        "Choose an option:\n\n"
        "[📥 Upload Number List]\n"
        "[📄 Get Non-Registered TXT]\n"
        "[⚙️ Toggle ✅ / ✔️ Style]\n"
        "[ℹ️ Help]\n\n"
        f"✅ Last Check Summary:\n"
        f"{tick} {summary['total_checked']} numbers checked\n"
        f"{tick} {summary['registered_count']} registered | "
        f"{tick} {summary['non_registered_count']} non-registered"
    )
    await update.message.reply_text(message, reply_markup=reply_markup)

# Callback Query Handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    config = load_config()

    if query.data == 'upload':
        await query.message.reply_text("📁 Please send the XLSX file containing phone numbers (one per row).")
    elif query.data == 'get_txt':
        txt_path = 'non_registered_numbers.txt'
        with open(txt_path, 'w') as f:
            for num in config['non_registered_numbers']:
                f.write(f"{num}\n")
        await query.message.reply_document(document=InputFile(txt_path),
                                           caption="📄 Here is the Non-Registered Numbers TXT file.")
        os.remove(txt_path)
    elif query.data == 'toggle_style':
        new_tick = '✔️' if config['tick_style'] == '✅' else '✅'
        config['tick_style'] = new_tick
        save_config(config)
        await query.message.reply_text(f"✅ Style toggled to: {new_tick}")
    elif query.data == 'help':
        await query.message.reply_text(
            "Usage Guide:\n"
            "📥 Upload a XLSX file (first column: numbers)\n"
            "📄 Download a TXT of non-registered numbers\n"
            "⚙️ Toggle between ✅ and ✔️ styles"
        )

# Handle XLSX file
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = 'numbers.xlsx'
    await file.download_to_drive(file_path)

    await update.message.reply_text('⏳ Processing the number list, please wait...')

    config = load_config()
    tick = config['tick_style']
    non_registered_numbers = []
    total_checked = 0
    registered_count = 0

    await client.start(PHONE_NUMBER)
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    message_lines = []

    for row in sheet.iter_rows(min_row=2, values_only=True):
        number = str(row[0])
        if not number.startswith('+'):
            number = '+' + number

        try:
            result = await client(functions.contacts.ImportContactsRequest(
                contacts=[types.InputPhoneContact(client_id=0, phone=number, first_name='Test', last_name='User')]
            ))

            if result.users:
                registered_count += 1
                status = f"{tick} Registered"
                await client(functions.contacts.DeleteContactsRequest(id=[result.users[0]]))
            else:
                non_registered_numbers.append(number)
                status = "❌ Not Registered"

            message_lines.append(f"`{number}` - {status}")
            total_checked += 1
            await asyncio.sleep(1)  # Delay for safety

        except Exception as e:
            message_lines.append(f"`{number}` - ❌ Error")

    await client.disconnect()
    os.remove(file_path)

    # Update config
    config['last_summary'] = {
        'total_checked': total_checked,
        'registered_count': registered_count,
        'non_registered_count': len(non_registered_numbers)
    }
    config['non_registered_numbers'] = non_registered_numbers
    save_config(config)

    # Send result summary + file
    result_text = "\n".join(message_lines)
    await update.message.reply_markdown(f"✅ Check complete! Results:\n\n{result_text}")

    result_xlsx = 'checked_numbers.xlsx'
    output_wb = openpyxl.Workbook()
    output_sheet = output_wb.active
    output_sheet.append(['Phone Number', 'Status'])

    for line in message_lines:
        parts = line.split(' - ')
        output_sheet.append([parts[0].strip('`'), parts[1]])

    output_wb.save(result_xlsx)
    await update.message.reply_document(document=InputFile(result_xlsx),
                                        caption="📊 Complete result XLSX file.")
    os.remove(result_xlsx)

# Main Entry
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print('Bot is running...')
    app.run_polling()
