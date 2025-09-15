import os
import json
import openpyxl
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "tick_style": "✅",
            "last_summary": {"total_checked": 0, "registered_count": 0, "non_registered_count": 0},
            "non_registered_numbers": []
        }
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    summary = config['last_summary']
    tick = config['tick_style']

    message = (
        "🤖 Welcome to Number Checker Bot!\n\n"
        "📥 Send me an XLSX or TXT file (one phone number per row or separated by spaces).\n"
        "📄 Use /get_txt to get non-registered numbers\n"
        "⚙️ Use /toggle_style to switch ✅ / ✔️ style\n\n"
        f"✅ Last Check Summary:\n"
        f"{tick} {summary['total_checked']} numbers checked\n"
        f"{tick} {summary['registered_count']} registered | "
        f"{tick} {summary['non_registered_count']} non-registered"
    )
    await update.message.reply_text(message)


async def toggle_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    config['tick_style'] = '✔️' if config['tick_style'] == '✅' else '✅'
    save_config(config)
    await update.message.reply_text(f"✅ Tick style toggled to: {config['tick_style']}")


async def get_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    txt_path = 'non_registered_numbers.txt'
    with open(txt_path, 'w') as f:
        for num in config['non_registered_numbers']:
            f.write(f"{num}\n")
    await update.message.reply_document(document=InputFile(txt_path), caption="📄 Non-Registered Numbers")
    os.remove(txt_path)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    file_path = update.message.document.file_name

    await file.download_to_drive(file_path)
    await update.message.reply_text('⏳ Processing numbers, please wait...')

    config = load_config()
    tick = config['tick_style']
    non_registered_numbers = []
    total_checked = 0
    registered_count = 0
    message_lines = []
    numbers = []

    # Read numbers from file
    if file_path.endswith('.xlsx'):
        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=1, values_only=True):
            number = row[0]
            if number:
                numbers.append(str(number).strip())
        wb.close()
    elif file_path.endswith('.txt'):
        with open(file_path, 'r') as f:
            content = f.read()
            for part in content.split():
                if part.strip():
                    numbers.append(part.strip())

    for number in numbers:
        if not number.startswith('+'):
            number = '+' + number

        # Dummy check logic (replace with real check)
        if len(number) >= 10:
            registered_count += 1
            status = f"{tick} Registered"
        else:
            non_registered_numbers.append(number)
            status = "❌ Not Registered"

        message_lines.append(f"`{number}` - {status}")
        total_checked += 1

    os.remove(file_path)

    config['last_summary'] = {
        'total_checked': total_checked,
        'registered_count': registered_count,
        'non_registered_count': len(non_registered_numbers)
    }
    config['non_registered_numbers'] = non_registered_numbers
    save_config(config)

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
    await update.message.reply_document(document=InputFile(result_xlsx), caption="📊 Result XLSX file.")
    os.remove(result_xlsx)


if __name__ == '__main__':
    BOT_TOKEN = os.environ.get('BOT_TOKEN')

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('toggle_style', toggle_style))
    app.add_handler(CommandHandler('get_txt', get_txt))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("✅ Bot is running in polling mode...")

    app.run_polling()
