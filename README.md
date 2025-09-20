# Telegram XLSX Number Checker Bot 🤖

A Telegram bot that:
- Accepts `.xlsx` files with phone numbers (and optional messages).
- Exports to `.txt`.
- Extracts only numbers or only messages.
- Checks which numbers are registered on Telegram ✅ or not ❌.
- Shows results in chat (preview) and also provides downloadable `.txt`.

## 🚀 Features
- 📄 Convert XLSX → TXT
- 🔢 Extract only numbers / messages
- ✅ Registered-only list
- ❌ Non-registered-only list
- 📊 Combined results with stats
- Render-ready deployment with webhook mode

## ⚙️ Setup

### 1. Get Telegram API Keys
- [my.telegram.org](https://my.telegram.org) → API Development → Get `API_ID` and `API_HASH`.
- Create a bot via [@BotFather](https://t.me/BotFather) → get `BOT_TOKEN`.

### 2. Deploy on Render
- Create a new **Web Service**.
- Connect your GitHub repo.
- Add **Environment Variables**:
