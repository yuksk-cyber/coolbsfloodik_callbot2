import asyncio
import random
import json
import os
import time
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ChatMemberUpdated, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.enums.chat_member_status import ChatMemberStatus
import emoji

API_TOKEN = "7807614014:AAGrbnnjYmW9whJtk2LxBBXg_I0nAfl5e8Y"
ADMIN_PASSWORD = "secret54993245"

EMOJI_FILE = "group_emojis.json"
USER_DB_FILE = "group_users.json"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

emoji_pool = list(emoji.EMOJI_DATA.keys())
pending_password = set()
awaiting_broadcast = set()
bot_enabled = True
last_call_time = {}

if os.path.exists(EMOJI_FILE):
    with open(EMOJI_FILE, "r", encoding="utf-8") as f:
        group_emojis = json.load(f)
else:
    group_emojis = {}

if os.path.exists(USER_DB_FILE):
    with open(USER_DB_FILE, "r", encoding="utf-8") as f:
        group_users = json.load(f)
else:
    group_users = {}

def save_emojis():
    with open(EMOJI_FILE, "w", encoding="utf-8") as f:
        json.dump(group_emojis, f, ensure_ascii=False, indent=2)

def save_users():
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(group_users, f, ensure_ascii=False, indent=2)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Переключить")],
        [KeyboardButton(text="📢 Разослать сообщение")],
        [KeyboardButton(text="❌️ Закрыть")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌️ Отмена")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

@dp.message()
async def handle_all_messages(message: Message):
    global bot_enabled

    user_id = str(message.from_user.id)
    chat_id = str(message.chat.id)
    text = (message.text or "").strip()

    # Рассылка
    if user_id in awaiting_broadcast:
        awaiting_broadcast.remove(user_id)
        await message.answer("📨 Рассылка запущена...", reply_markup=admin_kb)
        total = 0
        failed = 0
        for group in group_users.values():
            for uid in group:
                try:
                    await message.send_copy(chat_id=int(uid))
                    total += 1
                    await asyncio.sleep(0.05)
                except:
                    failed += 1
        await message.answer(f"📨 <b>Рассылка завершена.</b>\n✅️ Успешно: {total}\n❌️ Ошибок: {failed}", parse_mode="HTML")
        return

    # Личные сообщения
    if message.chat.type == "private":
        if text == "/start":
            msg = "<b>🛠 Ведутся технические работы!</b>\nБот временно недоступен." if not bot_enabled else \
                  "👋 Привет! Я бот-зазывала. Добавь меня в группу и напиши 'Калл', чтобы созвать всех участников."
            await message.answer(msg, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
            return

        if text == "/admin":
            pending_password.add(user_id)
            await message.answer("🔒 Введите пароль для доступа к админ-панели:", reply_markup=cancel_kb)
            return

        if user_id in pending_password:
            if text == "❌️ Отмена":
                pending_password.remove(user_id)
                await message.answer("❌️ Ввод пароля отменён.", reply_markup=ReplyKeyboardRemove())
                return
            if text == ADMIN_PASSWORD:
                pending_password.remove(user_id)
                await message.answer("🔓 Пароль принят.", reply_markup=admin_kb)
            else:
                pending_password.remove(user_id)
                await message.answer("❌ Неверный пароль.", reply_markup=ReplyKeyboardRemove())
            return

        if text == "📊 Статистика":
            total_groups = len(group_users)
            lines = [f"🛠 <b>Статистика бота</b>", f"Всего групп: {total_groups}"]
            for cid, users in group_users.items():
                lines.append(f"\n<b>Группа:</b> <code>{cid}</code>")
                lines.append(f"👥 Пользователей: {len(users)}")
            await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_kb)
            return

        if text == "⚙️ Переключить":
            bot_enabled = not bot_enabled
            status = "включён" if bot_enabled else "выключен"
            await message.answer(f"⚙️ Бот теперь <b>{status}</b>.", parse_mode="HTML", reply_markup=admin_kb)
            return

        if text == "📢 Разослать сообщение":
            awaiting_broadcast.add(user_id)
            await message.answer("✉️ Отправьте сообщение, которое нужно разослать всем пользователям.", reply_markup=cancel_kb)
            return

        if text == "❌️ Закрыть":
            await message.answer("🔒 Панель админа закрыта.", reply_markup=ReplyKeyboardRemove())
            return

    # Группы
    if message.chat.type not in ["group", "supergroup"]:
        return

    if not bot_enabled:
        return

    group_users.setdefault(chat_id, {})
    group_emojis.setdefault(chat_id, {})

    newly_registered = False
    if user_id not in group_users[chat_id]:
        group_users[chat_id][user_id] = {
            "id": message.from_user.id,
            "full_name": message.from_user.full_name,
            "username": message.from_user.username
        }
        newly_registered = True

    if user_id not in group_emojis[chat_id]:
        used_emojis = set(group_emojis[chat_id].values())
        available = [e for e in emoji_pool if e not in used_emojis]
        chosen = random.choice(available) if available else random.choice(emoji_pool)
        group_emojis[chat_id][user_id] = chosen
        newly_registered = True

    if newly_registered:
        save_users()
        save_emojis()

    if text.lower() == "чанджми":
        used_emojis = set(group_emojis[chat_id].values())
        current_emoji = group_emojis[chat_id].get(user_id)
        available = [e for e in emoji_pool if e not in used_emojis or e == current_emoji]
        if len(available) <= 1:
            available = [e for e in emoji_pool if e != current_emoji]
        new_emoji = random.choice(available) if available else current_emoji
        group_emojis[chat_id][user_id] = new_emoji
        save_emojis()
        await message.answer(f"Твоё эмодзи изменено на {new_emoji}", reply_markup=ReplyKeyboardRemove())
        return

    if text.lower() == "ми":
        current_emoji = group_emojis[chat_id].get(user_id)
        if current_emoji:
            await message.answer(f"Твоё текущее эмодзи: {current_emoji}", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer("У тебя пока нет эмодзи.", reply_markup=ReplyKeyboardRemove())
        return

    if not text.lower().startswith("калл"):
        return

    now = time.time()
    last_time = last_call_time.get(chat_id, 0)
    if now - last_time < 30:
        remain = int(30 - (now - last_time))
        await message.answer(f"⏳ Подождите {remain} секунд перед следующим созывом.", reply_markup=ReplyKeyboardRemove())
        return
    last_call_time[chat_id] = now

    emojified_mentions = []
    for uid in group_users[chat_id]:
        if uid not in group_emojis[chat_id]:
            continue
        try:
            member = await bot.get_chat_member(chat_id, int(uid))
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                continue
        except:
            continue
        emoji_char = group_emojis[chat_id][uid]
        emojified_mentions.append(f'<a href="tg://user?id={uid}">{emoji_char}</a>')

    parts = text.split(maxsplit=1)
    extra_text = parts[1] if len(parts) > 1 else None
    sender_link = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a> запустил(-а) призыв.'

    chunk_size = 40
    for i in range(0, len(emojified_mentions), chunk_size):
        lines = []
        if i == 0:
            lines.append(sender_link)
            lines.append("")
            if extra_text:
                lines.append(extra_text)
                lines.append("")
        lines.append(" ".join(emojified_mentions[i:i + chunk_size]))
        await message.answer("\n".join(lines), parse_mode="HTML")
        await asyncio.sleep(1)

@dp.chat_member(ChatMemberUpdatedFilter(member_status_changed=True))
async def handle_left_user(event: ChatMemberUpdated):
    chat_id = str(event.chat.id)
    user_id = str(event.from_user.id)

    if event.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
        if chat_id in group_users and user_id in group_users[chat_id]:
            del group_users[chat_id][user_id]
            save_users()
        if chat_id in group_emojis and user_id in group_emojis[chat_id]:
            del group_emojis[chat_id][user_id]
            save_emojis()

async def sync_group_members_periodically():
    while True:
        try:
            for chat_id_str in list(group_users.keys()):
                chat_id = int(chat_id_str)
                try:
                    admins = await bot.get_chat_administrators(chat_id)
                except Exception as e:
                    if "chat not found" in str(e).lower() or "bot was kicked" in str(e).lower():
                        group_users.pop(chat_id_str, None)
                        group_emojis.pop(chat_id_str, None)
                        save_users()
                        save_emojis()
                    continue
                real_ids = set(str(member.user.id) for member in admins)
                stored_ids = set(group_users.get(chat_id_str, {}).keys())
                to_remove = stored_ids - real_ids
                for uid in to_remove:
                    group_users[chat_id_str].pop(uid, None)
                    group_emojis[chat_id_str].pop(uid, None)
                if to_remove:
                    save_users()
                    save_emojis()
        except Exception as e:
            print("Ошибка при синхронизации:", e)
        await asyncio.sleep(3600)

async def main():
    print("Бот запущен.")
    asyncio.create_task(sync_group_members_periodically())
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())