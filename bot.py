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

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.telegram_vocab_bot
cards = db.cards


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Welcome!\n\n"
        "Use:\n"
        "/add word = translation\n"
        "/study\n"
        "/run (go through all words and translations) \n"
        "/delete (delete all words, be careful with this one)\n"
    )


async def add_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.replace("/add", "").strip()

    if "=" not in text:
        await update.message.reply_text(
            "❌ Format:\n/add word = translation"
        )
        return

    word, translation = map(str.strip, text.split("=", 1))

    await cards.insert_one({
        "user_id": user_id,
        "word": word,
        "translation": translation,
        "correct_count": 0
    })

    await update.message.reply_text(f"✅ Added:\n{word} → {translation}")


async def study(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    docs = await cards.find({"user_id": user_id}).to_list(length=1000)

    if not docs:
        await update.message.reply_text("📭 No words yet.")
        return

    card = random.choice(docs)
    
    context.user_data["current_card_id"] = str(card["_id"])
    context.user_data["current_answer"] = card["word"]

    await update.message.reply_text(
        f"🧠 Translate:\n\n**{card['translation']}**",
        parse_mode="Markdown"
    )

async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    docs = await cards.find({"user_id": user_id}).to_list(length=1000)

    if not docs:
        await update.message.reply_text("📭 No words yet.")
        return

    card = random.choice(docs)
    
    context.user_data["current_card_id"] = str(card["_id"])
    context.user_data["current_answer"] = card["word"]

    await update.message.reply_text(
        f"{card['word']}  {card['translation']}",
        parse_mode="Markdown"
    )


async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "current_answer" not in context.user_data:
        return

    user_answer = update.message.text.strip()
    correct = context.user_data.pop("current_answer")
    card_id = context.user_data.pop("current_card_id")

    if user_answer.lower() == correct.lower():
        # increment counter
        card = await cards.find_one_and_update(
            {"_id": ObjectId(card_id)},
            {"$inc": {"correct_count": 1}},
            return_document=True
        )

        new_count = card["correct_count"] + 1

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

async def delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    result = await cards.delete_many({"user_id": user_id})

    if result.deleted_count == 0:
        await update.message.reply_text("📭 Nothing to delete.")
    else:
        await update.message.reply_text(
            f"🗑 Deleted {result.deleted_count} words."
        )



def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_card))
    app.add_handler(CommandHandler("study", study))
    app.add_handler(CommandHandler("run", run))
    app.add_handler(CommandHandler("delete", delete_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))

    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

