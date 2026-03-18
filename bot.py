import asyncio
import json
import os
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Token va ADMIN_ID ni environment variables orqali olamiz
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7669524820:AAFlY0g5h_MQXUSHrzbHBY44Oh5yGvapgwI") 
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1925985144"))
STATS_FILE = "stats.json"

# ============================================================
# HAQORAT SO'ZLAR RO'YXATI
# ============================================================
WORDS_FILE = "bad_words.json"

DEFAULT_BAD_WORDS = [
    "ahmoq", "tentak", "nodon", "eshak", "it", "cho'chqa", "lalaydi",
    "ovsar", "bema'ni", "yaramas", "buzuq", "iflos", "past", "tuban",
    "beadab", "nomard", "qo'rqoq", "yolg'onchi", "firibgar", "munofiq",
    "xoin", "sotqin", "dangasa", "bekor", "ishyoqmas", "bechor", "baxtsiz",
    "aqilsiz", "johil", "g'o'l", "kalvak", "devona", "g'irt", "harom",
    "kazzob", "makkor", "razil", "pastkash", "sharmanda", "uyatsiz",
    "badfe'l", "qabih", "zalim", "zolim", "bedod", "benomus", "behayo",
    "besharm", "beor", "betamiz", "axmoq", "manfur", "mufsid", "fasiq",
    "vahshi", "yirtqich", "murdor", "najas", "nopok", "badniyat",
    "befahm", "bexosiyat", "beoqibat", "beqadr", "berahm", "beshafqat",
    "gumroh", "zalil", "ojiz", "nochor", "notavon", "sustkash",
    # Rus
    "дурак", "идиот", "тупой", "урод", "скотина", "свинья", "осёл",
    "баран", "козёл", "сволочь", "мерзавец", "негодяй", "подлец",
    "трус", "лжец", "жулик", "мошенник", "лицемер", "предатель",
    "бестолочь", "олух", "болван", "ничтожество", "бездарь", "неудачник",
    "durak", "idiot", "tupoy", "urod", "skotina", "svinya",
    "baran", "kozyol", "svoloch", "merzavec", "negodyay", "podlec",
    # Ingliz
    "stupid", "idiot", "moron", "fool", "dumb", "loser", "trash",
    "worthless", "pathetic", "ugly", "useless", "failure", "coward",
    "liar", "cheat", "hypocrite", "traitor", "lazy", "incompetent",
    "ignorant", "jerk", "creep", "freak", "disgrace", "shameful",
    "horrible", "terrible", "awful", "nasty", "vile", "cruel",
    "hopeless", "clueless", "brainless", "mindless", "spineless",
    "heartless", "ruthless", "selfish", "greedy", "arrogant",
]

def load_bad_words():
    if os.path.exists(WORDS_FILE):
        with open(WORDS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set(DEFAULT_BAD_WORDS)

def save_bad_words(words_set):
    with open(WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(words_set), f, ensure_ascii=False, indent=2)

BAD_WORDS = load_bad_words()

# ============================================================
# STATISTIKA VA XOTIRA
# ============================================================
LAST_REPORT_FILE = "last_report.txt"

def get_last_report_date():
    if os.path.exists(LAST_REPORT_FILE):
        with open(LAST_REPORT_FILE, "r") as f:
            return f.read().strip()
    return ""

def set_last_report_date(date_str):
    with open(LAST_REPORT_FILE, "w") as f:
        f.write(date_str)
def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_stats(data):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_stats(user_id, username, full_name, chat_id, chat_name, chat_type, words):
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {
            "username": username,
            "full_name": full_name,
            "total_violations": 0,
            "chats": {},
            "words_used": {},
            "last_violation": ""
        }
    stats[uid]["total_violations"] += 1
    stats[uid]["last_violation"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    stats[uid]["username"] = username
    stats[uid]["full_name"] = full_name

    cid = str(chat_id)
    if cid not in stats[uid]["chats"]:
        stats[uid]["chats"][cid] = {"name": chat_name, "type": chat_type, "count": 0}
    stats[uid]["chats"][cid]["count"] += 1

    for w in words:
        stats[uid]["words_used"][w] = stats[uid]["words_used"].get(w, 0) + 1

    save_stats(stats)

# ============================================================
# BOT
# ============================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def find_bad_words(text: str):
    t = text.lower()
    found = []
    for w in BAD_WORDS:
        # Har bir harf kamida 1 marta takrorlanishiga ruxsat beramiz (masalan: ahmmooqq)
        pattern = "".join([f"{re.escape(c)}+" for c in w])
        if re.search(pattern, t):
            found.append(w)
    return found

async def send_alert(chat_title, chat_id, chat_type, user_id,
                     username, full_name, found, text,
                     phone_number="Noma'lum",
                     chat_link="Noma'lum",
                     message_link="Noma'lum"):
    """Adminga xabar yuborish"""
    type_emoji = {"channel": "📢", "supergroup": "👥", "group": "👥"}.get(chat_type, "💬")
    
    # Chat nomi va linki
    chat_display = f"<a href='{chat_link}'>{chat_title}</a>" if chat_link != "Noma'lum" else f"<b>{chat_title}</b>"
    # Telegram odatda userni telefon raqamini yashiradi va faqat u botga ulashsa "contact" type orqali keladi.
    # Lekin ba'zi Premium userlarda yopilmagan bo'lsa yoki bazada bo'lsa qidirishga harakat qilamiz
    # Asosan bu narsa faqat Contact sifatida yuborilgan mesajda bo'ladi, doimiy messages ichida emas.
    # Uning uchun Telegram API 'user' obyektida telefon raqam qaytarmaydi :( (Faqat id, ism, username, premium mavjud).
    
    info = (
        f"⚠️ <b>Haqorat aniqlandi!</b>\n\n"
        f"{type_emoji} Tur: <b>{chat_type}</b>\n"
        f"📌 Nomi: {chat_display}\n"
        f"🔗 Chat Link: {chat_link}\n"
        f"🆔 Chat ID: <code>{chat_id}</code>\n"
        f"👤 User: <b>{full_name}</b>\n"
        f"🔗 Username: @{username or 'yoq'}\n"
        f"📞 Telefon: <b>{phone_number}</b>\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"🚫 So'zlar: <code>{', '.join(found)}</code>\n"
        f"🕐 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"💬 Xabar/Nomi:\n<i>{text[:400]}</i>"
    )
    
    kb = InlineKeyboardBuilder()
    if message_link != "Noma'lum":
        kb.button(text="➡️ Xabarga o'tish", url=message_link)
    kb.button(text="📊 Bu userni ko'rish", callback_data=f"ustats_{user_id}")
    await bot.send_message(ADMIN_ID, info, parse_mode="HTML",
                           reply_markup=kb.as_markup())

# ============================================================
# GURUH VA YOPIQ GURUH XABARLARI
# ============================================================
@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def monitor_group(message: Message):
    # Ovozli xabarni qabul qilish (ovozli nomi yoki caption'i bo'lishi mumkin)
    text = ""
    if message.text:
        text = message.text
    elif message.caption:
        text = message.caption
    elif message.audio and message.audio.file_name:
        text = message.audio.file_name
    elif message.voice:
        # Voice (ovozli xabar) larning ichini text qilib o'qish imkonsiz (Speech2Text kerak).
        # Hozircha uning caption bo'lsa shuni oladi. 
        pass
        
    if not text:
        return
    found = find_bad_words(text)
    if not found:
        return
        
    user = message.from_user
    phone = "Yashirin"
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
        
    chat_link = "Noma'lum"
    if message.chat.username:
        chat_link = f"https://t.me/{message.chat.username}"
    elif message.chat.invite_link:
        chat_link = message.chat.invite_link
        
    msg_link = "Noma'lum"
    if message.chat.username:
        msg_link = f"https://t.me/{message.chat.username}/{message.message_id}"
    elif message.chat.type == "supergroup":
        # Yopiq supergrouplar uchtalik ID bilan boshlanadigan link ishlatishadi. -100 idisni tekislaymiz
        clean_id = str(message.chat.id)[4:] if str(message.chat.id).startswith("-100") else str(message.chat.id)
        msg_link = f"https://t.me/c/{clean_id}/{message.message_id}"
        
    update_stats(user.id, user.username, user.full_name,
                 message.chat.id, message.chat.title,
                 message.chat.type, found)
    await send_alert(message.chat.title, message.chat.id,
                     message.chat.type, user.id,
                     user.username, user.full_name, found, text,
                     phone, chat_link, msg_link)

# ============================================================
# KANAL POSTLARI
# ============================================================
@dp.channel_post()
async def monitor_channel(message: Message):
    text = message.text or message.caption or ""
    if not text:
        return
    found = find_bad_words(text)
    if not found:
        return
        
    # Kanal postida user bo'lmaydi (admin yozadi)
    info = (
        f"⚠️ <b>Kanalda haqorat!</b>\n\n"
        f"📢 Kanal: <b>{message.chat.title}</b>\n"
        f"🆔 Kanal ID: <code>{message.chat.id}</code>\n"
        f"🚫 So'zlar: <code>{', '.join(found)}</code>\n"
        f"🕐 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"💬 Post:\n<i>{text[:400]}</i>"
    )
    await bot.send_message(ADMIN_ID, info, parse_mode="HTML")

# ============================================================
# BOT GURUHGA QO'SHILGANDA XABAR
# ============================================================
@dp.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def bot_added(event: ChatMemberUpdated):
    chat = event.chat
    chat_type = chat.type
    type_text = {
        "channel": "Kanal",
        "supergroup": "Yopiq/Ochiq guruh",
        "group": "Guruh"
    }.get(chat_type, chat_type)

    info = (
        f"✅ <b>Bot yangi joyga qo'shildi!</b>\n\n"
        f"📌 Nomi: <b>{chat.title}</b>\n"
        f"🆔 ID: <code>{chat.id}</code>\n"
        f"📂 Tur: <b>{type_text}</b>\n"
        f"🕐 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await bot.send_message(ADMIN_ID, info, parse_mode="HTML")

# ============================================================
# STATISTIKA BUYRUQLARI
# ============================================================
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = load_stats()
    if not stats:
        await message.answer("📊 Hali statistika yo'q.")
        return
    sorted_users = sorted(stats.items(),
                          key=lambda x: x[1]["total_violations"],
                          reverse=True)
    text = "📊 <b>Top 10 qoidabuzarlar</b>\n\n"
    for i, (uid, d) in enumerate(sorted_users[:10], 1):
        text += (f"{i}. <b>{d['full_name']}</b> (@{d['username'] or 'yoq'})\n"
                 f"   Jami: <b>{d['total_violations']}</b> | "
                 f"Oxirgi: {d['last_violation']}\n\n")
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("top"))
async def cmd_top(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = load_stats()
    if not stats:
        await message.answer("Ma'lumot yo'q.")
        return
    sorted_users = sorted(stats.items(),
                          key=lambda x: x[1]["total_violations"],
                          reverse=True)[:5]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    text = "🏆 <b>Top 5 qoidabuzarlar</b>\n\n"
    for i, (_, d) in enumerate(sorted_users):
        text += f"{medals[i]} <b>{d['full_name']}</b> — {d['total_violations']} ta\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("chats"))
async def cmd_chats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = load_stats()
    all_chats = {}
    for uid, d in stats.items():
        for cid, c in d["chats"].items():
            if cid not in all_chats:
                all_chats[cid] = {"name": c["name"], "type": c["type"], "total": 0}
            all_chats[cid]["total"] += c["count"]
    if not all_chats:
        await message.answer("Chat ma'lumotlari yo'q.")
        return
    text = "📋 <b>Barcha kuzatiladigan chatlar</b>\n\n"
    for cid, c in sorted(all_chats.items(),
                         key=lambda x: x[1]["total"], reverse=True):
        emoji = "📢" if c["type"] == "channel" else "👥"
        text += f"{emoji} <b>{c['name']}</b> — {c['total']} ta holat\n"
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("topwords"))
async def cmd_topwords(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    stats = load_stats()
    if not stats:
        await message.answer("Ma'lumot yo'q.")
        return
        
    global_words = {}
    for uid, d in stats.items():
        for w, count in d.get("words_used", {}).items():
            global_words[w] = global_words.get(w, 0) + count
            
    if not global_words:
        await message.answer("Hali hech qanday haqorat so'z qayd etilmagan.")
        return
        
    sorted_words = sorted(global_words.items(), key=lambda x: x[1], reverse=True)[:10]
    
    text = "🔥 <b>Barcha guruhlar bo'yicha eng ko'p ishlatilgan 10 ta haqorat:</b>\n\n"
    for i, (w, count) in enumerate(sorted_words, 1):
        text += f"{i}. <b>{w}</b> — {count} marta\n"
        
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data.startswith("ustats_"))
async def cb_user_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    uid = callback.data.split("_")[1]
    stats = load_stats()
    if uid not in stats:
        await callback.answer("Ma'lumot yo'q", show_alert=True)
        return
    d = stats[uid]
    top_words = sorted(d["words_used"].items(),
                       key=lambda x: x[1], reverse=True)[:5]
    chats_text = "\n".join(
        f"   • {c['name']} ({c['type']}): {c['count']} ta"
        for c in d["chats"].values()
    )
    words_text = ", ".join(f"{w}({n})" for w, n in top_words)
    text = (
        f"👤 <b>{d['full_name']}</b> (@{d['username'] or 'yoq'})\n\n"
        f"📊 Jami: <b>{d['total_violations']}</b>\n"
        f"🕐 Oxirgi: {d['last_violation']}\n\n"
        f"📌 Chatlar:\n{chats_text}\n\n"
        f"🔤 Ko'p so'zlar: {words_text}"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.message(Command("addword"))
async def cmd_addword(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if not args:
        await message.answer("❌ Qaysi so'zni qo'shmoqchisiz? Format: /addword so'z", parse_mode="HTML")
        return
    word = args[0].lower()
    if word in BAD_WORDS:
        await message.answer(f"⚠️ <b>{word}</b> ro'yxatda allaqachon mavjud.", parse_mode="HTML")
        return
    BAD_WORDS.add(word)
    save_bad_words(BAD_WORDS)
    await message.answer(f"✅ <b>{word}</b> haqoratli so'zlar ro'yxatiga qo'shildi.", parse_mode="HTML")

@dp.message(Command("removeword"))
async def cmd_removeword(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if not args:
        await message.answer("❌ Qaysi so'zni o'chirmoqchisiz? Format: /removeword so'z", parse_mode="HTML")
        return
    word = args[0].lower()
    if word not in BAD_WORDS:
        await message.answer(f"⚠️ <b>{word}</b> ro'yxatda topilmadi.", parse_mode="HTML")
        return
    BAD_WORDS.remove(word)
    save_bad_words(BAD_WORDS)
    await message.answer(f"✅ <b>{word}</b> haqoratli so'zlar ro'yxatidan o'chirildi.", parse_mode="HTML")

from aiogram.types import BotCommand

async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="stats", description="Top 10 qoidabuzarlar"),
        BotCommand(command="top", description="Top 5 qoidabuzarlar"),
        BotCommand(command="chats", description="Kuzatilayotgan chatlar"),
        BotCommand(command="topwords", description="Eng ko'p ishlatilgan so'zlar"),
        BotCommand(command="addword", description="Yangi haqorat so'z qo'shish"),
        BotCommand(command="removeword", description="Haqorat ro'yxatidan so'z olib tashlash"),
    ]
    await bot.set_my_commands(commands)

async def daily_report_task():
    """Har 1 soatda vaqtni tekshirib, 22:00 da (O'zbekiston vaqti bilan UTC+5) xabar yuboradi"""
    while True:
        try:
            # Hozirgi Local vaqt (Server vaqti O'zbekiston yoki UTC bo'lishi mumkinligi uchun aniqlashtirish kerak)
            # Render odatda UTC da ishlaydi. UTC ga 5 soat qo'shib tekshiramiz.
            now = datetime.utcnow()
            hour_uz = (now.hour + 5) % 24  # O'zbekiston vaqti
            date_uz = datetime.now().strftime("%Y-%m-%d")
            
            # Agar soat 22 (yoki undan keyin) bo'lsa va bugun hali report tashlanmagan bo'lsa
            if hour_uz >= 22 and get_last_report_date() != date_uz:
                stats = load_stats()
                if stats:
                    # Kunlik qisqa report
                    total_violators = len(stats)
                    total_violations = sum(d["total_violations"] for d in stats.values())
                    
                    text = (
                        f"📊 <b>KUNLIK HISOBOT ({date_uz})</b>\n\n"
                        f"Jami qoidabuzarlar: <b>{total_violators} ta</b>\n"
                        f"Jami haqoratlar qayd etildi: <b>{total_violations} marta</b>\n\n"
                        f"Batafsil ma'lumot uchun /top yoki /stats komandalarini bering."
                    )
                    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
                    set_last_report_date(date_uz)
        except Exception as e:
            print(f"Daily report xatoligi: {e}")
            
        await asyncio.sleep(3600)  # Har soatda tekshirish

# ============================================================
# ISHGA TUSHIRISH
# ============================================================
async def main():
    print("✅ Bot ishga tushdi!")
    await set_default_commands(bot)
    
    # Background vazifani ishga tushirish (Kunlik report)
    asyncio.create_task(daily_report_task())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
