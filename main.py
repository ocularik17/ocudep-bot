from keep_alive import keep_alive
keep_alive()

import telebot
from telebot import types
import sqlite3
import random
import time

BOT_TOKEN = "твой_токен"
CREATOR_ID = 1197889640
ADMIN_PASSWORD = "qwerty"

bot = telebot.TeleBot(BOT_TOKEN)

conn = sqlite3.connect("ocudep.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        nickname TEXT,
        points INTEGER DEFAULT 0
    )
""")
conn.commit()

user_states = {}
cooldowns = {}

def get_rank(points):
    if points < 1000:
        return "Новичок"
    elif points < 5000:
        return "Бывалый"
    elif points < 15000:
        return "Эксперт"
    elif points < 40000:
        return "Мастер"
    elif points < 80000:
        return "Гуру"
    else:
        return "Бог"
    
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        send_main_menu(message.chat.id)
    else:
        bot.send_message(message.chat.id, "👋 Добро пожаловать! Введи свой ник:")
        user_states[user_id] = "awaiting_nickname"

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📄 Профиль", "🎰 Рулетка")
    markup.row("📈 Лидерборд", "⚙️ Настройки")
    markup.row("🔒 Админ")
    bot.send_message(chat_id, "📍 Главное меню:", reply_markup=markup)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_nickname")
def handle_nickname(message):
    nickname = message.text.strip()
    user_id = message.from_user.id
    cursor.execute("INSERT INTO users (user_id, nickname) VALUES (?, ?)", (user_id, nickname))
    conn.commit()
    user_states.pop(user_id, None)
    bot.send_message(CREATOR_ID, f"🆕 Новый пользователь: {nickname} ({user_id})")
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "📄 Профиль")
def show_profile(message):
    user_id = message.from_user.id
    cursor.execute("SELECT nickname, points FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        nickname, points = user
        rank = get_rank(points)
        bot.send_message(message.chat.id, f"👤 Ник: {nickname}\n💰 Очки: {points}\n🏅 Ранг: {rank}")
    else:
        bot.send_message(message.chat.id, "❌ Ты не зарегистрирован.")

@bot.message_handler(func=lambda m: m.text == "🎰 Рулетка")
def ruletka_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("- Депнуть", "- Додеп", "- Ливнуть")
    bot.send_message(message.chat.id, "🎰 Выбери действие:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["- Депнуть", "- Додеп"])
def handle_deposit(message):
    user_id = message.from_user.id
    now = time.time()
    if cooldowns.get(user_id, 0) > now:
        bot.send_message(message.chat.id, "⏳ Подожди немного перед следующей попыткой.")
        return
    cooldowns[user_id] = now + 3

    frames = ["🎰 ▓▓▓", "🎰 ▒▒▒", "🎰 ░░░", "🎰 🎉🎉🎉"]
    for frame in frames:
        bot.send_message(message.chat.id, frame)
        time.sleep(0.5)

    result = random.randint(50, 500)
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (result, user_id))
    conn.commit()
    bot.send_message(message.chat.id, f"🎉 Ты получил {result} очков!")
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "📈 Лидерборд")
def show_leaderboard(message):
    cursor.execute("SELECT nickname, points FROM users ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()
    text = "🏆 Топ-10 игроков:\n\n"
    for i, (nickname, points) in enumerate(top_users, start=1):
        rank = get_rank(points)
        text += f"{i}. {nickname} — {points} очков ({rank})\n"
    bot.send_message(message.chat.id, text)

    return
@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def settings_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✏️ Сменить ник", "- Ливнуть")
    bot.send_message(message.chat.id, "⚙️ Настройки:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✏️ Сменить ник")
def change_nickname(message):
    bot.send_message(message.chat.id, "📝 Введи новый ник:")
    user_states[message.from_user.id] = "awaiting_nickname"

@bot.message_handler(func=lambda m: m.text == "🔒 Админ")
def admin_entry(message):
    bot.send_message(message.chat.id, "🔐 Введи пароль:")
    user_states[message.from_user.id] = "awaiting_password"

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_password")
def handle_admin_password(message):
    user_id = message.from_user.id
    if message.text == ADMIN_PASSWORD:
        user_states[user_id] = "admin_panel"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📋 Управление", "🚫 Забанить")
        markup.row("- Ливнуть")
        bot.send_message(message.chat.id, "✅ Админ доступ открыт:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Неверный пароль.")
        user_states.pop(user_id, None)

@bot.message_handler(func=lambda m: m.text == "📋 Управление")
def admin_manage(message):
    bot.send_message(message.chat.id, "👤 Введи ник пользователя:")
    user_states[message.from_user.id] = "admin_select_user"

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "admin_select_user")
def admin_select_user(message):
    nickname = message.text.strip()
    cursor.execute("SELECT user_id FROM users WHERE nickname = ?", (nickname,))
    result = cursor.fetchone()
    if result:
        user_states[message.from_user.id] = f"admin_balance_change:{result[0]}"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("+100", "+200", "-100", "-200")
        markup.row("✏️ Ввести вручную", "- Ливнуть")
        bot.send_message(message.chat.id, f"💰 Управление очками для {nickname}:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден.")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, "").startswith("admin_balance_change:"))
def admin_change_balance(message):
    admin_id = message.from_user.id
    target_id = int(user_states[admin_id].split(":")[1])
    delta = 0
    if message.text == "+100":
        delta = 100
    elif message.text == "+200":
        delta = 200
    elif message.text == "-100":
        delta = -100
    elif message.text == "-200":
        delta = -200
    elif message.text == "✏️ Ввести вручную":
        bot.send_message(admin_id, "🔢 Введи новое значение:")
        user_states[admin_id] = f"admin_manual_balance:{target_id}"
        return
    else:
        bot.send_message(admin_id, "❌ Неизвестная команда.")
        return

    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (delta, target_id))
    conn.commit()
    bot.send_message(admin_id, f"✅ Баланс обновлён на {delta} очков.")
    user_states.pop(admin_id, None)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, "").startswith("admin_manual_balance:"))
def admin_manual_balance(message):
    admin_id = message.from_user.id
    target_id = int(user_states[admin_id].split(":")[1])
    try:
        new_value = int(message.text.strip())
        cursor.execute("UPDATE users SET points = ? WHERE user_id = ?", (new_value, target_id))
        conn.commit()
        bot.send_message(admin_id, f"✅ Баланс установлен: {new_value} очков.")
    except:
        bot.send_message(admin_id, "❌ Неверный формат.")
    user_states.pop(admin_id, None)

@bot.message_handler(func=lambda m: m.text == "🚫 Забанить")
def admin_ban(message):
    bot.send_message(message.chat.id, "👤 Введи ник для бана:")
    user_states[message.from_user.id] = "admin_ban_confirm"

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "admin_ban_confirm")
def handle_ban(message):
    nickname = message.text.strip()
    cursor.execute("SELECT user_id FROM users WHERE nickname = ?", (nickname,))
    result = cursor.fetchone()
    if result:
        cursor.execute("DELETE FROM users WHERE user_id = ?", (result[0],))
        conn.commit()
        bot.send_message(message.chat.id, f"🚫 Пользователь {nickname} забанен.")
    else:
        bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    user_states.pop(message.from_user.id, None)

@bot.message_handler(func=lambda m: m.text == "- Ливнуть")
def leave(message):
    user_states.pop(message.from_user.id, None)
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    allowed_states = [
        "awaiting_nickname",
        "awaiting_password",
        "admin_select_user",
        "admin_balance_change",
        "admin_ban_confirm",
        "admin_manual_balance"
    ]
    if state in allowed_states:
        return
    bot.send_message(message.chat.id, "🚫 Писать сюда нельзя. Используй кнопки.")

bot.polling()
