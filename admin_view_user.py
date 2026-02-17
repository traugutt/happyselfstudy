import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

MONGO_URI = os.getenv("MONGO_URI")

async def view_user(username):
    mongo = AsyncIOMotorClient(MONGO_URI)
    db = mongo.telegram_vocab_bot
    cards = db.cards
    users = db.users

    # Find user
    user = await users.find_one({"username": username})

    if not user:
        print("❌ User not found.")
        return

    user_id = user.get("user_id")

    print(f"\n📚 Words for @{username}")
    print("=" * 40)

    # Fetch cards
    user_cards = await cards.find({"user_id": user_id}).to_list(length=1000)

    if not user_cards:
        print("📭 No words found.")
        return

    for i, card in enumerate(user_cards, 1):
        print(
            f"{i}. {card['word']} → {card['translation']} "
            f"({card['correct_count']}/6)"
        )

    print("\nTotal:", len(user_cards))


if __name__ == "__main__":
    username = input("Enter username (without @): ").strip()
    asyncio.run(view_user(username))

