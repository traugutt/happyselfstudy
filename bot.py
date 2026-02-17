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
TEACHER_ID = 1140145697

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
        "/add word = translation (add your own items)\n"
        "/study (here you need to write answer, press again to proceed to next item)\n"
        "/run (this one is just to go over items, press to proceed to next item)\n"
        "/delete (delete items added by you, use carefully)\n"
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
            # Create placeholder user
            result = await users.insert_one({
                "username": target_username,
                "user_id": None,  # unknown until they start
                "created_by_teacher": True
            })
            user_id = None
        else:
            user_id = target_user["user_id"]

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


# -------------------- STUDY --------------------

async def study(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    count = await cards.count_documents({"user_id": user_id})

    if count == 0:
        await update.message.reply_text("📭 No words yet.")
        return

    random_index = random.randint(0, count - 1)

    cursor = cards.find({"user_id": user_id}).skip(random_index).limit(1)
    card = await cursor.to_list(length=1)
    card = card[0]

    context.user_data["current_card_id"] = str(card["_id"])
    context.user_data["current_answer"] = card["word"]

    await update.message.reply_text(
        f"🧠 Translate:\n\n**{card['translation']}**",
        parse_mode="Markdown"
    )


# -------------------- RUN --------------------

async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    count = await cards.count_documents({"user_id": user_id})

    if count == 0:
        await update.message.reply_text("📭 No words yet.")
        return

    random_index = random.randint(0, count - 1)

    cursor = cards.find({"user_id": user_id}).skip(random_index).limit(1)
    card = await cursor.to_list(length=1)
    card = card[0]

    await update.message.reply_text(
        f"{card['word']}  {card['translation']}"
    )


# -------------------- CHECK ANSWER --------------------

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "current_answer" not in context.user_data:
        return

    user_answer = update.message.text.strip()
    correct = context.user_data.pop("current_answer")
    card_id = context.user_data.pop("current_card_id")

    if user_answer.lower() == correct.lower():
        card = await cards.find_one_and_update(
            {"_id": ObjectId(card_id)},
            {"$inc": {"correct_count": 1}},
            return_document=ReturnDocument.AFTER
        )

        new_count = card["correct_count"]

        if new_count >= 6:
            await cards.delete_one({"_id": ObjectId(card_id)})
            await update.message.reply_text(
                "🎉 Correct!\n\nThis word is mastered and removed 🧠✨"
            )
        else:
            await update.message.reply_text(
                f"✅ Correct!\nProgress: {new_count}/6"
            )
    else:
        await update.message.reply_text(
            f"❌ Nope\nCorrect: **{correct}**",
            parse_mode="Markdown"
        )


# -------------------- DELETE --------------------

async def delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    result = await cards.delete_many({"user_id": user_id})

    if result.deleted_count == 0:
        await update.message.reply_text("📭 Nothing to delete.")
    else:
        await update.message.reply_text(
            f"🗑 Deleted {result.deleted_count} words."
        )


# -------------------- ERROR HANDLER --------------------

async def error_handler(update, context):
    print(f"Exception: {context.error}")


# -------------------- MAIN --------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_card))
    app.add_handler(CommandHandler("study", study))
    app.add_handler(CommandHandler("run", run))
    app.add_handler(CommandHandler("delete", delete_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

    app.add_error_handler(error_handler)

    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
