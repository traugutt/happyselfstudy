import os
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pymongo import ReturnDocument

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# 🔒 Replace with your Telegram user ID
TEACHER_ID = "traugutt"  

mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.telegram_vocab_bot
cards = db.cards
users = db.users


# -------------------- START --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await users.update_one(
        {"user_id": user.id},
        {
            "$set": {
                "username": user.username or ""
            }
        },
        upsert=True
    )

    await update.message.reply_text(
        "📚 Welcome!\n\n"
        "Use:\n"
        "/add word = translation\n"
        "/study\n"
        "/run\n"
        "/delete\n"
    )


# -------------------- ADD CARD --------------------

async def add_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/add", "").strip()

    # Teacher adding for student
    if text.startswith("@"):
        if update.effective_user.id != TEACHER_ID:
            await update.message.reply_text(
                "❌ Only teacher can add cards for others."
            )
            return

        parts = text.split(" ", 1)
        target_username = parts[0].replace("@", "")
        text = parts[1] if len(parts) > 1 else ""

        target_user = await users.find_one({"username": target_username})

        if not target_user:
            await update.message.reply_text("❌ User not found.")
            return

        user_id = target_user["user_id"]
    else:
        user_id = update.effective_user.id

    if "=" not in text:
        await update.message.reply_text(
            "❌ Format:\n/add word = translation\nor\n/add @username word = translation"
        )
        return

    word, translation = map(str.strip, text.split("=", 1))

    await cards.insert_one({
        "user_id": user_id,
        "word": word,
        "translation": translation,
        "correct_count": 0
    })

    await update.message.reply_text(
        f"✅ Added:\n{word} → {translation}"
    )
